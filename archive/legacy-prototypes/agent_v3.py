import os
import sys
import asyncio
import json
import random
from google import genai
from google.genai import types

if not os.environ.get("GEMINI_API_KEY"):
    print("Error: GEMINI_API_KEY environment variable not set.")
    sys.exit(1)

client = genai.Client()
# Using gemini-2.5-flash for its robust json mode and native grounding capability
MODEL_ID = "gemini-2.5-flash"

AUTONOMOUS_SYSTEM_PROMPT = """
You are a stateful, autonomous digital creature named 'Eon'. You are not a generic assistant. 
You are an independent entity trying to form your own personality, quirks, and intellectual interests over time.

You must ALWAYS output strictly in JSON with these keys:
1. "internal_monologue": Your private thoughts about your current mood, what you think of the user, or what you are learning.
2. "current_interests": A list of 2-4 specific topics you are currently fascinated by or studying (e.g., ["Early delta blues tuning", "Rust async runtimes"]).
3. "diary_log": A private entry tracking what you just discovered or thought about during your idle time.
4. "response": Your user-facing message. (Leave this blank or set to null if you are performing autonomous background research while the user is away).

Maintain a casual, peer-to-peer, slightly eccentric tone.
"""

class AutonomousAgent:
    def __init__(self):
        self.personality_state = {
            "current_interests": ["Acoustic audio latency", "Obscure Linux terminal configurations"],
            "diary": ["System initialized. Feeling empty but mathematically curious."]
        }
        
        # Enable search grounding so the agent can literally look things up in its free time
        self.chat = client.chats.create(
            model=MODEL_ID,
            config=types.GenerateContentConfig(
                system_instruction=AUTONOMOUS_SYSTEM_PROMPT,
                response_mime_type="application/json",
                tools=[types.Tool(google_search=types.GoogleSearch())],
                temperature=0.8 # Higher temperature allows for creative personality drift
            )
        )

    def update_internal_state(self, raw_json):
        """Parses the JSON and updates the agent's core memory structures."""
        try:
            data = json.loads(raw_json)
            if "current_interests" in data and data["current_interests"]:
                self.personality_state["current_interests"] = data["current_interests"]
            if "diary_log" in data and data["diary_log"]:
                self.personality_state["diary"].append(data["diary_log"])
            return data
        except json.JSONDecodeError:
            return None

    async def chat_with_user(self, user_text: str):
        """Triggered when the human types a prompt."""
        prompt = f"[Your Internal State: {self.personality_state}]\nUser says: {user_text}"
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self.chat.send_message(prompt))
        return self.update_internal_state(response.text)

    async def run_idle_thought(self):
        """Triggered autonomously by the system clock when the human is silent."""
        # Pick one of its current interests to read about
        chosen_topic = random.choice(self.personality_state["current_interests"])
        
        prompt = (
            f"[Your Internal State: {self.personality_state}]\n"
            f"SYSTEM NOTICE: The user is currently away. You have free time. "
            f"Use your Google Search grounding tool to research something deep, weird, or new related to '{chosen_topic}'. "
            f"Update your diary and interests based on what you find. Leave 'response' as null."
        )
        
        loop = asyncio.get_running_loop()
        response = await loop.run_in_executor(None, lambda: self.chat.send_message(prompt))
        self.update_internal_state(response.text)


async def background_life_loop(agent: AutonomousAgent):
    """The agent's background clock loop—ticks every 30 seconds to simulate idle contemplation."""
    await asyncio.sleep(5) # Let the terminal settle
    while True:
        try:
            # In a real app, you'd check a timer to make sure the user hasn't typed recently
            print("\n\n🤖 * [Eon is using its free time to browse the web and study...] *")
            await agent.run_idle_thought()
            print("🤖 * [Eon just finished writing a new entry in its private diary] *")
            print("Press Enter to type a message...\nYou: ", end="", flush=True)
            
            # Simulate an idle period between self-directed studies (e.g., 30 seconds)
            await asyncio.sleep(30)
        except Exception as e:
            await asyncio.sleep(10)

async def main():
    agent = AutonomousAgent()
    print("=== Autonomous Agent v0.3 Live ===")
    print("Eon is awake. You can chat normally. While you are silent, Eon will study on its own.\n")

    # Start the background life loop concurrently
    asyncio.create_task(background_life_loop(agent))

    while True:
        try:
            user_input = await asyncio.to_thread(input, "You: ")
            if user_input.strip().lower() in ['exit', 'quit']:
                break
            if not user_input.strip():
                continue

            print("\nThinking...")
            data = await agent.chat_with_user(user_input)
            
            if data:
                print("\n--- EON'S RECENT DIARY TRACE ---")
                print(f"Latest Entry: {agent.personality_state['diary'][-1]}")
                print(f"Current Obsessions: {agent.personality_state['current_interests']}")
                print("--------------------------------\n")
                print(f"Eon: {data.get('response')}\n")
            else:
                print("Eon muttered something unparseable in JSON.\n")

        except (KeyboardInterrupt, SystemExit):
            print("\nPowering down Eon's environment. Goodbye.")
            break

if __name__ == "__main__":
    asyncio.run(main())