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
PAYLOAD_SIZE = 65535
HASH_SIZE = 32
MIN_FRAME_SIZE = CMD_SIZE + NONCE_SIZE + HASH_SIZE

# Protocol version
PROTOCOL_VERSION = 3

class MiniTelLiteProtocol:
    """Implementation of the MiniTel-Lite Protocol Version 3.0"""

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
        Encode a frame according to the MiniTel-Lite protocol specification.

        Args:
            cmd (int): Command ID
            nonce (int): Nonce value
            payload (bytes): Command-specific payload data

        Returns:
            bytes: Encoded frame with 2-byte length prefix

        Raises:
            ProtocolError: If there is an error encoding the frame
        """
        try:
            # Validate command
            if not isinstance(cmd, int) or not (0x00 <= cmd <= 0xFF):
                raise ProtocolError(f"Invalid command value: {cmd}")

            # Pack nonce as 4-byte big-endian
            nonce_bytes = struct.pack("!I", nonce)

            # Create binary frame (CMD + NONCE + PAYLOAD + HASH)
            binary_frame = bytes([cmd]) + nonce_bytes + payload + hashlib.sha256(bytes([cmd]) + nonce_bytes + payload).digest()

            # Base64 encode the binary frame
            encoded_frame = base64.b64encode(binary_frame)

            # Prepend 2-byte length prefix (big-endian)
            frame_length = struct.pack("!H", len(encoded_frame))

            # Return the complete encoded frame
            return frame_length + encoded_frame
        
        except Exception as e:
            self.logger.error(f"Error encoding frame: {str(e)}")
            raise

    def decode_frame(self, data: bytes) -> Dict[str, Any]:
        """
        Decode a frame according to the MiniTel-Lite protocol.

        Args:
            data (bytes): Raw frame data

        Returns:
            Dict[str, Any]: Decoded frame components

        Raises:
            MalformedFrameError: If the frame is malformed
            HashValidationError: If the frame hash is invalid
            Base64DecodeError: If the frame cannot be Base64 decoded
        """
        try:
            # Extract length prefix (2 bytes, big-endian)
            if len(data) < 2:
                raise MalformedFrameError("Frame too short to contain length prefix")
            frame_length = struct.unpack("!H", data[:2])[0]

            # Extract Base64 encoded data
            encoded_frame = data[2:frame_length + 2]

            # Base64 decode the frame
            binary_frame = base64.b64decode(encoded_frame)

            # Validate frame length
            if len(binary_frame) < MIN_FRAME_SIZE:
                raise MalformedFrameError(f"Binary frame too short. Expected at least {MIN_FRAME_SIZE} bytes, got {len(binary_frame)}")

            # Extract components from binary frame
            cmd = binary_frame[0]
            nonce = struct.unpack("!I", binary_frame[1:5])[0]
            payload = binary_frame[5:-HASH_SIZE]
            hash_value = binary_frame[-HASH_SIZE:]

            # Validate frame hash
            expected_hash = hashlib.sha256(bytes([cmd]) + struct.pack("!I", nonce) + payload).digest()
            if hash_value != expected_hash:
                raise HashValidationError("Frame hash validation failed")

            return {
                "cmd": cmd,
                "nonce": nonce,
                "payload": payload,
                "hash": hash_value
            }
        
        except Exception as e:
            self.logger.error(f"Error decoding frame: {str(e)}")
            if isinstance(e, ProtocolError):
                raise
            raise MalformedFrameError(f"Frame decoding failed: {str(e)}")

    def validate_nonce(self, received_nonce: int) -> bool:
        """
        Validate the nonce value received from the server.

        Args:
            received_nonce (int): The nonce value received

        Returns:
            bool: True if nonce is valid, False otherwise

        Raises:
            InvalidNonceError: If the nonce is invalid
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
        Process a server response according to the MiniTel-Lite protocol specifications.

        Args:
            response_data (bytes): Raw response data from the server

        Returns:
            Dict[str, Any]: Dictionary containing response details

        Raises:
            ProtocolError: If there is an error handling the server response
        """
        try:
            decoded = self.decode_frame(response_data)
            self.validate_nonce(decoded["nonce"])
            self.client_nonce += 1

            response_handlers = {
                RESPONSE_HELLO_ACK: self._handle_hello_ack,
                RESPONSE_DUMP_OK: self._handle_dump_ok,
                RESPONSE_DUMP_FAILED: self._handle_dump_failed,
                RESPONSE_STOP_OK: self._handle_stop_ok
            }

            handler = response_handlers.get(decoded["cmd"], self._handle_unknown_response)
            return handler(decoded)
        
        except Exception as e:
            self.logger.error(f"Error handling server response: {str(e)}")
            raise

    def send_command(self, cmd: int, payload: bytes = b"") -> bytes:
        """
        Send a command to the server.

        Args:
            cmd (int): Command ID to send
            payload (bytes): Command-specific payload data

        Returns:
            bytes: Encoded frame to send

        Raises:
            ProtocolError: If there is an error sending the command
        """
        try:
            # Update command sequence
            self.command_sequence.append(cmd)

            # Reset client nonce for HELLO command
            if cmd == CMD_HELLO:
                self.client_nonce = 0
            else:
                self.client_nonce += 1

            # Use current client nonce for this command
            nonce = self.client_nonce

            # Encode the frame
            encoded_frame = self.encode_frame(cmd, nonce, payload)

            # Track the last sent nonce before incrementing
            self.last_sent_nonce = nonce

            return encoded_frame
        
        except Exception as e:
            self.logger.error(f"Error sending command: {str(e)}")
            raise

    def _handle_hello_ack(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle HELLO_ACK response"""
        return {
            "command": "HELLO",
            "status": "success",
            "message": "Connection initialized successfully"
        }

    def _handle_dump_ok(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DUMP_OK response"""
        return {
            "command": "DUMP",
            "status": "success",
            "message": "Memory dump retrieved successfully",
            "data": decoded["payload"].decode("utf-8") if decoded["payload"] else None
        }
    
    def _handle_dump_failed(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DUMP_FAILED response"""
        return {
            "command": "DUMP",
            "status": "failed",
            "message": "Failed to retrieve memory dump"
        }
    
    def _handle_stop_ok(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle STOP_OK response"""
        return {
            "command": "STOP",
            "status": "success",
            "message": "Connection acknowledged"
        }
    
    def _handle_unknown_response(self, decoded: Dict[str, Any]) -> Dict[str, Any]:
        """Handle unknown response"""
        error_msg = f"Unknown response command: 0x{decoded['cmd']:02X}"
        self.logger.error(error_msg)
        raise ProtocolError(error_msg)
