#!/usr/bin/env python3
"""
Quick script to find the correct Vertex AI model name.
"""

import os
import sys


def check_vertex_models():
    """Find which Claude model works in Vertex AI."""
    project_id = os.environ.get("ANTHROPIC_VERTEX_PROJECT_ID")
    region = os.environ.get("CLOUD_ML_REGION", "us-east5")

    if not project_id:
        print("❌ ANTHROPIC_VERTEX_PROJECT_ID environment variable is NOT set")
        print()
        print("To set it, run:")
        print("  export ANTHROPIC_VERTEX_PROJECT_ID='your-project-id'")
        return False

    print(f"✓ Project ID: {project_id}")
    print(f"✓ Region: {region}")
    print()

    # Try to import anthropic
    try:
        from anthropic import AnthropicVertex
        print("✓ anthropic package is installed")
    except ImportError:
        print("❌ anthropic package is NOT installed")
        print()
        print("To install it, run:")
        print("  pip3 install anthropic[vertex]")
        return False

    print()
    print("Testing available Claude models in Vertex AI...")
    print("=" * 60)

    # Common Vertex AI model names to try
    models_to_try = [
        "claude-sonnet-4-5@20250929",  # Claude Code uses this
        "claude-3-5-sonnet@20240620",
        "claude-3-5-sonnet-v2@20241022",
        "claude-3-5-sonnet@20241022",
        "claude-3-opus@20240229",
        "claude-3-sonnet@20240229",
        "claude-3-haiku@20240307",
    ]

    client = AnthropicVertex(project_id=project_id, region=region)
    working_model = None

    for model in models_to_try:
        try:
            print(f"Trying {model}...", end=" ")
            response = client.messages.create(
                model=model,
                max_tokens=10,
                messages=[{"role": "user", "content": "Hi"}]
            )
            print(f"✓ SUCCESS!")
            print(f"  Response: {response.content[0].text}")
            working_model = model
            break
        except Exception as e:
            if "404" in str(e) or "NOT_FOUND" in str(e):
                print(f"✗ Not available")
            else:
                error_msg = str(e)[:100]
                print(f"✗ Error: {error_msg}")

    print()
    print("=" * 60)
    if working_model:
        print(f"✓ Found working model: {working_model}")
        print("=" * 60)
        print()
        print("Update llm_interface.py to use this model.")
        return True
    else:
        print("❌ No working models found")
        print("=" * 60)
        print()
        print("Your project may not have access to Claude models in Vertex AI.")
        print("Contact your GCP admin to enable Claude models.")
        return False


if __name__ == "__main__":
    success = check_vertex_models()
    sys.exit(0 if success else 1)
