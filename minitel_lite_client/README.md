# MiniTel-Lite Client

A Python command-line client implementing the MiniTel-Lite protocol for secure communication with backend servers.

## Features
- TCP communication with TLS support
- Protocol-compliant frame encoding/decoding
- Command handling (HELLO, DUMP, STOP)
- Emergency override code retrieval
- Session recording for auditing
- Comprehensive error handling and logging

## Requirements
- Python 3.8+
- Standard libraries (no external dependencies)

## Installation
```bash
# Clone the repository
git clone git@globantquest:rohitjankarglobant/LIGHTMANQuestRJ.git
cd LIGHTMANQuestRJ
```

## Usage
```bash
# Basic connection
python3 -m minitel_lite_client.cli --host=35.153.159.192 --port=7321

# With session recording
python3 -m minitel_lite_client.cli --host=35.153.159.192 --port=7321 --record-session --recording-dir=./recordings
```

## Testing
```bash
# Run full test suite
python3 run_tests.py --verbose
```

## Protocol Specification
The MiniTel-Lite protocol implements a secure communication framework with:
- Command sequence validation using nonces
- SHA-256 frame integrity verification
- Base64 encoding for binary-safe transport
- Error handling for connection failures and protocol violations

## Logging
All client activity is logged to `minitel_lite_client.log` with timestamps and severity levels.
