"""Tunnel AI Planning Agent - Analyzes natural language and creates test plans."""

from typing import List, Optional
from datetime import datetime
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from loguru import logger
from pydantic import BaseModel, Field

from core.types import TestRequest, TestPlan, TestStep, Assertion, ActionType, AssertionType
from config.settings import settings
from agents.utils import PageAnalyzer


class TestPlanOutput(BaseModel):
    """Structured output for test plan generation."""
    name: str = Field(description="Name of the test")
    description: str = Field(description="Detailed description of the test")
    steps: List[dict] = Field(description="List of test steps")
    assertions: List[dict] = Field(description="List of assertions")
    test_data: Optional[dict] = Field(default=None, description="Test data if needed")
    tags: List[str] = Field(default_factory=list, description="Test tags")


class TestPlanningAgent:
    """Agent responsible for creating test plans from natural language."""

    def __init__(self):
        self.llm = ChatOpenAI(
            model=settings.openai_model,
            temperature=0.1,
            api_key=settings.openai_api_key
        )
        self.output_parser = PydanticOutputParser(pydantic_object=TestPlanOutput)
        self.page_analyzer = PageAnalyzer()

    async def plan(self, request: TestRequest) -> TestPlan:
        """Create a test plan from natural language instruction."""

        # First, analyze the target page to understand its structure
        logger.info(f"Analyzing target page: {request.url}")
        page_context = await self.page_analyzer.get_page_context(request.url)

        prompt = ChatPromptTemplate.from_messages([
            ("system", self._get_system_prompt()),
            ("user", self._get_user_prompt())
        ])

        chain = prompt | self.llm | self.output_parser

        try:
            logger.info(f"Creating test plan for: {request.instruction}")

            result = await chain.ainvoke({
                "instruction": request.instruction,
                "url": request.url,
                "page_context": page_context,
                "format_instructions": self.output_parser.get_format_instructions()
            })

            # Convert to TestPlan
            test_plan = self._convert_to_test_plan(result, request)

            logger.success(f"Test plan created: {test_plan.id}")
            return test_plan

        except Exception as e:
            logger.error(f"Failed to create test plan: {e}")
            raise

    def _get_system_prompt(self) -> str:
        """Get the system prompt for test planning."""
        return """You are an expert test planning agent specializing in frontend web testing.

Your task is to create comprehensive test plans from natural language instructions.
You have been provided with the actual page structure and available selectors.

IMPORTANT: Use the EXACT selectors provided in the page context. Do not make up selectors.

Consider the following when creating test plans:
1. User interactions (clicks, typing, navigation, scrolling)
2. Wait conditions for dynamic content
3. Validation assertions to verify expected behavior
4. Edge cases and error scenarios
5. Data requirements for testing

For selectors, use EXACTLY what's provided in the page context:
- Use the exact selectors shown for each element
- Prefer data-testid selectors when available
- Use the provided ID selectors (e.g., #elementId)
- Use the provided class selectors (e.g., .className)
- Use the text-based selectors for buttons/links (e.g., button:has-text("Submit"))

Always include proper wait conditions and error handling steps.

{format_instructions}"""

    def _get_user_prompt(self) -> str:
        """Get the user prompt template."""
        return """Create a detailed test plan for the following:

Instruction: {instruction}
Target URL: {url}

PAGE CONTEXT AND AVAILABLE SELECTORS:
{page_context}

Based on the actual page structure above, generate a comprehensive test plan with:
1. Clear, descriptive name and description
2. Step-by-step actions using the EXACT selectors from the page context
3. Assertions to validate the test
4. Any necessary test data
5. Relevant tags for categorization

CRITICAL: Only use selectors that exist in the page context above. Do not invent new selectors.
If a needed element is not in the page context, mention it in the description but skip that step."""

    def _convert_to_test_plan(self, output: TestPlanOutput, request: TestRequest) -> TestPlan:
        """Convert the LLM output to a TestPlan object."""

        # Convert steps
        steps = []
        for step_data in output.steps:
            try:
                # Validate action type
                action = step_data.get("action", "click")
                if action not in [e.value for e in ActionType]:
                    logger.warning(f"Unknown action type: {action}, defaulting to click")
                    action = "click"

                steps.append(TestStep(
                    action=ActionType(action),
                    selector=step_data.get("selector"),
                    value=step_data.get("value"),
                    description=step_data.get("description", ""),
                    wait_before=step_data.get("wait_before"),
                    wait_after=step_data.get("wait_after")
                ))
            except Exception as e:
                logger.warning(f"Invalid step data: {step_data}, error: {e}")

        # Convert assertions
        assertions = []
        for assertion_data in output.assertions:
            try:
                # Validate assertion type
                assert_type = assertion_data.get("type", "visible")
                if assert_type not in [e.value for e in AssertionType]:
                    logger.warning(f"Unknown assertion type: {assert_type}, defaulting to visible")
                    assert_type = "visible"

                assertions.append(Assertion(
                    type=AssertionType(assert_type),
                    selector=assertion_data.get("selector"),
                    expected=assertion_data.get("expected"),
                    description=assertion_data.get("description", ""),
                    operator=assertion_data.get("operator", "equals")
                ))
            except Exception as e:
                logger.warning(f"Invalid assertion data: {assertion_data}, error: {e}")

        return TestPlan(
            id=f"test_{datetime.now().timestamp()}",
            name=output.name,
            description=output.description,
            url=request.url,
            steps=steps,
            assertions=assertions,
            test_data=output.test_data,
            tags=output.tags
        )