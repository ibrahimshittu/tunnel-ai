"""Playwright test code templates."""

from core.types import TestStep


def get_test_template() -> str:
    """Get the main test template."""
    return """import { test, expect } from '@playwright/test';

test('{test_name}', async ({ page }) => {{
  test.setTimeout(60000);

  // Test ID: {test_id}

  {test_body}
}});
"""


def get_python_test_template() -> str:
    """Get Python Playwright test template."""
    return """# Test: {test_name}
# Test ID: {test_id}

async def test_{test_id}(page):
    \"\"\"
    {test_name}
    \"\"\"
    {test_body}
"""


def get_step_template(step: TestStep) -> str:
    """Get template for a specific step."""

    templates = {
        "navigate": f"await page.goto('{step.value}'); // {step.description}",
        "click": f"await page.click('{step.selector}'); // {step.description}",
        "type": f"await page.fill('{step.selector}', '{step.value}'); // {step.description}",
        "wait": f"await page.wait_for_selector('{step.selector}', state='visible'); // {step.description}",
        "screenshot": f"await page.screenshot(path='screenshots/{step.value or 'screenshot'}.png'); // {step.description}",
        "select": f"await page.select_option('{step.selector}', '{step.value}'); // {step.description}",
        "hover": f"await page.hover('{step.selector}'); // {step.description}",
        "scroll": f"await page.evaluate('window.scrollTo(0, {step.value or 'document.body.scrollHeight'}'); // {step.description}",
    }

    return templates.get(step.action.value, f"// Unknown action: {step.action.value}")


def get_assertion_template(assertion_type: str, selector: str, expected: any) -> str:
    """Get template for assertions."""

    templates = {
        "visible": f"await expect(page.locator('{selector}')).toBeVisible();",
        "text": f"await expect(page.locator('{selector}')).toContainText('{expected}');",
        "value": f"await expect(page.locator('{selector}')).toHaveValue('{expected}');",
        "url": f"await expect(page).toHaveURL('{expected}');",
        "title": f"await expect(page).toHaveTitle('{expected}');",
        "count": f"await expect(page.locator('{selector}')).toHaveCount({expected});",
        "attribute": f"await expect(page.locator('{selector}')).toHaveAttribute('value', '{expected}');",
    }

    return templates.get(assertion_type, f"// Unknown assertion: {assertion_type}")


def get_page_object_template() -> str:
    """Get Page Object Model template."""
    return """class {page_name}Page:
    def __init__(self, page):
        self.page = page
        self.url = '{url}'

        # Selectors
        {selectors}

    async def navigate(self):
        await self.page.goto(self.url)
        await self.page.wait_for_load_state('networkidle')

    {methods}
"""


def get_test_suite_template() -> str:
    """Get test suite template."""
    return """import asyncio
from playwright.async_api import async_playwright

class TestSuite:
    def __init__(self):
        self.results = []

    async def setup(self):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)
        self.context = await self.browser.new_context()
        self.page = await self.context.new_page()

    async def teardown(self):
        await self.context.close()
        await self.browser.close()
        await self.playwright.stop()

    async def run_tests(self):
        await self.setup()
        try:
            {test_calls}
        finally:
            await self.teardown()

    {test_methods}
"""