# Client Streaming Guide

This guide explains how to use client streaming with the generated gRPC FastAPI client.

## Overview

Client streaming allows you to:
- Send multiple requests to the server
- Receive a single response after all requests are processed
- Use WebSocket connections for real-time communication

## Streaming Types Supported

### 1. Unary (Request-Response)
```python
request = HelloRequest(name="Alice", language="en")
response = await client.greeter_say_hello(request)
```

### 2. Server Streaming (Request-Stream)
```python
request = HelloRequest(name="Bob", language="en")
async for response in client.greeter_say_hello_stream_reply(request):
    print(response.message)
```

### 3. Client Streaming (Stream-Response) ⭐ NEW
```python
async def generate_requests():
    for name in ["Alice", "Bob", "Charlie"]:
        yield HelloRequest(name=name, language="en")

response = await client.greeter_say_hello_client_stream(generate_requests())
print(response.message)  # Single response after all requests
```

### 4. Bidirectional Streaming (Stream-Stream)
```python
async def generate_requests():
    for name in ["Alice", "Bob", "Charlie"]:
        yield HelloRequest(name=name, language="en")

async for response in client.greeter_say_hello_bidi_stream(generate_requests()):
    print(response.message)  # Multiple responses
```

## Client Streaming Details

### WebSocket Connection
Client streaming uses WebSocket connections for efficient bidirectional communication:

```python
# The client automatically:
# 1. Establishes WebSocket connection
# 2. Sends multiple requests as JSON messages
# 3. Signals end of stream
# 4. Waits for single response
# 5. Closes connection properly
```

### Input Stream Generator
Create an async generator to provide input requests:

```python
async def my_request_stream():
    # Send requests based on your logic
    for i in range(10):
        request = HelloRequest(
            name=f"User {i}",
            language="en"
        )
        yield request
        
        # Optional: Add delays or conditions
        await asyncio.sleep(0.1)
        
        # Optional: Break based on conditions
        if some_condition:
            break
```

### Error Handling
Handle various error scenarios:

```python
try:
    response = await client.greeter_say_hello_client_stream(my_stream())
    print(f"Success: {response.message}")
    
except websockets.exceptions.ConnectionClosed:
    print("WebSocket connection was closed")
    
except asyncio.TimeoutError:
    print("Request timed out")
    
except json.JSONDecodeError:
    print("Invalid response format")
    
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Advanced Usage

### Dynamic Request Generation
```python
async def dynamic_requests(user_data):
    """Generate requests based on dynamic data"""
    for user in user_data:
        if user.is_active:
            request = HelloRequest(
                name=user.name,
                language=user.preferred_language
            )
            yield request
            
        # Add processing delay
        await asyncio.sleep(0.1)

# Usage
users = get_active_users()
response = await client.greeter_say_hello_client_stream(
    dynamic_requests(users)
)
```

### Conditional Streaming
```python
async def conditional_stream(max_requests=100):
    """Stream with conditions and limits"""
    count = 0
    
    while count < max_requests:
        # Check some condition
        if should_send_request():
            request = create_request(count)
            yield request
            count += 1
            
        await asyncio.sleep(0.1)
        
        # Break on external condition
        if external_stop_condition():
            break
```

### Batched Streaming
```python
async def batched_stream(data_batches):
    """Send requests in batches"""
    for batch in data_batches:
        for item in batch:
            request = HelloRequest(
                name=item.name,
                language=item.language
            )
            yield request
            
        # Pause between batches
        await asyncio.sleep(1.0)
```

## Performance Considerations

### Connection Management
- WebSocket connections are automatically managed
- Connections are properly closed even on errors
- Consider connection pooling for high-frequency calls

### Memory Usage
- Use generators to avoid loading all requests in memory
- Process data incrementally when possible

### Error Recovery
```python
async def resilient_streaming(requests, max_retries=3):
    """Streaming with retry logic"""
    for attempt in range(max_retries):
        try:
            response = await client.greeter_say_hello_client_stream(requests)
            return response
            
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"Attempt {attempt + 1} failed, retrying...")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise e
```

## Testing Client Streaming

### Unit Tests
```python
import pytest

@pytest.mark.asyncio
async def test_client_streaming():
    client = ExampleClient("http://localhost:8000")
    
    async def test_requests():
        for i in range(3):
            yield HelloRequest(name=f"Test {i}", language="en")
    
    response = await client.greeter_say_hello_client_stream(test_requests())
    assert response.message is not None
```

### Integration Tests
```python
@pytest.mark.asyncio
async def test_large_stream():
    """Test with many requests"""
    client = ExampleClient("http://localhost:8000")
    
    async def large_stream():
        for i in range(1000):
            yield HelloRequest(name=f"User {i}", language="en")
    
    response = await client.greeter_say_hello_client_stream(large_stream())
    assert "1000" in response.message  # Assuming server counts requests
```

## Troubleshooting

### Common Issues

1. **Connection Timeout**
   - Increase client timeout
   - Check server availability
   - Verify WebSocket support

2. **Memory Issues**
   - Use generators instead of lists
   - Process data in chunks
   - Monitor memory usage

3. **Network Issues**
   - Add retry logic
   - Handle connection drops gracefully
   - Use appropriate timeouts

### Debug Tips

```python
import logging

# Enable debug logging
logging.getLogger("example.client.example_client").setLevel(logging.DEBUG)

# Add request/response logging
async def debug_stream():
    for i in range(5):
        request = HelloRequest(name=f"Debug {i}", language="en")
        print(f"Sending: {request}")
        yield request
```

## See Also

- [Client Testing Guide](tests/README.md)
- [Performance Examples](client_streaming_example.py)
- [WebSocket Configuration](../grpc_fastapi_gateway/README.md)
