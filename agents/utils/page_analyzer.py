"""Page Analyzer - Extracts page structure and selectors for test planning."""

import json
from typing import Dict, List, Any, Optional
from playwright.async_api import (
    async_playwright,
    TimeoutError as PlaywrightTimeoutError,
)
from loguru import logger
from pydantic import BaseModel, Field


class PageElement(BaseModel):
    """Represents a page element with its selector information."""

    tag: str
    text: Optional[str] = None
    id: Optional[str] = None
    classes: List[str] = Field(default_factory=list)
    data_testid: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = None
    placeholder: Optional[str] = None
    href: Optional[str] = None
    role: Optional[str] = None
    aria_label: Optional[str] = None
    selector: str
    xpath: Optional[str] = None
    is_visible: bool = True
    is_interactive: bool = False


class PageAnalysis(BaseModel):
    """Complete page analysis result."""

    url: str
    title: str
    forms: List[Dict[str, Any]] = Field(default_factory=list)
    buttons: List[PageElement] = Field(default_factory=list)
    links: List[PageElement] = Field(default_factory=list)
    inputs: List[PageElement] = Field(default_factory=list)
    navigation: List[PageElement] = Field(default_factory=list)
    interactive_elements: List[PageElement] = Field(default_factory=list)
    page_structure: str = ""
    meta_description: Optional[str] = None


