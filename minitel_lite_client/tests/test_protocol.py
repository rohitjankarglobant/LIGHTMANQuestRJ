import pytest
import hashlib
import struct
import base64
from minitel_lite_client.protocol import MiniTelLiteProtocol, CMD_HELLO, CMD_DUMP, CMD_STOP, RESPONSE_HELLO_ACK, RESPONSE_DUMP_OK, RESPONSE_DUMP_FAILED, RESPONSE_STOP_OK
from minitel_lite_client.exceptions import InvalidNonceError, MalformedFrameError, HashValidationError

class TestMiniTelLiteProtocol:
    @pytest.fixture
    def protocol(self):
        """Fixture to create a test protocol instance"""
        return MiniTelLiteProtocol()
    
    def test_encode_decode_round_trip(self, protocol):
        """Test that encoding and decoding a frame returns the original data"""
        # Test HELLO command with no payload
        cmd = CMD_HELLO
        nonce = 0
        payload = b""
        
        # Encode frame
        encoded = protocol.encode_frame(cmd, nonce, payload)
        
        # Decode frame
        decoded = protocol.decode_frame(encoded)
        
        # Verify components
        assert decoded['cmd'] == cmd
        assert decoded['nonce'] == nonce
        assert decoded['payload'] == payload
    
    def test_encode_with_payload(self, protocol):
        """Test frame encoding with payload"""
        cmd = CMD_DUMP
        nonce = 2
        payload = b"test_payload"
        
        encoded = protocol.encode_frame(cmd, nonce, payload)
        decoded = protocol.decode_frame(encoded)
        
        assert decoded['cmd'] == cmd
        assert decoded['nonce'] == nonce
        assert decoded['payload'] == payload
    
    def test_hash_validation(self, protocol):
        """Test frame hash validation"""
        cmd = CMD_HELLO
        nonce = 0
        payload = b"test_data"
        
        # Create valid frame
        encoded = protocol.encode_frame(cmd, nonce, payload)
        decoded = protocol.decode_frame(encoded)
        assert decoded['cmd'] == cmd
        
        # Modify payload to break hash
        modified_encoded = encoded[:-33] + b"\x00" + encoded[-32:]
        
        with pytest.raises(HashValidationError):
            protocol.decode_frame(modified_encoded)
    
    def test_nonce_validation_success(self, protocol):
        """Test successful nonce validation"""
        # First message should expect nonce 0
        assert protocol.validate_nonce(0) is True
        assert protocol.expected_nonce == 1
        
        # Next message should expect nonce 1
        assert protocol.validate_nonce(1) is True
        assert protocol.expected_nonce == 2
    
    def test_nonce_validation_failure(self, protocol):
        """Test nonce validation failure"""
        # First message should expect nonce 0
        with pytest.raises(InvalidNonceError):
            protocol.validate_nonce(1)
        
        # After failure, expected nonce should remain unchanged
        assert protocol.expected_nonce == 0
    
    def test_hello_response_nonce(self, protocol):
        """Test nonce handling for HELLO response"""
        # Send HELLO command
        protocol.send_command(CMD_HELLO)
        
        # Server should respond with nonce = 0 + 1 = 1
        assert protocol.validate_nonce(1) is True
        assert protocol.expected_nonce == 2
    
    def test_malformed_frame_errors(self, protocol):
        """Test error handling for malformed frames"""
        # Test short frame
        with pytest.raises(MalformedFrameError):
            protocol.decode_frame(b"\x00")  # Too short for length prefix
        
        # Test incomplete frame
        with pytest.raises(MalformedFrameError):
            protocol.decode_frame(b"\x00\x0A\x01")  # Length prefix says 10 bytes, but only 1 provided
    
    def test_base64_decoding(self, protocol):
        """Test Base64 decoding in frame decoding"""
        # Create a frame that needs Base64 decoding
        cmd = CMD_STOP
        nonce = 6
        payload = b"base64_data"
        
        # Normally frames don't need Base64 decoding, but test the path
        binary_frame = bytes([cmd]) + struct.pack('!I', nonce) + payload + hashlib.sha256(bytes([cmd]) + struct.pack('!I', nonce) + payload).digest()
        len_prefix = struct.pack('!H', len(binary_frame))
        
        # Wrap in Base64 encoded frame
        base64_data = base64.b64encode(binary_frame)
        encoded_frame = len_prefix + base64_data
        
        # Decode should handle Base64 automatically
        decoded = protocol.decode_frame(encoded_frame)
        assert decoded['cmd'] == cmd
        assert decoded['nonce'] == nonce
        assert decoded['payload'] == payload
    
    def test_handle_server_response(self, protocol):
        """Test server response handling"""
        # Test HELLO_ACK response
        hello_frame = protocol.encode_frame(RESPONSE_HELLO_ACK, 1)
        hello_response = protocol.handle_server_response(hello_frame)
        assert hello_response['command'] == 'HELLO'
        assert hello_response['status'] == 'success'
        
        # Test DUMP_OK response
        dump_frame = protocol.encode_frame(RESPONSE_DUMP_OK, 3, b"override_code")
        dump_response = protocol.handle_server_response(dump_frame)
        assert dump_response['command'] == 'DUMP'
        assert dump_response['status'] == 'success'
        assert dump_response['data'] == 'override_code'
        
        # Test DUMP_FAILED response
        dump_fail_frame = protocol.encode_frame(RESPONSE_DUMP_FAILED, 5)
        dump_fail_response = protocol.handle_server_response(dump_fail_frame)
        assert dump_fail_response['command'] == 'DUMP'
        assert dump_fail_response['status'] == 'failed'
    
    def test_send_command(self, protocol):
        """Test send_command method"""
        # Test HELLO command
        hello_frame = protocol.send_command(CMD_HELLO)
        hello_decoded = protocol.decode_frame(hello_frame)
        assert hello_decoded['cmd'] == CMD_HELLO
        assert hello_decoded['nonce'] == 0  # First command starts at nonce 0
        
        # Test DUMP command
        dump_frame = protocol.send_command(CMD_DUMP)
        dump_decoded = protocol.decode_frame(dump_frame)
        assert dump_decoded['cmd'] == CMD_DUMP
        assert dump_decoded['nonce'] == 1  # Next nonce should be 1

if __name__ == "__main__":
    pytest.main(["-v", __file__])
