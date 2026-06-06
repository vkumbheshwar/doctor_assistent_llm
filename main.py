"""
Doctor's Assistant - Main Entry Point
========================================

This is the main application that ties together:
  1. Configuration (config/settings.py)
  2. Database (db/models.py)
  3. Tool definitions + handlers (tools/tools_definitions.py)
  4. OpenAI client with tool calling (llm/openai_client.py)

HOW TO RUN:
  python -m doctor_assistant.main

PREREQUISITES:
  1. Install dependencies: pip install -r requirements.txt
  2. Set your OpenAI API key in .env file (copy from .env.example)
  3. Run the application

ARCHITECTURE OVERVIEW:
  ┌─────────────────────────────────────────────────────┐
  │                    main.py                          │
  │                 (Orchestrator)                      │
  │                                                     │
  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐  │
  │  │ config/  │  │   db/    │  │   llm/           │  │
  │  │settings  │  │ models   │  │ openai_client    │  │
  │  │          │  │          │  │                  │  │
  │  │ .env     │  │ SQLite   │  │ OpenAI API       │  │
  │  │ vars     │  │ in-memory│  │ + tool calling   │  │
  │  └──────────┘  └────┬─────┘  └────────┬─────────┘  │
  │                     │                  │            │
  │                     ▼                  │            │
  │              ┌──────────┐              │            │
  │              │ tools/   │◄─────────────┘            │
  │              │definitions│                          │
  │              └──────────┘                           │
  └─────────────────────────────────────────────────────┘

Flow:
  1. User sends a message
  2. main.py sends it to OpenAIChatClient
  3. OpenAIChatClient calls OpenAI API with tools defined
  4. If OpenAI decides to use a tool, tools_definitions.py
     handles it by querying/modifying the database
  5. Result goes back to OpenAI for natural language response
  6. Response is displayed to the user

DESIGN PATTERN: Layered Architecture
---------------------------------------
This follows a clean layered architecture:
  - Presentation Layer (main.py) - CLI interface
  - Application Layer (llm/) - Business logic orchestration
  - Domain Layer (tools/) - Tool definitions and handlers
  - Persistence Layer (db/) - Database operations
  - Configuration Layer (config/) - Settings management

Each layer depends only on the layer below it.
This separation allows each component to be tested,
modified, or replaced independently.
"""

import sys
import json
from datetime import datetime

from doctor_assistant.db.models import DoctorAssistantDB
from doctor_assistant.llm.openai_client import OpenAIChatClient
from doctor_assistant.config.settings import CLINIC_NAME


def print_header():
    """Print a nice header for the application."""
    print("\n" + "=" * 60)
    print(f"  Welcome to {CLINIC_NAME} - Doctor's Assistant")
    print("  Powered by OpenAI + In-Memory Database")
    print("=" * 60)
    print()
    print("Commands:")
    print("  /quit    - Exit the application")
    print("  /new     - Start a new conversation")
    print("  /summary - Show conversation summary")
    print("  /help    - Show this help menu")
    print()
    print("Type your message and press Enter to chat.")
    print("The assistant can help you find doctors,")
    print("check availability, and book appointments.")
    print()


def run_interactive_session(db):
    """
    Run an interactive chat session with the user.
    
    This function:
    1. Creates a new chat client (with system prompt)
    2. Sends user messages and displays AI responses
    3. Handles special commands (/quit, /new, etc.)
    4. Preserves conversation history between messages
    
    The conversation state is maintained in the
    OpenAIChatClient.messages list, which grows with
    each exchange, allowing the AI to maintain context.
    """
    chat_client = OpenAIChatClient(db)
    
    print_header()
    
    # Initial greeting from the assistant
    chat_client.add_user_message("Start the conversation")
    initial_response = chat_client.get_response()
    print(f"\n{CLINIC_NAME} Assistant: {initial_response}\n")
    
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()
            
            # Handle special commands
            if user_input.lower() in ["/quit", "/exit", "/q"]:
                print("\nThank you for using the Doctor's Assistant.")
                print("Have a great day!")
                break
            
            if user_input.lower() in ["/new", "/reset"]:
                chat_client.reset()
                print("\n--- Conversation reset. Starting fresh ---\n")
                
                # Start new conversation with greeting
                chat_client.add_user_message("Start the conversation")
                initial_response = chat_client.get_response()
                print(f"\n{CLINIC_NAME} Assistant: {initial_response}\n")
                continue
            
            if user_input.lower() == "/summary":
                print("\n--- Conversation Summary ---")
                print(chat_client.get_conversation_summary())
                print("--- End Summary ---\n")
                continue
            
            if user_input.lower() in ["/help", "/h"]:
                print_header()
                continue
            
            if not user_input:
                continue
            
            # Send user message to the AI
            chat_client.add_user_message(user_input)
            
            print("  [Processing...]")
            response = chat_client.get_response()
            
            print(f"\n{CLINIC_NAME} Assistant: {response}\n")
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        
        except Exception as e:
            print(f"\n  [Error] An error occurred: {e}")
            print("  Please try again or type /quit to exit.\n")


