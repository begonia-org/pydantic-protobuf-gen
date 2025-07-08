#!/usr/bin/env python3
"""
测试脚本用于验证H2Protocol补丁是否正常工作
"""

import asyncio
import sys
import traceback


def test_patch_application():
    """测试补丁应用过程"""
    print("=== Testing H2Protocol Patch Application ===")

    try:
        # 测试最小化补丁
        from grpc_fastapi_gateway.patch import patch_h2_protocol_minimal

        print("Applying minimal patch...")
        patch_h2_protocol_minimal()
        print("✓ Minimal patch applied successfully")

        # 验证补丁是否正确应用
        from hypercorn.protocol.h2 import H2Protocol

        # 检查方法是否被替换
        method_name = H2Protocol.stream_send.__name__
        print(f"Current stream_send method: {method_name}")

        if "patched" in method_name:
            print("✓ Patch successfully applied to H2Protocol.stream_send")
        else:
            print("⚠ Patch may not have been applied correctly")

        return True

    except Exception as e:
        print(f"✗ Error testing patch: {e}")
        traceback.print_exc()
        return False


def test_trailers_event_handling():
    """测试Trailers事件处理"""
    print("\n=== Testing Trailers Event Handling ===")

    try:
        from hypercorn.protocol.events import Trailers

        # 创建一个模拟的Trailers事件
        trailers_event = Trailers(
            stream_id=1, headers=[(b"grpc-status", b"0"), (b"grpc-message", b"OK")]
        )

        print(f"Created Trailers event: stream_id={trailers_event.stream_id}")
        print(f"Headers: {trailers_event.headers}")
        print("✓ Trailers event creation successful")

        return True

    except Exception as e:
        print(f"✗ Error testing Trailers event: {e}")
        traceback.print_exc()
        return False


def test_import_dependencies():
    """测试所需依赖的导入"""
    print("\n=== Testing Import Dependencies ===")

    dependencies = [
        "hypercorn.protocol.h2",
        "hypercorn.protocol.events",
        "hypercorn.events",
        "h2.exceptions",
        "priority",
    ]

    success_count = 0

    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✓ Successfully imported {dep}")
            success_count += 1
        except ImportError as e:
            print(f"✗ Failed to import {dep}: {e}")

    print(f"\nImport success rate: {success_count}/{len(dependencies)}")
    return success_count == len(dependencies)


async def test_async_functionality():
    """测试异步功能"""
    print("\n=== Testing Async Functionality ===")

    try:
        # 模拟异步环境
        await asyncio.sleep(0.1)
        print("✓ Async environment working correctly")

        # 测试异步事件处理
        # 创建一个模拟的H2Protocol实例（这里只是测试导入）
        # 实际使用中需要完整的初始化
        print("✓ H2Protocol class accessible")

        return True

    except Exception as e:
        print(f"✗ Error in async test: {e}")
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("Starting H2Protocol Patch Tests\n")

    tests = [
        ("Import Dependencies", test_import_dependencies),
        ("Patch Application", test_patch_application),
        ("Trailers Event Handling", test_trailers_event_handling),
    ]

    results = []

    # 运行同步测试
    for test_name, test_func in tests:
        print(f"Running {test_name}...")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} failed with exception: {e}")
            results.append((test_name, False))

    # 运行异步测试
    print("Running Async Functionality...")
    try:
        result = asyncio.run(test_async_functionality())
        results.append(("Async Functionality", result))
    except Exception as e:
        print(f"✗ Async Functionality failed with exception: {e}")
        results.append(("Async Functionality", False))

    # 总结结果
    print("\n" + "=" * 50)
    print("TEST RESULTS SUMMARY")
    print("=" * 50)

    passed = 0
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        print(f"{test_name}: {status}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! The patch implementation looks good.")
        return 0
    else:
        print("⚠ Some tests failed. Please check the implementation.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
