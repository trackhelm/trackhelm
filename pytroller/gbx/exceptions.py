class GbxError(Exception):
    """Base GBX exception."""


class ConnectionClosed(GbxError):
    """Raised when the connection is closed."""


class AuthenticationError(GbxError):
    """Raised when authentication fails."""


class ProtocolError(GbxError):
    """Raised when protocol framing is invalid."""


class RequestTimeout(GbxError):
    """Raised when a request times out."""
