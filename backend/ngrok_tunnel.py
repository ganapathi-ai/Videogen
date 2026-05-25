"""
THE INNER CITADEL — Ngrok Tunnel Manager
Exposes your local FastAPI backend to the internet so Vercel can reach it.

This is how "Vercel deployable" works:
  - Frontend: Vercel (public URL)
  - Backend:  Your PC (localhost:8000) → Ngrok tunnel → public URL

Usage:
    python ngrok_tunnel.py

It will:
  1. Start ngrok tunnel on port 8000
  2. Print your public URL
  3. Optionally update .env with the new BACKEND_URL
  4. Keep running until you press Ctrl+C
"""

import os
import sys
import time
import json
import signal
from pathlib import Path

# Load .env
env_path = Path(__file__).parent.parent / ".env"
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=env_path)

GREEN  = "\033[92m"
BLUE   = "\033[94m"
YELLOW = "\033[93m"
RED    = "\033[91m"
BOLD   = "\033[1m"
CYAN   = "\033[96m"
RESET  = "\033[0m"

PORT = 8000


def update_env_file(key: str, value: str):
    """Updates or adds a key=value in .env file."""
    if not env_path.exists():
        return
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    new_lines = []
    for line in lines:
        if line.startswith(f"{key}=") or line.startswith(f"# {key}="):
            new_lines.append(f"{key}={value}")
            updated = True
        else:
            new_lines.append(line)
    if not updated:
        new_lines.append(f"{key}={value}")
    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def start_tunnel():
    try:
        from pyngrok import ngrok, conf
    except ImportError:
        print(f"{RED}❌ pyngrok not installed. Run: pip install pyngrok{RESET}")
        sys.exit(1)

    # Get auth token
    ngrok_token = os.getenv("NGROK_AUTHTOKEN", "")

    if ngrok_token and ngrok_token != "YOUR_NGROK_TOKEN_HERE":
        conf.get_default().auth_token = ngrok_token
        print(f"{GREEN}✅ Using Ngrok auth token from .env{RESET}")
    else:
        print(f"{YELLOW}⚠️  No NGROK_AUTHTOKEN found — using anonymous tunnel{RESET}")
        print(f"   Free account gives stable URLs: https://ngrok.com (takes 1 min)")
        print(f"   Without it: random URL changes each restart\n")

    print(f"{BLUE}[Ngrok]{RESET} Starting tunnel on port {PORT}...")

    try:
        # Kill any existing tunnels first to avoid ERR_NGROK_334
        try:
            ngrok.kill()
            time.sleep(1)
        except Exception:
            pass

        tunnel = ngrok.connect(PORT, proto="http")
        public_url = tunnel.public_url

        # Force HTTPS
        if public_url.startswith("http://"):
            public_url = public_url.replace("http://", "https://", 1)

        print(f"""
{'='*55}
  INNER CITADEL - TUNNEL ACTIVE
{'='*55}

  Public URL:  {public_url}
  Local URL:   http://localhost:{PORT}

  Next Steps:
  1. Copy this URL: {public_url}
  2. Vercel dashboard -> Settings -> Environment Variables
  3. Set NEXT_PUBLIC_BACKEND_URL = {public_url}
  4. Redeploy your Vercel project

{'='*55}
Press Ctrl+C to stop
""")

        # Auto-update .env
        update_env_file("BACKEND_URL", public_url)
        print(f"  .env BACKEND_URL updated automatically\n")

        # Keep alive
        try:
            while True:
                time.sleep(10)
        except KeyboardInterrupt:
            print(f"\n[Ngrok] Stopping tunnel...")
            ngrok.disconnect(tunnel.public_url)
            ngrok.kill()
            print(f"[Ngrok] Tunnel closed.")

    except Exception as e:
        print(f"Tunnel error: {e}")
        # Try to get existing tunnel URL if already running
        try:
            tunnels = ngrok.get_tunnels()
            if tunnels:
                existing_url = tunnels[0].public_url
                if existing_url.startswith("http://"):
                    existing_url = existing_url.replace("http://", "https://", 1)
                print(f"\n  Reconnected to existing tunnel: {existing_url}")
                print(f"  Copy this URL to Vercel as NEXT_PUBLIC_BACKEND_URL\n")
                update_env_file("BACKEND_URL", existing_url)
                while True:
                    time.sleep(10)
            else:
                print(f"  Get free token: https://dashboard.ngrok.com")
                sys.exit(1)
        except Exception:
            sys.exit(1)


if __name__ == "__main__":
    start_tunnel()
