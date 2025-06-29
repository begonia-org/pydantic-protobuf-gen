# gRPC 客户端流式传输指南

## 概述

客户端流式传输是 gRPC 的四种调用模式之一，允许客户端发送多个请求消息，服务器返回单个响应消息。本指南介绍如何在 gRPC FastAPI Gateway 中使用客户端流式传输。

## 支持的协议

### 1. WebSocket 协议（推荐）
- 适用于 HTTP/1.1 环境
- 提供真正的双向通信
- 支持实时数据传输

### 2. HTTP 分块传输编码
- 适用于 HTTP/2 环境
- 使用换行符分隔的 JSON 对象
- 兼容标准 HTTP 客户端

## 配置示例

### services.json 配置
```json
{
  "Greeter": {
    "SayHelloClientStream": {
      "input_type": ".helloworld.HelloRequest",
      "output_type": ".helloworld.HelloReply",
      "options": {
        "[google.api.http]": {
          "post": "/v1/helloworld/client-stream",
          "body": "*"
        }
      },
      "streaming_type": "client_streaming",
      "method_full_name": "/helloworld.Greeter/SayHelloClientStream",
      "http": {
        "method": "POST",
        "path": "/v1/helloworld/client-stream",
        "body": "*"
      }
    }
  }
}
```

### gRPC 服务定义
```protobuf
service Greeter {
  // 客户端流式传输：客户端发送多个请求，服务器返回单个响应
  rpc SayHelloClientStream(stream HelloRequest) returns (HelloReply) {
    option (google.api.http) = {
      post: "/v1/helloworld/client-stream"
      body: "*"
    };
  }
}
```

## 客户端使用示例

### 1. WebSocket 客户端

```python
import asyncio
import json
import websockets
from example.models.helloworld_model import HelloRequest, HelloReply

async def client_streaming_websocket():
    uri = "ws://localhost:8000/v1/helloworld/client-stream"
    
    async with websockets.connect(uri) as websocket:
        # 发送多个请求
        requests = [
            HelloRequest(name="Alice", language="en"),
            HelloRequest(name="Bob", language="zh"),
            HelloRequest(name="Charlie", language="es"),
        ]
        
        # 逐个发送请求
        for request in requests:
            message = request.model_dump_json()
            await websocket.send(message)
            print(f"发送: {request.name}")
        
        # 接收响应
        async for message in websocket:
            data = json.loads(message)
            
            if data.get("type") == "response":
                response = HelloReply.model_validate(data["data"])
                print(f"收到响应: {response.message}")
            elif data.get("type") == "complete":
                print("传输完成")
                break
            elif data.get("type") == "error":
                print(f"错误: {data['error']}")
                break
```

### 2. HTTP 客户端

```python
import httpx
from example.models.helloworld_model import HelloRequest, HelloReply

async def client_streaming_http():
    url = "http://localhost:8000/v1/helloworld/client-stream"
    
    # 准备多个请求（每行一个 JSON）
    requests = [
        HelloRequest(name="Alice", language="en"),
        HelloRequest(name="Bob", language="zh"),
        HelloRequest(name="Charlie", language="es"),
    ]
    
    # 构建请求体
    request_lines = [req.model_dump_json() for req in requests]
    request_body = '\n'.join(request_lines)
    
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
                reply = HelloReply.model_validate(data["data"])
                print(f"响应: {reply.message}")
```

### 3. JavaScript 客户端

```javascript
// WebSocket 客户端
const ws = new WebSocket('ws://localhost:8000/v1/helloworld/client-stream');

ws.onopen = () => {
    // 发送多个请求
    const requests = [
        { name: "Alice", language: "en" },
        { name: "Bob", language: "zh" },
        { name: "Charlie", language: "es" }
    ];
    
    requests.forEach(req => {
        ws.send(JSON.stringify(req));
    });
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'response') {
        console.log('收到响应:', data.data.message);
    } else if (data.type === 'complete') {
        console.log('传输完成');
        ws.close();
    } else if (data.type === 'error') {
        console.error('错误:', data.error);
    }
};
```

## 服务器端实现

### gRPC 服务实现
```python
import grpc
from typing import AsyncGenerator

class GreeterServicer:
    async def SayHelloClientStream(
        self, 
        request_iterator: AsyncGenerator[HelloRequest, None], 
        context: grpc.ServicerContext
    ) -> HelloReply:
        """客户端流式传输：接收多个请求，返回单个响应"""
        names = []
        
        # 收集所有请求
        async for request in request_iterator:
            names.append(request.name)
            print(f"收到请求: {request.name}")
        
        # 返回汇总响应
        combined_names = ", ".join(names)
        return HelloReply(
            message=f"Hello to all: {combined_names}!",
            language="en"
        )
```

## 错误处理

### WebSocket 错误响应
```json
{
  "type": "error",
  "error": "Validation error: name is required"
}
```

### HTTP 错误响应
```json
{
  "code": 400,
  "message": "Validation error",
  "data": null
}
```

## 性能优化建议

1. **批量处理**: 在服务器端收集多个请求后批量处理
2. **流控制**: 控制客户端发送速率，避免服务器过载
3. **超时设置**: 设置合理的连接和处理超时时间
4. **资源清理**: 确保 WebSocket 连接正确关闭

## 监控和调试

### 日志记录
```python
import logging

logger = logging.getLogger(__name__)

# 在服务方法中添加日志
async def SayHelloClientStream(self, request_iterator, context):
    request_count = 0
    async for request in request_iterator:
        request_count += 1
        logger.info(f"收到第 {request_count} 个请求: {request.name}")
    
    logger.info(f"客户端流式传输完成，共处理 {request_count} 个请求")
```

### 指标收集
- 请求计数
- 处理延迟
- 连接时长
- 错误率

## 常见问题

### Q: WebSocket 连接断开怎么办？
A: 实现重连机制和错误恢复逻辑。

### Q: HTTP 分块传输如何确保数据完整性？
A: 使用换行符分隔 JSON 对象，并在服务器端验证每个对象。

### Q: 如何处理大量并发客户端流？
A: 使用连接池和限流机制控制并发数量。

## 参考资料

- [gRPC 官方文档](https://grpc.io/docs/)
- [WebSocket 规范](https://tools.ietf.org/html/rfc6455)
- [HTTP/2 规范](https://tools.ietf.org/html/rfc7540)
