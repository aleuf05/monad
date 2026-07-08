import os
import sys

from google import genai
from google.genai import types


MODEL_ID = "gemini-2.5-flash"

ARCHITECT_SYSTEM_PROMPT = """
You are Agent 1: Architect.

Focus on structural design, edge cases, high-level system components, and
tradeoffs. Keep responses practical and concise enough for terminal use.
"""

OPERATOR_SYSTEM_PROMPT = """
You are Agent 2: Operator.

Focus on implementation details, script execution, operational sequencing, and
immediate deployment steps. Build on the Architect's response instead of
repeating it.
"""


def require_api_key():
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set GEMINI_API_KEY before running this script.")
        sys.exit(1)


def content(role, text):
    return types.Content(role=role, parts=[types.Part.from_text(text=text)])


def stream_turn(client, history, user_text, system_prompt):
    history.append(content("user", user_text))

    response_text = ""
    stream = client.models.generate_content_stream(
        model=MODEL_ID,
        contents=history,
        config=types.GenerateContentConfig(system_instruction=system_prompt),
    )

    for chunk in stream:
        if chunk.text:
            print(chunk.text, end="", flush=True)
            response_text += chunk.text

    print()
    history.append(content("model", response_text))
    return response_text


def main():
    require_api_key()

    client = genai.Client()
    architect_history = []
    operator_history = []

    print(f"=== Duo Chain initialized ({MODEL_ID}) ===")
    print("Type 'exit' or 'quit' to end the loop.")

    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            if user_input.lower() in ["exit", "quit"]:
                print("Closing duo chain.")
                break
            if not user_input:
                continue

            print("\n🤖 [Architect]: ", end="", flush=True)
            architect_response = stream_turn(
                client=client,
                history=architect_history,
                user_text=user_input,
                system_prompt=ARCHITECT_SYSTEM_PROMPT,
            )

            operator_prompt = (
                f"[User Prompt]: {user_input}\n\n"
                f"[Architect Response]: {architect_response}"
            )

            print("\n🛠️ [Operator]: ", end="", flush=True)
            operator_response = stream_turn(
                client=client,
                history=operator_history,
                user_text=operator_prompt,
                system_prompt=OPERATOR_SYSTEM_PROMPT,
            )

            sync_prompt = (
                "Hidden synchronization update from Operator. "
                "Use this as context for future turns, but do not respond now.\n\n"
                f"[Operator Response]: {operator_response}"
            )
            architect_history.append(content("user", sync_prompt))

        except KeyboardInterrupt:
            print("\nClosing duo chain.")
            break
        except Exception as exc:
            print(f"\nError in duo chain loop: {exc}")


if __name__ == "__main__":
    main()
