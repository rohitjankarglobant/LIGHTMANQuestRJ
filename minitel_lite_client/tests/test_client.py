import pytest
import socket
from unittest.mock import Mock, patch
from minitel_lite_client.client import MiniTelLiteClient
from minitel_lite_client.exceptions import ConnectionError, TimeoutError, ProtocolError

class TestMiniTelLiteClient:
    @pytest.fixture
    def client(self):
        """Fixture to create a test client instance"""
        return MiniTelLiteClient("localhost", 7321)
    
    @patch("minitel_lite_client.client.socket")
    def test_connect_success(self, mock_socket, client):
        """Test successful connection to the server"""
        # Create mock socket and SSL socket
        mock_sock = Mock()
        mock_ssl_sock = Mock()
        
        # Configure SSL context to return mock SSL socket
        mock_ssl_context = Mock()
        mock_ssl_context.wrap_socket.return_value = mock_ssl_sock
        mock_socket.ssl.create_default_context.return_value = mock_ssl_context
        
        # Configure socket to return mock socket
        mock_socket.socket.return_value = mock_sock
        
        client.connect()
        assert client.connected is True
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_connect_timeout(self, mock_socket, client):
        """Test connection timeout"""
        mock_socket.return_value.connect.side_effect = socket.timeout("Connection timed out")
        
        with pytest.raises(TimeoutError):
            client.connect()
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_connect_failure(self, mock_socket, client):
        """Test connection failure"""
        mock_socket.return_value.connect.side_effect = socket.error("Connection refused")
        
        with pytest.raises(ConnectionError):
            client.connect()
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_disconnect(self, mock_socket, client):
        """Test graceful disconnection"""
        # Create mock socket and SSL socket
        mock_sock = Mock()
        mock_ssl_sock = Mock()
        
        # Configure client socket
        client.socket = mock_ssl_sock
        client.connected = True
        
        client.disconnect()
        assert client.connected is False
        mock_ssl_sock.shutdown.assert_called_once_with(socket.SHUT_RDWR)
        mock_ssl_sock.close.assert_called_once()
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_send_data(self, mock_socket, client):
        """Test sending data to the server"""
        # Create mock socket and SSL socket
        mock_sock = Mock()
        mock_ssl_sock = Mock()
        
        # Configure client socket
        client.socket = mock_ssl_sock
        client.connected = True
        
        client.send(b"test_data")
        mock_ssl_sock.sendall.assert_called_once_with(b"test_data")
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_send_not_connected(self, mock_socket, client):
        """Test sending data when not connected"""
        with pytest.raises(ConnectionError):
            client.send(b"test_data")
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_receive_data(self, mock_socket, client):
        """Test receiving data from the server"""
        # Create mock socket and SSL socket
        mock_sock = Mock()
        mock_ssl_sock = Mock()
        
        # Configure client socket
        client.socket = mock_ssl_sock
        client.connected = True
        
        # Configure receive response
        mock_ssl_sock.recv.return_value = b"test_response"
        
        response = client.receive()
        assert response == b"test_response"
        mock_ssl_sock.recv.assert_called_once_with(client.DEFAULT_BUFFER_SIZE)
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_receive_not_connected(self, mock_socket, client):
        """Test receiving data when not connected"""
        with pytest.raises(ConnectionError):
            client.receive()
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_receive_empty_response(self, mock_socket, client):
        """Test receiving empty response (connection closed)"""
        # Create mock socket and SSL socket
        mock_sock = Mock()
        mock_ssl_sock = Mock()
        
        # Configure client socket
        client.socket = mock_ssl_sock
        client.connected = True
        
        # Configure empty response
        mock_ssl_sock.recv.return_value = b""
        
        with pytest.raises(ConnectionError):
            client.receive()
        mock_ssl_sock.recv.assert_called_once_with(client.DEFAULT_BUFFER_SIZE)
    
    @patch("minitel_lite_client.client.socket.socket")
    def test_get_connection_status(self, mock_socket, client):
        """Test connection status check"""
        assert client.get_connection_status() is False
        
        # Create mock socket and SSL socket
        mock_sock = Mock()
        mock_ssl_sock = Mock()
        
        # Configure client socket
        client.socket = mock_ssl_sock
        client.connected = True
        
        assert client.get_connection_status() is True
    
    def test_get_last_nonce(self, client):
        """Test getting last nonce value"""
        assert client.get_last_nonce() == 0
        client.set_last_nonce(5)
        assert client.get_last_nonce() == 5
    
    def test_set_last_nonce(self, client):
        """Test setting last nonce value"""
        client.set_last_nonce(10)
        assert client.get_last_nonce() == 10

if __name__ == "__main__":
    pytest.main(["-v", __file__])
