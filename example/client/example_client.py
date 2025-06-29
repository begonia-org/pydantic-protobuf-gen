"""
Auto-generated gRPC FastAPI client
Generated from services.json
"""
import asyncio
import json
import logging
from typing import Any, Dict, Optional, AsyncGenerator
from urllib.parse import urlparse, urlunparse

import httpx
import websockets
from websockets.exceptions import ConnectionClosed
from pydantic import ValidationError

# Import all required models
from example.models.helloworld_model import HelloReply
from example.models.helloworld_model import HelloRequest

logger = logging.getLogger(__name__)


class ExampleClient:
    """Generated gRPC FastAPI client with type safety"""

    def __init__(
        self,
        base_url: str,
        api_key: str = "",
        timeout: float = 30.0
    ):
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout

    def _build_headers(self, extra_headers: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
        """Build request headers with authentication"""
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        if extra_headers:
            headers.update(extra_headers)
        return headers

    def _build_websocket_uri(self, path: str) -> str:
        """Build WebSocket URI from HTTP base URL"""
        parsed = urlparse(self.base_url)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunparse((
            ws_scheme,
            parsed.netloc,
            path.lstrip('/'),
            parsed.params,
            parsed.query,
            parsed.fragment
        ))

    # Greeter methods

    async def greeter_say_hello(
        self,
        request: HelloRequest,
        headers: Optional[Dict[str, Any]] = None
    ) -> HelloReply:
        """SayHello - Unary RPC call"""
        url = f"{self.base_url}/v1/helloworld"
        request_headers = self._build_headers(headers)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                url,
                json=request.model_dump(exclude_none=True),
                headers=request_headers
            )

            if response.status_code >= 400:
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}",
                    request=response.request,
                    response=response
                )

            data = response.json()
            return HelloReply(**data.get('data', data))

    async def greeter_say_hello_stream_reply(
        self,
        request: HelloRequest,
        headers: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[HelloReply, None]:
        """SayHelloStreamReply - Server streaming RPC call"""
        url = f"{self.base_url}/v1/helloworld/stream"
        request_headers = self._build_headers(headers)
        request_headers["Accept"] = "text/event-stream"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            async with client.stream(
                "POST",
                url,
                json=request.model_dump(exclude_none=True),
                headers=request_headers
            ) as response:
                if response.status_code >= 400:
                    raise httpx.HTTPStatusError(
                        f"HTTP {response.status_code}",
                        request=response.request,
                        response=response
                    )

                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        if data_str.strip():
                            try:
                                data = json.loads(data_str)
                                yield HelloReply(**data)
                            except (json.JSONDecodeError, ValidationError) as e:
                                logger.error(f"Failed to parse SSE data: {e}")

    async def greeter_say_hello_bidi_stream(
        self,
        input_stream: AsyncGenerator[HelloRequest, None],
        headers: Optional[Dict[str, Any]] = None
    ) -> AsyncGenerator[HelloReply, None]:
        """SayHelloBidiStream - Bidirectional streaming RPC call"""
        uri = self._build_websocket_uri("/v1/helloworld/ws")
        extra_headers = self._build_headers(headers)

        websocket = None
        sender_task = None

        try:
            websocket = await websockets.connect(uri, extra_headers=extra_headers)

            # Create a flag to signal when to stop sending
            should_close = asyncio.Event()

            # Input sender task
            async def send_inputs():
                try:
                    async for request in input_stream:
                        if should_close.is_set():
                            break
                        message = request.model_dump_json(exclude_none=True)
                        await websocket.send(message)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Error sending input: {e}")
                    raise
                finally:
                    should_close.set()

            # Start sender task
            sender_task = asyncio.create_task(send_inputs())

            try:
                async for message in websocket:
                    try:
                        data = json.loads(message)
                        yield HelloReply(**data)
                    except (json.JSONDecodeError, ValidationError) as e:
                        logger.error(f"Failed to parse WebSocket message: {e}")
            except ConnectionClosed:
                logger.info("WebSocket connection closed")
            except Exception as e:
                logger.error(f"Error receiving output: {e}")
                raise

        except Exception as e:
            logger.error(f"Error in bidirectional streaming: {e}")
            raise
        finally:
            if sender_task:
                sender_task.cancel()
                try:
                    await sender_task
                except asyncio.CancelledError:
                    pass
            if websocket:
                await websocket.close()

    async def greeter_say_hello_stream(
        self,
        input_stream: AsyncGenerator[HelloRequest, None],
        headers: Optional[Dict[str, Any]] = None
    ) -> HelloReply:
        """SayHelloStream - Client streaming RPC call"""
        uri = self._build_websocket_uri("/v1/helloworld/sse")
        extra_headers = self._build_headers(headers)

        websocket = None
        try:
            websocket = await websockets.connect(uri, extra_headers=extra_headers)

            # Send all input requests
            async for request in input_stream:
                message = request.model_dump_json(exclude_none=True)
                await websocket.send(message)

            # Signal end of input stream
            await websocket.send(json.dumps({"__end_stream__": True}))

            # Wait for single response
            response_message = await websocket.recv()

            try:
                data = json.loads(response_message)
                return HelloReply(**data)
            except (json.JSONDecodeError, ValidationError) as e:
                logger.error(f"Failed to parse response: {e}")
                raise

        except ConnectionClosed:
            logger.error("WebSocket connection closed unexpectedly")
            raise
        except Exception as e:
            logger.error(f"Error in client streaming: {e}")
            raise
        finally:
            if websocket:
                await websocket.close()
