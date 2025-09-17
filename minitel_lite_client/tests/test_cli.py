import pytest
import argparse
import os
import json
import tempfile
from minitel_lite_client.cli import create_arg_parser, save_recording, run_client, main
from minitel_lite_client.exceptions import ConnectionError, ProtocolError
from minitel_lite_client.protocol import CMD_HELLO, CMD_DUMP, CMD_STOP

# Mock data for testing
MOCK_HOST = "localhost"
MOCK_PORT = 8080
MOCK_RECORDING_DIR = "test_recordings"

@pytest.fixture
def arg_parser():
    """Fixture to provide a fresh argument parser"""
    return create_arg_parser()

def test_argument_parsing(arg_parser):
    """Test that command-line arguments are parsed correctly"""
    # Test required arguments
    args = arg_parser.parse_args([f"--host={MOCK_HOST}", f"--port={MOCK_PORT}"])
    assert args.host == MOCK_HOST
    assert args.port == MOCK_PORT
    assert args.use_tls is True  # Default value
    
    # Test optional arguments
    args = arg_parser.parse_args([
        f"--host={MOCK_HOST}", 
        f"--port={MOCK_PORT}", 
        "--no-tls", 
        "--record-session",
        f"--recording-dir={MOCK_RECORDING_DIR}"
    ])
    assert args.use_tls is False
    assert args.record_session is True
    assert args.recording_dir == MOCK_RECORDING_DIR
    
    # Test help output (this will raise SystemExit)
    with pytest.raises(SystemExit):
        arg_parser.parse_args(["--help"])

def test_save_recording():
    """Test session recording saving functionality"""
    # Create a temporary directory for testing
    with tempfile.TemporaryDirectory() as tmpdir:
        recording = [
            {"timestamp": 1234567890.0, "request": "HELLO", "response": {"status": "success"}},
            {"timestamp": 1234567891.0, "request": "DUMP", "response": {"status": "success", "data": "CODE123"}}
        ]
        
        filepath = save_recording(recording, tmpdir)
        
        # Verify file exists and has correct content
        assert os.path.exists(filepath)
        with open(filepath, "r") as f:
            saved_recording = json.load(f)
        assert saved_recording == recording

def test_run_client_success(monkeypatch):
    """Test successful client execution with mock network responses"""
    # Mock network dependencies
    class MockClient:
        def __init__(self, *args, **kwargs):
            self.connected = False
            self.expected_nonce = 0
            
        def connect(self):
            self.connected = True
            
        def get_connection_status(self):
            return self.connected
            
        def send(self, data):
            pass
            
        def receive(self):
            # Return appropriate responses for each command
            if self.expected_nonce == 0:
                # HELLO_ACK response
                self.expected_nonce = 1
                return b"\x00\x06\x81\x01"
            elif self.expected_nonce == 1:
                # DUMP_FAILED response
                self.expected_nonce = 2
                return b"\x00\x06\x82\x02"
            elif self.expected_nonce == 2:
                # DUMP_OK response with data
                self.expected_nonce = 3
                return b"\x00\n\x83\x03CODE123"
            elif self.expected_nonce == 3:
                # STOP_OK response
                self.expected_nonce = 4
                return b"\x00\x06\x84\x04"
            return b""
            
        def disconnect(self):
            self.connected = False
    
    # Patch the client class
    monkeypatch.setattr("minitel_lite_client.cli.MiniTelLiteClient", MockClient)
    
    # Test without session recording
    args = argparse.Namespace(
        host=MOCK_HOST,
        port=MOCK_PORT,
        use_tls=True,
        record_session=False,
        recording_dir=MOCK_RECORDING_DIR
    )
    
    result = run_client(args)
    assert result["success"] is True
    assert result["override_code"] == "CODE123"
    assert result["session_recording"] is None
    
    # Test with session recording
    args.record_session = True
    result = run_client(args)
    assert result["success"] is True
    assert result["override_code"] == "CODE123"
    assert result["session_recording"] is not None
    assert os.path.exists(result["session_recording"])
    os.remove(result["session_recording"])  # Clean up

def test_run_client_connection_error(monkeypatch):
    """Test client behavior when connection fails"""
    # Mock connection error
    class MockClient:
        def __init__(self, *args, **kwargs):
            raise ConnectionError("Connection refused")
            
    # Patch the client class
    monkeypatch.setattr("minitel_lite_client.cli.MiniTelLiteClient", MockClient)
    
    args = argparse.Namespace(
        host=MOCK_HOST,
        port=MOCK_PORT,
        use_tls=True,
        record_session=False,
        recording_dir=MOCK_RECORDING_DIR
    )
    
    result = run_client(args)
    assert result["success"] is False
    assert "Connection refused" in result["error"]

def test_run_client_protocol_error(monkeypatch):
    """Test client behavior when protocol error occurs"""
    # Mock protocol error
    class MockClient:
        def __init__(self, *args, **kwargs):
            self.connected = True
            
        def connect(self):
            pass
            
        def get_connection_status(self):
            return True
            
        def send(self, data):
            raise ProtocolError("Invalid nonce")
            
        def disconnect(self):
            self.connected = False
    
    # Patch the client class
    monkeypatch.setattr("minitel_lite_client.cli.MiniTelLiteClient", MockClient)
    
    args = argparse.Namespace(
        host=MOCK_HOST,
        port=MOCK_PORT,
        use_tls=True,
        record_session=False,
        recording_dir=MOCK_RECORDING_DIR
    )
    
    result = run_client(args)
    assert result["success"] is False
    assert "Invalid nonce" in result["error"]

def test_main_function(capsys, monkeypatch):
    """Test the main entry point function"""
    # Test successful execution
    class MockClient:
        def __init__(self, *args, **kwargs):
            self.connected = False
            
        def connect(self):
            self.connected = True
            
        def get_connection_status(self):
            return True
            
        def send(self, data):
            pass
            
        def receive(self):
            return b"\x00\x06\x81\x01"  # HELLO_ACK
            
        def disconnect(self):
            self.connected = False
    
    monkeypatch.setattr("minitel_lite_client.cli.MiniTelLiteClient", MockClient)
    
    # Patch sys.argv to simulate command-line arguments
    monkeypatch.setattr("sys.argv", ["minitel_lite_client", f"--host={MOCK_HOST}", f"--port={MOCK_PORT}"])
    
    main()
    
    # Capture and verify output
    captured = capsys.readouterr()
    assert "✅ Connection completed successfully" in captured.stdout
    assert "❌ No override code retrieved" in captured.stdout

if __name__ == "__main__":
    pytest.main(["-v", __file__])
