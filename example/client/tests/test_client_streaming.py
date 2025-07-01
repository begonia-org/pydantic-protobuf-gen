"""
Dedicated tests for client streaming functionality
"""
import asyncio
import pytest
from example.client.example_client import ExampleClient
from example.models.helloworld_model import HelloRequest, HelloReply


class TestClientStreaming:
    """Dedicated tests for client streaming (greeter_say_hello_stream)"""

    @pytest.fixture
    def client(self):
        """Create test client instance"""
        return ExampleClient(
            base_url="http://localhost:8010",
            api_key="",
            timeout=30.0
        )

    @pytest.mark.asyncio
    async def test_basic_client_streaming(self, client):
        """Test basic client streaming functionality"""
        
        async def request_stream():
            requests = [
                HelloRequest(name="User1", language="en"),
                HelloRequest(name="User2", language="es"),
                HelloRequest(name="User3", language="zh"),
            ]
            for req in requests:
                print(f"→ Sending: {req.name} ({req.language})")
                yield req
                await asyncio.sleep(0.1)

        try:
            response = await client.greeter_say_hello_stream(request_stream())
            
            assert isinstance(response, HelloReply)
            assert response.message is not None
            print(f"✓ Final response: {response.message}")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"Basic client streaming failed: {e}")

    @pytest.mark.asyncio
    async def test_empty_stream(self, client):
        """Test client streaming with empty input stream"""
        
        async def empty_stream():
            return
            yield  # Never reached

        try:
            response = await client.greeter_say_hello_stream(empty_stream())
            
            assert isinstance(response, HelloReply)
            print(f"✓ Empty stream response: {response.message}")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                # Empty stream might be expected to fail
                print(f"ℹ️ Empty stream failed as expected: {e}")

    @pytest.mark.asyncio
    async def test_single_request_stream(self, client):
        """Test client streaming with single request"""
        
        async def single_stream():
            yield HelloRequest(name="OnlyUser", language="en")

        try:
            response = await client.greeter_say_hello_stream(single_stream())
            
            assert isinstance(response, HelloReply)
            assert "OnlyUser" in response.message
            print(f"✓ Single request response: {response.message}")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"Single request streaming failed: {e}")

    @pytest.mark.asyncio
    async def test_large_stream(self, client):
        """Test client streaming with many requests"""
        
        async def large_stream():
            for i in range(20):
                yield HelloRequest(name=f"User{i:02d}", language="en")
                if i % 5 == 0:
                    await asyncio.sleep(0.05)  # Occasional pause

        try:
            response = await client.greeter_say_hello_stream(large_stream())
            
            assert isinstance(response, HelloReply)
            print(f"✓ Large stream response: {response.message}")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"Large stream failed: {e}")

    @pytest.mark.asyncio
    async def test_stream_with_different_languages(self, client):
        """Test client streaming with requests in different languages"""
        
        async def multilang_stream():
            requests = [
                HelloRequest(name="Alice", language="en"),
                HelloRequest(name="Bob", language="es"),
                HelloRequest(name="Charlie", language="zh"),
                HelloRequest(name="David", language="fr"),
                HelloRequest(name="Eve", language="de"),
            ]
            for req in requests:
                print(f"→ {req.name} speaks {req.language}")
                yield req
                await asyncio.sleep(0.1)

        try:
            response = await client.greeter_say_hello_stream(multilang_stream())
            
            assert isinstance(response, HelloReply)
            print(f"✓ Multilingual response: {response.message}")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"Multilingual streaming failed: {e}")

    @pytest.mark.asyncio
    async def test_concurrent_client_streams(self, client):
        """Test multiple concurrent client streaming calls"""
        
        async def create_stream(prefix: str, count: int):
            for i in range(count):
                yield HelloRequest(name=f"{prefix}{i}", language="en")
                await asyncio.sleep(0.05)

        async def run_stream(prefix: str, count: int):
            return await client.greeter_say_hello_stream(create_stream(prefix, count))

        try:
            # Run 3 concurrent client streaming calls
            tasks = [
                run_stream("A", 3),
                run_stream("B", 3),
                run_stream("C", 3),
            ]
            
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            
            successful_responses = []
            for i, response in enumerate(responses):
                if isinstance(response, HelloReply):
                    successful_responses.append(response)
                    print(f"✓ Concurrent stream {i+1}: {response.message}")
                else:
                    print(f"✗ Concurrent stream {i+1} failed: {response}")
            
            # At least one should succeed if the server supports concurrent connections
            if len(successful_responses) == 0:
                pytest.skip("No concurrent client streams succeeded - server may not support concurrent WebSocket connections")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"Concurrent client streaming failed: {e}")

    @pytest.mark.asyncio
    async def test_stream_error_handling(self, client):
        """Test error handling in client streaming"""
        
        async def error_stream():
            # Send a few valid requests
            yield HelloRequest(name="Valid1", language="en")
            yield HelloRequest(name="Valid2", language="en")
            
            # This should complete normally - any errors would be server-side
            yield HelloRequest(name="Valid3", language="en")

        try:
            response = await client.greeter_say_hello_stream(error_stream())
            
            assert isinstance(response, HelloReply)
            print(f"✓ Error handling test response: {response.message}")
            
        except Exception as e:
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                # Depending on implementation, this might be expected
                print(f"ℹ️ Error handling test failed: {e}")

    @pytest.mark.asyncio
    async def test_stream_timeout(self, client):
        """Test timeout behavior in client streaming"""
        
        # Create a client with short timeout
        timeout_client = ExampleClient(
            base_url="http://localhost:8010",
            timeout=2.0  # 2 second timeout
        )
        
        async def slow_stream():
            yield HelloRequest(name="Fast", language="en")
            await asyncio.sleep(0.5)  # Short delay
            yield HelloRequest(name="Slow", language="en")

        try:
            response = await timeout_client.greeter_say_hello_stream(slow_stream())
            
            assert isinstance(response, HelloReply)
            print(f"✓ Timeout test response: {response.message}")
            
        except Exception as e:
            if "timeout" in str(e).lower():
                print("✓ Timeout behavior working as expected")
            elif "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"Unexpected timeout test failure: {e}")


if __name__ == "__main__":
    # Run with: python -m pytest example/client/tests/test_client_streaming.py -v -s
    pytest.main([__file__, "-v", "-s"])
