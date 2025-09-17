"""Tunnel AI Generation Agent - Converts test plans into executable Playwright code."""

from typing import Optional
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from loguru import logger

from core.types import TestPlan
from config.settings import settings
from templates.playwright_templates import get_test_template, get_step_template


class TestGenerationAgent:
    """Agent responsible for generating Playwright test code from test plans."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key
        )

    async def generate(self, plan: TestPlan) -> str:
        """Generate Playwright test code from a test plan."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", self._get_user_prompt())
        ])

        chain = prompt | self.llm

        try:
            logger.info(f"Generating test code for plan: {plan.id}")

            # Generate the test code
            response = await chain.ainvoke({
                "test_name": plan.name,
                "test_description": plan.description,
                "url": plan.url,
                "steps": self._format_steps(plan),
                "assertions": self._format_assertions(plan),
                "test_data": plan.test_data or {}
            })

            generated_code = response.content

            # Wrap in test template
            test_code = get_test_template().format(
                test_id=plan.id,
                test_name=plan.name,
                test_body=generated_code
            )

            logger.success(f"Test code generated for plan: {plan.id}")
            return test_code

        except Exception as e:
            logger.error(f"Failed to generate test code: {e}")
            # Return fallback code
            return self._generate_fallback_code(plan)

    def _get_system_prompt(self) -> str:
        """Get the system prompt for code generation."""
        return """You are an expert Playwright test code generator.

Generate clean, maintainable, and robust Playwright test code based on test plans.

Follow these Playwright best practices:
1. Use proper wait strategies (waitForSelector, waitForLoadState, expect with timeout)
2. Include error handling with try-catch blocks
3. Use data-testid selectors when available
4. Add descriptive comments for complex operations
5. Use Page Object Model patterns for reusability
6. Include proper setup and teardown

Important guidelines:
- Generate ONLY the test function body (no imports or test wrapper)
- Use async/await syntax
- Include logging for debugging
- Handle dynamic content with appropriate waits
- Use Playwright's built-in assertions (expect)

The code should be production-ready and handle edge cases."""

    def _get_user_prompt(self) -> str:
        """Get the user prompt template."""
        return """Generate Playwright test code for:

Test Name: {test_name}
Description: {test_description}
URL: {url}

Steps to implement:
{steps}

Assertions to validate:
{assertions}

Test Data:
{test_data}

Generate clean, well-commented Playwright code that:
1. Navigates to the URL
2. Executes all steps in sequence
3. Validates all assertions
4. Handles errors gracefully
5. Takes screenshots on failure

Return ONLY the test function body code."""

    def _format_steps(self, plan: TestPlan) -> str:
        """Format steps for prompt."""
        formatted_steps = []
        for i, step in enumerate(plan.steps, 1):
            formatted_steps.append(
                f"{i}. {step.description}\n"
                f"   Action: {step.action.value}\n"
                f"   Selector: {step.selector or 'N/A'}\n"
                f"   Value: {step.value or 'N/A'}"
            )
        return "\n".join(formatted_steps)

    def _format_assertions(self, plan: TestPlan) -> str:
        """Format assertions for prompt."""
        formatted_assertions = []
        for i, assertion in enumerate(plan.assertions, 1):
            formatted_assertions.append(
                f"{i}. {assertion.description}\n"
                f"   Type: {assertion.type.value}\n"
                f"   Selector: {assertion.selector or 'N/A'}\n"
                f"   Expected: {assertion.expected}"
            )
        return "\n".join(formatted_assertions)

    def _generate_fallback_code(self, plan: TestPlan) -> str:
        """Generate fallback code if LLM fails."""
        code_parts = [f"// Test: {plan.name}"]
        code_parts.append(f"// {plan.description}")
        code_parts.append(f"await page.goto('{plan.url}');")
        code_parts.append("await page.waitForLoadState('networkidle');")

        # Add steps
        for step in plan.steps:
            step_code = get_step_template(step)
            if step_code:
                code_parts.append(step_code)

        # Add assertions
        for assertion in plan.assertions:
            if assertion.selector:
                if assertion.type.value == "visible":
                    code_parts.append(
                        f"await expect(page.locator('{assertion.selector}')).toBeVisible();"
                    )
                elif assertion.type.value == "text":
                    code_parts.append(
                        f"await expect(page.locator('{assertion.selector}')).toContainText('{assertion.expected}');"
                    )

        return "\n".join(code_parts)