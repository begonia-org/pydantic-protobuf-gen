"""
Test runner for client tests
Usage: python run_tests.py
"""
import asyncio
import sys
import subprocess


def run_unit_tests():
    """Run unit tests with pytest"""
    print("Running unit tests...")
    print("=" * 50)
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "example/client/tests/test_client.py",
        "-v", "-s"
    ], capture_output=False)
    
    return result.returncode == 0


async def run_performance_tests():
    """Run performance tests"""
    print("\nRunning performance tests...")
    print("=" * 50)
    
    try:
        from example.client.tests.test_performance import TestClientPerformance
        
        test_instance = TestClientPerformance()
        test_instance.setup_method()
        
        await test_instance.test_single_call_latency()
        print()
        
        await test_instance.test_concurrent_calls_throughput()
        print()
        
        await test_instance.test_streaming_performance()
        print()
        
        await test_instance.test_latency_distribution()
        
        print("\n✓ All performance tests completed!")
        return True
        
    except Exception as e:
        print(f"✗ Performance tests failed: {e}")
        return False


def check_server():
    """Check if the server is running"""
    import httpx
    
    try:
        httpx.get("http://localhost:8010", timeout=5.0)
        return True
    except Exception:
        return False


async def main():
    """Main test runner"""
    print("gRPC FastAPI Client Test Runner")
    print("=" * 50)
    
    # Check if server is running
    if not check_server():
        print("⚠️  Warning: Server not detected at http://localhost:8010")
        print("   Make sure your gRPC FastAPI server is running before running integration tests.")
        print()
    
    # Run unit tests
    unit_success = run_unit_tests()
    
    # Run performance tests if server is available
    perf_success = True
    if check_server():
        perf_success = await run_performance_tests()
    else:
        print("\n⏭️  Skipping performance tests (server not available)")
    
    # Summary
    print("\n" + "=" * 50)
    print("Test Summary:")
    print(f"  Unit Tests: {'✓ PASSED' if unit_success else '✗ FAILED'}")
    print(f"  Performance Tests: {'✓ PASSED' if perf_success else '✗ FAILED'}")
    
    if unit_success and perf_success:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
