import socket
import ssl
import struct
from typing import Optional, Tuple
from minitel_lite_client.exceptions import ConnectionError, TimeoutError, ProtocolError
from minitel_lite_client.logger import get_logger

logger = get_logger(__name__)

class MiniTelLiteClient:
    """
    TCP client implementation for MiniTel-Lite Protocol Version 3.0
    
    This class handles the TCP communication layer with secure socket connections,
    implementing best practices for connection management, error handling, and
    data transmission.
    """
    
    DEFAULT_TIMEOUT = 5.0  # seconds
    DEFAULT_BUFFER_SIZE = 4096  # bytes
    
    def __init__(self, host: str, port: int, use_tls: bool = False, timeout: float = DEFAULT_TIMEOUT):
        """
        Initialize the MiniTel-Lite client
        
        Args:
            host: Server hostname or IP address
            port: Server port number
            use_tls: Whether to use TLS encryption (default: False)
            timeout: Connection timeout in seconds (default: 5.0)
        """
        self.host = host
        self.port = port
        self.use_tls = use_tls
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None
        self.ssl_context = self._create_ssl_context() if use_tls else None
        self.connected = False
        self.last_nonce = 0
    
    def connect(self) -> None:
        """
        Establish a connection to the MiniTel-Lite server
        
        Raises:
            ConnectionError: If connection fails
            TimeoutError: If connection times out
        """
        try:
            # Create TCP socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            
            # Connect to server
            logger.debug(f"Connecting to {self.host}:{self.port}")
            self.socket.connect((self.host, self.port))
            
            # Wrap with TLS if requested
            if self.use_tls and self.ssl_context:
                logger.debug("Upgrading connection to TLS")
                self.socket = self.ssl_context.wrap_socket(self.socket, server_hostname=self.host)
            
            self.connected = True
            logger.info("Successfully connected to server")
            
        except socket.timeout as e:
            logger.error(f"Connection timeout: {str(e)}")
            raise TimeoutError(f"Connection to {self.host}:{self.port} timed out after {self.timeout} seconds") from e
        except socket.error as e:
            logger.error(f"Connection error: {str(e)}")
            raise ConnectionError(f"Failed to connect to {self.host}:{self.port}: {str(e)}") from e
    
    def disconnect(self) -> None:
        """
        Gracefully disconnect from the server
        """
        if self.socket:
            try:
                logger.debug("Initiating graceful disconnect")
                self.socket.shutdown(socket.SHUT_RDWR)
            except socket.error as e:
                logger.warning(f"Error during shutdown: {str(e)}")
            finally:
                self.socket.close()
                self.socket = None
                self.connected = False
                logger.info("Successfully disconnected from server")
    
    def send(self, data: bytes) -> None:
        """
        Send data to the server
        
        Args:
            data: Bytes to send
            
        Raises:
            ConnectionError: If send operation fails
        """
        if not self.connected or not self.socket:
            logger.error("Attempted to send data while not connected")
            raise ConnectionError("Not connected to server")
        
        try:
            logger.debug(f"Sending {len(data)} bytes of data")
            self.socket.sendall(data)
        except socket.error as e:
            logger.error(f"Error sending data: {str(e)}")
            raise ConnectionError(f"Failed to send data: {str(e)}") from e
    
    def receive(self, buffer_size: int = DEFAULT_BUFFER_SIZE) -> bytes:
        """
        Receive data from the server
        
        Args:
            buffer_size: Size of buffer for receiving data
            
        Returns:
            Received bytes
            
        Raises:
            ConnectionError: If receive operation fails
        """
        if not self.connected or not self.socket:
            logger.error("Attempted to receive data while not connected")
            raise ConnectionError("Not connected to server")
        
        try:
            logger.debug(f"Receiving data with buffer size {buffer_size}")
            data = self.socket.recv(buffer_size)
            
            if not data:
                logger.warning("Empty response received - connection may be closed")
                raise ConnectionError("Connection closed by server")
            
            logger.debug(f"Received {len(data)} bytes of data")
            return data
        except socket.error as e:
            logger.error(f"Error receiving data: {str(e)}")
            raise ConnectionError(f"Failed to receive data: {str(e)}") from e
    
    def _create_ssl_context(self) -> ssl.SSLContext:
        """
        Create a secure SSL/TLS context
        
        Returns:
            Configured SSLContext object
        """
        logger.debug("Creating SSL context")
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        
        # Enforce secure protocols and cipher suites
        context.options |= ssl.OP_NO_SSLv2 | ssl.OP_NO_SSLv3 | ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1
        
        # Require certificate validation
        context.check_hostname = True
        context.verify_mode = ssl.CERT_REQUIRED
        
        # Use modern cipher suites
        context.set_ciphers("DEFAULT@SECLEVEL=2")
        
        return context
    
    def get_connection_status(self) -> bool:
        """
        Get the current connection status
        
        Returns:
            True if connected, False otherwise
        """
        return self.connected
    
    def get_last_nonce(self) -> int:
        """
        Get the last used nonce value
        
        Returns:
            Last nonce value
        """
        return self.last_nonce
    
    def set_last_nonce(self, nonce: int) -> None:
        """
        Set the last used nonce value
        
        Args:
            nonce: New nonce value
        """
        self.last_nonce = nonce
        logger.debug(f"Updated last nonce to {nonce}")
