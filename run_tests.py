#!/usr/bin/env python3
import pytest
import os
import sys
import argparse
from pathlib import Path

def create_arg_parser():
    """Create and configure the argument parser for the test runner"""
    parser = argparse.ArgumentParser(
        description="MiniTel-Lite Client Test Runner - Execute the test suite for the MiniTel-Lite client application",
        epilog="""
        Example usage:
          %(prog)s --verbose
          %(prog)s --test-dir minitel_lite_client/tests
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Test execution options
    test_group = parser.add_argument_group("Test Execution Options")
    test_group.add_argument("--verbose", "-v", action="store_true", 
                          help="Enable verbose output (show test names)")
    test_group.add_argument("--test-dir", type=str, default="minitel_lite_client/tests",
                          help="Directory containing test files (default: minitel_lite_client/tests)")
    test_group.add_argument("--html-report", type=str, default=None,
                          help="Generate HTML report at specified path")
    test_group.add_argument("--junit-xml", type=str, default=None,
                          help="Generate JUnit XML report at specified path")
    
    # Help and version
    parser.add_argument("--version", action="version", version="%(prog)s 1.0",
                      help="Show program version and exit")
    
    return parser

def main():
    """Main entry point for the test runner"""
    try:
        # Parse command-line arguments
        parser = create_arg_parser()
        args = parser.parse_args()
        
        # Verify test directory exists
        if not os.path.exists(args.test_dir):
            print(f"Error: Test directory does not exist: {args.test_dir}")
            sys.exit(1)
        
        # Build pytest command line arguments
        pytest_args = [args.test_dir]
        
        if args.verbose:
            pytest_args.append("-v")
            
        if args.html_report:
            pytest_args.extend(["--html", args.html_report, "--self-contained-html"])
            
        if args.junit_xml:
            pytest_args.extend(["--junitxml", args.junit_xml])
        
        # Run pytest
        print(f"🚀 Running tests in {args.test_dir}")
        result = pytest.main(pytest_args)
        
        # Print summary
        if result == 0:
            print("\n✅ All tests passed successfully!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nUser interrupted the test run")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
