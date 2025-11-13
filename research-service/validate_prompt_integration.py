#!/usr/bin/env python3
"""Validate prompt strategy integration structure.

This script checks that all required code changes are in place
without importing dependencies.
"""

import re
from pathlib import Path


def check_file_contains(file_path: Path, patterns: list[str], description: str) -> bool:
    """Check if file contains all required patterns."""
    print(f"\n  📄 Checking {file_path.name}...")
    
    if not file_path.exists():
        print(f"    ❌ File not found!")
        return False
    
    content = file_path.read_text(encoding="utf-8")
    
    all_found = True
    for pattern in patterns:
        if re.search(pattern, content, re.MULTILINE):
            print(f"    ✅ {description}: Found '{pattern[:50]}...'")
        else:
            print(f"    ❌ {description}: Missing '{pattern[:50]}...'")
            all_found = False
    
    return all_found


def main():
    """Validate integration structure."""
    print("=" * 70)
    print("🔍 PROMPT STRATEGY STRUCTURE VALIDATION")
    print("=" * 70)
    
    base_path = Path(__file__).parent
    src_path = base_path / "src"
    
    all_checks_passed = True
    
    # 1. Check prompt_strategy.py helper
    print("\n📋 1. Helper Module (src/agents/prompt_strategy.py)")
    prompt_strategy_file = src_path / "agents" / "prompt_strategy.py"
    patterns = [
        r"def resolve_prompt_strategy\(",
        r"def should_use_dynamic_prompts\(",
        r"def get_planning_prompt\(",
        r"def get_synthesis_prompt\(",
        r"def get_search_prompt\(",
    ]
    if check_file_contains(prompt_strategy_file, patterns, "Function"):
        print("  🎉 Helper module complete!")
    else:
        all_checks_passed = False
    
    # 2. Check API schemas
    print("\n📋 2. API Schemas (src/api/v1/schemas.py)")
    schemas_file = src_path / "api" / "v1" / "schemas.py"
    patterns = [
        r'prompt_strategy.*Literal\["static", "dynamic", "auto"\]',
        r"class ResearchRequest",
        r"class SearchRequest",
    ]
    if check_file_contains(schemas_file, patterns, "Schema"):
        print("  🎉 API schemas complete!")
    else:
        all_checks_passed = False
    
    # 3. Check research endpoint
    print("\n📋 3. Research Endpoint (src/api/v1/endpoints/research.py)")
    research_file = src_path / "api" / "v1" / "endpoints" / "research.py"
    patterns = [
        r"prompt_strategy=request\.prompt_strategy",
    ]
    if check_file_contains(research_file, patterns, "Endpoint"):
        print("  🎉 Research endpoint complete!")
    else:
        all_checks_passed = False
    
    # 4. Check ResearchAgent
    print("\n📋 4. Research Agent (src/agents/research_agent.py)")
    agent_file = src_path / "agents" / "research_agent.py"
    patterns = [
        r"def generate_plan\(.*prompt_strategy",
        r"def synthesize_findings\(.*prompt_strategy",
        r"async def run\(.*prompt_strategy",
    ]
    if check_file_contains(agent_file, patterns, "Agent Method"):
        print("  🎉 Research agent complete!")
    else:
        all_checks_passed = False
    
    # 5. Check Streamlit UI
    print("\n📋 5. Streamlit UI (streamlit_ui.py)")
    streamlit_file = base_path / "streamlit_ui.py"
    patterns = [
        r'prompt_strategy.*st\.radio.*"System Prompt Strategy"',
        r'def render_search_mode\(.*prompt_strategy: str',
        r'def render_research_mode\(.*prompt_strategy: str',
        r'"prompt_strategy": prompt_strategy',
    ]
    if check_file_contains(streamlit_file, patterns, "UI Component"):
        print("  🎉 Streamlit UI complete!")
    else:
        all_checks_passed = False
    
    # Summary
    print("\n" + "=" * 70)
    if all_checks_passed:
        print("✅ ALL STRUCTURE CHECKS PASSED!")
        print("=" * 70)
        print("\n📊 Phase 4 Integration Complete:")
        print("  ✅ Helper module (prompt_strategy.py)")
        print("  ✅ API schemas (ResearchRequest, SearchRequest)")
        print("  ✅ Research endpoint forwarding")
        print("  ✅ ResearchAgent methods")
        print("  ✅ Streamlit UI (selector + payloads)")
        print("\n🎯 Ready for:")
        print("  - Manual testing via Streamlit UI")
        print("  - Phase 5: Docker Updates")
        print("  - Phase 6: Full Validation")
        print("\n💡 Test with Streamlit:")
        print("  python streamlit_ui.py")
        print("  Select prompt strategy in sidebar:")
        print("    🤖 Auto (Config) - Uses ENABLE_DYNAMIC_PROMPTS")
        print("    📝 Static (Fixed) - Original prompts")
        print("    ✨ Dynamic (Context-Aware) - Query-aware prompts")
        return 0
    else:
        print("❌ SOME CHECKS FAILED")
        print("=" * 70)
        print("\nPlease review the failures above and fix them.")
        return 1


if __name__ == "__main__":
    exit(main())
