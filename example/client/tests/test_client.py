"""
Test cases for ExampleClient
Tests against local server on port 8010
"""
import asyncio
import pytest
from example.client.example_client import ExampleClient
from example.models.helloworld_model import HelloRequest, HelloReply


class TestExampleClientIntegration:
    """Integration tests for ExampleClient against local server"""

    @pytest.fixture
    def client(self):
        """Create test client instance"""
        return ExampleClient(
            base_url="http://localhost:8010",
            api_key="",
            timeout=30.0
        )

    @pytest.mark.asyncio
    async def test_greeter_say_hello(self, client):
        """Test unary call: SayHello"""
        request = HelloRequest(name="Alice", language="en")

        try:
            response = await client.greeter_say_hello(request)

            assert isinstance(response, HelloReply)
            assert "Alice" in response.message
            print(f"✓ SayHello response: {response.message}")

        except Exception as e:
            pytest.fail(f"SayHello failed: {e}")

    @pytest.mark.asyncio
    async def test_greeter_say_hello_stream_reply(self, client):
        """Test server streaming: SayHelloStreamReply"""
        request = HelloRequest(name="Bob", language="en")

        try:
            responses = []
            async for response in client.greeter_say_hello_stream_reply(request):
                assert isinstance(response, HelloReply)
                assert "Bob" in response.message
                responses.append(response)
                print(f"✓ Stream response: {response.message}")

                # Limit to avoid infinite streams
                if len(responses) >= 5:
                    break

            assert len(responses) > 0, "Should receive at least one response"

        except Exception as e:
            pytest.fail(f"SayHelloStreamReply failed: {e}")

    @pytest.mark.asyncio
    async def test_greeter_say_hello_bidi_stream(self, client: ExampleClient):
        """Test bidirectional streaming: SayHelloBidiStream"""

        async def input_generator():
            """Generate input requests"""
            names = ["Charlie", "David", "Eve"]
            for name in names:
                request = HelloRequest(name=name, language="en")
                print(f"→ Sending: {name}")
                yield request
                await asyncio.sleep(0.1)  # Small delay between sends

        try:
            responses = []
            response_count = 0
            async for response in client.greeter_say_hello_bidi_stream(input_generator()):
                assert isinstance(response, HelloReply)
                responses.append(response)
                response_count += 1
                print(f"← Received: {response.message}")

                # Limit to avoid hanging - break after reasonable number of responses
                if response_count >= 3:
                    break

            assert len(responses) > 0, "Should receive at least one response"

        except Exception as e:
            # Allow connection errors if server doesn't support WebSocket
            if "connection" in str(e).lower() or "websocket" in str(e).lower():
                pytest.skip(f"WebSocket not available: {e}")
            else:
                pytest.fail(f"SayHelloBidiStream failed: {e}")

        # Add a small delay to allow cleanup
        await asyncio.sleep(0.1)

    @pytest.mark.asyncio
    async def test_multiple_concurrent_calls(self, client):
        """Test multiple concurrent unary calls"""

        async def make_call(name: str):
            request = HelloRequest(name=name, language="en")
            return await client.greeter_say_hello(request)

        try:
            # Make 3 concurrent calls
            tasks = [
                make_call("User1"),
                make_call("User2"),
                make_call("User3")
            ]

            responses = await asyncio.gather(*tasks)

            assert len(responses) == 3
            for i, response in enumerate(responses):
                assert isinstance(response, HelloReply)
                assert f"User{i+1}" in response.message
                print(f"✓ Concurrent call {i+1}: {response.message}")

        except Exception as e:
            pytest.fail(f"Concurrent calls failed: {e}")

    @pytest.mark.asyncio
    async def test_error_handling_invalid_endpoint(self, client):
        """Test error handling for invalid endpoint"""
        # Modify client to use invalid endpoint
        client.base_url = "http://localhost:8010/invalid"

        request = HelloRequest(name="Test", language="en")

        with pytest.raises(Exception):  # Should raise an HTTP error
            await client.greeter_say_hello(request)
        print("✓ Error handling test passed")

    @pytest.mark.asyncio
    async def test_timeout_handling(self):
        """Test timeout handling"""
        # Create client with very short timeout
        client = ExampleClient(
            base_url="http://localhost:8010",
            timeout=0.001  # 1ms timeout
        )

        request = HelloRequest(name="Test", language="en")

        with pytest.raises(Exception):  # Should timeout
            await client.greeter_say_hello(request)
        print("✓ Timeout handling test passed")


