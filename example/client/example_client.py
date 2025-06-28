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
            # Connect with proper parameter name
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
                    logger.debug("Send inputs task cancelled")
                except Exception as e:
                    logger.error(f"Error sending input: {e}")
                finally:
                    # Signal close without actually closing (let context manager handle it)
                    should_close.set()

            # Start sender task
            sender_task = asyncio.create_task(send_inputs())

            try:
                # Receive outputs
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
            logger.error(f"WebSocket connection failed: {e}")
            raise
        finally:
            # Clean up tasks and connections
            should_close.set() if 'should_close' in locals() else None

            if sender_task and not sender_task.done():
                sender_task.cancel()
                try:
                    await asyncio.wait_for(sender_task, timeout=2.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    logger.debug("Sender task cleanup completed")

            if websocket and not websocket.closed:
                try:
                    await websocket.close()
                except Exception:
                    logger.debug("WebSocket close during cleanup")
