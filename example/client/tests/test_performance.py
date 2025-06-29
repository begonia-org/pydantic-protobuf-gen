"""
Performance and load tests for ExampleClient
"""
import asyncio
import time
import statistics
from example.client.example_client import ExampleClient
from example.models.helloworld_model import HelloRequest


class TestClientPerformance:
    """Performance tests for the client"""

    def setup_method(self):
        """Setup for each test method"""
        self.client = ExampleClient(
            base_url="http://localhost:8010",
            timeout=30.0
        )

    async def test_single_call_latency(self):
        """Test latency of a single call"""
        request = HelloRequest(name="PerfTest", language="en")
        
        start_time = time.time()
        response = await self.client.greeter_say_hello(request)
        end_time = time.time()
        
        latency = (end_time - start_time) * 1000  # Convert to milliseconds
        print(f"Single call latency: {latency:.2f}ms")
        
        assert response.message is not None
        assert latency < 5000  # Should be less than 5 seconds

    async def test_concurrent_calls_throughput(self):
        """Test throughput with concurrent calls"""
        request = HelloRequest(name="ConcurrentTest", language="en")
        num_calls = 10
        
        async def make_call():
            return await self.client.greeter_say_hello(request)
        
        start_time = time.time()
        tasks = [make_call() for _ in range(num_calls)]
        responses = await asyncio.gather(*tasks)
        end_time = time.time()
        
        total_time = end_time - start_time
        throughput = num_calls / total_time
        
        print(f"Concurrent calls: {num_calls}")
        print(f"Total time: {total_time:.2f}s")
        print(f"Throughput: {throughput:.2f} calls/second")
        
        assert len(responses) == num_calls
        assert all(r.message is not None for r in responses)

    async def test_streaming_performance(self):
        """Test streaming call performance"""
        request = HelloRequest(name="StreamTest", language="en")
        
        start_time = time.time()
        response_count = 0
        
        async for response in self.client.greeter_say_hello_stream_reply(request):
            response_count += 1
            if response_count >= 6:  # Test with 10 responses
                break
        
        end_time = time.time()
        total_time = end_time - start_time
        
        print(f"Streaming test - {response_count} responses in {total_time:.2f}s")
        print(f"Rate: {response_count/total_time:.2f} responses/second")
        print(f"Response count: {response_count} seconds")
        assert response_count == 6

    async def test_latency_distribution(self):
        """Test latency distribution over multiple calls"""
        request = HelloRequest(name="LatencyTest", language="en")
        latencies = []
        
        for i in range(20):
            start_time = time.time()
            await self.client.greeter_say_hello(request)
            end_time = time.time()
            
            latency = (end_time - start_time) * 1000
            latencies.append(latency)
        
        avg_latency = statistics.mean(latencies)
        median_latency = statistics.median(latencies)
        min_latency = min(latencies)
        max_latency = max(latencies)
        
        print("Latency statistics over 20 calls:")
        print(f"  Average: {avg_latency:.2f}ms")
        print(f"  Median: {median_latency:.2f}ms")
        print(f"  Min: {min_latency:.2f}ms")
        print(f"  Max: {max_latency:.2f}ms")
        
        assert avg_latency < 1000  # Average should be less than 1 second

    async def test_client_streaming_performance(self):
        """Test client streaming performance"""
        request_count = 50
        
        async def performance_stream():
            for i in range(request_count):
                yield HelloRequest(name=f"PerfUser{i}", language="en")
        
        start_time = time.time()
        response = await self.client.greeter_say_hello_stream(performance_stream())
        end_time = time.time()
        
        total_time = end_time - start_time
        throughput = request_count / total_time
        
        print("Client streaming performance:")
        print(f"  Requests: {request_count}")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} requests/second")
        
        assert response.message is not None
        assert total_time < 30  # Should complete within 30 seconds


if __name__ == "__main__":
    async def run_tests():
        test_instance = TestClientPerformance()
        test_instance.setup_method()
        
        print("Running performance tests...")
        print("=" * 50)
        
        await test_instance.test_single_call_latency()
        print()
        
        await test_instance.test_concurrent_calls_throughput()
        print()
        
        await test_instance.test_streaming_performance()
        print()
        
        await test_instance.test_latency_distribution()
        print()
        
        await test_instance.test_client_streaming_performance()
        print()
        
        print("All performance tests completed!")

    asyncio.run(run_tests())
