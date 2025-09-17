"""Tunnel AI Validation Agent - Analyzes and validates test results."""

from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from loguru import logger

from core.types import TestResult
from config.settings import settings


class ValidationAgent:
    """Agent responsible for validating and analyzing test results."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0,
            api_key=settings.openai_api_key
        )

    async def validate(self, result: TestResult) -> TestResult:
        """Validate and enhance test results with insights."""

        try:
            logger.info(f"Validating test result: {result.id}")

            # Analyze the result
            analysis = await self._analyze_result(result)

            # Update result with analysis
            if result.error and not result.success:
                # Try to categorize the error
                error_category = await self._categorize_error(result.error)
                result.error = f"{error_category}: {result.error}"

            # Count passed/failed assertions
            passed = sum(1 for step in result.steps if step.success)
            failed = len(result.steps) - passed

            result.passed_assertions = passed
            result.failed_assertions = failed

            logger.success(f"Validation complete for result: {result.id}")
            return result

        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return result

    async def _analyze_result(self, result: TestResult) -> Dict[str, Any]:
        """Analyze test results for insights."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_analysis_prompt()),
            ("user", self._format_result_for_analysis(result))
        ])

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({})
            return {"analysis": response.content}
        except Exception as e:
            logger.error(f"Failed to analyze result: {e}")
            return {"analysis": "Analysis unavailable"}

    async def _categorize_error(self, error: str) -> str:
        """Categorize the error type."""

        error_keywords = {
            "timeout": "Timeout Error",
            "selector": "Selector Error",
            "navigation": "Navigation Error",
            "network": "Network Error",
            "assertion": "Assertion Failed",
            "element not found": "Element Not Found",
            "click": "Interaction Error",
            "fill": "Input Error"
        }

        error_lower = error.lower()
        for keyword, category in error_keywords.items():
            if keyword in error_lower:
                return category

        return "Test Execution Error"

    def _get_analysis_prompt(self) -> str:
        """Get the prompt for result analysis."""
        return """You are a test result analysis expert.

Analyze the test execution result and provide:
1. Summary of what was tested
2. Key findings
3. Potential issues identified
4. Recommendations for improvement

Be concise and focus on actionable insights."""

    def _format_result_for_analysis(self, result: TestResult) -> str:
        """Format result for analysis."""
        return f"""Test Result Analysis:

Success: {result.success}
Execution Time: {result.execution_time:.2f}s
Steps Executed: {len(result.steps)}
Passed Steps: {sum(1 for s in result.steps if s.success)}
Failed Steps: {sum(1 for s in result.steps if not s.success)}

Error (if any): {result.error or 'None'}

Failed Steps Details:
{self._format_failed_steps(result.steps)}

Provide a brief analysis of this test execution."""

    def _format_failed_steps(self, steps: List[Any]) -> str:
        """Format failed steps for analysis."""
        failed = [s for s in steps if not s.success]
        if not failed:
            return "No failed steps"

        formatted = []
        for step in failed[:5]:  # Limit to 5 failed steps
            formatted.append(
                f"- {step.step.description}: {step.error}"
            )

        return "\n".join(formatted)