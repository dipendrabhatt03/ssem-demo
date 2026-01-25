#!/usr/bin/env python3
"""
Interactive Environment Blueprint Compiler

Responsibility:
- Accept user input for environment blueprint description
- Guide user through conversational flow with real input
- Generate valid Environment Blueprint YAML

This is the interactive entry point for the system.
"""

import sys
from conversation_engine import ConversationEngine


def print_header():
    """Print welcome header."""
    print()
    print("=" * 80)
    print("CONVERSATIONAL ENVIRONMENT BLUEPRINT COMPILER")
    print("=" * 80)
    print()
    print("Welcome! I'll help you create a Harness Environment Blueprint through")
    print("a conversational interface.")
    print()
    print("Available resources:")
    print("  - IaCM Templates: TempNamespace (creates a Kubernetes namespace)")
    print("  - Catalog Components: frontend, backend")
    print("  - CD Environments: mycluster")
    print()
    print("Example: 'Create a namespace using TempNamespace and deploy frontend service'")
    print()
    print("Type 'quit' or 'exit' at any time to stop.")
    print("=" * 80)
    print()


def get_user_input(prompt: str) -> str:
    """
    Get input from user with error handling.

    Args:
        prompt: Prompt to display to user

    Returns:
        User input string
    """
    try:
        user_input = input(prompt).strip()
        return user_input
    except (KeyboardInterrupt, EOFError):
        print("\n\nExiting...")
        sys.exit(0)


def main():
    """
    Main interactive loop.

    Flow:
    1. Get initial user intent
    2. Parse intent and create initial graph
    3. Loop: Ask questions → Get answers → Update graph
    4. Generate final YAML when complete
    """
    print_header()

    # Initialize conversation engine
    engine = ConversationEngine()

    # Get initial user intent
    print("What environment blueprint do you want to create?")
    user_intent = get_user_input("> ")

    # Check for exit commands
    if user_intent.lower() in ['quit', 'exit', '']:
        print("Goodbye!")
        return

    print()
    print("Processing your request...")
    print()

    # Process initial input
    try:
        response = engine.process_user_input(user_intent)
    except Exception as e:
        print(f"Error processing input: {e}")
        print("\nPlease check your ANTHROPIC_API_KEY is set correctly.")
        print("Run: export ANTHROPIC_API_KEY='your-key-here'")
        sys.exit(1)

    # Interactive conversation loop
    max_iterations = 50  # Safety limit
    iteration = 0

    while engine.state == "NEEDS_INPUT" and iteration < max_iterations:
        # Display the system's question
        print(f"SYSTEM: {response}")
        print()

        # Get user's answer
        answer = get_user_input("YOUR ANSWER: ")

        # Check for exit commands
        if answer.lower() in ['quit', 'exit']:
            print("\nExiting without completing blueprint.")
            return

        if not answer:
            print("(Please provide an answer)")
            print()
            continue

        print()

        # Process the answer
        try:
            response = engine.process_user_input(answer)
        except Exception as e:
            print(f"Error processing answer: {e}")
            print("Please try again.")
            print()
            continue

        iteration += 1

    # Check if we hit iteration limit
    if iteration >= max_iterations:
        print("⚠️  WARNING: Reached maximum iterations.")
        print("There may be an issue with the conversation flow.")
        return

    # Display final result
    print()
    print("=" * 80)

    if engine.state == "YAML_RENDERED":
        print("✓ BLUEPRINT COMPILATION COMPLETE!")
        print("=" * 80)
        print()
        print("Generated YAML:")
        print()
        print(response)
        print()
        print("=" * 80)
        print()
        print("Your Environment Blueprint is ready to use!")
        print("Copy the YAML above and apply it to your Harness account.")
    else:
        print("⚠️  Blueprint compilation incomplete")
        print(f"Final state: {engine.state}")
        print("=" * 80)


if __name__ == "__main__":
    main()
