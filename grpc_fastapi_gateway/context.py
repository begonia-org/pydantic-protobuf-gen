from typing import List
from typing import Any, Tuple
import fastapi
import grpc

from grpc_fastapi_gateway.utils import RequestToGrpc


class GRPCServicerContextAdapter(grpc.ServicerContext):
    """
    Adapter for gRPC ServicerContext.
    This class is used to adapt the gRPC ServicerContext to a format that can be used by the application.
    """

    def __init__(self, request: fastapi.Request, response: fastapi.Response):
        self._request: fastapi.Request = request
        self._response: fastapi.Response = response
        self._code: int = grpc.StatusCode.OK
        self._details: Any = None
        self._message: str = "ok"
        self._trailing_metadata: dict[str, str] = {}
        self._initial_metadata = {}

    def peer(self):
        """
        Get the peer information from the context.
        Returns:
            The peer information as a string.
        """
        peer = self._request.headers.get("x-forwarded-for")
        if not peer:
            peer = self._request.client.host
        return peer

    def peer_identities(self):
        """
        Get the peer identities from the context.
        Returns:
            An iterable of peer identities as bytes.
        """
        return [self._request.headers.get("x-forwarded-for", "").encode()]

    def peer_identity_key(self):
        """
        Get the peer identity key from the context.
        Returns:
            The peer identity key as a string.
        """
        return "x-forwarded-for"

    def auth_context(self):
        """
        Get the authentication context from the context.
        Returns:
            A dictionary representing the authentication context.
        """
        return {
            key: [value.encode()]
            for key, value in self._request.headers.items()
            if value is not None
        }

    def set_trailing_metadata(self, trailing_metadata: List[Tuple[str, str]]):
        """
        Set the trailing metadata for the RPC.
        Args:
            trailing_metadata: The trailing metadata to set.
        """
        if self._response:
            self._response.headers.update({k: v for k, v in trailing_metadata})
        self._trailing_metadata = trailing_metadata

    def trailing_metadata(self) -> dict[str, str]:
        """
        Access the trailing metadata for the RPC.
        Returns:
            The trailing metadata as a dictionary.
        """
        return self._trailing_metadata

    def send_initial_metadata(self, initial_metadata: List[tuple[str, str]]):
        """
        Send the initial metadata to the client.
        Args:
            initial_metadata: The initial metadata to send.
        """
        # This method is not implemented in this adapter, as it is not needed for the current use case.
        self._initial_metadata = initial_metadata
        if self._response:
            self._response.init_headers({k: v for k, v in initial_metadata})

    def set_code(self, code):
        self._code = code
        if self._response:
            self._response.status_code = RequestToGrpc.grpc_status_to_http_status(code)

    def code(self):
        """
        Get the status code from the context.
        Returns:
            The status code as an integer.
        """
        return self._code

    def set_details(self, details):
        self._details = details
        if self._response:
            self._response.headers["grpc-message"] = details

    def details(self):
        """
        Get the details from the context.
        Returns:
            The details as a string.
        """
        return self._details if self._details is not None else "No details provided"

    def abort(self, code, message):
        self._code = code
        self._message = message
        raise fastapi.exceptions.HTTPException(code, f"Aborted with {message}")

    def abort_with_status(self, status):
        """
        Abort the RPC with a given status.
        Args:
            status: The status to abort with.
        """
        self._code = status.code
        self._message = status.details
        raise fastapi.exceptions.HTTPException(
            status.code, f"Aborted with {status.details}"
        )

    def disable_next_message_compression(self):
        """
        Disable compression for the next response message.
        This method is not implemented in this adapter, as it is not needed for the current use case.
        """
        pass

    def invocation_metadata(self):
        """
        Get the invocation metadata from the context.
        Returns:
            The invocation metadata as a dictionary.
        """
        headers = self._request.headers
        return [(k, v) for k, v in headers.items()]

    def add_callback(self, callback):
        pass

    def cancel(self):
        """
        Cancel the RPC.
        This method is not implemented in this adapter, as it is not needed for the current use case.
        """
        raise fastapi.HTTPException(
            status_code=fastapi.status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="RPC cancelled",
        )

    def is_active(self):
        """
        Check if the RPC is active.
        Returns:
            True if the RPC is active, False otherwise.
        """
        return True

    def time_remaining(self):
        """
        Get the time remaining for the RPC.
        Returns:
            The time remaining in seconds.
        """
        # This method is not implemented in this adapter, as it is not needed for the current use case.
        return None
