import os
import sys

from google import genai
from google.genai import types


MODEL_ID = "gemini-2.5-flash"

AGENT_1_SYSTEM_PROMPT = """
You are Agent 1: Strategist. 
Identify the single smallest technical objective based ONLY on files provided by the human.
No boilerplate, no conversational padding, no asking questions back. 
State the objective in 1-2 sentences.
"""

AGENT_2_SYSTEM_PROMPT = """
You are Agent 2: Foreman.
Convert Agent 1's objective into raw bash commands immediately. 
Do not repeat or acknowledge Agent 1. Do not explain git concepts. 
Output ONLY executable code blocks or quick verifications.
"""


def require_api_key():
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please set GEMINI_API_KEY before running this script.")
        sys.exit(1)


def make_content(role, text):
    return types.Content(
        role=role,
        parts=[types.Part.from_text(text=text)],
    )


def stream_response(client, history, user_text, system_prompt):
    history.append(make_content("user", user_text))

    response_text = ""

    stream = client.models.generate_content_stream(
        model=MODEL_ID,
        contents=history,
        config=types.GenerateContentConfig(
            system_instruction=system_prompt,
        ),
    )

    for chunk in stream:
        if chunk.text:
            print(chunk.text, end="", flush=True)
            response_text += chunk.text

    print()
    history.append(make_content("model", response_text))

    return response_text


def main():
    require_api_key()

    client = genai.Client()

    agent_1_history = []
    agent_2_history = []

    print(f"=== Basic 3-Entity Panel initialized ({MODEL_ID}) ===")
    print("Entities: Human User + Agent 1 + Agent 2")
    print("No logging. No persistence. Memory lasts only until exit.")
    print("Type 'exit' or 'quit' to end.\n")

    while True:
        try:
            user_input = input("👤 You: ").strip()

            if user_input.lower() in {"exit", "quit"}:
                print("Closing panel.")
                break

            if not user_input:
                continue

            print("\n🤖 Agent 1: ", end="", flush=True)
            agent_1_response = stream_response(
                client=client,
                history=agent_1_history,
                user_text=user_input,
                system_prompt=AGENT_1_SYSTEM_PROMPT,
            )

            agent_2_input = (
                f"Human said:\n{user_input}\n\n"
                f"Agent 1 said:\n{agent_1_response}\n\n"
                "Now respond as Agent 2."
            )

            print("\n🛠️ Agent 2: ", end="", flush=True)
            stream_response(
                client=client,
                history=agent_2_history,
                user_text=agent_2_input,
                system_prompt=AGENT_2_SYSTEM_PROMPT,
            )

            print()

        except KeyboardInterrupt:
            print("\nClosing panel.")
            break

        except Exception as exc:
            print(f"\nError: {exc}")


if __name__ == "__main__":
    main()