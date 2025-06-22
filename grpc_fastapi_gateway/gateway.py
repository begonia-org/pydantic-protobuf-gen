from typing import Annotated, AsyncGenerator, Awaitable, Callable, Tuple, TypeVar
import inspect
import json
import os
import logging
import sys
import importlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Type
from starlette.types import Send, Receive, Scope
from fastapi import Body, FastAPI, HTTPException, Query, Request, Response, WebSocket
from fastapi.responses import StreamingResponse

from pydantic import BaseModel, ValidationError
from sse_starlette import EventSourceResponse
from grpc_fastapi_gateway.context import GRPCServicerContextAdapter
from grpc_fastapi_gateway.patch import patch_h2_protocol
from grpc_fastapi_gateway.response import BaseHttpResponse
from grpc_fastapi_gateway.typings import LoggerType
from grpc_fastapi_gateway.utils import RequestToGrpc

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

logger = logging.getLogger(__name__)

patch_h2_protocol()


def endpoint_generic_decorator(
    response_cls: Type[OutputT],
    service_method: Callable[[InputT], Awaitable[BaseHttpResponse[OutputT]]],
) -> Callable[
    [Callable[[InputT], Awaitable[BaseHttpResponse[OutputT]]]],
    Callable[[InputT], Awaitable[BaseHttpResponse[OutputT]]],
]:
    async def endpoint_generic(
        ctx: Request,
        response: Response,
        request,
    ) -> BaseHttpResponse[OutputT]:
        context = GRPCServicerContextAdapter(ctx, response)
        rsp = await service_method(request.to_protobuf(), context)
        data = response_cls.from_protobuf(rsp)
        response.headers.update(context.trailing_metadata())
        return BaseHttpResponse[OutputT](code=0, message="success", data=data)

    return endpoint_generic


