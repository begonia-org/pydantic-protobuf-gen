"""
客户端流式传输测试示例
"""
import asyncio
import json
import websockets
from example.models.helloworld_model import HelloRequest, HelloReply


async def test_client_streaming_websocket():
    """测试客户端流式传输 WebSocket 端点"""
    uri = "ws://localhost:8000/v1/helloworld/client-stream"
    
    try:
        async with websockets.connect(uri) as websocket:
            # 发送多个请求
            requests = [
                HelloRequest(name="Alice", language="en"),
                HelloRequest(name="Bob", language="zh"),
                HelloRequest(name="Charlie", language="es"),
            ]
            
            print("发送客户端流式请求...")
            for i, request in enumerate(requests):
                message = request.model_dump_json()
                await websocket.send(message)
                print(f"发送请求 {i+1}: {request.name}")
                await asyncio.sleep(0.1)  # 模拟客户端间隔发送
            
            # 接收服务器响应
            print("\n等待服务器响应...")
            async for message in websocket:
                data = json.loads(message)
                print(f"收到响应: {data}")
                
                if data.get("type") == "response":
                    response = HelloReply.model_validate(data["data"])
                    print(f"最终响应: {response.message}")
                elif data.get("type") == "complete":
                    print("流式传输完成")
                    break
                elif data.get("type") == "error":
                    print(f"错误: {data['error']}")
                    break
                    
    except Exception as e:
        print(f"WebSocket 测试失败: {e}")


async def test_client_streaming_http():
    """测试客户端流式传输 HTTP 端点（使用分块传输编码）"""
    import httpx
    
    url = "http://localhost:8000/v1/helloworld/client-stream"
    
    # 准备多个请求数据
    requests = [
        HelloRequest(name="Alice", language="en"),
        HelloRequest(name="Bob", language="zh"),
        HelloRequest(name="Charlie", language="es"),
    ]
    
    # 构建请求体（每行一个 JSON 对象）
    request_lines = []
    for request in requests:
        request_lines.append(request.model_dump_json())
    
    request_body = '\n'.join(request_lines)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                content=request_body,
                headers={
                    "Content-Type": "application/json",
                    "Transfer-Encoding": "chunked"
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get("code") == 0:
                    reply_data = data.get("data")
                    if reply_data:
                        reply = HelloReply.model_validate(reply_data)
                        print(f"HTTP 客户端流式响应: {reply.message}")
                    else:
                        print("HTTP 客户端流式传输成功，无返回数据")
                else:
                    print(f"HTTP 响应错误: {data}")
            else:
                print(f"HTTP 请求失败: {response.status_code} - {response.text}")
                
    except Exception as e:
        print(f"HTTP 测试失败: {e}")


async def main():
    """运行测试"""
    print("=== gRPC 客户端流式传输测试 ===")
    print()
    
    print("1. 测试 WebSocket 客户端流式传输:")
    await test_client_streaming_websocket()
    print()
    
    print("2. 测试 HTTP 客户端流式传输:")
    await test_client_streaming_http()
    print()
    
    print("测试完成！")


if __name__ == "__main__":
    asyncio.run(main())
