"""
Improved decorators for gRPC FastAPI Gateway endpoints
"""
import json
import logging
from typing import Type, Callable
from contextlib import asynccontextmanager

from fastapi import Request, Response, WebSocket
from fastapi.responses import StreamingResponse
from sse_starlette import EventSourceResponse
from pydantic import BaseModel, ValidationError

from .context import GRPCServicerContextAdapter
from .response import BaseHttpResponse
from .exceptions import ConnectionError, ValidationError as GatewayValidationError
from .config import get_config
from .utils.validation import get_validator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def safe_websocket_connection(websocket: WebSocket):
    """
    Safe WebSocket connection context manager
    Ensures proper connection handling and cleanup
    """
    connection_established = False
    try:
        await websocket.accept()
        connection_established = True
        yield websocket
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        if not connection_established:
            raise ConnectionError(f"Failed to establish WebSocket connection: {e}", "websocket")
        raise
    finally:
        if connection_established:
            try:
                if websocket.client_state.name == "CONNECTED":
                    await websocket.close()
            except Exception as e:
                logger.debug(f"Error closing WebSocket: {e}")


def safe_endpoint_decorator(
    response_cls: Type[BaseModel],
    service_method: Callable,
) -> Callable:
    """
    Safe endpoint decorator with improved error handling
    """
    async def endpoint(
        ctx: Request,
        response: Response,
        request: BaseModel,
    ) -> BaseHttpResponse:
        config = get_config()
        validator = get_validator()
        
        try:
            # Create context
            context = GRPCServicerContextAdapter(ctx, response)
            
            # Call service method
            rsp = await service_method(request.to_protobuf(), context)
            
            # Convert response
            data = response_cls.from_protobuf(rsp)
            
            # Update headers
            response.headers.update(context.trailing_metadata())
            
            return BaseHttpResponse[response_cls](
                code=0,
                message="success",
                data=data
            )
            
        except ValidationError as e:
            error_msg = validator.sanitize_error_message(str(e))
            logger.error(f"Validation error in {service_method.__name__}: {error_msg}")
            raise GatewayValidationError(error_msg, [str(err) for err in e.errors()])
        
        except Exception as e:
            error_msg = validator.sanitize_error_message(str(e))
            if config.debug:
                logger.exception(f"Error in {service_method.__name__}")
            else:
                logger.error(f"Error in {service_method.__name__}: {type(e).__name__}")
            
            # Re-raise with sanitized message
            raise type(e)(error_msg)

    return endpoint


def safe_sse_endpoint_decorator(
    response_cls: Type[BaseModel],
    service_method: Callable,
) -> Callable:
    """
    Safe SSE endpoint decorator with improved error handling
    """
    async def sse_endpoint(
        ctx: Request,
        response: Response,
        request: BaseModel
    ) -> EventSourceResponse:
        config = get_config()
        validator = get_validator()
        
        async def safe_async_generator():
            try:
                context = GRPCServicerContextAdapter(ctx, response)
                
                async for item in service_method(request.to_protobuf(), context):
                    data = response_cls.from_protobuf(item)
                    yield json.dumps(data.model_dump(), ensure_ascii=False)
                    
            except Exception as e:
                error_msg = validator.sanitize_error_message(str(e))
                if config.debug:
                    logger.exception(f"Error in SSE stream {service_method.__name__}")
                else:
                    logger.error(f"Error in SSE stream {service_method.__name__}: {type(e).__name__}")
                
                # Send error event
                yield f"event: error\ndata: {json.dumps({'error': error_msg})}\n\n"

        return EventSourceResponse(
            safe_async_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive"
            },
        )

    return sse_endpoint


def safe_websocket_endpoint_decorator(
    request_cls: Type[BaseModel],
    response_cls: Type[BaseModel],
    service_method: Callable,
    is_websocket: bool = True,
) -> Callable:
    """
    Safe WebSocket endpoint decorator for bidirectional streaming
    """
    async def websocket_endpoint(websocket: WebSocket) -> None:
        config = get_config()
        validator = get_validator()
        
        async with safe_websocket_connection(websocket) as ws:
            try:
                async def request_stream():
                    """Generate request stream from WebSocket messages"""
                    async for message in ws.iter_text():
                        if not message.strip():
                            continue
                            
                        try:
                            # Validate message
                            data = validator.validate_websocket_message(message)
                            request_obj = request_cls.model_validate(data)
                            yield request_obj.to_protobuf()
                            
                        except (ValidationError, GatewayValidationError) as e:
                            error_msg = validator.sanitize_error_message(str(e))
                            await ws.send_json({
                                "type": "error",
                                "error": f"Invalid request: {error_msg}"
                            })
                            continue

                context = GRPCServicerContextAdapter(websocket, None)
                
                # Process bidirectional stream
                async for response_item in service_method(request_stream(), context):
                    data = response_cls.from_protobuf(response_item)
                    await ws.send_json({
                        "type": "response",
                        "data": data.model_dump()
                    })
                
                # Send completion signal
                await ws.send_json({"type": "complete"})
                
            except Exception as e:
                error_msg = validator.sanitize_error_message(str(e))
                if config.debug:
                    logger.exception(f"Error in WebSocket stream {service_method.__name__}")
                else:
                    logger.error(f"Error in WebSocket stream {service_method.__name__}: {type(e).__name__}")
                
                try:
                    await ws.send_json({
                        "type": "error",
                        "error": error_msg
                    })
                except Exception:
                    pass  # Connection might be closed

    async def http_streaming_endpoint(request: Request):
        """HTTP streaming endpoint for bidirectional communication"""
        config = get_config()
        validator = get_validator()
        
        async def process_stream():
            try:
                context = GRPCServicerContextAdapter(request, None)

                async def request_stream():
                    """Generate request stream from HTTP chunks"""
                    buffer = ""
                    async for chunk in request.stream():
                        if chunk:
                            buffer += chunk.decode('utf-8')
                            
                            # Process complete lines
                            while '\n' in buffer:
                                line, buffer = buffer.split('\n', 1)
                                line = line.strip()
                                if line:
                                    try:
                                        data = validator.validate_json_payload(line)
                                        request_obj = request_cls.model_validate(data)
                                        yield request_obj.to_protobuf()
                                    except Exception as e:
                                        logger.error(f"Error processing chunk: {e}")
                                        continue

                    # Process remaining buffer
                    if buffer.strip():
                        try:
                            data = validator.validate_json_payload(buffer.strip())
                            request_obj = request_cls.model_validate(data)
                            yield request_obj.to_protobuf()
                        except Exception as e:
                            logger.error(f"Error processing final chunk: {e}")

                async for response_item in service_method(request_stream(), context):
                    data = response_cls.from_protobuf(response_item)
                    yield json.dumps(data.model_dump(), ensure_ascii=False) + '\n'

            except Exception as e:
                error_msg = validator.sanitize_error_message(str(e))
                if config.debug:
                    logger.exception(f"Error in HTTP stream {service_method.__name__}")
                else:
                    logger.error(f"Error in HTTP stream {service_method.__name__}: {type(e).__name__}")
                
                yield json.dumps({"error": error_msg}) + '\n'

        return StreamingResponse(
            process_stream(),
            media_type="application/x-ndjson",
            headers={"Connection": "keep-alive"}
        )

    return websocket_endpoint if is_websocket else http_streaming_endpoint


