#!/usr/bin/env python3
"""
Automated Demo Module

Responsibility:
- Run automated demo with simulated answers
- Useful for testing without manual input
- Shows complete flow without user interaction

This is the automated demo that runs without user input.
"""

from conversation_engine import ConversationEngine


def get_answer_for_question(question: str) -> str:
    """
    Simulate intelligent answer selection based on question content.
    This provides automatic answers for demo purposes.
    """
    question_lower = question.lower()

    # Workspace questions
    if "workspace" in question_lower:
        return "dev-workspace"

    # Name for namespace
    if "name" in question_lower and "'ns'" in question:
        return "my-namespace"

    # IaCM pipelines
    if "apply" in question_lower and "'ns'" in question:
        return "RunIaCM"
    if "destroy" in question_lower and "'ns'" in question:
        return "DestroyIaCM"

    # Catalog identifier
    if "identifier" in question_lower and "'frontend'" in question:
        return "frontend"

    # Environment
    if "environment" in question_lower:
        return "mycluster"

    # Infrastructure
    if "infrastructure" in question_lower:
        return "ssemteamdelegate"

    # Catalog pipelines
    if "apply" in question_lower and "'frontend'" in question:
        return "DeployService"
    if "destroy" in question_lower and "'frontend'" in question:
        return "UninstallService"

    # Default
    return "default-value"


def main():
    """
    Automated demo: Create namespace and deploy frontend with simulated answers.
    """
    print()
    print("=" * 80)
    print("AUTOMATED DEMO - CONVERSATIONAL ENVIRONMENT BLUEPRINT COMPILER")
    print("=" * 80)
    print()
    print("This demo runs automatically with simulated answers.")
    print("For interactive mode, run: python3 main.py")
    print()
    print("=" * 80)
    print()

    # Initialize conversation engine
    engine = ConversationEngine()

    # User's initial intent
    user_intent = "Create namespace using TempNamespace template and deploy frontend component"

    print(f"USER: {user_intent}")
    print()

    # Process initial input
    try:
        response = engine.process_user_input(user_intent)
    except Exception as e:
        print(f"Error: {e}")
        print("\nPlease check your ANTHROPIC_API_KEY is set correctly.")
        print("Run: export ANTHROPIC_API_KEY='your-key-here'")
        return

    print(f"SYSTEM: {response}")
    print()

    # Automated conversation loop with simulated answers
    max_iterations = 20  # Safety limit
    iteration = 0

    while engine.state == "NEEDS_INPUT" and iteration < max_iterations:
        # Get intelligent answer based on question
        answer = get_answer_for_question(response)

        print(f"USER: {answer}")
        print()

        try:
            response = engine.process_user_input(answer)
        except Exception as e:
            print(f"Error: {e}")
            break

        print(f"SYSTEM: {response}")
        print()

        iteration += 1

    if iteration >= max_iterations:
        print("⚠️  WARNING: Reached maximum iterations")
        print()

    print("=" * 80)
    print("DEMO COMPLETE")
    print("=" * 80)
    print()

    # Show final state
    if engine.state == "YAML_RENDERED":
        print("✓ Blueprint successfully compiled!")
        print()
        print("Key Features Demonstrated:")
        print("  ✓ Claude parsed natural language intent")
        print("  ✓ Claude generated contextual questions")
        print("  ✓ Claude extracted values from answers")
        print("  ✓ Dependency auto-wiring: namespace → frontend")
        print("  ✓ Valid YAML blueprint generated")
    else:
        print(f"⚠️  Final state: {engine.state}")


if __name__ == "__main__":
    main()
