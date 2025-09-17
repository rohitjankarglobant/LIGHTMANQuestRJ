import struct
import base64
import hashlib
from typing import Tuple, Optional, Dict, Any
from minitel_lite_client.exceptions import ProtocolError, InvalidNonceError, MalformedFrameError, HashValidationError, Base64DecodeError

# Protocol constants from PRD
CMD_HELLO = 0x01
CMD_DUMP = 0x02
CMD_STOP = 0x04

RESPONSE_HELLO_ACK = 0x81
RESPONSE_DUMP_OK = 0x83
RESPONSE_DUMP_FAILED = 0x82
RESPONSE_STOP_OK = 0x84

# Frame structure constants
CMD_SIZE = 1
NONCE_SIZE = 4
HASH_SIZE = 32
MIN_FRAME_SIZE = CMD_SIZE + NONCE_SIZE + HASH_SIZE

# Protocol version
PROTOCOL_VERSION = 3

class MiniTelLiteProtocol:
    """
    Implementation of the MiniTel-Lite Protocol Version 3.0
    
    This class handles the protocol-specific aspects of the communication,
    including frame encoding/decoding, command handling, and nonce validation.
    """
    
    def __init__(self):
        """Initialize the protocol handler"""
        self.client_nonce = 0
        self.last_sent_nonce = 0
        self.command_sequence = []
        self.logger = self._setup_logger()
    
    def _setup_logger(self):
        """Set up logger for the protocol handler"""
        import logging
        return logging.getLogger("minitel_lite_client")
    
    def encode_frame(self, cmd: int, nonce: int, payload: bytes = b"") -> bytes:
        """
        Encode a frame according to the MiniTel-Lite protocol
        
        Frame Format:
        LEN (2 bytes, big-endian) | DATA_B64 (LEN bytes, Base64 encoded)
        
        Binary Frame (after Base64 decoding):
        CMD (1 byte) | NONCE (4 bytes, big-endian) | PAYLOAD (0-65535 bytes) | HASH (32 bytes SHA-256)
        
        Args:
            cmd: Command ID (1 byte)
            nonce: 4-byte unsigned integer, big-endian
            payload: Command-specific data
            
        Returns:
            Encoded frame bytes (LEN + Base64 encoded data)
        """
        try:
            # Validate command
            if not isinstance(cmd, int) or not (0x00 <= cmd <= 0xFF):
                raise ProtocolError(f"Invalid command value: {cmd}")
            
            # Pack nonce as 4-byte big-endian
            nonce_bytes = struct.pack('!I', nonce)
            
            # Calculate hash
            hash_data = bytes([cmd]) + nonce_bytes + payload
            hash_value = hashlib.sha256(hash_data).digest()
            
            # Create binary frame
            binary_frame = bytes([cmd]) + nonce_bytes + payload + hash_value
            
            # Base64 encode the binary frame
            encoded_frame = base64.b64encode(binary_frame)
            
            # Prepend length prefix (2 bytes, big-endian)
            len_prefix = struct.pack('!H', len(encoded_frame))
            
            # Return complete frame (length prefix + Base64 encoded data)
            return len_prefix + encoded_frame
            
        except Exception as e:
            self.logger.error(f"Error encoding frame: {str(e)}")
            raise
    
    def decode_frame(self, data: bytes) -> Dict[str, Any]:
        """
        Decode a frame according to the MiniTel-Lite protocol
        
        Args:
            data: Raw frame data to decode
            
        Returns:
            Dictionary containing decoded frame components:
            {
                'cmd': command ID,
                'nonce': nonce value,
                'payload': command payload,
                'hash': SHA-256 hash
            }
        """
        try:
            if len(data) < 2:
                raise MalformedFrameError("Frame too short to contain length prefix")
            
            # Extract length prefix
            frame_length = struct.unpack('!H', data[:2])[0]
            remaining_data = data[2:]
            
            if len(remaining_data) < frame_length:
                raise MalformedFrameError(f"Frame data incomplete. Expected {frame_length} bytes, got {len(remaining_data)}")
            
            # Extract binary frame
            binary_frame = remaining_data[:frame_length]
            
            if len(binary_frame) < MIN_FRAME_SIZE:
                raise MalformedFrameError(f"Binary frame too short. Expected at least {MIN_FRAME_SIZE} bytes, got {len(binary_frame)}")
            
            # Always decode Base64 as per protocol specification
            try:
                decoded_data = base64.b64decode(binary_frame)
            except Exception as e:
                raise Base64DecodeError(f"Base64 decoding failed: {str(e)}")
            
            # Extract components
            cmd = decoded_data[0]
            nonce = struct.unpack('!I', decoded_data[1:5])[0]
            payload = decoded_data[5:-HASH_SIZE]
            hash_value = decoded_data[-HASH_SIZE:]
            
            # Validate hash
            expected_hash = hashlib.sha256(decoded_data[:-HASH_SIZE]).digest()
            if hash_value != expected_hash:
                raise HashValidationError("Frame hash validation failed")
            
            return {
                'cmd': cmd,
                'nonce': nonce,
                'payload': payload,
                'hash': hash_value
            }
            
        except Exception as e:
            self.logger.error(f"Error decoding frame: {str(e)}")
            if isinstance(e, ProtocolError):
                raise
            raise MalformedFrameError(f"Frame decoding failed: {str(e)}")
    
    def validate_nonce(self, received_nonce: int) -> bool:
        """
        Validate the nonce value against expected sequence
        
        Args:
            received_nonce: The nonce value received from the server
            
        Returns:
            True if nonce is valid
            
        Raises:
            InvalidNonceError: If nonce validation fails
        """
        try:
            # Server should respond with client's sent nonce value + 1
            expected_nonce = self.last_sent_nonce + 1
            
            if received_nonce != expected_nonce:
                error_msg = f"Nonce mismatch. Expected {expected_nonce}, got {received_nonce}"
                self.logger.error(error_msg)
                raise InvalidNonceError(error_msg)
            return True
        except Exception as e:
            self.logger.error(f"Nonce validation error: {str(e)}")
            raise
    
    def handle_server_response(self, response_data: bytes) -> Dict[str, Any]:
        """
        Process a server response according to protocol specifications
        
        Args:
            response_data: Raw response data from the server
            
        Returns:
            Dictionary containing response details
        """
        try:
            decoded = self.decode_frame(response_data)
            self.validate_nonce(decoded['nonce'])

            self.logger.info(f"decoded data from server is : {decoded}")
            print(f"decoded data from server is : {decoded}")
            response_handlers = {
                RESPONSE_HELLO_ACK: self._handle_hello_ack,
                RESPONSE_DUMP_OK: self._handle_dump_ok,
                RESPONSE_DUMP_FAILED: self._handle_dump_failed,
                RESPONSE_STOP_OK: self._handle_stop_ok
            }
            
            handler = response_handlers.get(decoded['cmd'], self._handle_unknown_response)
            return handler(decoded)
            
        except Exception as e:
            self.logger.error(f"Error handling server response: {str(e)}")
            raise
    
    def send_command(self, cmd: int, payload: bytes = b"") -> bytes:
        """
        Send a command to the server and return the encoded frame
        
        Args:
            cmd: Command ID to send
            payload: Command payload
            
        Returns:
            Encoded frame to send
        """
        try:
            # Update command sequence
            self.command_sequence.append(cmd)
            
            # For HELLO command, reset client nonce
            if cmd == CMD_HELLO:
                self.client_nonce = 0
            
            # Use current client nonce for this command
            nonce = self.client_nonce
            
            # Create and return encoded frame
            encoded_frame = self.encode_frame(cmd, nonce, payload)
            
            # Track last sent nonce before incrementing
            self.last_sent_nonce = nonce
            
            # Increment client nonce for next command
            self.client_nonce += 1
            
            return encoded_frame
            
        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            raise
    
    def _handle_hello_ack(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle HELLO_ACK response"""
        return {
            'command': 'HELLO',
            'status': 'success',
            'message': 'Connection initialized successfully'
        }
    
    def _handle_dump_ok(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DUMP_OK response"""
        return {
            'command': 'DUMP',
            'status': 'success',
            'message': 'Memory dump retrieved successfully',
            'data': decoded['payload'].decode('utf-8') if decoded['payload'] else None
        }
    
    def _handle_dump_failed(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DUMP_FAILED response"""
        return {
            'command': 'DUMP',
            'status': 'failed',
            'message': 'Failed to retrieve memory dump'
        }
    
    def _handle_stop_ok(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle STOP_OK response"""
        return {
            'command': 'STOP',
            'status': 'success',
            'message': 'Connection acknowledged'
        }
    
    def _handle_unknown_response(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown responses"""
        error_msg = f"Unknown response command: 0x{decoded['cmd']:02X}"
        self.logger.error(error_msg)
        raise UnknownCommandError(error_msg)
