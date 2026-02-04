#!/usr/bin/env python3
"""
Protocol Generation API Startup Script

Quick startup script for the Protocol Generation REST API server.

Usage:
    python start_api.py
    python start_api.py --port 8003 --host 0.0.0.0
    python start_api.py --reload --debug

Author: Enhancement Team
"""

import argparse
import sys
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from api.protocol_api import run_dev_server


def main():
    """Main function with argument parsing."""
    parser = argparse.ArgumentParser(description="Start Protocol Generation API Server")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8002, help="Port to bind to")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    
    args = parser.parse_args()
    
    print(f"🚀 Starting Protocol Generation API Server")
    print(f"   Host: {args.host}")
    print(f"   Port: {args.port}")
    print(f"   Reload: {args.reload}")
    print(f"   Debug: {args.debug}")
    print()
    print(f"🌐 API will be available at:")
    print(f"   Swagger UI: http://{args.host}:{args.port}/api/v1/protocols/docs")
    print(f"   Health Check: http://{args.host}:{args.port}/api/v1/protocols/health")
    print()
    
    try:
        run_dev_server(host=args.host, port=args.port)
    except KeyboardInterrupt:
        print("\n👋 API Server stopped")
    except Exception as e:
        print(f"❌ Failed to start API server: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()