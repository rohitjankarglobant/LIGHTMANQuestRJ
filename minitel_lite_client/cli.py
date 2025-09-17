import argparse
import json
import os
import sys
import time
from typing import Optional, Dict, Any
from minitel_lite_client.client import MiniTelLiteClient
from minitel_lite_client.protocol import MiniTelLiteProtocol
from minitel_lite_client.exceptions import ConnectionError, ProtocolError
from minitel_lite_client.logger import get_logger
from minitel_lite_client.protocol import CMD_DUMP, CMD_HELLO, CMD_STOP

logger = get_logger(__name__)

def create_arg_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser for the MiniTel-Lite client"""
    parser = argparse.ArgumentParser(
        description="MiniTel-Lite Infiltration Tool - Retrieve emergency override codes from the JOSHUA system",
        epilog="""
        Example usage:
          %(prog)s --host localhost --port 8080 --record-session
          %(prog)s --host 192.168.1.100 --port 8080 --no-tls
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    # Connection arguments
    connection_group = parser.add_argument_group("Connection Settings")
    connection_group.add_argument("--host", type=str, required=True,
                              help="Server hostname or IP address to connect to")
    connection_group.add_argument("--port", type=int, required=True,
                              help="Server port number to connect to")
    connection_group.add_argument("--no-tls", action="store_false",
                              help="Disable TLS encryption for the connection")

    # Session recording arguments
    recording_group = parser.add_argument_group("Session Recording")
    recording_group.add_argument("--record-session", action="store_true",
                             help="Enable session recording to a JSON file")
    recording_group.add_argument("--recording-dir", type=str, default="recordings",
                             help="Directory to store session recordings (default: recordings)")

    # Help and version arguments
    parser.add_argument("--version", action="version", version="%(prog)s 1.0",
                     help="Show program version and exit")

    return parser

def save_recording(recording: list, directory: str = "recordings") -> str:
    """
    Save a session recording to a JSON file with a timestamped filename
    """
    # Create the recording directory if it doesn't exist
    os.makedirs(directory, exist_ok=True)

    # Generate a timestamped filename
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    filename = f"minitel_lite_recording_{timestamp}.json"
    filepath = os.path.join(directory, filename)

    # Save the recording to the JSON file
    with open(filepath, "w") as f:
        json.dump(recording, f, indent=2)

    logger.info(f"Session recording saved to {filepath}")
    return filepath

def run_client(args: argparse.Namespace) -> Dict[str, Any]:
    """
    Run the MiniTel-Lite client with the provided arguments
    """
    protocol = MiniTelLiteProtocol()
    result = {
        "success": False,
        "override_code": None,
        "error": None,
        "session_recording": None
    }

    try:
        # Create and connect the client
        client = MiniTelLiteClient(args.host, args.port, use_tls=not args.no_tls)
        logger.info(f"Connecting to {args.host}:{args.port}")

        # Initialize session recording if enabled
        session_recording = [] if args.record_session else None

        client.connect()

        # Initialize session recording if enabled
        if session_recording is not None:
            session_recording.append({
                "timestamp": time.time(),
                "request": "HELLO",
                "response": None
            })
            
        # Send HELLO command
        hello_frame = protocol.send_command(CMD_HELLO)
        logger.info(f"Sending HELLO command with nonce {protocol.client_nonce}")
        client.send(hello_frame)

        # Receive HELLO_ACK response
        hello_response_data = client.receive()
        logger.info(f"Received HELLO_ACK response data: {hello_response_data}")
        hello_response = protocol.handle_server_response(hello_response_data)

        if session_recording is not None:
            session_recording[-1]["response"] = hello_response

        logger.info("Successfully initialized connection with HELLO_ACK")

        # First DUMP command
        if session_recording is not None:
            session_recording.append({
                "timestamp": time.time(),
                "request": "DUMP",
                "response": None
            })
            
        dump_frame = protocol.send_command(CMD_DUMP)
        logger.info(f"Sending DUMP command with nonce {protocol.client_nonce}")
        client.send(dump_frame)

        # Receive DUMP response
        dump_response_data = client.receive()
        logger.info(f"Received DUMP response data: {dump_response_data}")
        dump_response = protocol.handle_server_response(dump_response_data)

        if session_recording is not None:
            session_recording[-1]["response"] = dump_response

        logger.info("First DUMP command completed")

        # Second DUMP command
        if session_recording is not None:
            session_recording.append({
                "timestamp": time.time(),
                "request": "DUMP",
                "response": None
            })
            
        dump_frame = protocol.send_command(CMD_DUMP)
        logger.info(f"Sending second DUMP command with nonce {protocol.client_nonce}")
        client.send(dump_frame)

        # Receive final DUMP response
        final_dump_response_data = client.receive()
        logger.info(f"Received final DUMP response data: {final_dump_response_data}")
        final_dump_response = protocol.handle_server_response(final_dump_response_data)

        if session_recording is not None:
            session_recording[-1]["response"] = final_dump_response

        logger.info("Second DUMP command completed successfully")

        # Extract override code from final DUMP response
        if final_dump_response["status"] == "success" and final_dump_response.get("data"):
            result["override_code"] = final_dump_response["data"]
            logger.info(f"Emergency override code retrieved: {result['override_code']}")

        # Send STOP command
        if session_recording is not None:
            session_recording.append({
                "timestamp": time.time(),
                "request": "STOP",
                "response": None
            })
            
        stop_frame = protocol.send_command(CMD_STOP)
        logger.info(f"Sending STOP command with nonce {protocol.client_nonce}")
        client.send(stop_frame)

        # Receive STOP response
        stop_response_data = client.receive()
        logger.info(f"Received STOP response data: {stop_response_data}")
        stop_response = protocol.handle_server_response(stop_response_data)

        if session_recording is not None:
            session_recording[-1]["response"] = stop_response

        logger.info("Connection acknowledged with STOP command")

        # Gracefully disconnect
        client.disconnect()

        # Save session recording if enabled
        if session_recording is not None:
            result["session_recording"] = save_recording(session_recording, args.recording_dir)

        result["success"] = True

    except ConnectionError as e:
        logger.error(f"Connection error: {str(e)}")
        result["error"] = f"Connection failed: {str(e)}"
    except ProtocolError as e:
        logger.error(f"Protocol error: {str(e)}")
        result["error"] = f"Protocol error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        result["error"] = f"Unexpected error: {str(e)}"
    finally:
        if 'client' in locals() and client.get_connection_status():
            client.disconnect()

    return result

def main():
    """
    Main entry point for the MiniTel-Lite client command-line interface
    """
    try:
        # Parse command-line arguments
        parser = create_arg_parser()
        args = parser.parse_args()
        
        # Run the client with the provided arguments
        result = run_client(args)
        
        # Display results to user
        if result["success"]:
            print("\n✅ Connection completed successfully")
            
            if result["override_code"]:
                print(f"🔐 Emergency override code: {result['override_code']}")
            
            if result["session_recording"]:
                print(f"\n📼 Session recording saved to: {result['session_recording']}")
            else:
                print("\n❌ No session recording saved")
                
            if result["error"]:
                print(f"\n⚠️ Warning: {result['error']}")
        else:
            print(f"\n❌ Connection failed: {result['error']}")
            
    except KeyboardInterrupt:
        print("\n\nUser interrupted the operation")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        logger.error(f"Unexpected error in main: {str(e)}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
