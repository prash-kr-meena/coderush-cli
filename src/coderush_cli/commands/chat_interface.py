from datetime import datetime, timedelta
from pathlib import Path

import anthropic
import rich_click as click
from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from rich.console import Console
from rich.panel import Panel

from .chat import chat
from .commands import CommandType, get_claude_system_prompt, parse_command, show_help
from .config import config
from .report import report
from .review import review
from .. import __version__
from ..config import get_anthropic_api_key, get_anthropic_base_url
from ..utils import load_config

console = Console()
CONFIG_FILE = Path.home() / ".coderush" / "config.json"
HISTORY_FILE = Path.home() / ".coderush" / "command_history"


@click.command()
@click.pass_context
def chat_interface(ctx):
  """Interactive chat interface for Coderush"""
  loaded_config = load_config()
  # print("loaded_config :", loaded_config)

  if not CONFIG_FILE.exists():
    console.print("[yellow]First time setup detected. Let's configure your workspace.[/]\n")
    config()

  console.print(Panel.fit(
    "[bold blue]Coderush[/] - Interactive Mode",
    subtitle=f"v{__version__}",
    border_style="blue",
  ))

  # Initialize Anthropic client if configured  
  client = None
  print("# Initialize Anthropic client if configured")
  if get_anthropic_api_key():
    client = anthropic.Client(base_url=get_anthropic_base_url(), api_key=get_anthropic_api_key())

  # print("client: ", client)

  # Initialize the prompt session
  session = PromptSession(history=FileHistory(str(HISTORY_FILE)))

  while True:
    try:
      console.print("\n[bold cyan]What would you like to do?[/] (type 'help' for suggestions)")
      command = session.prompt("coderush> ")

      if command.lower() in ["exit", "quit", "q"]:
        break

      if command.lower() in ["help", "?"]:
        show_help()
        continue

      if client:
        # Use Claude to interpret the natural language command
        try:
          response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=1024,
            messages=[{
              "role": "user",
              "content": f"Convert this natural language request into a Coderush CLI command: {command}",
            }],
            system=get_claude_system_prompt(),
          )

          interpreted_command = response.content[0].text.strip()
          console.print(f"Original command: '{command}' → Interpreted as: '{interpreted_command}'")
          console.print(f"[dim]Interpreting as: {interpreted_command}[/dim]")

          if interpreted_command:
            execute_command(interpreted_command)
          else:
            console.print(
              "[yellow]I couldn't understand that request. Try rephrasing or type 'help' for suggestions.[/]"
              )

        except Exception as e:
          console.print(f"[red]Error processing command: {str(e)}[/]")
      else:
        # Basic command parsing without AI
        execute_command(command)

    except Exception as e:
      console.print(f"[red]Error: {str(e)}[/]")


def execute_command(command_str: str) -> bool:
  """Execute a parsed command."""
  try:
    command_type, args, time_range = parse_command(command_str)
    ctx = click.get_current_context()

    if command_type == CommandType.REVIEW:

      parts = command_str.split()

      date_args = {}

      # Parse the command parts directly
      for i in range(len(parts)):
        if parts[i] == "--start-date" and i + 1 < len(parts):
          date_args["start-date"] = parts[i + 1]
        elif parts[i] == "--end-date" and i + 1 < len(parts):
          date_args["end-date"] = parts[i + 1]
        elif parts[i] == "--team" and i + 1 < len(parts):
          date_args["team"] = parts[i + 1]
        elif parts[i] == "--user" and i + 1 < len(parts):
          date_args["user"] = parts[i + 1]

      # Initialize dates
      now = datetime.now()

      if "start-date" in date_args and "end-date" in date_args:
        start_date = datetime.strptime(date_args["start-date"], "%Y-%m-%d")
        end_date = datetime.strptime(date_args["end-date"], "%Y-%m-%d")
      else:
        # Default to last 7 days
        end_date = now
        start_date = end_date - timedelta(days=7)

      # Ensure proper time boundaries
      end_date = end_date.replace(hour=23, minute=59, second=59)
      start_date = start_date.replace(hour=0, minute=0, second=0)

      # Get team from args
      team = date_args.get("team")

      # get user from args
      user = date_args.get("user")

      ctx.invoke(review, start_date=start_date, end_date=end_date, team=team, user=user)
    elif command_type == CommandType.CONFIG:
      ctx.invoke(config)
    elif command_type == CommandType.HELP:
      show_help()
    elif command_type == CommandType.CHAT:
      initial_question = args[0] if args else None
      console.print(f"Initial question: {initial_question}")
      if not initial_question or initial_question.lower() == "chat":  # If no question, enter interactive mode
        ctx.invoke(chat)
        return True  # Continue the main loop after chat exits
      else:  # If there's a question, process it and return
        ctx.invoke(chat, initial_question=initial_question)
        return False  # Return to main prompt
    elif command_type == CommandType.REPORT:
      ctx.invoke(report)
    else:
      console.print("[yellow]Invalid command. Type 'help' for available commands.[/]")
      return False
    return True

  except Exception as e:
    console.print(f"[red]Error executing command: {str(e)}[/]")
    return False
