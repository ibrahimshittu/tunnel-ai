#!/usr/bin/env python3
"""Example script to analyze a web page and extract selectors."""

import asyncio
import sys
from agents.utils import PageAnalyzer


async def analyze_url(url: str):
    """Analyze a URL and display the results."""

    analyzer = PageAnalyzer()

    print(f"Analyzing: {url}")
    print("=" * 60)

    try:
        # Analyze the page
        analysis = await analyzer.analyze(url, headless=True)

        print(f"\n📄 Page Title: {analysis.title}")
        print(f"🔗 URL: {analysis.url}")

        if analysis.meta_description:
            print(f"📝 Description: {analysis.meta_description[:100]}...")

        # Display forms
        if analysis.forms:
            print(f"\n📋 Forms Found: {len(analysis.forms)}")
            for i, form in enumerate(analysis.forms, 1):
                print(f"\n  Form {i}:")
                if form.get("id"):
                    print(f"    ID: {form['id']}")
                print(f"    Inputs: {len(form.get('inputs', []))}")
                for inp in form.get("inputs", [])[:3]:
                    print(f"      • {inp.get('type', 'text')}: {inp.get('selector')}")
                    if inp.get("placeholder"):
                        print(f"        Placeholder: {inp['placeholder']}")

        # Display buttons
        if analysis.buttons:
            print(f"\n🔘 Buttons: {len(analysis.buttons)}")
            for btn in analysis.buttons[:5]:
                if btn.text:
                    print(f"  • {btn.text[:40]}")
                    print(f"    Selector: {btn.selector}")

        # Display input fields
        if analysis.inputs:
            print(f"\n📝 Input Fields: {len(analysis.inputs)}")
            for inp in analysis.inputs[:5]:
                inp_info = f"  • {inp.type or 'text'}"
                if inp.placeholder:
                    inp_info += f" [{inp.placeholder}]"
                print(inp_info)
                print(f"    Selector: {inp.selector}")

        # Display navigation
        if analysis.navigation:
            print(f"\n🧭 Navigation Links: {len(analysis.navigation)}")
            for nav in analysis.navigation[:5]:
                if nav.text:
                    print(f"  • {nav.text[:30]}: {nav.selector}")

        # Display page structure
        print(f"\n🏗️ Page Structure:")
        print(analysis.page_structure)

        # Show formatted prompt context
        print("\n" + "=" * 60)
        print("📋 FORMATTED CONTEXT FOR LLM:")
        print("=" * 60)
        print(analyzer.format_for_prompt(analysis))

    except Exception as e:
        print(f"\n❌ Error analyzing page: {e}")
        import traceback
        traceback.print_exc()


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test URL
        url = "https://example.com"
        print(f"No URL provided, using default: {url}")
        print("Usage: python analyze_page.py <url>")
        print()

    asyncio.run(analyze_url(url))


if __name__ == "__main__":
    main()