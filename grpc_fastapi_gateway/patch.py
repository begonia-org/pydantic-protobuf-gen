from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from hypercorn.protocol.h2 import H2Protocol


def patch_h2_protocol():
    """
    Patch the h2 protocol to support gRPC over HTTP/2.
    This is necessary for compatibility with FastAPI and other ASGI frameworks.

    This implementation uses monkey patching to modify the stream_send method
    instead of relying on external patch files.
    """
    try:
        from hypercorn.protocol.h2 import H2Protocol
        from hypercorn.protocol.events import Trailers
        from hypercorn.events import Updated

        async def patched_stream_send(self: "H2Protocol", event) -> None:
            """
            Patched version of stream_send that handles Trailers events properly for gRPC.

            The key change is in the Trailers handling:
            - Add priority.unblock(event.stream_id)
            - Set has_data event
            - Drain stream buffers
            - Send headers with end_stream=True
            """
            try:
                if isinstance(event, Trailers):
                    self.priority.unblock(event.stream_id)
                    await self.has_data.set()
                    await self.stream_buffers[event.stream_id].drain()
                    self.connection.send_headers(
                        event.stream_id, event.headers, end_stream=True
                    )
                    await self._flush()
                else:
                    from hypercorn.protocol.events import (
                        InformationalResponse,
                        Response,
                        Body,
                        Data,
                        EndBody,
                        EndData,
                        StreamClosed,
                        Request,
                    )

                    if isinstance(event, (InformationalResponse, Response)):
                        self.connection.send_headers(
                            event.stream_id,
                            [(b":status", b"%d" % event.status_code)]
                            + event.headers
                            + self.config.response_headers("h2"),
                        )
                        await self._flush()
                    elif isinstance(event, (Body, Data)):
                        self.priority.unblock(event.stream_id)
                        await self.has_data.set()
                        await self.stream_buffers[event.stream_id].push(event.data)
                    elif isinstance(event, (EndBody, EndData)):
                        self.stream_buffers[event.stream_id].set_complete()
                        self.priority.unblock(event.stream_id)
                        await self.has_data.set()
                        await self.stream_buffers[event.stream_id].drain()
                    elif isinstance(event, StreamClosed):
                        await self._close_stream(event.stream_id)
                        idle = len(self.streams) == 0 or all(
                            stream.idle for stream in self.streams.values()
                        )
                        if idle and self.context.terminated.is_set():
                            self.connection.close_connection()
                            await self._flush()
                        await self.send(Updated(idle=idle))
                    elif isinstance(event, Request):
                        await self._create_server_push(
                            event.stream_id, event.raw_path, event.headers
                        )

            except Exception as e:
                from hypercorn.protocol.h2 import BufferCompleteError
                import priority
                import h2.exceptions

                if isinstance(
                    e,
                    (
                        BufferCompleteError,
                        KeyError,
                        priority.MissingStreamError,
                        h2.exceptions.ProtocolError,
                    ),
                ):
                    return
                else:
                    raise

        # 应用猴子补丁
        H2Protocol.stream_send = patched_stream_send

        print("Successfully patched H2Protocol.stream_send for gRPC compatibility")

    except ImportError as e:
        print(f"Failed to import hypercorn modules: {e}")
        raise
    except Exception as e:
        print(f"Failed to apply H2Protocol patch: {e}")
        raise


def patch_h2_protocol_minimal():
    """
    A minimal version of the patch that only modifies the Trailers handling.
    This approach is safer as it preserves most of the original logic.
    """
    try:
        from hypercorn.protocol.h2 import H2Protocol
        from hypercorn.protocol.events import Trailers

        # 保存原始方法
        original_stream_send = H2Protocol.stream_send

        async def minimal_patched_stream_send(self: "H2Protocol", event) -> None:
            """
            Minimally patched version that only changes Trailers handling.
            """
            if isinstance(event, Trailers):
                # 应用gRPC特定的trailers处理
                self.priority.unblock(event.stream_id)
                await self.has_data.set()
                await self.stream_buffers[event.stream_id].drain()
                self.connection.send_headers(
                    event.stream_id, event.headers, end_stream=True
                )
                await self._flush()
            else:
                # 对于其他所有事件，使用原始方法
                await original_stream_send(self, event)

        # 应用补丁
        H2Protocol.stream_send = minimal_patched_stream_send

        print("Successfully applied minimal H2Protocol patch for gRPC Trailers")

    except ImportError as e:
        print(f"Failed to import hypercorn modules: {e}")
        raise
    except Exception as e:
        print(f"Failed to apply minimal H2Protocol patch: {e}")
        raise
