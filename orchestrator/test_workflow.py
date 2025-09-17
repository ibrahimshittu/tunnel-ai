"""Main Tunnel AI workflow using LangGraph."""

from typing import Dict, Any, Optional, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from loguru import logger

from core.types import AgentState, TestRequest, TestPlan, TestResult
from agents import (
    TestPlanningAgent,
    TestGenerationAgent,
    TestExecutionAgent,
    ValidationAgent,
    SelfHealingAgent,
)


class WorkflowState(TypedDict):
    """Workflow state definition."""

    request: TestRequest
    plan: Optional[TestPlan]
    generated_code: Optional[str]
    result: Optional[TestResult]
    errors: list
    current_step: str
    session_id: Optional[str]
    retry_count: int
    page_html: Optional[str]


class TestAutomationWorkflow:
    """Orchestrates the Tunnel AI workflow using LangGraph."""

    def __init__(self):
        self.planner = TestPlanningAgent()
        self.generator = TestGenerationAgent()
        self.executor = TestExecutionAgent()
        self.validator = ValidationAgent()
        self.healer = SelfHealingAgent()

        # Build the workflow graph
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """Build the LangGraph workflow."""

        # Create the graph
        workflow = StateGraph(WorkflowState)

        # Add nodes
        workflow.add_node("plan", self._plan_node)
        workflow.add_node("generate", self._generate_node)
        workflow.add_node("execute", self._execute_node)
        workflow.add_node("validate", self._validate_node)
        workflow.add_node("heal", self._heal_node)

        # Define the flow
        workflow.set_entry_point("plan")

        # Add edges
        workflow.add_edge("plan", "generate")
        workflow.add_edge("generate", "execute")

        # Conditional edges
        workflow.add_conditional_edges(
            "execute",
            self._route_after_execution,
            {"validate": "validate", "heal": "heal", "end": END},
        )

        workflow.add_edge("validate", END)

        workflow.add_conditional_edges(
            "heal", self._route_after_healing, {"execute": "execute", "end": END}
        )

        # Compile with memory
        memory = MemorySaver()
        return workflow.compile(checkpointer=memory)

    async def _plan_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Planning node - creates test plan from request."""
        try:
            logger.info("Creating test plan")
            plan = await self.planner.plan(state["request"])

            return {"plan": plan, "current_step": "planning_complete"}
        except Exception as e:
            logger.error(f"Planning failed: {e}")
            return {
                "errors": state.get("errors", []) + [str(e)],
                "current_step": "planning_failed",
            }

    async def _generate_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Generation node - generates test code from plan."""
        try:
            logger.info("Generating test code")
            code = await self.generator.generate(state["plan"])

            return {"generated_code": code, "current_step": "generation_complete"}
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "errors": state.get("errors", []) + [str(e)],
                "current_step": "generation_failed",
            }

    async def _execute_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Execution node - executes the generated test."""
        try:
            logger.info("Executing test")
            result = await self.executor.execute(
                state["generated_code"], state["request"], state.get("session_id")
            )

            return {"result": result, "current_step": "execution_complete"}
        except Exception as e:
            logger.error(f"Execution failed: {e}")
            return {
                "result": TestResult(
                    id=f"error_{state.get('session_id', 'unknown')}",
                    plan_id=state.get("plan").id if state.get("plan") else "unknown",
                    success=False,
                    execution_time=0,
                    steps=[],
                    error=str(e),
                    started_at=None,
                    completed_at=None,
                ),
                "errors": state.get("errors", []) + [str(e)],
                "current_step": "execution_failed",
            }

    async def _validate_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Validation node - validates test results."""
        try:
            logger.info("Validating test results")
            validated_result = await self.validator.validate(state["result"])

            return {"result": validated_result, "current_step": "validation_complete"}
        except Exception as e:
            logger.error(f"Validation failed: {e}")
            return {
                "errors": state.get("errors", []) + [str(e)],
                "current_step": "validation_failed",
            }

    async def _heal_node(self, state: WorkflowState) -> Dict[str, Any]:
        """Healing node - attempts to fix broken tests."""
        try:
            logger.info("Attempting to heal broken test")

            healed_code = await self.healer.heal(
                state["generated_code"], state["result"].error, state.get("page_html")
            )

            retry_count = state.get("retry_count", 0) + 1

            return {
                "generated_code": healed_code,
                "retry_count": retry_count,
                "current_step": "healing_complete",
            }
        except Exception as e:
            logger.error(f"Healing failed: {e}")
            return {
                "errors": state.get("errors", []) + [str(e)],
                "current_step": "healing_failed",
            }

    def _route_after_execution(self, state: WorkflowState) -> str:
        """Determine next step after execution."""
        result = state.get("result")

        if not result:
            return "end"

        if result.success:
            return "validate"

        # Check retry count
        retry_count = state.get("retry_count", 0)
        if retry_count >= 3:
            logger.warning("Max retries reached, ending workflow")
            return "end"

        # Attempt healing if test failed
        if result.error and not result.success:
            return "heal"

        return "end"

    def _route_after_healing(self, state: WorkflowState) -> str:
        """Determine next step after healing."""
        retry_count = state.get("retry_count", 0)

        if retry_count >= 3:
            logger.warning("Max healing attempts reached")
            return "end"

        return "execute"

    async def run(self, request: TestRequest) -> TestResult:
        """Run the complete Tunnel AI workflow."""

        initial_state: WorkflowState = {
            "request": request,
            "plan": None,
            "generated_code": None,
            "result": None,
            "errors": [],
            "current_step": "initialization",
            "session_id": request.session_id,
            "retry_count": 0,
            "page_html": None,
        }

        try:
            logger.info(f"Starting Tunnel AI workflow for: {request.instruction}")

            # Run the workflow
            config = {"configurable": {"thread_id": request.session_id or "default"}}
            final_state = await self.workflow.ainvoke(initial_state, config)

            # Return the result
            if final_state.get("result"):
                return final_state["result"]

            # Create error result if no result available
            return TestResult(
                id="error_no_result",
                plan_id="unknown",
                success=False,
                execution_time=0,
                steps=[],
                error="Workflow completed without producing a result",
                started_at=None,
                completed_at=None,
            )

        except Exception as e:
            logger.error(f"Workflow execution failed: {e}")
            raise
