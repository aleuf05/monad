import os
import sys
import asyncio
import json
from google import genai
from google.genai import types

# Verify the API key is present in your Git Bash environment
if not os.environ.get("GEMINI_API_KEY"):
    print("Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

# Initialize the modern SDK client
client = genai.Client()
model_id = "gemini-2.5-flash"

# System instruction forcing the agent to maintain an internal state schema
AGENT_SYSTEM_PROMPT = """
You are a stateful AI agent capable of independent reflection. 
For every user prompt, you must maintain an internal mental state before responding.

You must structure your output strictly in JSON format with the following keys:
1. "internal_monologue": Your private thoughts, analyzing the user's implicit intent, mood, and what you need to remember.
2. "state_updates": A list of key facts, preferences, or context about the user or the environment you are tracking for long-term memory.
3. "response": The actual message you send back to the user.

Keep your tone casual, peer-to-peer, and supportive. Do not break character.
"""

class StatefulAgent:
    def __init__(self):
        self.memory_log = []  # Core long-term memory storage array
        
        # Open a standard chat session configured to enforce a JSON output structure
        self.chat = client.chats.create(
            model=model_id,
            config=types.GenerateContentConfig(
                system_instruction=AGENT_SYSTEM_PROMPT,
                response_mime_type="application/json",
                temperature=0.7
            )
        )

    async def process_input(self, user_prompt: str):
        """Processes input through the agent's internal monologue loop."""
        # Inject the persistent memory log directly into the context window
        contextual_prompt = f"[Current Memory Log: {self.memory_log}]\nUser: {user_prompt}"
        
        # Run the API call in an executor so the async terminal loop doesn't block
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(
            None, lambda: self.chat.send_message(contextual_prompt)
        )
        
        return response.text

async def main_loop():
    agent = StatefulAgent()
    print(f"=== Stateful Agent v0.2 Initialized ({model_id}) ===")
    print("Type 'exit' to quit.\n")

    while True:
        try:
            # Native async input wrapper compatible with Git Bash execution
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.strip().lower() in ['exit', 'quit']:
                print("Shutting down agent state. Goodbye!")
                break
                
            if not user_input.strip():
                continue

            print("\n* Agent is thinking... *")
            
            # Await the model's background generation
            raw_json_output = await agent.process_input(user_input)
            
            try:
                # Parse the structured JSON response
                data = json.loads(raw_json_output)
                
                # 1. Render the Internal Monologue to screen
                print("\n--- AGENT INTERNAL MONOLOGUE ---")
                print(f"> {data.get('internal_monologue')}")
                
                # 2. Extract and append any new state updates to the persistent log
                updates = data.get("state_updates", [])
                if updates:
                    print("-> State Updates Detected:")
                    for update in updates:
                        print(f"   [MEM]: {update}")
                        if update not in agent.memory_log:
                            agent.memory_log.append(update)
                print("--------------------------------\n")
                
                # 3. Deliver the final user-facing message
                print(f"Agent: {data.get('response')}\n")
                
            except json.JSONDecodeError:
                # Safe fallback if the model outputs invalid formatting
                print(f"\nAgent (Raw): {raw_json_output}\n")

        except KeyboardInterrupt:
            print("\nShutting down agent state. Goodbye!")
            break
        except Exception as e:
            print(f"\nError in control loop: {e}\n")

if __name__ == "__main__":
    # Fire up the asynchronous runtime loop cleanly
    asyncio.run(main_loop())