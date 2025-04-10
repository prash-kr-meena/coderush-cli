import json
import time
import webbrowser

import pyperclip
import requests
from rich.console import Console

from ..config import CONFIG_DIR

console = Console()
TOKEN_FILE = CONFIG_DIR / "github_token.json"


def request_device_code(client_id: str):
  """Request a device code from GitHub"""
  response = requests.post(
    "https://github.com/login/device/code",
    headers={"Accept": "application/json"},
    data={"client_id": client_id},
    timeout=30,
  )
  data = response.json()
  return data


def poll_for_token(client_id: str, device_code: str, interval: int):
  """Poll GitHub for the user token"""
  while True:
    response = requests.post(
      "https://github.com/login/oauth/access_token",
      headers={"Accept": "application/json"},
      data={
        "client_id": client_id,
        "device_code": device_code,
        "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
      },
      timeout=30,
    )
    data = response.json()

    if "error" in data:
      if data["error"] == "authorization_pending":
        time.sleep(interval)
        continue
      elif data["error"] == "slow_down":
        time.sleep(interval + 5)
        continue
      elif data["error"] in ["expired_token", "access_denied"]:
        raise Exception(f"Authentication failed: {data['error']}")
      else:
        raise Exception(f"Unknown error: {data}")

    # Save token
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(TOKEN_FILE, "w") as f:
      json.dump(data, f)

    return data["access_token"]


def authenticate_user():
  """Complete device flow authentication"""
  from .app_config import CODERUSH_APP

  # Request device code
  device_data = request_device_code(CODERUSH_APP["CLIENT_ID"])

  # Show instructions to user with proper formatting
  console.print("\n[bold cyan]GitHub Authentication Required[/]")
  console.print("\nPlease visit: [link]https://github.com/login/device[/]")
  github_device_url = "https://github.com/login/device"
  webbrowser.open(github_device_url)
  console.print(f"\nOpening: [link]{github_device_url}[/]")
  pyperclip.copy(device_data["user_code"])
  console.print(
    f"And enter code: [bold yellow]{device_data['user_code']}[/] (copied to clipboard)"
  )
  console.print("\nWaiting for authentication...")

  # Poll for token
  try:
    token = poll_for_token(
      CODERUSH_APP["CLIENT_ID"],
      device_data["device_code"],
      device_data.get("interval", 5),  # Default to 5 seconds if not provided
    )
    console.print("[green]✓ Successfully authenticated with GitHub![/]")
    return token
  except Exception as e:
    console.print(f"[red]Authentication failed: {str(e)}[/]")
    return None


def get_user_token():
  """Get cached token or authenticate user"""
  if TOKEN_FILE.exists():
    with open(TOKEN_FILE) as f:
      data = json.load(f)
      return data["access_token"]
  return authenticate_user()


def clear_user_token():
  """Clear cached token"""
  if TOKEN_FILE.exists():
    TOKEN_FILE.unlink()
