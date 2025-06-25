#!/usr/bin/env python3
"""
gRPC Python Client for Greeter Service

This client demonstrates how to use the Greeter service with different RPC types:
- Unary RPC (SayHello)
- Server streaming RPC (SayHelloStreamReply)
- Bidirectional streaming RPC (SayHelloBidiStream)
"""

import asyncio
import grpc
import logging
from typing import AsyncIterator, Iterator

# Import the generated protobuf classes
# You need to generate these files using:
# python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto
import helloworld_pb2
import helloworld_pb2_grpc

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AsyncGreeterClient:
    """Async gRPC client for the Greeter service."""

    def __init__(self, server_address: str = "localhost:8010"):
        """
        Initialize the async client.

        Args:
            server_address: The address of the gRPC server
        """
        self.server_address = server_address
        self.channel = None
        self.stub = None

    async def connect(self):
        """Establish async connection to the gRPC server."""
        self.channel = grpc.aio.insecure_channel(self.server_address)
        self.stub = helloworld_pb2_grpc.GreeterStub(self.channel)
        logger.info(f"Connected to gRPC server at {self.server_address}")

    async def close(self):
        """Close the async connection to the gRPC server."""
        if self.channel:
            await self.channel.close()
            logger.info("Async connection closed")

    async def say_hello(
        self, name: str, language: str = "en"
    ) -> helloworld_pb2.HelloReply:
        """
        Send an async unary greeting request.

        Args:
            name: The name of the person to greet
            language: The language for the greeting

        Returns:
            HelloReply: The greeting response
        """
        try:
            request = helloworld_pb2.HelloRequest(name=name, language=language)
            response = await self.stub.SayHello(request)
            logger.info(f"Received async response: {response.message}")
            return response
        except grpc.RpcError as e:
            logger.error(f"Async RPC failed: {e.code()}: {e.details()}")
            raise

    async def say_hello_stream_reply(
        self, name: str, language: str = "en"
    ) -> AsyncIterator[helloworld_pb2.HelloReply]:
        """
        Send an async request and receive streaming responses.

        Args:
            name: The name of the person to greet
            language: The language for the greeting

        Yields:
            HelloReply: Stream of greeting responses
        """
        try:
            request = helloworld_pb2.HelloRequest(name=name, language=language)
            response_stream = self.stub.SayHelloStreamReply(request)

            async for response in response_stream:
                logger.info(f"Received async streaming response: {response.message}")
                yield response
        except grpc.RpcError as e:
            logger.error(f"Async streaming RPC failed: {e.code()}: {e.details()}")
            raise

    async def say_hello_bidi_stream(
        self, requests: AsyncIterator[helloworld_pb2.HelloRequest]
    ) -> AsyncIterator[helloworld_pb2.HelloReply]:
        """
        Send async streaming requests and receive streaming responses.

        Args:
            requests: Async iterator of HelloRequest messages

        Yields:
            HelloReply: Stream of greeting responses
        """
        try:
            response_stream = self.stub.SayHelloBidiStream(requests)

            async for response in response_stream:
                logger.info(
                    f"Received async bidirectional streaming response: {response.message}"
                )
                yield response
        except grpc.RpcError as e:
            logger.error(
                f"Async bidirectional streaming RPC failed: {e.code()}: {e.details()}"
            )
            raise


def create_request_stream(
    names: list, language: str = "en"
) -> Iterator[helloworld_pb2.HelloRequest]:
    """Helper function to create a stream of requests."""
    for name in names:
        yield helloworld_pb2.HelloRequest(name=name, language=language)


async def create_async_request_stream(
    names: list, language: str = "en"
) -> AsyncIterator[helloworld_pb2.HelloRequest]:
    """Helper function to create an async stream of requests."""
    for name in names:
        await asyncio.sleep(0.1)  # Simulate delay between requests
        yield helloworld_pb2.HelloRequest(name=name, language=language)


async def async_main():
    """Main function demonstrating asynchronous client usage."""
    client = AsyncGreeterClient()

    try:
        # Connect to the server
        await client.connect()

        # Test async unary RPC
        print("=== Testing Async Unary RPC ===")
        response = await client.say_hello("Alice", "en")
        print(f"Async response: {response.message}")

        # Test async server streaming RPC
        print("\n=== Testing Async Server Streaming RPC ===")
        async for response in client.say_hello_stream_reply("Bob", "en"):
            print(f"Async streaming response: {response.message}")

        # Test async bidirectional streaming RPC
        print("\n=== Testing Async Bidirectional Streaming RPC ===")
        names = ["Charlie", "David", "Eve"]
        request_stream = create_async_request_stream(names, "en")

        async for response in client.say_hello_bidi_stream(request_stream):
            print(f"Async bidi streaming response: {response.message}")

    except Exception as e:
        logger.error(f"Async client error: {e}")
    finally:
        await client.close()


if __name__ == "__main__":
    print("Choose mode:")
    print("1. Synchronous client")
    print("2. Asynchronous client")
    asyncio.run(async_main())
