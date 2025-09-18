# MiniTel-Lite Infiltration Tool

A Python command-line application for infiltrating the MiniTel-Lite network and retrieving emergency override codes from the JOSHUA system.

## Overview

The MiniTel-Lite Infiltration Tool is designed to connect to MiniTel-Lite servers, authenticate using the HELLO protocol, and retrieve emergency override codes by following a precise sequence of commands. It implements the MiniTel-Lite Protocol Version 3.0 with full support for secure connections, session recording, and error handling.

## Features

- **Terminal Connection**: Connect to MiniTel-Lite servers and authenticate using the HELLO protocol
- **Protocol Implementation**: Full implementation of the MiniTel-Lite Protocol Version 3.0
- **Session Recording**: Record all client-server interactions for later analysis
- **TUI Replay Application**: Replay recorded sessions with a text-based user interface
- **Secure Connections**: Optional TLS encryption for secure communications
- **Comprehensive Error Handling**: Robust error handling for connection issues, protocol violations, and more

## Installation

```bash
# Create and activate a virtual environment (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install the package
pip install -r requirements.txt
```

## Usage

### Command-Line Client

```bash
# Basic usage
python -m minitel_lite_client.cli --host <hostname> --port <port>

# Enable session recording
python -m minitel_lite_client.cli --host <hostname> --port <port> --record-session

# Specify a custom directory for session recordings
python -m minitel_lite_client.cli --host <hostname> --port <port> --record-session --recording-dir ./my-recordings

# Enable TLS encryption (disabled by default)
python -m minitel_lite_client.cli --host <hostname> --port <port> --no-tls
```

Example : `python3 -m minitel_lite_client.cli --host=localhost --port=7321 --record-session --recording-dir=./recordings`

### Session Replay TUI

```bash
# Replay a recorded session
python -m minitel_lite_client.replay <session-file>
```

Example : `python3 -m minitel_lite_client.replay ./recordings/minitel_lite_recording_20250917_200333.json`

#### TUI Controls

- **N / n**: Next step
- **P / p**: Previous step
- **Q / q**: Quit

## Protocol Specification

The MiniTel-Lite Protocol Version 3.0 is a minimalist TCP-based protocol designed for educational purposes and system testing. It includes the following commands:

- **HELLO (0x01)**: Initialize connection
- **DUMP (0x02)**: Request secret (stateful)
- **STOP_CMD (0x04)**: Acknowledgment/testing

### Frame Structure

```
LEN (2 bytes, big-endian) | DATA_B64 (LEN bytes, Base64 encoded)
```

Binary Frame (after Base64 decoding):

```
CMD (1 byte) | NONCE (4 bytes, big-endian) | PAYLOAD (0-65535 bytes) | HASH (32 bytes SHA-256)
```

### Nonce Sequence

- Client messages: Use expected nonce value
- Server responses: Increment nonce by 1
- Validation: Any nonce mismatch results in immediate disconnection

### Example Sequence

1. Client HELLO (nonce=0) → Server HELLO_ACK (nonce=1)
2. Client DUMP (nonce=2) → Server DUMP_FAILED (nonce=3)
3. Client DUMP (nonce=4) → Server DUMP_OK (nonce=5)
4. Client STOP_CMD (nonce=6) → Server STOP_OK (nonce=7)

## Architecture

The application follows clean architecture principles to separate concerns:

- **Client**: Handles TCP communication with secure socket connections
- **Protocol**: Implements the MiniTel-Lite Protocol with frame encoding/decoding
- **CLI**: Provides a command-line interface for user interaction
- **Replay**: Offers a TUI for replaying recorded sessions

## Error Handling

The application implements comprehensive error handling for:

- Invalid nonce
- Unknown command
- Malformed frame
- Hash validation failure
- Invalid Base64
- Connection issues
- Timeout errors

## Testing

```bash
# Run all tests
python -m run_tests

# Run specific test modules
python -m unittest minitel_lite_client.tests.test_client
python -m unittest minitel_lite_client.tests.test_protocol
python -m unittest minitel_lite_client.tests.test_cli
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.
