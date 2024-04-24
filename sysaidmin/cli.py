#!/usr/bin/env python3
import argparse
import datetime
import json
import subprocess
import sys
import tempfile
import time
import traceback
from importlib import metadata
from typing import Optional
from typing import Tuple

import openai

try:
    VERSION = metadata.version("sysaidmin")
except Exception:
    VERSION = "0.0.0"


class Assistant:
    def __init__(self, model: str) -> None:
        self._client = openai.OpenAI()
        self._assistant = self._client.beta.assistants.create(
            name="Sysaidmin",
            instructions=(
                "You are a helpful system administrator. You are helping to debug Unix "
                "issues the user is facing by using their terminal. You run commands "
                "on your own, rather than asking the user to run them."
            ),
            model=model,
            tools=[
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
            ],
        )
        self._thread = self._client.beta.threads.create()
        self._last_run = None

    def wait_for_run(self):
        """Wait for a run to complete, and return the latest state."""
        while self._last_run.status in ("queued", "in_progress"):
            self._last_run = self._client.beta.threads.runs.retrieve(
                thread_id=self._thread.id, run_id=self._last_run.id
            )
            time.sleep(1)
        return self._last_run

    def next_step(
        self, command_output: str
    ) -> Optional[Tuple[Optional[str], Optional[str]]]:
        """Send the current output to ChatGPT, and get the next command."""
        if self._last_run and self._last_run.status == "requires_action":
            call = self._last_run.required_action.submit_tool_outputs.tool_calls[0]
            self._last_run = self._client.beta.threads.runs.submit_tool_outputs(
                thread_id=self._thread.id,
                run_id=self._last_run.id,
                tool_outputs=[
                    {
                        "tool_call_id": call.id,
                        "output": command_output,
                    }
                ],
            )
        else:
            # Add a message to the thread.
            self._client.beta.threads.messages.create(
                self._thread.id,
                role="user",
                content=command_output,
            )

            # Run the thread.
            self._last_run = self._client.beta.threads.runs.create(
                thread_id=self._thread.id, assistant_id=self._assistant.id
            )

        # Wait for the run to complete.
        self.wait_for_run()

        # Let's see what we got.
        response = command = None
        if self._last_run.status == "requires_action":  # type: ignore[attr-defined]
            function = self._last_run.required_action.submit_tool_outputs.tool_calls[  # type: ignore[attr-defined]
                0
            ].function
            if function.name == "end_session":
                # The AI wants to end the session, clean up the assistant.
                self._client.beta.assistants.delete(self._assistant.id)
                return None
            else:
                command = json.loads(function.arguments)["command"]
        elif self._last_run.status == "completed":  # type: ignore[attr-defined]
            thread_messages = self._client.beta.threads.messages.list(
                self._thread.id, limit=4
            )
            response = thread_messages.data[0].content[0].text.value
        else:
            raise ValueError("ERROR: Got unknown run status.")
        return response, command

    def delete(self):
        self._client.beta.assistants.delete(self._assistant.id)


def run_assistant(assistant, problem):
    output = f"""
You are a Linux expert, and I want you to help fix my problem. My problem is the
following:

{problem}

The run_terminal_command function allows you to directly run terminal commands. Call it
with  the command you want to run, and I will reply with its output. Whenever you need
to run a command, just call this function, don't ask me or tell me to.

If there's nothing else you can do, or I am satisfied that the matter has been solved,
call end_session to end the session.

Don't say you want to call functions, or what functions you will call, just call them.
Only run one function at a time.

Begin now, and explain to me each step as you run it."""

    logfile_name = f'{tempfile.gettempdir()}/sysaidmin_{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}.log'
    logfile = open(logfile_name, "w")
    print(f"Writing log to {logfile_name}...")
    logfile.write(f"Problem:\n\n{problem}\n\n")
    while True:
        returned = assistant.next_step(output)
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


def cli():
    parser = argparse.ArgumentParser(prog="sysaidmin")
    parser.add_argument("problem", help="A detailed description of your problem")
    parser.add_argument("--version", action="version", version=f"%(prog)s {VERSION}")
    parser.add_argument(
        "-m", "--model", default="gpt-4-1106-preview", help="The model to use"
    )
    args = parser.parse_args()

    assistant = Assistant(model=args.model)
    try:
        run_assistant(assistant, args.problem)
    except Exception:
        assistant.delete()
        sys.exit(traceback.print_exc())


if __name__ == "__main__":
    cli()