class PageAnalyzer:
    """Analyzes web pages to extract selectors and structure."""

    def __init__(self):
        self.page_script = """
        () => {
            function getSelector(element) {
                // Priority: data-testid > id > unique class > text content
                if (element.dataset.testid) {
                    return `[data-testid="${element.dataset.testid}"]`;
                }
                if (element.id) {
                    return `#${element.id}`;
                }
                if (element.className && typeof element.className === 'string') {
                    const classes = element.className.split(' ').filter(c => c);
                    if (classes.length > 0) {
                        return '.' + classes.join('.');
                    }
                }
                // For buttons/links with text
                if (element.textContent && element.textContent.trim()) {
                    const text = element.textContent.trim().substring(0, 30);
                    if (element.tagName === 'BUTTON') {
                        return `button:has-text("${text}")`;
                    }
                    if (element.tagName === 'A') {
                        return `a:has-text("${text}")`;
                    }
                }
                return element.tagName.toLowerCase();
            }

            function extractElement(el) {
                const rect = el.getBoundingClientRect();
                return {
                    tag: el.tagName.toLowerCase(),
                    text: el.textContent?.trim().substring(0, 100),
                    id: el.id || null,
                    classes: el.className ? el.className.split(' ').filter(c => c) : [],
                    data_testid: el.dataset.testid || null,
                    name: el.name || null,
                    type: el.type || null,
                    placeholder: el.placeholder || null,
                    href: el.href || null,
                    role: el.getAttribute('role') || null,
                    aria_label: el.getAttribute('aria-label') || null,
                    selector: getSelector(el),
                    is_visible: rect.width > 0 && rect.height > 0,
                    is_interactive: ['button', 'a', 'input', 'textarea', 'select'].includes(el.tagName.toLowerCase())
                };
            }

            // Extract forms
            const forms = Array.from(document.querySelectorAll('form')).map(form => {
                const inputs = Array.from(form.querySelectorAll('input, textarea, select')).map(extractElement);
                const buttons = Array.from(form.querySelectorAll('button, input[type="submit"]')).map(extractElement);
                return {
                    id: form.id || null,
                    name: form.name || null,
                    action: form.action || null,
                    method: form.method || null,
                    inputs: inputs,
                    buttons: buttons
                };
            });

            // Extract all interactive elements
            const buttons = Array.from(document.querySelectorAll('button, [role="button"], input[type="submit"], input[type="button"]')).map(extractElement);
            const links = Array.from(document.querySelectorAll('a[href]')).slice(0, 50).map(extractElement);
            const inputs = Array.from(document.querySelectorAll('input:not([type="submit"]):not([type="button"]), textarea, select')).map(extractElement);

            // Extract navigation elements
            const navigation = Array.from(document.querySelectorAll('nav a, header a, [role="navigation"] a')).slice(0, 20).map(extractElement);

            // Get page structure overview
            const structure = {
                hasHeader: !!document.querySelector('header'),
                hasNav: !!document.querySelector('nav'),
                hasFooter: !!document.querySelector('footer'),
                hasMain: !!document.querySelector('main'),
                hasForms: forms.length > 0,
                formCount: forms.length,
                buttonCount: buttons.length,
                linkCount: document.querySelectorAll('a').length,
                inputCount: inputs.length
            };

            return {
                title: document.title,
                url: window.location.href,
                forms: forms,
                buttons: buttons.slice(0, 30),
                links: links,
                inputs: inputs.slice(0, 30),
                navigation: navigation,
                meta_description: document.querySelector('meta[name="description"]')?.content || null,
                page_structure: JSON.stringify(structure, null, 2)
            };
        }
        """

    async def analyze(self, url: str, headless: bool = True) -> PageAnalysis:
        """Analyze a web page and extract its structure and selectors."""

        logger.info(f"Analyzing page: {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=headless)
            context = await browser.new_context(
                viewport={"width": 1280, "height": 720},
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
                locale="en-US",
                ignore_https_errors=True,
                extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
            )
            page = await context.new_page()
            page.set_default_timeout(60000)
            page.set_default_navigation_timeout(90000)

            try:
                # Navigate to the page with robust retries and alternative wait strategies
                await self._navigate_with_retries(page, url)

                # Wait for content to load (give it a moment to render)
                await page.wait_for_load_state("domcontentloaded")
                # Wait a bit for dynamic content
                await page.wait_for_timeout(2000)

                # Execute analysis script
                analysis_data = await page.evaluate(self.page_script)

                # Convert to PageAnalysis model
                analysis = PageAnalysis(
                    url=analysis_data["url"],
                    title=analysis_data["title"],
                    forms=analysis_data["forms"],
                    buttons=[PageElement(**btn) for btn in analysis_data["buttons"]],
                    links=[PageElement(**link) for link in analysis_data["links"]],
                    inputs=[PageElement(**inp) for inp in analysis_data["inputs"]],
                    navigation=[
                        PageElement(**nav) for nav in analysis_data["navigation"]
                    ],
                    page_structure=analysis_data["page_structure"],
                    meta_description=analysis_data.get("meta_description"),
                )

                # Add interactive elements
                analysis.interactive_elements = (
                    analysis.buttons[:10] + analysis.inputs[:10] + analysis.links[:5]
                )

                logger.success(f"Page analysis complete: {url}")
                return analysis

            except Exception as e:
                logger.error(f"Failed to analyze page: {e}")
                # Return minimal analysis on error with basic structure
                return PageAnalysis(
                    url=url,
                    title="Page Analysis Failed - Using Fallback",
                    page_structure=json.dumps(
                        {
                            "error": str(e),
                            "fallback": True,
                            "note": "Analysis failed, using generic selectors",
                        },
                        indent=2,
                    ),
                    buttons=[
                        PageElement(
                            tag="button",
                            text="Generic Submit Button",
                            selector="button[type='submit']",
                            is_interactive=True,
                        )
                    ],
                    inputs=[
                        PageElement(
                            tag="input",
                            type="text",
                            selector="input[type='text']",
                            placeholder="Generic text input",
                            is_interactive=True,
                        ),
                        PageElement(
                            tag="input",
                            type="password",
                            selector="input[type='password']",
                            placeholder="Generic password input",
                            is_interactive=True,
                        ),
                    ],
                    links=[
                        PageElement(
                            tag="a",
                            text="Generic Link",
                            selector="a",
                            is_interactive=True,
                        )
                    ],
                )
            finally:
                await context.close()
                await browser.close()

    async def _navigate_with_retries(self, page, url: str) -> None:
        """Navigate with multiple strategies to reduce flakiness/timeouts.

        Tries a sequence of wait strategies with increasing leniency.
        Raises the last error if all attempts fail.
        """

        attempts = [
            {"wait_until": "domcontentloaded", "timeout": 60000},
            {"wait_until": "commit", "timeout": 90000},
            {"wait_until": "load", "timeout": 120000},
        ]

        last_error: Optional[Exception] = None
        for attempt in attempts:
            try:
                await page.goto(url, **attempt)
                return
            except PlaywrightTimeoutError as e:
                logger.warning(
                    f"Navigation timed out with wait_until='{attempt['wait_until']}', retrying..."
                )
                last_error = e
            except Exception as e:
                logger.warning(
                    f"Navigation failed with wait_until='{attempt['wait_until']}': {e}. Retrying..."
                )
                last_error = e

        if last_error:
            raise last_error

    def format_for_prompt(self, analysis: PageAnalysis) -> str:
        """Format page analysis for LLM prompt."""

        prompt_parts = [
            f"Page URL: {analysis.url}",
            f"Page Title: {analysis.title}",
            "",
        ]

        if analysis.meta_description:
            prompt_parts.append(f"Description: {analysis.meta_description}\n")

        # Add form information
        if analysis.forms:
            prompt_parts.append("FORMS FOUND:")
            for i, form in enumerate(analysis.forms, 1):
                prompt_parts.append(f"\nForm {i}:")
                if form.get("id"):
                    prompt_parts.append(f"  ID: {form['id']}")

                prompt_parts.append("  Inputs:")
                for inp in form.get("inputs", [])[:5]:
                    inp_desc = f"    - {inp['type'] or 'text'} input"
                    if inp.get("name"):
                        inp_desc += f" (name: {inp['name']})"
                    if inp.get("placeholder"):
                        inp_desc += f" [placeholder: {inp['placeholder']}]"
                    inp_desc += f" -> {inp['selector']}"
                    prompt_parts.append(inp_desc)

                if form.get("buttons"):
                    prompt_parts.append("  Submit buttons:")
                    for btn in form["buttons"][:2]:
                        prompt_parts.append(
                            f"    - {btn.get('text', 'Submit')} -> {btn['selector']}"
                        )

        # Add key interactive elements
        if analysis.buttons:
            prompt_parts.append("\nKEY BUTTONS:")
            for btn in analysis.buttons[:10]:
                if btn.text:
                    prompt_parts.append(f"  - {btn.text[:50]} -> {btn.selector}")

        if analysis.inputs and not analysis.forms:  # If inputs are outside forms
            prompt_parts.append("\nINPUT FIELDS:")
            for inp in analysis.inputs[:10]:
                inp_desc = f"  - {inp.type or 'text'}"
                if inp.placeholder:
                    inp_desc += f" [{inp.placeholder}]"
                inp_desc += f" -> {inp.selector}"
                prompt_parts.append(inp_desc)

        if analysis.navigation:
            prompt_parts.append("\nNAVIGATION LINKS:")
            for nav in analysis.navigation[:8]:
                if nav.text:
                    prompt_parts.append(f"  - {nav.text[:30]} -> {nav.selector}")

        # Add page structure
        prompt_parts.append(f"\nPAGE STRUCTURE:")
        prompt_parts.append(analysis.page_structure)

        return "\n".join(prompt_parts)

    async def get_page_context(self, url: str) -> str:
        """Get formatted page context for test planning."""
        analysis = await self.analyze(url)
        return self.format_for_prompt(analysis)
