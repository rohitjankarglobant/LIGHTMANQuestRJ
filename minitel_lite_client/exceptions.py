class MiniTelLiteError(Exception):
    """Base class for all MiniTel-Lite client errors"""
    pass

class ConnectionError(MiniTelLiteError):
    """Raised when there's a connection-related error"""
    pass

class TimeoutError(MiniTelLiteError):
    """Raised when a connection times out"""
    pass

class ProtocolError(MiniTelLiteError):
    """Raised when there's a protocol-related error"""
    pass

class InvalidNonceError(ProtocolError):
    """Raised when a nonce validation fails"""
    pass

class UnknownCommandError(ProtocolError):
    """Raised when an unknown command is received"""
    pass

class MalformedFrameError(ProtocolError):
    """Raised when a frame is malformed"""
    pass

class HashValidationError(ProtocolError):
    """Raised when a hash validation fails"""
    pass

class Base64DecodeError(ProtocolError):
    """Raised when Base64 decoding fails"""
    pass
