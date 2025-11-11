"""Test why GitHub Universe query returns old data."""

import httpx

API_BASE_URL = "http://localhost:8001/api/v1"

def test_github_universe_query():
    """Test the GitHub Universe query to see what sources are returned."""
    
    query = "what about GitHub Universe latest conference with new product launches"
    mode = "deep"
    
    print("\n" + "="*70)
    print("🔍 TESTING GITHUB UNIVERSE QUERY")
    print("="*70)
    print(f"\nQuery: {query}")
    print(f"Mode: {mode.upper()}")
    print(f"\n{'─'*70}\n")
    
    try:
        response = httpx.post(
            f"{API_BASE_URL}/search",
            json={
                "query": query,
                "mode": mode,
                "model": "anthropic/claude-3.5-sonnet",
            },
            timeout=120,
        )
        
        if response.status_code == 200:
            data = response.json()
            answer = data.get("answer", "")
            sources = data.get("sources", [])
            
            print("📊 SOURCES RETURNED:")
            print(f"{'─'*70}\n")
            
            for idx, source in enumerate(sources, 1):
                print(f"[{idx}] {source.get('title', 'No title')}")
                print(f"    URL: {source.get('url', 'No URL')}")
                print(f"    Relevance: {source.get('relevance', 0):.3f}")
                print(f"    Snippet: {source.get('snippet', '')[:150]}...")
                print()
            
            print(f"{'='*70}")
            print("📝 ANSWER:")
            print(f"{'='*70}\n")
            print(answer)
            print(f"\n{'='*70}")
            
            # Check for date mentions
            dates_found = []
            for year in ['2023', '2024', '2025']:
                if year in answer:
                    dates_found.append(year)
            
            print(f"\n📅 Date Analysis:")
            print(f"  Dates mentioned: {', '.join(dates_found) if dates_found else 'None'}")
            
            if '2023' in answer and '2025' not in answer:
                print(f"  ⚠️ WARNING: Only 2023 data found - sources may be outdated")
            
            # Check source dates
            print(f"\n🔗 Source URL Analysis:")
            old_sources = 0
            for source in sources:
                url = source.get('url', '')
                if '2023' in url:
                    old_sources += 1
                    print(f"  ⚠️ Old source: {url}")
            
            if old_sources > 0:
                print(f"\n  ❌ Found {old_sources} sources with '2023' in URL")
                print(f"  💡 Issue: Search is returning old content instead of recent news")
            
            return data
            
        else:
            print(f"❌ Request failed: {response.status_code}")
            print(f"Error: {response.json()}")
            return None
            
    except Exception as e:
        print(f"❌ Request failed: {str(e)}")
        return None


if __name__ == "__main__":
    test_github_universe_query()
