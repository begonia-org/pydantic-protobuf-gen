# 将 diff 内容保存到文件
cat > hypercorn_h2.patch << 'EOF'
--- /opt/.uv.venv/lib/python3.11/site-packages/hypercorn/protocol/h2.py 2025-06-17 08:36:05.203296492 +0000
+++ h2.py       2025-06-17 08:34:56.611146226 +0000
@@ -217,7 +217,10 @@
                 await self.has_data.set()
                 await self.stream_buffers[event.stream_id].drain()
             elif isinstance(event, Trailers):
-                self.connection.send_headers(event.stream_id, event.headers)
+                self.priority.unblock(event.stream_id)
+                await self.has_data.set()
+                await self.stream_buffers[event.stream_id].drain()
+                self.connection.send_headers(event.stream_id, event.headers, end_stream=True)
                 await self._flush()
             elif isinstance(event, StreamClosed):
                 await self._close_stream(event.stream_id)
EOF

# 应用补丁
patch /opt/.uv.venv/lib/python3.11/site-packages/hypercorn/protocol/h2.py < hypercorn_h2.patch