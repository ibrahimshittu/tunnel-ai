"""Tunnel AI Self-Healing Agent - Automatically fixes broken tests."""

from typing import Optional, Dict, Any
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from loguru import logger
import re

from config.settings import settings


class SelfHealingAgent:
    """Agent responsible for automatically fixing broken tests."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,
            api_key=settings.openai_api_key
        )

    async def heal(self, test_code: str, error: str, page_html: Optional[str] = None) -> str:
        """Attempt to fix broken test code based on error."""

        try:
            logger.info("Attempting to heal broken test")

            # Identify the type of error
            error_type = self._identify_error_type(error)

            # Apply appropriate healing strategy
            if error_type == "selector":
                healed_code = await self._fix_selector_error(test_code, error, page_html)
            elif error_type == "timeout":
                healed_code = await self._fix_timeout_error(test_code, error)
            elif error_type == "navigation":
                healed_code = await self._fix_navigation_error(test_code, error)
            else:
                healed_code = await self._general_fix(test_code, error)

            logger.success("Test healing completed")
            return healed_code

        except Exception as e:
            logger.error(f"Failed to heal test: {e}")
            return test_code  # Return original if healing fails

    def _identify_error_type(self, error: str) -> str:
        """Identify the type of error."""
        error_lower = error.lower()

        if "selector" in error_lower or "element" in error_lower:
            return "selector"
        elif "timeout" in error_lower:
            return "timeout"
        elif "navigation" in error_lower or "goto" in error_lower:
            return "navigation"
        else:
            return "general"

    async def _fix_selector_error(
        self,
        test_code: str,
        error: str,
        page_html: Optional[str] = None
    ) -> str:
        """Fix selector-related errors."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_selector_fix_prompt()),
            ("user", self._format_selector_fix_request(test_code, error, page_html))
        ])

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({})
            return response.content
        except Exception as e:
            logger.error(f"Failed to fix selector error: {e}")
            return self._apply_fallback_selector_fix(test_code, error)

    async def _fix_timeout_error(self, test_code: str, error: str) -> str:
        """Fix timeout-related errors."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_timeout_fix_prompt()),
            ("user", f"""Fix the timeout issue in this code:

Error: {error}

Code:
{test_code}

Add appropriate waits and timeout handling.""")
        ])

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({})
            return response.content
        except Exception as e:
            logger.error(f"Failed to fix timeout error: {e}")
            return self._apply_fallback_timeout_fix(test_code)

    async def _fix_navigation_error(self, test_code: str, error: str) -> str:
        """Fix navigation-related errors."""

        # Add retry logic for navigation
        fixed_code = test_code.replace(
            "await page.goto(",
            "await page.goto(",
        )

        # Add wait for load state
        if "waitForLoadState" not in fixed_code:
            fixed_code = fixed_code.replace(
                "await page.goto(",
                "await page.goto(",
            )
            fixed_code += "\nawait page.waitForLoadState('networkidle');"

        return fixed_code

    async def _general_fix(self, test_code: str, error: str) -> str:
        """Apply general fixes for unidentified errors."""

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_general_fix_prompt()),
            ("user", f"""Fix this broken test code:

Error: {error}

Code:
{test_code}

Return the fixed code with improved error handling.""")
        ])

        chain = prompt | self.llm

        try:
            response = await chain.ainvoke({})
            return response.content
        except Exception as e:
            logger.error(f"Failed to apply general fix: {e}")
            return test_code

    def _get_selector_fix_prompt(self) -> str:
        """Get prompt for fixing selector errors."""
        return """You are an expert at fixing broken Playwright selectors.

When a selector fails, you should:
1. Identify the problematic selector
2. Suggest alternative selectors (text, role, testid)
3. Add proper wait conditions
4. Use more resilient selector strategies

Fix the selector issue and return ONLY the corrected code."""

    def _get_timeout_fix_prompt(self) -> str:
        """Get prompt for fixing timeout errors."""
        return """You are an expert at fixing timeout issues in Playwright tests.

To fix timeout issues:
1. Add explicit waits before interactions
2. Use waitForSelector with appropriate timeout
3. Add waitForLoadState after navigations
4. Increase timeout values for slow operations
5. Add retry logic for flaky operations

Return ONLY the corrected code with proper timeout handling."""

    def _get_general_fix_prompt(self) -> str:
        """Get prompt for general fixes."""
        return """You are an expert at fixing Playwright test issues.

Analyze the error and fix the code by:
1. Adding proper error handling
2. Improving selector strategies
3. Adding necessary waits
4. Fixing syntax issues
5. Improving test reliability

Return ONLY the corrected, working code."""

    def _format_selector_fix_request(
        self,
        test_code: str,
        error: str,
        page_html: Optional[str] = None
    ) -> str:
        """Format the selector fix request."""
        request = f"""Fix the selector error in this code:

Error: {error}

Current Code:
{test_code}"""

        if page_html:
            # Extract relevant HTML around potential elements
            request += f"""

Relevant HTML structure:
{page_html[:2000]}  # Limit HTML to avoid token limits"""

        request += """

Provide alternative selectors that are more reliable."""

        return request

    def _apply_fallback_selector_fix(self, test_code: str, error: str) -> str:
        """Apply fallback fixes for selector errors."""

        # Extract the problematic selector from error
        selector_match = re.search(r"'([^']+)'", error)
        if selector_match:
            old_selector = selector_match.group(1)

            # Try text-based selector
            if old_selector.startswith("#") or old_selector.startswith("."):
                # Convert to text selector if possible
                element_text = old_selector.replace("#", "").replace(".", "").replace("-", " ")
                new_selector = f"text={element_text}"
                test_code = test_code.replace(f"'{old_selector}'", f"'{new_selector}'")

        # Add waits before all click and fill operations
        test_code = re.sub(
            r"await page\.(click|fill)\(",
            r"await page.waitForLoadState('domcontentloaded');\nawait page.\1(",
            test_code
        )

        return test_code

    def _apply_fallback_timeout_fix(self, test_code: str) -> str:
        """Apply fallback fixes for timeout errors."""

        # Increase all timeout values
        test_code = re.sub(
            r"timeout:\s*(\d+)",
            lambda m: f"timeout: {int(m.group(1)) * 2}",
            test_code
        )

        # Add default timeout if not present
        if "timeout" not in test_code:
            test_code = re.sub(
                r"await page\.(click|fill|waitForSelector)\(",
                r"await page.\1(",
                test_code
            )

        # Add wait for load state after navigation
        test_code = re.sub(
            r"await page\.goto\([^)]+\);",
            r"\g<0>\nawait page.waitForLoadState('networkidle');",
            test_code
        )

        return test_code