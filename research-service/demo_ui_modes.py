"""Visual demonstration of mode selector behavior.

This script demonstrates what happens when you select different modes
in the Streamlit UI and how they affect the search behavior.
"""

def show_mode_demo():
    """Show visual demo of mode selection."""
    
    print("\n" + "="*70)
    print("🎨 STREAMLIT UI MODE SELECTOR - VISUAL DEMO")
    print("="*70)
    
    print("\n📱 Open Streamlit UI at: http://localhost:8501")
    print("\n" + "─"*70)
    
    # Demo 1: SPEED Mode
    print("\n🔹 DEMO 1: SPEED Mode - Quick Fact Check")
    print("─"*70)
    print("""
    1. In sidebar, select: ○ ⚡ SPEED
    
    2. Info box shows:
       ╔═══════════════════════════╗
       ║ 5 sources | 15 seconds    ║
       ║                           ║
       ║ ✨ Snippets only,         ║
       ║    no crawling            ║
       ║                           ║
       ║ 💡 Best for: Quick lookups║
       ╚═══════════════════════════╝
    
    3. Enter query: "What is FastAPI?"
    
    4. Click [🔍 Search]
    
    5. Results show:
       ┌──────────────────────────────────────┐
       │ 📄 Answer                            │
       │ FastAPI is a modern web framework... │
       ├────────┬──────┬─────────┬───────────┤
       │ 12.3s  │ 82%  │ 5 src   │ ⚡ SPEED  │
       └────────┴──────┴─────────┴───────────┘
    
    ✅ Fast response, basic info, perfect for quick lookups!
    """)
    
    print("─"*70)
    
    # Demo 2: BALANCED Mode
    print("\n🔹 DEMO 2: BALANCED Mode - Standard Query")
    print("─"*70)
    print("""
    1. In sidebar, select: ○ ⚖️ BALANCED (default)
    
    2. Info box shows:
       ╔═══════════════════════════════════╗
       ║ 10 sources | 45 seconds          ║
       ║                                   ║
       ║ ✨ Selective crawling (5 URLs),  ║
       ║    reranking enabled              ║
       ║                                   ║
       ║ 💡 Best for: Default for most    ║
       ║              queries              ║
       ╚═══════════════════════════════════╝
    
    3. Enter query: "Explain Pydantic AI agents"
    
    4. Click [🔍 Search]
    
    5. Results show:
       ┌────────────────────────────────────────────┐
       │ 📄 Answer                                  │
       │ Pydantic AI is a Python framework that     │
       │ enables production-ready agent development │
       │ with type safety and validation...         │
       ├──────────┬──────┬──────────┬──────────────┤
       │ 23.1s    │ 88%  │ 10 src   │ ⚖️ BALANCED  │
       └──────────┴──────┴──────────┴──────────────┘
    
    ✅ Good balance of speed and quality, works for 90% of queries!
    """)
    
    print("─"*70)
    
    # Demo 3: DEEP Mode
    print("\n🔹 DEMO 3: DEEP Mode - Comprehensive Research")
    print("─"*70)
    print("""
    1. In sidebar, select: ○ 🔍 DEEP
    
    2. Info box shows:
       ╔═══════════════════════════════════════╗
       ║ 20 sources | 60 seconds              ║
       ║                                       ║
       ║ ✨ Full crawling, reranking,         ║
       ║    RAG with history                   ║
       ║                                       ║
       ║ 💡 Best for: Comprehensive research  ║
       ╚═══════════════════════════════════════╝
    
    3. Enter query: "Compare LangChain vs Pydantic AI"
    
    4. Click [🔍 Search]
    
    5. Results show:
       ┌──────────────────────────────────────────────┐
       │ 📄 Answer                                    │
       │ Here's a comprehensive comparison:           │
       │                                              │
       │ 🏗️ Architecture:                            │
       │ - LangChain: Modular, chain-based...        │
       │ - Pydantic AI: Type-safe, agent-focused...  │
       │                                              │
       │ 🎯 Use Cases:                               │
       │ - LangChain: Complex workflows...           │
       │ - Pydantic AI: Production agents...         │
       ├──────────┬──────┬──────────┬───────────────┤
       │ 37.5s    │ 92%  │ 20 src   │ 🔍 DEEP       │
       └──────────┴──────┴──────────┴───────────────┘
    
    ✅ Comprehensive results with deep analysis!
    """)
    
    print("─"*70)
    
    # Advanced Override Demo
    print("\n🔹 DEMO 4: Advanced Override")
    print("─"*70)
    print("""
    Sometimes you want BALANCED quality but need more sources:
    
    1. Select: ⚖️ BALANCED
    
    2. In "Advanced Parameters":
       Max Sources: ─────────○─── 15  (override to 15)
       Timeout:     ─────────○─── 60  (override to 60)
    
    3. API receives:
       {
         "mode": "balanced",      # BALANCED config applied
         "max_sources": 15,       # But override to 15 sources
         "timeout": 60            # And 60s timeout
       }
    
    4. Result: BALANCED features (crawling, reranking) 
               with custom limits (15 sources, 60s)
    
    💡 Pro tip: Most users never need to override!
    """)
    
    print("─"*70)
    
    # Comparison Table
    print("\n📊 MODE COMPARISON AT A GLANCE")
    print("─"*70)
    print("""
    ┌──────────┬──────────────────────────────────────────────┐
    │   Mode   │             Characteristics                  │
    ├──────────┼──────────────────────────────────────────────┤
    │ ⚡ SPEED │ • 5 sources, 15s timeout                     │
    │          │ • Snippets only, no crawling                 │
    │          │ • ~12s avg response time                     │
    │          │ • Best for: Quick facts                      │
    ├──────────┼──────────────────────────────────────────────┤
    │ ⚖️ BAL   │ • 10 sources, 45s timeout                    │
    │          │ • Crawl top 5 URLs, reranking enabled        │
    │          │ • ~23s avg response time                     │
    │          │ • Best for: Most queries (DEFAULT)           │
    ├──────────┼──────────────────────────────────────────────┤
    │ 🔍 DEEP  │ • 20 sources, 60s timeout                    │
    │          │ • Full crawling, reranking, RAG              │
    │          │ • ~35s avg response time                     │
    │          │ • Best for: Comprehensive research           │
    └──────────┴──────────────────────────────────────────────┘
    """)
    
    print("\n" + "="*70)
    print("🎬 TRY IT YOURSELF!")
    print("="*70)
    print("""
    1. Open http://localhost:8501 in your browser
    2. Try the same query with all 3 modes
    3. Compare the results, time, and source counts
    4. See which mode fits your needs best!
    
    💡 Tips:
    - SPEED for quick checks during conversations
    - BALANCED for blog posts, articles, general use
    - DEEP for reports, research papers, deep dives
    """)
    
    print("\n✅ Mode selector is ready to use!")
    print("="*70 + "\n")


if __name__ == "__main__":
    show_mode_demo()