def sse_endpoint_generic_decorator(
    response_cls: Type[OutputT],
    service_method: Callable[[InputT], AsyncGenerator[str, OutputT]],
) -> Callable[
    [Callable[[InputT], AsyncGenerator[str, OutputT]]],
    Callable[[InputT], EventSourceResponse],
]:
    async def sse_endpoint_generic(
        ctx: Request, response: Response, request
    ) -> EventSourceResponse:
        async def async_to_json(rsp: AsyncGenerator[str, OutputT]):
            async for r in rsp:
                yield json.dumps(
                    response_cls.from_protobuf(r).model_dump(), ensure_ascii=False
                )
            return

        context = GRPCServicerContextAdapter(ctx, response)
        return EventSourceResponse(
            async_to_json(service_method(request, context)),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    return sse_endpoint_generic


def websocket_endpoint_generic_decorator(
    request_cls: Type[InputT],
    response_cls: Type[OutputT],
    service_method: Callable[[InputT], AsyncGenerator[str, OutputT]],
    is_webscoket=False,
) -> Callable[
    [Callable[[InputT], AsyncGenerator[str, OutputT]]],
    Callable[[InputT], EventSourceResponse],
]:
    async def websocket_endpoint(
        websocket: WebSocket,
    ) -> AsyncGenerator[OutputT, None]:
        try:
            ws = websocket
            await ws.accept()

            async def async_to_pb():
                async for message in ws.iter_text():
                    request_obj = json.loads(message)
                    request = request_cls.model_validate(request_obj)
                    print(f"WebSocket Request data: {request}")
                    yield request.to_protobuf()

            context = GRPCServicerContextAdapter(websocket, None)
            # rsp = await service_method(async_to_pb, context)
            async for r in service_method(async_to_pb(), context):
                data = response_cls.from_protobuf(r)
                print(f"WebSocket Response data: {data}")
                await ws.send_json(data.model_dump())
        except Exception as e:
            import traceback

            traceback.print_exc()
            raise ValueError(f"Error processing WebSocket message: {str(e)}") from e
        finally:
            await websocket.close()

    async def bidirectional_streaming_endpoint(request: Request):
        async def process_stream():
            context = GRPCServicerContextAdapter(request, None)

            async def _to_pb():
                async for chunk in request.stream():
                    if chunk:
                        print(f"Received chunk: {chunk.decode()}")
                        try:
                            data = json.loads(chunk.decode())
                            yield request_cls.model_validate(data).to_protobuf()
                        except json.JSONDecodeError:
                            print(f"Invalid JSON data: {chunk.decode()}")

            async for r in service_method(_to_pb(), context):
                data = response_cls.from_protobuf(r)
                yield json.dumps(data.model_dump(), ensure_ascii=False)

        return StreamingResponse(
            process_stream(),
            media_type="application/octet-stream",
        )

    if is_webscoket:
        return websocket_endpoint
    else:
        return bidirectional_streaming_endpoint


class Gateway:
    def __init__(
        self,
        fastapi_app: FastAPI,
        service_groups: Dict[str, List[object]],
        models_dir: str,
        pb_dir: str,
        logger: Optional[LoggerType] = logging.getLogger(__name__),
        debug: bool = False,
    ):
        """
        Initialize the Gateway with FastAPI app, services, models directory, and protobuf directory.
        Args:
            fastapi_app: FastAPI application instance
            service_groups: A dictionary of service group and their corresponding service instances
            models_dir: Directory containing the Pydantic model definitions
            pb_dir: Directory containing the protobuf definitions
            logger: Optional logger instance for logging
            debug: Enable debug logging if True
        """
        self.fastapi_app = fastapi_app
        self.service_groups = service_groups
        self._models_dir = models_dir
        self._pb_dir = pb_dir
        self._services: Dict[str, Dict[str, Any]] = {}
        self.logger = logger or logging.getLogger(__name__)
        self.debug = debug
        if hasattr(self.logger, "setLevel"):
            self.logger.setLevel(logging.DEBUG if debug else logging.INFO)

    def _scan_and_import_class_safe(
        self, directory: str, class_name: str
    ) -> Optional[Type]:
        """
        Scan a directory for Python files and import a class by name.
        """
        import importlib.util
        import inspect

        directory = Path(directory)

        if not directory.exists() or not directory.is_dir():
            raise ValueError(
                f"Directory {directory} does not exist or is not a directory."
            )

        for py_file in directory.glob("**/*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                # Generate a unique module name to avoid conflicts
                module_name = f"temp_module_{py_file.stem}_{id(py_file)}"

                spec = importlib.util.spec_from_file_location(module_name, py_file)

                if spec is None or spec.loader is None:
                    continue

                module = importlib.util.module_from_spec(spec)

                # Set module attributes to mimic a normal import
                module.__file__ = str(py_file)
                module.__package__ = None  # Set package to None for isolated execution

                # Execute the module to load it
                spec.loader.exec_module(module)

                if hasattr(module, class_name):
                    cls = getattr(module, class_name)
                    if inspect.isclass(cls):
                        return cls

            except Exception as e:
                self.logger.error(f"Error importing from {py_file}: {e}")
                continue

        return None

    def _scan_and_import_class(
        self, package_dir: str, class_name: str
    ) -> Optional[Type]:
        """
        Scan a directory for Python packages and import a class by name.
        """

        package_dir = Path(package_dir)

        if not package_dir.exists() or not package_dir.is_dir():
            raise ValueError(f"Package directory {package_dir} does not exist.")

        # check if the directory is a valid package
        if not (package_dir / "__init__.py").exists():
            self.logger.warning(
                f"{package_dir} doesn't contain __init__.py, not a valid package"
            )
            return self._scan_and_import_class_safe(str(package_dir), class_name)

        parent_dir = package_dir.parent
        package_name = package_dir.name

        # add parent directory to sys.path if not already present
        original_path = sys.path.copy()
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))

        try:
            # import the package
            package = importlib.import_module(package_name)

            # Recursive function to search for the class in the package and its submodules
            def search_in_package(pkg, pkg_name):
                # Check if the package has the class directly
                if hasattr(pkg, class_name):
                    cls = getattr(pkg, class_name)
                    if inspect.isclass(cls):
                        return cls

                # Check if the package has a submodule with the class
                if hasattr(pkg, "__path__"):
                    import pkgutil

                    for importer, modname, ispkg in pkgutil.iter_modules(
                        pkg.__path__, pkg_name + "."
                    ):
                        try:
                            submodule = importlib.import_module(modname)
                            result = search_in_package(submodule, modname)
                            if result:
                                return result
                        except Exception as e:
                            self.logger.error(
                                f"Error importing submodule {modname}: {e}"
                            )
                            continue

                return None

            return search_in_package(package, package_name)

        except Exception as e:
            self.logger.error(f"Error importing package {package_name}: {e}")
            return None
        finally:
            sys.path[:] = original_path

    def _get_service_class(self, servicer_name: str) -> Tuple[str, Type[object]]:
        """
        Get the service class by its name from the service groups.
        Args:
            servicer_name (str): The name of the service class to find.
        Returns:
            Tuple[str, Type[object]]: The group name and the service class.
        Raises:
            ValueError: If the service class is not found in any group.
        """
        for group, services in self.service_groups.items():
            for service in services:
                parent_names = [base.__name__ for base in service.__class__.__bases__]
                self.logger.debug(
                    f"Service: {service.__class__.__name__}, Parent Names: {parent_names}"
                )
                # GreeterServicer
                if not servicer_name.endswith("Servicer"):
                    servicer_name += "Servicer"
                if servicer_name in parent_names:
                    return group, service
        raise ValueError(f"Service {servicer_name} not found")
        # raise ValueError(f"Service {service_name} not found")

    def _get_io_models(self, input_model: str, output_model: str) -> Tuple[Type, Type]:
        input_cls = self._scan_and_import_class(self._models_dir, input_model)
        outpt_cls = self._scan_and_import_class(self._models_dir, output_model)
        if not input_cls or not outpt_cls:
            raise ValueError(
                f"Input model {input_model} or output model {output_model} not found in {self._models_dir}"
            )
        return input_cls, outpt_cls

    def _get_io_pb2(self, input_pb2: str, output_pb2: str) -> Tuple[Type, Type]:
        input_cls = self._scan_and_import_class(self._pb_dir, input_pb2)
        outpt_cls = self._scan_and_import_class(self._pb_dir, output_pb2)
        if not input_cls or not outpt_cls:
            raise ValueError(
                f"Input pb2 {input_pb2} or output pb2 {output_pb2} not found in {self._pb_dir}"
            )
        return input_cls, outpt_cls

    def load_services(self):
        """
                Load gRPC services from a JSON file.
                This method reads a JSON file containing service definitions and initializes
                the services for the gRPC server.

                {
            "Greeter": {
                "SayHello": {
                    "input_type": ".helloworld.HelloRequest",
                    "output_type": ".helloworld.HelloReply",
                    "options": {
                        "[google.api.http]": {
                            "post": "/v1/helloworld",
                            "body": "*"
                        }
                    },
                    "streaming_type": "unary",
                    "method_full_name": "/helloworld.Greeter/SayHello",
                    "http": {
                        "method": "POST",
                        "path": "/v1/helloworld",
                        "body": "*"
                    }
                },
                "SayHelloStreamReply": {
                    "input_type": ".helloworld.HelloRequest",
                    "output_type": ".helloworld.HelloReply",
                    "options": {
                        "[google.api.http]": {
                            "post": "/v1/helloworld/stream",
                            "body": "*"
                        }
                    },
                    "streaming_type": "server_streaming",
                    "method_full_name": "/helloworld.Greeter/SayHelloStreamReply",
                    "http": {
                        "method": "POST",
                        "path": "/v1/helloworld/stream",
                        "body": "*"
                    }
                },
                "SayHelloBidiStream": {
                    "input_type": ".helloworld.HelloRequest",
                    "output_type": ".helloworld.HelloReply",
                    "options": {
                        "[google.api.http]": {
                            "post": "/v1/helloworld/bidi",
                            "body": "*"
                        }
                    },
                    "streaming_type": "bidirectional_streaming",
                    "method_full_name": "/helloworld.Greeter/SayHelloBidiStream",
                    "http": {
                        "method": "POST",
                        "path": "/v1/helloworld/bidi",
                        "body": "*"
                    }
                }
            }
        }
        """
        services_json_file = f"{self._models_dir}/services.json"
        if not os.path.exists(services_json_file):
            raise FileNotFoundError(
                f"Services JSON file not found: {services_json_file}"
            )
        with open(services_json_file, "r", encoding="utf-8") as f:
            services_data: Dict[str, Any] = json.load(f)
            for service_name, service_info in services_data.items():
                group, service_class = self._get_service_class(service_name)
                for method_name, method_info in service_info.items():
                    service_method = getattr(service_class, method_name, None)
                    if not service_method:
                        raise AttributeError(
                            f"Method {method_name} not found in service {service_name}"
                        )
                    http_info = method_info.get("http", {})
                    if http_info:
                        input_type: str = method_info.get("input_type", "")
                        output_type = method_info.get("output_type", "")
                        if not input_type or not output_type:
                            raise ValueError(
                                f"Input or output type not specified for method {method_name} in service {service_name}"
                            )
                        _in = input_type.split(".")[-1]
                        _out = output_type.split(".")[-1]
                        input_cls, output_cls = self._get_io_models(_in, _out)
                        stream_type = method_info.get("streaming_type", "unary")
                        # endpoint = endpoint_generic(input_cls, service_method)
                        method_full_name = method_info.get("method_full_name", "")
                        input_pb2, output_pb2 = self._get_io_pb2(
                            input_type.split(".")[-1], output_type.split(".")[-1]
                        )
                        from google.protobuf import descriptor_pool, message_factory

                        pool = descriptor_pool.Default()
                        input_type = input_type.removeprefix(".")
                        output_type = output_type.removeprefix(".")
                        in_nested_proto = pool.FindMessageTypeByName(input_type)
                        in_nested_cls = message_factory.GetMessageClass(in_nested_proto)
                        out_nested_proto = pool.FindMessageTypeByName(output_type)
                        out_nested_cls = message_factory.GetMessageClass(
                            out_nested_proto
                        )
                        self._services[method_full_name] = {
                            "service": service_class,
                            "method": service_method,
                            "input_type": input_cls,
                            "output_type": output_cls,
                            "input_pb2": input_pb2,
                            "output_pb2": output_pb2,
                            "streaming_type": stream_type,
                            "http_info": http_info,
                            "group": group,
                            "input_message_cls": in_nested_cls,
                            "output_message_cls": out_nested_cls,
                        }
                        endpoint = endpoint_generic_decorator(
                            output_cls, service_method
                        )

                        if stream_type == "unary":
                            endpoint = endpoint_generic_decorator(
                                output_cls, service_method
                            )
                        if stream_type == "server_streaming":
                            endpoint = sse_endpoint_generic_decorator(
                                output_cls, service_method
                            )
                        if stream_type == "bidirectional_streaming":
                            endpoint = websocket_endpoint_generic_decorator(
                                input_cls, output_cls, service_method, True
                            )
                            self.fastapi_app.add_api_websocket_route(
                                path=http_info.get("path", ""),
                                endpoint=endpoint,
                            )
                            self.fastapi_app.add_api_route(
                                http_info.get("path", ""),
                                endpoint=websocket_endpoint_generic_decorator(
                                    input_cls, output_cls, service_method, False
                                ),
                                methods=[http_info.get("method", "POST").upper()],
                                tags=[group],
                                description=service_method.__doc__,
                                summary=f"""{service_method.__doc__}  
                                (Using the WebSocket protocol for bidirectional streaming communication under HTTP/1, 
                                while also supporting bidirectional streaming communication with HTTP/2 protocol)"""
                                if service_method.__doc__
                                else f"""{service_name}.{method_name}  
                                (Using the WebSocket protocol for bidirectional streaming communication under HTTP/1, 
                                while also supporting bidirectional streaming communication with HTTP/2 protocol)""",
                            )
                            self.logger.debug(
                                f"Added WebSocket route for {method_full_name} at {http_info.get('path', '')}"
                            )
                            continue
                        use_body = http_info.get("body", None)
                        input_annotations = input_cls
                        if use_body:
                            input_annotations = Annotated[input_cls, Body()]
                        else:
                            input_annotations = Annotated[input_cls, Query()]
                        endpoint.__annotations__ = {
                            "ctx": Request,
                            "response": Response,
                            "request": input_annotations,
                            "return": BaseHttpResponse[output_cls],
                        }
                        summary = service_method.__doc__
                        if not summary:
                            summary = f"{service_name}.{method_name}"
                        if stream_type == "server_streaming":
                            summary = f"{summary} (SSE)"
                        self.fastapi_app.add_api_route(
                            path=http_info.get("path", ""),
                            endpoint=endpoint,
                            methods=[http_info.get("method", "POST").upper()],
                            response_model=BaseHttpResponse[output_cls],
                            description=service_method.__doc__,
                            tags=[group],
                            summary=summary,
                        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send):
        if self._is_grpc_request(scope):
            await self._handle_grpc_to_fastapi(scope, receive, send)
        else:

            async def fastapi_receive() -> dict:
                request = await receive()
                return request

            await self.fastapi_app(scope, fastapi_receive, send)

    def _is_grpc_request(self, scope: Scope) -> bool:
        """Determine if the request is a gRPC request."""
        # gRPC requests typically have a content-type of application/grpc

        headers = dict(scope.get("headers", []))
        content_type = headers.get(b"content-type", b"").decode()
        path = scope.get("path", "")

        # Check if the content type indicates a gRPC request
        if content_type.startswith("application/grpc"):
            return True

        # Check if the path looks like a gRPC method path
        if self._looks_like_grpc_path(path):
            return True

        return False

    def _looks_like_grpc_path(self, path: str) -> bool:
        """Check if the path looks like a gRPC method path."""
        # gRPC 路径通常是 /package.service/method 格式
        parts = path.strip("/").split("/")
        return len(parts) == 2 and "." in parts[0]

    def _build_fastapi_scope(
        self,
        original_scope: Scope,
        full_method_name: str,
    ) -> Scope:
        """
        Build FastAPI scope from gRPC scope
        """
        # Transform gRPC method name to FastAPI path
        # For Example: helloworld.Greeter/SayHello -> /api/v1/greeter/say-hello
        headers = original_scope.get("headers", [])
        http_info = self._services[full_method_name]["http_info"]
        path = http_info.get("path", "")
        method = http_info.get("method", "POST").upper()
        fastapi_scope = original_scope.copy()
        new_headers = [
            (b"content-type", b"application/json"),
            (b"x-grpc-method", full_method_name.encode("utf-8")),
        ]
        new_headers.extend(headers)
        fastapi_scope.update(
            {
                "path": path,
                "raw_path": path.encode("utf-8"),
                "method": method,  # gRPC调用通常映射为POST请求
                "headers": new_headers,
            }
        )
        self.logger.debug(f"Building FastAPI scope: {fastapi_scope}")
        return fastapi_scope

    def _build_fastapi_receive(
        self,
        original_receive: Receive,
        full_method_name: str,
        body_decompress_algorithm: Optional[str] = "gzip",
    ) -> Receive:
        """
        Build FastAPI receive function from gRPC receive function
        This function processes the incoming request, decompresses the body if necessary,
        """

        async def fastapi_receive() -> dict:
            request = await original_receive()
            if request.get("body", b"") == b"":
                return request
            if request.get("type") == "http.request":
                service = self._services[full_method_name]
                in_cls = service["input_message_cls"]
                in_model_cls = service["input_type"]
                try:
                    message = RequestToGrpc.parse_grpc_message(
                        request.get("body", b""), in_cls, body_decompress_algorithm
                    )
                    if not message:
                        return request
                    in_model = in_model_cls.from_protobuf(message)
                    body = json.dumps(in_model.model_dump(), ensure_ascii=False).encode(
                        "utf-8"
                    )

                    request["body"] = body
                    return request
                except Exception as e:
                    self.logger.error(f"Error parsing gRPC request body: {e}")
                    raise ValueError(
                        f"Failed to parse gRPC request body for method {full_method_name}"
                    )
            return request

        return fastapi_receive

    def _get_sse_data(self, data: str) -> str:
        """
        Get SSE data from bytes or string
        """
        if isinstance(data, bytes):
            data = data.decode("utf-8")
        data = data.removeprefix("data: ")
        data = data.removesuffix(EventSourceResponse.DEFAULT_SEPARATOR).removesuffix(
            EventSourceResponse.DEFAULT_SEPARATOR
        )
        return data

    async def _send_trailers(self, send_func: Send):
        """Send gRPC trailers"""
        trailers_message = {
            "type": "http.response.trailers",
            "headers": [
                (b"grpc-status", b"0"),
                (b"grpc-message", b"OK"),
                (b"te", b"trailers"),
                (b"content-type", b"application/grpc"),
            ],
            "more_trailers": False,
        }
        await send_func(trailers_message)

    def _build_fastapi_send(self, original_send: Send, full_method_name: str) -> Send:
        """
        Build FastAPI send function from gRPC send function
        """
        connection_open = True
        trailers_sent = False
        sse = False

        async def fastapi_send(message: dict):
            nonlocal connection_open, trailers_sent, sse

            if message.get("type") == "http.response.start":
                headers = message.get("headers", [])
                context_length_index = -1
                for i, (key, value) in enumerate(headers):
                    if key == b"content-type":
                        val = value.decode("utf-8")
                        if val.find("event-stream") >= 0:
                            sse = True
                        headers[i] = (key, b"application/grpc")
                    elif key == b"content-length":
                        context_length_index = i
                if context_length_index >= 0:
                    headers.pop(context_length_index)
                message["headers"] = headers
                # Enable trailers support
                message["trailers"] = True
                await original_send(message)
            elif message.get("type") in ["http.response.body"]:
                service = self._services[full_method_name]
                out_model_cls = service["output_type"]
                body_data = message.get("body", b"")
                more_body = message.get("more_body", False)
                if body_data:
                    if sse:
                        body_data = self._get_sse_data(body_data).encode("utf-8")
                    body = out_model_cls.model_validate_json(body_data.decode("utf-8"))
                    out_ob2 = body.to_protobuf()
                    message["body"] = RequestToGrpc.create_grpc_message(out_ob2, "")
                    await original_send(message)
                if not more_body and not trailers_sent:
                    trailers_sent = True

                    message["trailers"] = True
                    if message["body"] == b"":
                        await original_send(message)
                    await self._send_trailers(original_send)
            else:
                await original_send(message)

        return fastapi_send

    async def _send_grpc_error(self, send_func, error_message: str, code: int):
        """Send gRPC error trailers"""
        try:
            encode_code = str(code).encode("utf-8")
            error_trailers = {
                "type": "http.response.trailers",
                "headers": [
                    (b"grpc-status", encode_code),
                    (b"grpc-message", error_message.encode("utf-8")),
                ],
                "more_trailers": False,
            }
            await send_func(error_trailers)
        except Exception as e:
            self.logger.error(f"Failed to send error trailers: {e}")

    async def _handle_grpc_to_fastapi(self, scope: Scope, receive: Receive, send: Send):
        """
        Handle gRPC to FastAPI request conversion
        """
        path = scope.get("path", "")

        new_scope = self._build_fastapi_scope(scope, path)
        headers = dict(new_scope.get("headers", []))
        grpc_content_compression = headers.get(b"grpc-accept-encoding", b"").decode()
        fastapi_receive = self._build_fastapi_receive(
            receive, path, grpc_content_compression
        )
        fastapi_send = self._build_fastapi_send(send, path)
        try:
            await self.fastapi_app(new_scope, fastapi_receive, fastapi_send)
        except HTTPException as e:
            self.logger.error(f"HTTPException occurred: {e.detail}")
            await self._send_grpc_error(fastapi_send, f"{e.detail}", e.status_code)
        except ValidationError as e:
            self.logger.error(f"ValidationError occurred: {e.errors()}")
            await self._send_grpc_error(fastapi_send, f"{e.errors()}", 400)
        except Exception as e:
            self.logger.error(f"Unhandled exception: {str(e)}")
            await self._send_grpc_error(
                fastapi_send, f"Internal Server Error: {str(e)}", 500
            )
