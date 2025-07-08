#!/usr/bin/env python3
"""
示例：使用纯Python H2Protocol补丁的完整示例

这个示例展示了如何在实际应用中使用我们的H2Protocol补丁。
"""

import asyncio
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GrpcFastApiGateway:
    """
    一个示例的gRPC FastAPI网关类，演示如何使用H2Protocol补丁
    """

    def __init__(self):
        self.is_patched = False
        self.server = None

    def apply_h2_patch(self, use_minimal: bool = True):
        """
        应用H2协议补丁

        Args:
            use_minimal: 是否使用最小化补丁（推荐）
        """
        try:
            if use_minimal:
                from grpc_fastapi_gateway.patch import patch_h2_protocol_minimal

                patch_h2_protocol_minimal()
                logger.info("✓ Applied minimal H2Protocol patch")
            else:
                from grpc_fastapi_gateway.patch import patch_h2_protocol

                patch_h2_protocol()
                logger.info("✓ Applied full H2Protocol patch")

            self.is_patched = True

        except Exception as e:
            logger.error(f"✗ Failed to apply H2Protocol patch: {e}")
            raise

    def verify_patch(self):
        """验证补丁是否正确应用"""
        if not self.is_patched:
            logger.warning("⚠ Patch not applied yet")
            return False

        try:
            from hypercorn.protocol.h2 import H2Protocol

            method_name = H2Protocol.stream_send.__name__
            logger.info(f"Current stream_send method: {method_name}")

            if "patched" in method_name:
                logger.info("✓ Patch verification successful")
                return True
            else:
                logger.warning("⚠ Patch may not be applied correctly")
                return False

        except Exception as e:
            logger.error(f"✗ Patch verification failed: {e}")
            return False

    async def simulate_trailers_handling(self):
        """模拟trailers事件处理"""
        logger.info("Simulating gRPC trailers handling...")

        try:
            from hypercorn.protocol.events import Trailers

            # 创建模拟的trailers事件
            trailers_event = Trailers(
                stream_id=123,
                headers=[
                    (b"grpc-status", b"0"),
                    (b"grpc-message", b"Request processed successfully"),
                    (b"content-type", b"application/grpc"),
                ],
            )

            logger.info("Created Trailers event:")
            logger.info(f"  Stream ID: {trailers_event.stream_id}")
            logger.info(f"  Headers: {trailers_event.headers}")

            # 在实际应用中，这里会被H2Protocol.stream_send处理
            logger.info("✓ Trailers event would be processed by patched stream_send")

            return True

        except Exception as e:
            logger.error(f"✗ Trailers simulation failed: {e}")
            return False

    async def start_server(self, host: str = "127.0.0.1", port: int = 8000):
        """启动服务器（模拟）"""
        logger.info(f"Starting gRPC-FastAPI gateway on {host}:{port}")

        if not self.is_patched:
            logger.warning(
                "⚠ Starting without H2Protocol patch - this may cause issues"
            )

        # 在实际应用中，这里会启动Hypercorn服务器
        # 例如：
        # from hypercorn.asyncio import serve
        # from hypercorn.config import Config
        # config = Config()
        # config.bind = [f"{host}:{port}"]
        # await serve(app, config)

        logger.info("✓ Server started successfully (simulation)")
        await asyncio.sleep(1)  # 模拟运行时间

    async def stop_server(self):
        """停止服务器"""
        logger.info("Stopping server...")
        # 在实际应用中，这里会执行清理工作
        logger.info("✓ Server stopped")


async def main():
    """主函数演示完整的使用流程"""
    logger.info("=== gRPC FastAPI Gateway with H2Protocol Patch ===")

    # 创建网关实例
    gateway = GrpcFastApiGateway()

    try:
        # 步骤1: 应用H2协议补丁
        logger.info("Step 1: Applying H2Protocol patch...")
        gateway.apply_h2_patch(use_minimal=True)

        # 步骤2: 验证补丁
        logger.info("Step 2: Verifying patch...")
        if not gateway.verify_patch():
            logger.error("Patch verification failed, stopping...")
            return

        # 步骤3: 模拟trailers处理
        logger.info("Step 3: Testing trailers handling...")
        if not await gateway.simulate_trailers_handling():
            logger.error("Trailers handling test failed, stopping...")
            return

        # 步骤4: 启动服务器（模拟）
        logger.info("Step 4: Starting server...")
        await gateway.start_server()

        # 步骤5: 模拟一些工作
        logger.info("Step 5: Server running... (simulating work)")
        for i in range(3):
            await asyncio.sleep(1)
            logger.info(f"  Processing requests... {i + 1}/3")

        # 步骤6: 停止服务器
        logger.info("Step 6: Stopping server...")
        await gateway.stop_server()

        logger.info("🎉 All steps completed successfully!")

    except Exception as e:
        logger.error(f"✗ Error in main execution: {e}")
        raise


def demo_usage_patterns():
    """演示不同的使用模式"""
    logger.info("\n=== Usage Patterns Demo ===")

    # 模式1: 直接使用
    logger.info("Pattern 1: Direct usage")
    try:
        from grpc_fastapi_gateway.patch import patch_h2_protocol_minimal

        patch_h2_protocol_minimal()
        logger.info("✓ Direct patch application successful")
    except Exception as e:
        logger.error(f"✗ Direct patch failed: {e}")

    # 模式2: 条件应用
    logger.info("Pattern 2: Conditional application")
    try:
        import os

        if os.getenv("ENABLE_GRPC_PATCH", "true").lower() == "true":
            from grpc_fastapi_gateway.patch import patch_h2_protocol_minimal

            patch_h2_protocol_minimal()
            logger.info("✓ Conditional patch application successful")
        else:
            logger.info("✓ Patch disabled by environment variable")
    except Exception as e:
        logger.error(f"✗ Conditional patch failed: {e}")

    # 模式3: 错误处理
    logger.info("Pattern 3: Error handling")
    try:
        from grpc_fastapi_gateway.patch import patch_h2_protocol_minimal

        patch_h2_protocol_minimal()
        logger.info("✓ Error handling pattern successful")
    except ImportError:
        logger.warning("⚠ Required modules not available, skipping patch")
    except Exception as e:
        logger.error(f"✗ Unexpected error: {e}")


if __name__ == "__main__":
    # 演示使用模式
    demo_usage_patterns()

    # 运行主演示
    asyncio.run(main())
