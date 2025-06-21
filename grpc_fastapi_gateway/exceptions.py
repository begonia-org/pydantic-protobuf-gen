import grpc


def http_status_to_grpc_status(status_code: int) -> grpc.StatusCode:
    """将 HTTP 状态码转换为 gRPC 状态码"""
    if 200 <= status_code < 300:
        return grpc.StatusCode.OK
    elif status_code == 400:
        return grpc.StatusCode.INVALID_ARGUMENT
    elif status_code == 401:
        return grpc.StatusCode.UNAUTHENTICATED
    elif status_code == 403:
        return grpc.StatusCode.PERMISSION_DENIED
    elif status_code == 404:
        return grpc.StatusCode.NOT_FOUND
    elif status_code == 409:
        return grpc.StatusCode.ALREADY_EXISTS
    elif status_code == 500:
        return grpc.StatusCode.INTERNAL
    else:
        return grpc.StatusCode.UNKNOWN


class GrpcError(Exception):
    """自定义 gRPC 错误异常"""

    def __init__(self, message: str, status_code: grpc.StatusCode):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
