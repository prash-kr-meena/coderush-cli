import logging

import rich_click as click
from coderush_cli import __version__
from rich.console import Console

from .commands import chat, chat_interface, config, report, review

# Configure rich-click
click.rich_click.USE_RICH_MARKUP = True
click.rich_click.USE_MARKDOWN = True
click.rich_click.SHOW_ARGUMENTS = True
click.rich_click.GROUP_ARGUMENTS_OPTIONS = True
click.rich_click.STYLE_ERRORS_SUGGESTION = "yellow italic"
click.rich_click.ERRORS_SUGGESTION = "Try '--help' for more information."

# Initialize rich console
console = Console()


@click.group(invoke_without_command=True)
@click.version_option(version=__version__, prog_name="coderush-cli")
@click.option(
  "-v",
  "--verbose",
  count=True,
  help="Increase verbosity (can be used multiple times)",
)
@click.pass_context
def cli(ctx, verbose):
  # Create a custom dict of useful attributes
  ctx_info = {
    "command": ctx.command.name if ctx.command else None,
    "subcommand": ctx.invoked_subcommand,
    "parent": (
      ctx.parent.command.name if ctx.parent and ctx.parent.command else None
    ),
    "params": ctx.params,
    "args": ctx.args,
    "resilient_parsing": ctx.resilient_parsing,
    "auto_envvar_prefix": ctx.auto_envvar_prefix,
    "obj": ctx.obj,
  }

  console.print("Context information:")
  console.print(ctx_info)
  print("verbose : ", verbose)

  """🚀 Coderush CLI - Engineering Metrics Analysis Tool"""
  # Set up logging based on verbosity level
  if verbose == 0:
    log_level = logging.WARNING
  elif verbose == 1:
    log_level = logging.INFO
  else:  # verbose >= 2
    log_level = logging.DEBUG

  logging.basicConfig(level=log_level, format="%(levelname)s:%(message)s")

  if ctx.invoked_subcommand is None:
    # Start interactive mode by default
    ctx.invoke(chat_interface)


# Add commands to CLI group
cli.add_command(review)
cli.add_command(config)
cli.add_command(chat_interface, name="chat")
cli.add_command(chat)
cli.add_command(report)


def main():
  cli()


if __name__ == "__main__":
  main()

hi = "there"
