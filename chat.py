import os
import sys
from google import genai

def main():
    # Verify the API key is accessible in the environment
    if not os.environ.get("GEMINI_API_KEY"):
        print("Error: GEMINI_API_KEY environment variable not set.")
        print("Please run: export GEMINI_API_KEY='your_key'")
        sys.exit(1)

    print("Initializing Monad v0.1 baseline...")
    client = genai.Client()
    
    # Using the fast, responsive flash model
    model_id = "gemini-2.5-flash"
    
    # Create a persistent chat manager that tracks conversation state automatically
    chat = client.chats.create(model=model_id)
    
    print(f"Chat session established with {model_id}.")
    print("Type 'exit' or 'quit' to end the loop.\n")

    while True:
        try:
            # Git Bash compatible user input prompt
            user_input = input("You: ")
            
            # Check for breakout commands
            if user_input.strip().lower() in ['exit', 'quit']:
                print("Closing session. Goodbye!")
                break
                
            if not user_input.strip():
                continue

            # Send the message—the chat object handles the history context automatically
            response = chat.send_message(user_input)
            
            # Print the model's reply
            print(f"\nMonad: {response.text}\n")
            
        except KeyboardInterrupt:
            # Handle Ctrl+C cleanly in the terminal
            print("\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {e}\n")

if __name__ == "__main__":
    main()