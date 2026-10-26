#!/usr/bin/env python3
"""Launcher for ResoAI Web Bot Interface.

Runs the FastAPI server bound to 0.0.0.0:8000 so anyone on your local network
(or via public tunnels) can access and query the bot from any browser.
"""

from __future__ import annotations

import socket
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn


def get_local_ip() -> str:
    """Detect the machine's primary local IP address on the network."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def main():
    host = "0.0.0.0"
    port = 8000
    local_ip = get_local_ip()

    print("=" * 70)
    print("🚀 STARTING RESOAI FUTURISTIC WEB CHATBOT")
    print("=" * 70)
    print(f"\n📍 Local Browser:   http://localhost:{port}/")
    print(f"🌐 Local Network:   http://{local_ip}:{port}/")
    print(f"🔗 Pre-filled link: http://{local_ip}:{port}/?q=How+many+employees+are+in+HR%3F")
    print("\n💡 To share globally over the Internet with judges:")
    print("   Run in a separate terminal:")
    print(f"   cloudflared tunnel --url http://localhost:{port}")
    print("   or:")
    print(f"   ngrok http {port}")
    print("=" * 70 + "\n")

    uvicorn.run("src.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
