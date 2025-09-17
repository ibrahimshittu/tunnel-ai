#!/usr/bin/env python3
"""Test script for the enhanced planner with page analysis."""

import asyncio
from agents.planner import TestPlanningAgent
from core.types import TestRequest
import json


async def test_planner():
    """Test the planner with a real website."""

    # Create a test request
    request = TestRequest(
        instruction="Test the login functionality by entering username and password, then clicking submit",
        url="https://example.com",  # Replace with actual test URL
        browser="chromium",
        headless=True
    )

    # Initialize the planner
    planner = TestPlanningAgent()

    print("Testing Tunnel AI Planner with Page Analysis")
    print("=" * 50)
    print(f"Instruction: {request.instruction}")
    print(f"Target URL: {request.url}")
    print("\nAnalyzing page and creating test plan...")

    try:
        # Create the test plan
        test_plan = await planner.plan(request)

        print("\n✅ Test Plan Created Successfully!")
        print("=" * 50)
        print(f"Test Name: {test_plan.name}")
        print(f"Description: {test_plan.description}")

        print("\n📋 Test Steps:")
        for i, step in enumerate(test_plan.steps, 1):
            print(f"{i}. {step.description}")
            print(f"   Action: {step.action.value}")
            if step.selector:
                print(f"   Selector: {step.selector}")
            if step.value:
                print(f"   Value: {step.value}")

        print("\n✓ Assertions:")
        for i, assertion in enumerate(test_plan.assertions, 1):
            print(f"{i}. {assertion.description}")
            print(f"   Type: {assertion.type.value}")
            if assertion.selector:
                print(f"   Selector: {assertion.selector}")
            print(f"   Expected: {assertion.expected}")

        if test_plan.test_data:
            print("\n📊 Test Data:")
            print(json.dumps(test_plan.test_data, indent=2))

        print("\n🏷️ Tags:", ", ".join(test_plan.tags) if test_plan.tags else "None")

    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    # Run the test
    asyncio.run(test_planner())