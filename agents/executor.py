"""Tunnel AI Execution Agent - Executes generated tests using Playwright and Browserbase."""

import asyncio
import time
from typing import Optional, List
from datetime import datetime
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from core.types import TestRequest, TestResult, StepResult, TestStep
from core.browserbase_client import BrowserbaseClient
from config.settings import settings


class TestExecutionAgent:
    """Agent responsible for executing tests on Browserbase infrastructure."""

    def __init__(self):
        self.browserbase = BrowserbaseClient()
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None

    async def execute(
        self,
        test_code: str,
        request: TestRequest,
        session_id: Optional[str] = None
    ) -> TestResult:
        """Execute the generated test code."""

        start_time = time.time()
        screenshots: List[str] = []
        step_results: List[StepResult] = []

        try:
            logger.info(f"Starting test execution with browser: {request.browser}")

            # Create or reuse browser session
            if not session_id:
                session = await self.browserbase.create_session(
                    browser=request.browser.value,
                    headless=request.headless,
                    viewport=request.viewport
                )
                session_id = session["sessionId"]

            # Connect to Browserbase via Playwright
            async with async_playwright() as p:
                # Connect to remote browser
                browser = await p.chromium.connect(
                    self.browserbase.get_playwright_connection_url(session_id)
                )

                context = await browser.new_context(
                    viewport=request.viewport,
                    record_video_dir="./videos" if not request.headless else None
                )

                page = await context.new_page()
                self.page = page

                # Execute the test code
                try:
                    # Create execution environment
                    exec_globals = {
                        "page": page,
                        "expect": self._create_expect_function(page),
                        "screenshot": self._create_screenshot_function(screenshots)
                    }

                    # Execute the test
                    exec(f"async def test_function():\n{self._indent_code(test_code)}", exec_globals)
                    await exec_globals["test_function"]()

                    success = True
                    error = None

                except Exception as e:
                    logger.error(f"Test execution failed: {e}")
                    success = False
                    error = str(e)

                    # Take screenshot on failure
                    if settings.screenshot_on_failure:
                        try:
                            screenshot_path = f"./screenshots/error_{session_id}_{time.time()}.png"
                            await page.screenshot(path=screenshot_path)
                            screenshots.append(screenshot_path)
                        except:
                            pass

                finally:
                    await context.close()
                    await browser.close()

            # Get additional artifacts from Browserbase
            browserbase_screenshots = await self.browserbase.get_screenshots(session_id)
            screenshots.extend(browserbase_screenshots)

            video_url = await self.browserbase.get_recording(session_id)

            execution_time = time.time() - start_time

            result = TestResult(
                id=f"result_{time.time()}",
                plan_id=request.session_id or "unknown",
                success=success,
                execution_time=execution_time,
                steps=step_results,
                screenshots=screenshots,
                video_url=video_url,
                error=error,
                started_at=datetime.fromtimestamp(start_time),
                completed_at=datetime.now()
            )

            logger.info(f"Test execution completed in {execution_time:.2f}s - Success: {success}")
            return result

        except Exception as e:
            logger.error(f"Failed to execute test: {e}")

            return TestResult(
                id=f"result_{time.time()}",
                plan_id=request.session_id or "unknown",
                success=False,
                execution_time=time.time() - start_time,
                steps=step_results,
                screenshots=screenshots,
                error=str(e),
                started_at=datetime.fromtimestamp(start_time),
                completed_at=datetime.now()
            )

    def _create_expect_function(self, page: Page):
        """Create an expect function for assertions."""
        from playwright.async_api import expect
        return expect

    def _create_screenshot_function(self, screenshots: List[str]):
        """Create a screenshot function."""
        async def take_screenshot(name: str = None):
            if self.page:
                filename = f"./screenshots/{name or 'screenshot'}_{time.time()}.png"
                await self.page.screenshot(path=filename)
                screenshots.append(filename)
                return filename
            return None
        return take_screenshot

    def _indent_code(self, code: str, spaces: int = 4) -> str:
        """Indent code for execution."""
        lines = code.split('\n')
        return '\n'.join(' ' * spaces + line if line.strip() else line for line in lines)

    async def execute_step(self, step: TestStep, page: Page) -> StepResult:
        """Execute a single test step."""
        start_time = time.time()

        try:
            # Add wait before action
            if step.wait_before:
                await asyncio.sleep(step.wait_before / 1000)

            # Execute the action
            if step.action.value == "navigate":
                await page.goto(step.value)
            elif step.action.value == "click":
                await page.click(step.selector)
            elif step.action.value == "type":
                await page.fill(step.selector, step.value)
            elif step.action.value == "wait":
                await page.wait_for_selector(step.selector, state="visible")
            elif step.action.value == "screenshot":
                await page.screenshot(path=f"./screenshots/{step.value}.png")
            elif step.action.value == "select":
                await page.select_option(step.selector, step.value)
            elif step.action.value == "hover":
                await page.hover(step.selector)
            elif step.action.value == "scroll":
                await page.evaluate(f"window.scrollTo(0, {step.value or 'document.body.scrollHeight'})")

            # Add wait after action
            if step.wait_after:
                await asyncio.sleep(step.wait_after / 1000)

            duration = time.time() - start_time

            return StepResult(
                step=step,
                success=True,
                duration=duration
            )

        except Exception as e:
            duration = time.time() - start_time

            return StepResult(
                step=step,
                success=False,
                error=str(e),
                duration=duration
            )