#!/usr/bin/env python3
import argparse
import json
import subprocess
from typing import Optional
from typing import Tuple

import openai
import pkg_resources

try:
    VERSION = pkg_resources.get_distribution("sysaidmin").version
except Exception:
    VERSION = "0.0.0"

client = openai.OpenAI()


CONTEXT = [
    {
        "role": "system",
        "content": "You are a helpful system administrator. You are helping to debug "
        "Unix issues the user is facing by using their terminal. You run commands on "
        "your own, rather than asking the user to run them.",
    },
]


def next_step(output: str) -> Tuple[Optional[str], Optional[str]]:
    """Send the current output to ChatGPT, and get the next command."""
    global CONTEXT
    tools = [
        {
            "type": "function",
            "function": {
                "name": "run_terminal_command",
                "description": "Run a command in the terminal and get its output.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "command": {
                            "type": "string",
                            "description": "The command to run.",
                        },
                    },
                    "required": ["command"],
                },
            },
        }
    ]

    CONTEXT.append({"role": "user", "content": "Command output:\n{output}"})
    completion = client.chat.completions.create(
        model="gpt-4-1106-preview", messages=CONTEXT, tools=tools
    )

    response = command = None
    if completion.choices[0].finish_reason == "tool_calls":
        command = json.loads(
            completion.choices[0].message.tool_calls[0].function.arguments
        )["command"]
    else:
        response = completion.choices[0].message.content

    return response, command


def cli():
    parser = argparse.ArgumentParser(prog="sysaidmin")
    parser.add_argument("problem", help="A detailed description of your problem")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    args = parser.parse_args()

    output = f"""
You are a Linux expert, and I want you to help fix my problem. My problem is the
following:

{args.problem}

You will call the run_terminal_command function to specify the command you want to run,
and I will reply with its output. Whenever you need to run a command, just run it, you
don't need to ask me to.

Begin now.
    """
    while True:
        response, command = next_step(output)
        if response:
            print("\033[94m\n" + ("=" * 30))
            print(response)
            print(("=" * 30) + "\033[0m")

        if command:
            print("\033[91m\n" + ("=" * 30))
            print(f"Want to run: {command}")
            print(("=" * 30) + "\033[0m")
            print("Press any key to continue, Ctrl-C to terminate...")
            input()
            process = subprocess.Popen(
                command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )
            stdout, stderr = process.communicate()
            output = stdout.decode() + stderr.decode()
            print(output)
        else:
            print("\n\033[92mYour response: \033[0m", end="")
            output = input()


if __name__ == "__main__":
    cli()
