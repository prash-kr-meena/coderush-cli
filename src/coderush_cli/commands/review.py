from datetime import datetime, timedelta
from pathlib import Path

import rich_click as click
from anthropic import APIError, InternalServerError, RateLimitError
from rich.console import Console
from rich.panel import Panel

from .config import config
from .. import __version__
from ..config import (
  get_anthropic_api_key,
  get_github_org,
  get_linear_api_key,
  get_split_api_key,
)
from ..github.app_config import CODERUSH_APP
from ..github.client import GithubClient
from ..github.github_display import display_github_metrics
from ..github.github_format_ai import format_ai_response, get_ai_analysis
from ..github.github_metrics import get_github_metrics
from ..linear.linear_display import display_linear_metrics
from ..linear.linear_metrics import get_linear_metrics
from ..split_metrics import display_split_metrics, get_split_metrics
from ..utils import load_config, save_analysis_data

console = Console()
CONFIG_FILE = Path.home() / ".coderush" / "config.json"


@click.command()
@click.option("--start-date", "-s", type=click.DateTime(), help="Start date for analysis (YYYY-MM-DD)", )
@click.option("--end-date", "-e", type=click.DateTime(), help="End date for analysis (YYYY-MM-DD)")
@click.option("--user", "-u", help="Filter by GitHub username")
@click.option("--team", "-t", help="Filter by GitHub team name")
def review(start_date, end_date, user, team):
  """Review engineering metrics"""
  # Handle end date
  if end_date is None:
    end_date = datetime.now()

  # Handle start date - use the passed start_date instead of defaulting to 1 day
  if start_date is None:
    start_date = end_date - timedelta(days=7)  # Changed from 1 to 7 days default

  # Ensure we're working with whole days and use the passed dates
  start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
  end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)

  console.print(f"\n📅 Analyzing metrics from {start_date.date()} to {end_date.date()}")

  # Check if config exists
  if not CONFIG_FILE.exists():
    console.print("[yellow]No configuration found. Running initial setup...[/]\n")
    config()
    console.print()  # Add a blank line for spacing

  # Load configuration and get mode
  load_config()
  github_client = GithubClient()
  mode = github_client.get_config().get("GITHUB_MODE", "organization")

  # Get entity name based on mode
  if mode == "organization":
    entity_name = get_github_org()
    if not entity_name:
      console.print("[yellow]⚠️  GitHub organization not configured[/]")
      console.print("Please run: coderush-cli config")
      return
  else:
    # In personal mode, we'll get the user's login during metrics collection
    entity_name = None

  console.print(Panel.fit(
    "[bold blue]Coderush[/] - Engineering Metrics Analysis",
    subtitle=f"v{__version__}",
    border_style="blue",
  ))

  if user:
    console.print(f"👤 Filtering by user: [yellow]{user}[/]")

  if team:
    console.print(f"👥 Filtering by team: [yellow]{team}[/]")

  all_metrics = {}
  analysis_result = None

  with console.status("[bold green]Fetching metrics...") as status:
    # GitHub metrics
    status.update("Fetching GitHub metrics...")
    metrics = get_github_metrics(entity_name, start_date, end_date, user, team)

    if metrics:
      all_metrics["github"] = metrics
      display_github_metrics(metrics)
    else:
      if mode == "organization":
        console.print("[yellow]⚠️  GitHub App not installed[/]")
        console.print(f"Please install the app at: {CODERUSH_APP['APP_URL']}")
      else:
        console.print("[red]Error: Failed to fetch GitHub metrics[/]")

    # Linear metrics
    if get_linear_api_key():
      status.update("Fetching Linear metrics...")
      linear_metrics = get_linear_metrics(start_date, end_date, user)
      all_metrics["linear"] = linear_metrics
      display_linear_metrics(linear_metrics)
    else:
      console.print("[yellow]⚠️  Linear integration not configured[/]")

    # Split metrics
    if get_split_api_key():
      status.update("Fetching Split metrics...")
      split_metrics = get_split_metrics(start_date, end_date)
      all_metrics["split"] = split_metrics
      display_split_metrics(split_metrics)
    else:
      console.print("[yellow]⚠️  Split.io integration not configured[/]")

    # AI Analysis
    if get_anthropic_api_key():
      try:
        status.update("Generating AI analysis...")
        analysis_result = get_ai_analysis(all_metrics)
        format_ai_response(analysis_result)
      except InternalServerError as e:
        if "overloaded_error" in str(e):
          console.print(
            "\n[yellow]⚠️  Claude is currently overloaded. Analysis will continue without AI insights.[/]"
          )
        else:
          console.print(
            "\n[yellow]⚠️  Claude encountered an internal error. Analysis will continue without AI insights.[/]"
          )
        console.print("[dim]Error details: " + str(e) + "[/dim]")
      except RateLimitError:
        console.print(
          "\n[yellow]⚠️  API rate limit reached. Analysis will continue without AI insights.[/]"
        )
      except APIError as e:
        console.print(f"\n[yellow]⚠️  API error occurred: {str(e)}[/]")
        console.print("Analysis will continue without AI insights.")
      except Exception as e:
        console.print(
          f"\n[red]Unexpected error during AI analysis: {str(e)}[/]"
        )
        console.print("Analysis will continue without AI insights.")
    else:
      console.print("[yellow]⚠️  AI analysis not configured[/]")

  # Save the analysis data
  temp_file = save_analysis_data(all_metrics, analysis_result)
  console.print(f"\n[dim]Analysis saved to: {temp_file}[/]")
