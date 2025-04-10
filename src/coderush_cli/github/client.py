import threading

import requests
from github import Github
from requests.adapters import HTTPAdapter
from rich.console import Console
from urllib3.util import Retry

from .app_config import CODERUSH_APP
from .auth import get_user_token
from ..utils import load_config

console = Console()


# Create a global session with proper pooling
def create_global_session():
  session = requests.Session()

  retry_strategy = Retry(
    total=3,
    backoff_factor=1,
    status_forcelist=[429, 500, 502, 503, 504],
  )

  adapter = HTTPAdapter(
    pool_connections=100,
    pool_maxsize=100,
    max_retries=retry_strategy,
    pool_block=True,
  )

  session.mount("https://", adapter)
  return session


# Global session
GITHUB_SESSION = create_global_session()


class GithubClient:
  """Thread-safe GitHub client wrapper"""

  _instance = None
  _lock = threading.Lock()

  def __new__(cls):
    with cls._lock:
      if cls._instance is None:
        cls._instance = super().__new__(cls)
      return cls._instance

  def __init__(self):
    if not hasattr(self, "_initialized"):
      self._github = None
      self._config = load_config() or {}
      self._local = threading.local()
      self._initialized = True

  def _ensure_token(self):
    """Ensure we have a valid token"""
    if not hasattr(self._local, "token"): # Does it have the token attr in the thread_local field
      self._local.token = get_user_token()
      if not self._local.token:
        raise ValueError("GitHub authentication required")

  def _get_installation_id(self, org_name: str) -> int:
    """Get the installation ID for the organization"""
    try:
      self._ensure_token()  # Make sure we have a token

      headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"token {self._local.token}",
      }

      url = "https://api.github.com/user/installations"
      response = GITHUB_SESSION.get(url, headers=headers)

      if response.status_code == 200:
        data = response.json()
        installations = data.get("installations", [])
        for installation in installations:
          account = installation.get("account", {})
          if account.get("login", "").lower() == org_name.lower():
            return installation.get("id")

      return None
    except Exception as e:
      console.print(f"[red]Error checking app installation: {str(e)}[/]")
      return None

  def _check_app_installation(self, org_name: str) -> bool:
    """Check if the GitHub App is installed for the organization"""
    installation_id = self._get_installation_id(org_name)
    if installation_id:
      return True

    console.print(f"[yellow]No installation found for organization: {org_name}[/]")
    return False

  @property
  def client(self):
    """Get the GitHub client, ensuring we have a token"""
    if not hasattr(self._local, "github"):
      # Ensure we have a token
      self._ensure_token()

      # Get mode from config - reload to ensure we have latest
      self._config = load_config() or {}
      mode = self._config.get("GITHUB_MODE", "personal")

      if mode == "organization":
        org_name = self._config.get("GITHUB_ORG")
        if not org_name:
          console.print("[red]Error: Organization name not configured[/]")
          console.print("Please run: coderush-cli config")
          return None

        # Check if the GitHub App is installed for org mode
        if not self._check_app_installation(org_name):
          console.print("[red]Error: Coderush GitHub App not installed[/]")
          console.print(
            f"Please install the app at: {CODERUSH_APP['APP_URL']}"
          )
          console.print(f"Select organization: {org_name}")
          return None

      # Create GitHub client with user token
      self._local.github = Github(self._local.token)
      self._local.github._Github__requester._Requester__session = GITHUB_SESSION

    return self._local.github

  def get_config(self):
    """Get the configuration settings"""
    return self._config

  def reload_config(self):
    """Force reload of configuration and reset client state"""
    self._config = load_config() or {}
    if hasattr(self._local, "github"):
      delattr(self._local, "github")
    if hasattr(self._local, "token"):
      delattr(self._local, "token")


def get_github_client():
  """Returns an authenticated GitHub client instance"""
  github_client = GithubClient()
  return github_client.client