def safe_client_streaming_endpoint_decorator(
    request_cls: Type[BaseModel],
    response_cls: Type[BaseModel],
    service_method: Callable,
    is_websocket: bool = True,
) -> Callable:
    """
    Safe client streaming endpoint decorator
    """
    async def websocket_client_streaming_endpoint(websocket: WebSocket) -> None:
        config = get_config()
        validator = get_validator()
        
        async with safe_websocket_connection(websocket) as ws:
            try:
                async def request_stream():
                    """Generate request stream from WebSocket messages"""
                    async for message in ws.iter_text():
                        if not message.strip():
                            continue
                            
                        try:
                            # Validate message
                            data = validator.validate_websocket_message(message)
                            request_obj = request_cls.model_validate(data)
                            yield request_obj.to_protobuf()
                            
                        except (ValidationError, GatewayValidationError) as e:
                            error_msg = validator.sanitize_error_message(str(e))
                            await ws.send_json({
                                "type": "error",
                                "error": f"Invalid request: {error_msg}"
                            })
                            continue

                context = GRPCServicerContextAdapter(websocket, None)
                
                # Call streaming service method (returns single response)
                response = await service_method(request_stream(), context)
                
                if response:
                    data = response_cls.from_protobuf(response)
                    await ws.send_json({
                        "type": "response",
                        "data": data.model_dump()
                    })
                
                # Send completion signal
                await ws.send_json({"type": "complete"})
                
            except Exception as e:
                error_msg = validator.sanitize_error_message(str(e))
                if config.debug:
                    logger.exception(f"Error in client streaming {service_method.__name__}")
                else:
                    logger.error(f"Error in client streaming {service_method.__name__}: {type(e).__name__}")
                
                try:
                    await ws.send_json({
                        "type": "error",
                        "error": error_msg
                    })
                except Exception:
                    pass  # Connection might be closed

    async def http_client_streaming_endpoint(request: Request):
        """HTTP endpoint for client streaming"""
        config = get_config()
        validator = get_validator()
        
        try:
            context = GRPCServicerContextAdapter(request, None)

            async def request_stream():
                """Generate request stream from HTTP chunks"""
                buffer = ""
                async for chunk in request.stream():
                    if chunk:
                        buffer += chunk.decode('utf-8')
                        
                        # Process complete lines
                        while '\n' in buffer:
                            line, buffer = buffer.split('\n', 1)
                            line = line.strip()
                            if line:
                                try:
                                    data = validator.validate_json_payload(line)
                                    request_obj = request_cls.model_validate(data)
                                    yield request_obj.to_protobuf()
                                except Exception as e:
                                    logger.error(f"Error processing chunk: {e}")
                                    continue

                # Process remaining buffer
                if buffer.strip():
                    try:
                        data = validator.validate_json_payload(buffer.strip())
                        request_obj = request_cls.model_validate(data)
                        yield request_obj.to_protobuf()
                    except Exception as e:
                        logger.error(f"Error processing final chunk: {e}")

            # Call streaming service method
            response = await service_method(request_stream(), context)
            
            if response:
                data = response_cls.from_protobuf(response)
                return BaseHttpResponse[response_cls](
                    code=0,
                    message="success",
                    data=data
                )
            else:
                return BaseHttpResponse[response_cls](
                    code=0,
                    message="success",
                    data=None
                )

        except Exception as e:
            error_msg = validator.sanitize_error_message(str(e))
            if config.debug:
                logger.exception(f"Error in HTTP client streaming {service_method.__name__}")
            else:
                logger.error(f"Error in HTTP client streaming {service_method.__name__}: {type(e).__name__}")
            
            from fastapi import HTTPException
            raise HTTPException(status_code=500, detail=error_msg)

    return websocket_client_streaming_endpoint if is_websocket else http_client_streaming_endpoint
