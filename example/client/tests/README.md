# Client Tests

This directory contains comprehensive tests for the ExampleClient.

## Test Files

- `test_client.py` - Main integration and unit tests
- `test_performance.py` - Performance and load tests  
- `run_tests.py` - Test runner script
- `conftest.py` - Test configuration

## Prerequisites

1. Make sure your gRPC FastAPI server is running on `http://localhost:8000`
2. Install required dependencies:
   ```bash
   pip install pytest pytest-asyncio httpx
   ```

## Running Tests

### Option 1: Using the test runner (Recommended)
```bash
cd /app
python example/client/tests/run_tests.py
```

### Option 2: Using pytest directly
```bash
cd /app
python -m pytest example/client/tests/test_client.py -v -s
```

### Option 3: Running specific test classes
```bash
# Integration tests only
python -m pytest example/client/tests/test_client.py::TestExampleClientIntegration -v -s

# Unit tests only  
python -m pytest example/client/tests/test_client.py::TestExampleClientUnit -v -s

# Performance tests
python example/client/tests/test_performance.py
```

## Test Categories

### Integration Tests (`TestExampleClientIntegration`)
- Tests against actual running server
- Validates all RPC types: unary, server streaming, bidirectional streaming
- Tests concurrent calls
- Tests error handling and timeouts

### Unit Tests (`TestExampleClientUnit` & `TestModelValidation`)
- Tests client helper methods
- Tests model validation and serialization
- No server required

### Performance Tests (`TestClientPerformance`)
- Measures latency and throughput
- Tests concurrent call performance
- Generates performance statistics

## Sample Output

```
✓ SayHello response: Hello, Alice!
✓ Stream response: Hello, Bob! (1/3)
✓ Stream response: Hello, Bob! (2/3)
→ Sending: Charlie
← Received: Hello, Charlie!
✓ Concurrent call 1: Hello, User1!
✓ Error handling test passed
✓ Timeout handling test passed

Performance Results:
Single call latency: 45.23ms
Concurrent calls: 10
Total time: 0.52s
Throughput: 19.23 calls/second
```

## Troubleshooting

1. **Server not running**: Start your gRPC FastAPI server first
2. **Import errors**: Make sure you're running from the `/app` directory
3. **Timeout errors**: Increase timeout values if your server is slow
4. **pytest not found**: Install with `pip install pytest pytest-asyncio`
