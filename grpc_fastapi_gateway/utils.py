import struct
from typing import Type
from google.protobuf import message as _message
import grpc


class RequestToGrpc:
    """
    Converts a request header dictionary to gRPC metadata.
    """

    @staticmethod
    def convert_metadata(request_header: dict) -> list[tuple[str, str]]:
        """
        Convert request header dictionary to gRPC metadata.

        Args:
            request_header (dict): The request header dictionary.

        Returns:
            list[tuple[str, str]]: The converted gRPC metadata.
        """
        return [(key, str(value)) for key, value in request_header.items()]

    @staticmethod
    def decompress_body(compressed_data: bytes, algorithm: str) -> bytes:
        if algorithm == "gzip":
            import gzip

            return gzip.decompress(compressed_data)
        elif algorithm == "deflate":
            import zlib

            return zlib.decompress(compressed_data)
        elif algorithm == "brotli":
            import brotli

            return brotli.decompress(compressed_data)
        elif algorithm == "zstd":
            import zstandard

            dctx = zstandard.ZstdDecompressor()
            return dctx.decompress(compressed_data)
        else:
            raise ValueError(f"Unsupported algorithm: {algorithm}")

    @staticmethod
    def parse_grpc_message(
        raw_data: bytes, messsage_cls: Type[_message.Message], algorithm="gzip"
    ):
        """
        Parse raw gRPC message data into a protobuf message object.

        Args:
            raw_data (bytes): The raw gRPC message data.
            messsage_cls: The protobuf message class to parse into.

        Returns:
            messsage_cls: The parsed protobuf message object.
        """
        if not raw_data:
            return None
        compression_flag = raw_data[0]
        message_length = int.from_bytes(raw_data[1:5], "big")
        message_body = raw_data[5 : 5 + message_length]
        if compression_flag == 0x01:
            try:
                message_body = RequestToGrpc.decompress_body(message_body, algorithm)
            except Exception as e:
                raise ValueError(f"Failed to decompress message body: {e}")
        message = messsage_cls()
        try:
            message.ParseFromString(message_body)
        except Exception as e:
            raise ValueError(f"Failed to parse message: {e}")
        return message

    @staticmethod
    def create_grpc_message(message: _message.Message, algorithm="") -> bytes:
        """
        Create a gRPC message with optional compression.

        Args:
            message (_message.Message): The protobuf message to serialize.
            algorithm (str): The compression algorithm to use.

        Returns:
            bytes: The serialized gRPC message.
        """
        if not message.IsInitialized():
            raise ValueError("Message is not initialized")
        serialized_message = message.SerializeToString()
        if algorithm == "gzip":
            import gzip

            compressed_message = gzip.compress(serialized_message)
        elif algorithm == "deflate":
            import zlib

            compressed_message = zlib.compress(serialized_message)
        elif algorithm == "brotli":
            import brotli

            compressed_message = brotli.compress(serialized_message)
        elif algorithm == "zstd":
            import zstandard

            cctx = zstandard.ZstdCompressor()
            compressed_message = cctx.compress(serialized_message)
        if algorithm not in ["gzip", "deflate", "brotli", "zstd"]:
            compressed_message = serialized_message
        compress_flag = 0x01 if algorithm else 0x00
        return (
            bytes([compress_flag])
            + len(compressed_message).to_bytes(4, "big")
            + compressed_message
        )

    @staticmethod
    def create_empty_grpc_message() -> bytes:
        """
        Create an empty gRPC message with no compression.
        This is used to indicate an empty request or response.
        Returns:
            bytes: The serialized empty gRPC message.
        """
        return struct.pack("!BI", 0x00, 0x00000000)

    @staticmethod
    def http_status_to_grpc_status(status_code: int) -> grpc.StatusCode:
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

    @staticmethod
    def grpc_status_to_http_status(status_code: grpc.StatusCode) -> int:
        if status_code == grpc.StatusCode.OK:
            return 200
        elif status_code == grpc.StatusCode.INVALID_ARGUMENT:
            return 400
        elif status_code == grpc.StatusCode.UNAUTHENTICATED:
            return 401
        elif status_code == grpc.StatusCode.PERMISSION_DENIED:
            return 403
        elif status_code == grpc.StatusCode.NOT_FOUND:
            return 404
        elif status_code == grpc.StatusCode.ALREADY_EXISTS:
            return 409
        elif status_code == grpc.StatusCode.INTERNAL:
            return 500
        else:
            return 500