def run_demo_scenarios(db):
    """
    Run the three predefined demo scenarios from the requirements.
    
    These demonstrate the chatbot's capabilities:
    
    Scenario 1: Direct doctor request with time negotiation
    Scenario 2: Symptom-based referral (when no specialist available)
    Scenario 3: Symptom-based referral with alternative doctor
    
    Each scenario runs as a separate conversation session
    (new chat client, fresh context).
    """
    
    # ─────────────────────────────────────────────────────
    # SCENARIO 1: Direct appointment booking with time negotiation
    # ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" SCENARIO 1: Direct doctor request + time negotiation")
    print("=" * 60)
    
    chat1 = OpenAIChatClient(db)
    chat1.add_user_message("Start the conversation")
    response = chat1.get_response()
    print(f"\n[Agent]: {response}")
    
    conversations_scenario1 = [
        "Hi, can I have an appointment with Dr. Sharma?",
        "I would like to meet him tomorrow at 10 AM. My name is Ananya.",
    ]
    
    for msg in conversations_scenario1:
        print(f"\n[Caller]: {msg}")
        chat1.add_user_message(msg)
        print("  [Processing...]")
        response = chat1.get_response()
        print(f"[Agent]: {response}")
    
    # If there's a pending booking, confirm it
    # The AI should ask for confirmation
    print(f"\n[Caller]: Ok, that works. Please book the appointment.")
    chat1.add_user_message("Ok, that works. Please book the appointment.")
    print("  [Processing...]")
    response = chat1.get_response()
    print(f"[Agent]: {response}")
    
    print("\n" + "-" * 40)
    print(" Scenario 1 Complete!")
    print("-" * 40)
    
    # ─────────────────────────────────────────────────────
    # SCENARIO 2: Symptom described, no specialist available
    # ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" SCENARIO 2: Symptom-based - no specialist available")
    print("=" * 60)
    
    chat2 = OpenAIChatClient(db)
    chat2.add_user_message("Start the conversation")
    response = chat2.get_response()
    print(f"\n[Agent]: {response}")
    
    conversations_scenario2 = [
        "Hi, I have been having these rashes for the past few days. "
        "Would like to meet a doctor, could you help?",
        "No, that's all. Thank you.",
    ]
    
    for msg in conversations_scenario2:
        print(f"\n[Caller2]: {msg}")
        chat2.add_user_message(msg)
        print("  [Processing...]")
        response = chat2.get_response()
        print(f"[Agent]: {response}")
    
    print("\n" + "-" * 40)
    print(" Scenario 2 Complete!")
    print("-" * 40)
    
    # ─────────────────────────────────────────────────────
    # SCENARIO 3: Symptom described, alternative doctor offered
    # ─────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print(" SCENARIO 3: Symptom-based with alternative doctor")
    print("=" * 60)
    
    chat3 = OpenAIChatClient(db)
    chat3.add_user_message("Start the conversation")
    response = chat3.get_response()
    print(f"\n[Agent]: {response}")
    
    conversations_scenario3 = [
        "Hi, I fell down while playing badminton - my ankle is swollen. "
        "Would like to meet a doctor today, could you help?",
    ]
    
    for msg in conversations_scenario3:
        print(f"\n[Caller3]: {msg}")
        chat3.add_user_message(msg)
        print("  [Processing...]")
        response = chat3.get_response()
        print(f"[Agent]: {response}")
    
    # The AI should suggest Dr. Singh or Dr. Gupta (Orthopedics)
    # Let the user pick one
    print(f"\n[Caller3]: I would like to meet Dr. Singh")
    chat3.add_user_message("I would like to meet Dr. Singh")
    print("  [Processing...]")
    response = chat3.get_response()
    print(f"[Agent]: {response}")
    
    # If not available, suggest alternative
    print(f"\n[Caller3]: Oh! In that case, can I meet Dr. Gupta today?")
    chat3.add_user_message("Oh! In that case, can I meet Dr. Gupta today? My name is Rahul.")
    print("  [Processing...]")
    response = chat3.get_response()
    print(f"[Agent]: {response}")
    
    # Confirm booking
    print(f"\n[Caller3]: Ok, that sounds good. Please book it.")
    chat3.add_user_message("Ok, that sounds good. Please book it.")
    print("  [Processing...]")
    response = chat3.get_response()
    print(f"[Agent]: {response}")
    
    print("\n" + "-" * 40)
    print(" Scenario 3 Complete!")
    print("-" * 40)
    
    print("\n" + "=" * 60)
    print(" All demo scenarios completed!")
    print("=" * 60)
    
    # Show final database state
    print("\n\nFinal Database State:")
    print("-" * 40)
    appointments = db.get_upcoming_appointments()
    if appointments:
        print(f"Total appointments booked: {len(appointments)}")
        for apt in appointments:
            print(f"  - {apt['patient_name']} with {apt['doctor_name']} "
                  f"on {apt['date']} at {apt['start_time']}")
    else:
        print("No appointments booked.")
    
    # Show available slots for a doctor that has bookings
    print("\n\nAvailable slots for Dr. Singh tomorrow:")
    from datetime import datetime, timedelta
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    slots = db.get_available_slots(3, tomorrow)  # Dr. Singh = ID 3
    if slots:
        for slot in slots:
            print(f"  - {slot['start_time']} to {slot['end_time']}")
    else:
        print("  (No availability or day off)")


def main():
    """
    Main entry point. Initializes DB and starts the application.
    
    The database is created in-memory and populated with seed data.
    Since it's in-memory, data is lost when the program exits.
    """
    print("Initializing Doctor's Assistant...")
    print("  Creating in-memory database...")
    
    # Initialize the in-memory database
    db = DoctorAssistantDB()
    
    print("  Loading sample data...")
    print("  Connecting to OpenAI API...")
    print("  Ready!")
    
    # Check if running demo mode or interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_demo_scenarios(db)
    else:
        run_interactive_session(db)
    
    # Clean up
    db.close()
    print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()