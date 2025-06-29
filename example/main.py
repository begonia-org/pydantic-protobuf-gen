#!/usr/bin/env python3
"""Minimal gRPC example server.

The legacy FastAPI gateway path has been retired. This example now exposes the
underlying gRPC service only.
"""

import asyncio
import logging

import grpc
from grpc import aio

from example.pb import helloworld_pb2
from example.pb import helloworld_pb2_grpc

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class GreeterServicer(helloworld_pb2_grpc.GreeterServicer):
    """实现 Greeter 服务"""

    def __init__(self):
        self.greeting_templates = {
            "en": "Hello, {name}!",
            "zh": "你好，{name}！",
            "es": "¡Hola, {name}!",
            "fr": "Bonjour, {name}!",
            "de": "Hallo, {name}!",
            "ja": "こんにちは、{name}さん！",
        }

    def _get_greeting(self, name: str, language: str) -> str:
        """根据语言生成问候语"""
        template = self.greeting_templates.get(language, self.greeting_templates["en"])
        return template.format(name=name)

    async def SayHello(self, request, context):
        """单次问候 RPC"""
        print(
            f"Received SayHello request: name={request.name}, language={request.language}"
        )

        # 验证输入
        if not request.name.strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Name cannot be empty")
            return helloworld_pb2.HelloReply()

        # 生成问候消息
        message = self._get_greeting(request.name, request.language or "en")

        response = helloworld_pb2.HelloReply(
            message=message, language=request.language or "en"
        )

        logger.info(f"Sending response: {response.message}")
        return response

    async def SayHelloStream(self, request_iterator, context):
        """流式问候 RPC - 服务器返回多个问候"""
        logger.info("Starting streaming SayHello")

        async for request in request_iterator:
            logger.info(
                f"Received SayHelloStream streaming request: name={request.name}, language={request.language}"
            )

            if not request.name.strip():
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details("Name cannot be empty")
                yield helloworld_pb2.HelloReply()
                continue

            # 生成问候消息
            message = self._get_greeting(request.name, request.language or "en")
            response = helloworld_pb2.HelloReply(
                message=message, language=request.language or "en"
            )

            logger.info(f"Sending response: {response.message}")
            yield response

    async def SayHelloStreamReply(self, request, context):
        """流式回复 RPC - 服务器返回多个问候"""
        logger.info(
            f"Received SayHelloStreamReply request: name={request.name}, language={request.language}"
        )

        if not request.name.strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Name cannot be empty")
            return

        # 返回多种语言的问候
        languages = ["en", "zh", "es", "fr", "de", "ja"]
        target_lang = request.language or "en"

        # 如果指定了语言，先返回指定语言的问候
        if target_lang in languages:
            message = self._get_greeting(request.name, target_lang)
            yield helloworld_pb2.HelloReply(message=message, language=target_lang)
            await asyncio.sleep(0.5)  # 模拟处理时间

        # 然后返回其他语言的问候
        for lang in languages:
            if lang != target_lang:
                message = self._get_greeting(request.name, lang)
                yield helloworld_pb2.HelloReply(message=message, language=lang)
                await asyncio.sleep(0.5)  # 模拟处理时间

    async def SayHelloBidiStream(self, request_iterator, context):
        """双向流 RPC - 客户端和服务器都可以发送多个消息"""
        logger.info("Starting bidirectional streaming")

        async for request in request_iterator:
            logger.info(
                f"Received SayHelloBidiStream streaming request: name={request.name}, language={request.language}"
            )

            if not request.name.strip():
                # 发送错误响应
                yield helloworld_pb2.HelloReply(
                    message="Error: Name cannot be empty", language="en"
                )
                continue

            # 为每个请求生成问候
            message = self._get_greeting(request.name, request.language or "en")
            response = helloworld_pb2.HelloReply(
                message=message, language=request.language or "en"
            )

            yield response

            # 额外发送一个确认消息
            confirmation = helloworld_pb2.HelloReply(
                message=f"Processed greeting for {request.name}", language="en"
            )
            yield confirmation

    async def AuthCheck(self, request, context) -> helloworld_pb2.HelloReply:
        """验证用户身份的 RPC"""
        logger.info(f"Received AuthCheck request: name={request.name}")

        # 验证输入
        if not request.name.strip():
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details("Name cannot be empty")
            return helloworld_pb2.HelloReply()

        # 生成问候消息
        message = self._get_greeting(request.name, request.language or "en")

        response = helloworld_pb2.HelloReply(
            message=message, language=request.language or "en"
        )

        logger.info(f"Sending AuthCheck response: {response.message}")
        return response

    async def Health(self, request, context) -> helloworld_pb2.HealthResponse:
        return helloworld_pb2.HealthResponse(healthy=True, message="Service is healthy")


async def grpc_serve():
    """启动 gRPC 服务器"""
    server = aio.server()
    # 添加服务
    helloworld_pb2_grpc.add_GreeterServicer_to_server(GreeterServicer(), server)
    # 配置监听地址
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logger.info(f"Starting gRPC server on {listen_addr}")
    try:
        await server.start()
        logger.info("Server started successfully")
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("Shutting down server...")
        await server.stop(grace=5)
    except Exception as e:
        logger.error(f"Server error: {e}")
        await server.stop(grace=5)


if __name__ == "__main__":
    asyncio.run(grpc_serve())
