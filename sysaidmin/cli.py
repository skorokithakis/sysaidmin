#!/usr/bin/env python3
import argparse
import asyncio
import datetime
import os
import subprocess
import sys
import tempfile
from importlib import metadata

from agents import (
    Agent,
    OpenAIChatCompletionsModel,
    Runner,
    function_tool,
    set_default_openai_client,
    set_tracing_disabled,
)
from openai import AsyncOpenAI

try:
    VERSION = metadata.version("sysaidmin")
except Exception:
    VERSION = "0.0.0"

LOGFILE = None


def print_message(message: str, section: str):
    """Prints a colored message, with the appropriate section prefix."""

    def template(s, l):
        line = f"\33[37;48:2:0:113:102m {s} \33[39;49m    {l}"
        return (" " * (6 - len(section))) + line

    for line in message.strip("\n").splitlines():
        print(template(section.upper(), line))

    print()


@function_tool
def ask_for_info(question: str) -> str:
    """Ask the user for information or clarification."""
    LOGFILE.write(("=" * 30) + f"\nAI response:\n{question}\n\n")  # type: ignore
    print_message(question, "AI")

    print("\n\033[92mYour response: \033[0m", end="")
    output = input()
    print()

    LOGFILE.write(("=" * 30) + f"\nUser response:\n{output}\n\n")  # type: ignore
    print_message(output, "User")
    return output


@function_tool
def run_command(command: str) -> str:
    LOGFILE.write(("=" * 30) + f"\nAI command:\n{command}\n\n")  # type: ignore
    print_message(f"Want to run: {command}", "AI")
    print("Press any key to continue, Ctrl-C to terminate...")
    input()
    process = subprocess.Popen(
        command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    stdout, stderr = process.communicate()
    output = stdout.decode() + stderr.decode()
    print_message(output, "OUT")
    LOGFILE.write(("=" * 30) + f"\nCommand output:\n{output}\n\n")  # type: ignore
    return output


async def run(problem: str, base_url: str | None, api_key: str, model_name: str):
    custom_client = AsyncOpenAI(
        base_url=base_url,
        api_key=api_key,
    )
    set_default_openai_client(custom_client)
    set_tracing_disabled(True)

    model = OpenAIChatCompletionsModel(
        model=model_name,
        openai_client=custom_client,
    )

    agent = Agent(
        name="sysadmin_agent",
        instructions=(
            f"You are a helpful system administrator. You are helping to debug the following Unix "
            f"issue the user is facing by using their terminal: {problem}\n\n"
            "You run commands on your own, rather than asking the user to run them."
        ),
        tools=[run_command, ask_for_info],
        model=model,
    )

    global LOGFILE
    logfile_name = f"{tempfile.gettempdir()}/sysaidmin_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log"
    LOGFILE = open(logfile_name, "w")
    print_message(f"Writing log to {logfile_name}...\n", "Sysai")
    LOGFILE.write(f"Problem:\n\n{problem}\n\n")

    result = await Runner.run(
        agent,
        f"""
You are a Linux expert, and I want you to help fix my problem. My problem is the following:

{problem}

The run_terminal_command tool allows you to directly run terminal commands. Call it
with the command you want to run, and I will reply with its output. Whenever you need
to run a command, just call this tool, don't ask me or tell me to.

If there's nothing else you can do, or I am satisfied that the matter has been solved,
end the session.

Don't say you want to run a tool, or what tool you will run, just run it.
Only run one tool at a time.

Don't try to run commands that require input, you can't provide it and they will freeze.
Instead, ask the user to run them for you, and ask them to provide their output to you.

Begin now, and explain to me each step as you run it.""",
    )

    LOGFILE.write(("=" * 30) + f"\nAI response:\n{result.final_output}\n\n")
    print_message(result.final_output, "AI")

    print_message("This session has completed.", "Sysai")
    LOGFILE.write(("=" * 30) + "\nAI response:\nSession ended.")

    return


def cli():
    parser = argparse.ArgumentParser(
        description="Sysaidmin - AI System Administration Helper",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("problem", help="A detailed description of your problem")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "-b",
        "--base-url",
        help="Custom base URL for the AI API",
        default=os.getenv("SYSAIDMIN_BASE_URL", "https://api.openai.com/v1/"),
    )
    parser.add_argument(
        "-a",
        "--api-key",
        default=os.getenv("SYSAIDMIN_API_KEY", ""),
        help="API key for the AI service",
    )
    parser.add_argument(
        "-m",
        "--model",
        default=os.getenv("SYSAIDMIN_MODEL", "o4-mini"),
        help="The model to use for the AI agent",
    )

    args = parser.parse_args()

    if not args.api_key:
        sys.exit(
            "Error: API key not found. Please set the `SYSAIDMIN_API_KEY` environment "
            "variable or use the --api-key argument."
        )

    asyncio.run(run(args.problem, args.base_url, args.api_key, args.model))


if __name__ == "__main__":
    cli()
