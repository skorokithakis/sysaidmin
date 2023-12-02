#!/usr/bin/env python3
import argparse
import datetime
import json
import subprocess
import tempfile
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


def next_step(
    command_output: str, model: str
) -> Optional[Tuple[Optional[str], Optional[str]]]:
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
        },
        {
            "type": "function",
            "function": {
                "name": "end_session",
                "description": "End the session, either because it's successful or because there's nothing else to try.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
        },
    ]

    CONTEXT.append({"role": "user", "content": f"Command output:\n{command_output}"})
    completion = client.chat.completions.create(
        model=model, messages=CONTEXT, tools=tools
    )

    response = command = None
    if completion.choices[0].finish_reason == "tool_calls":
        function_name = completion.choices[0].message.tool_calls[0].function.name
        if function_name == "end_session":
            # The AI wants to end the session.
            return None
        else:
            command = json.loads(
                completion.choices[0].message.tool_calls[0].function.arguments
            )["command"]
            CONTEXT.append({"role": "assistant", "content": f"Run command: {command}"})
    else:
        response = completion.choices[0].message.content

    return response, command


def cli():
    parser = argparse.ArgumentParser(prog="sysaidmin")
    parser.add_argument("problem", help="A detailed description of your problem")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "-m", "--model", default="gpt-4-1106-preview", help="The model to use"
    )
    args = parser.parse_args()

    output = f"""
You are a Linux expert, and I want you to help fix my problem. My problem is the
following:

{args.problem}

You will call the run_terminal_command function to specify the command you want to run,
and I will reply with its output. Whenever you need to run a command, just run it, you
don't need to ask me to.

If you feel like there's nothing else you can do, or the user is satisfied that the
matter has been solved, feel free to call end_session to end the session.

Begin now.
    """

    logfile_name = f'{tempfile.gettempdir()}/sysaidmin_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    logfile = open(logfile_name, "w")
    print(f"Writing log to {logfile_name}...")
    while True:
        returned = next_step(output, args.model)
        if returned is None:
            print("\033[94m\n" + ("=" * 30))
            print("This session has completed.")
            print(("=" * 30) + "\033[0m")
            logfile.write(("=" * 30) + "\nAI response:\nSession ended.")
            return

        response, command = returned
        if response:
            logfile.write(("=" * 30) + f"\nAI response:\n{response}\n\n")
            print("\033[94m\n" + ("=" * 30))
            print(response)
            print(("=" * 30) + "\033[0m")

        if command:
            logfile.write(("=" * 30) + f"\nAI command:\n{command}\n\n")
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
            logfile.write(("=" * 30) + f"\nCommand output:\n{output}\n\n")
        else:
            print("\n\033[92mYour response: \033[0m", end="")
            output = input()
            logfile.write(("=" * 30) + f"\nUser response:\n{output}\n\n")


if __name__ == "__main__":
    cli()