class TestExampleClientUnit:
    """Unit tests for ExampleClient helper methods"""

    def test_client_initialization(self):
        """Test client initialization"""
        client = ExampleClient(
            base_url="http://localhost:8010",
            api_key="test-key",
            timeout=10.0
        )

        assert client.base_url == "http://localhost:8010"
        assert client.api_key == "test-key"
        assert client.timeout == 10.0

    def test_build_headers_no_api_key(self):
        """Test headers building without API key"""
        client = ExampleClient(base_url="http://localhost:8010")
        headers = client._build_headers()
        assert "Authorization" not in headers

    def test_build_headers_with_api_key(self):
        """Test headers building with API key"""
        client = ExampleClient(
            base_url="http://localhost:8010",
            api_key="test-key"
        )
        headers = client._build_headers()
        assert headers["Authorization"] == "Bearer test-key"

    def test_build_headers_with_extra(self):
        """Test headers building with extra headers"""
        client = ExampleClient(base_url="http://localhost:8010")
        extra = {"Custom-Header": "value", "Another": "header"}
        headers = client._build_headers(extra)
        assert headers["Custom-Header"] == "value"
        assert headers["Another"] == "header"

    def test_build_websocket_uri_http(self):
        """Test WebSocket URI building from HTTP"""
        client = ExampleClient(base_url="http://localhost:8010")
        uri = client._build_websocket_uri("/v1/test")
        assert uri == "ws://localhost:8010/v1/test"

    def test_build_websocket_uri_https(self):
        """Test WebSocket URI building from HTTPS"""
        client = ExampleClient(base_url="https://api.example.com")
        uri = client._build_websocket_uri("/v1/test")
        assert uri == "wss://api.example.com/v1/test"

    def test_base_url_cleanup(self):
        """Test base URL cleanup (trailing slash removal)"""
        client = ExampleClient(base_url="http://localhost:8010/")
        assert client.base_url == "http://localhost:8010"


class TestModelValidation:
    """Test model validation and serialization"""

    def test_hello_request_creation(self):
        """Test HelloRequest creation"""
        request = HelloRequest(name="Alice", language="en")
        assert request.name == "Alice"
        assert request.language == "en"

    def test_hello_request_defaults(self):
        """Test HelloRequest with defaults"""
        request = HelloRequest(name="Bob")
        assert request.name == "Bob"
        # Check if language has default value
        assert request.language is not None

    def test_hello_reply_creation(self):
        """Test HelloReply creation"""
        reply = HelloReply(message="Hello!", language="en")
        assert reply.message == "Hello!"
        assert reply.language == "en"

    def test_model_serialization(self):
        """Test model serialization"""
        request = HelloRequest(name="Alice", language="en")
        data = request.model_dump(exclude_none=True)

        assert isinstance(data, dict)
        assert "name" in data
        assert data["name"] == "Alice"

    def test_model_json_serialization(self):
        """Test model JSON serialization"""
        request = HelloRequest(name="Alice", language="en")
        json_str = request.model_dump_json(exclude_none=True)

        assert isinstance(json_str, str)
        assert "Alice" in json_str


if __name__ == "__main__":
    # Run with: python -m pytest example/client/tests/test_client.py -v
    pytest.main([__file__, "-v", "-s"])
