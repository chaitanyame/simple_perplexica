"""Test temporal filtering with various year queries.

Tests:
1. Specific year query (2023)
2. Multiple years query (2022 vs 2024)
3. Recent/latest query (should get 2025)
4. Historical query (no temporal filter)

Note: Uses mode configurations from src/core/search_modes.py:
- SPEED: 5 sources, 15s timeout
- BALANCED: 10 sources, 45s timeout
- DEEP: 20 sources, 60s timeout
"""

import httpx

API_BASE_URL = "http://localhost:8001/api/v1"

# Mode configurations (from src/core/search_modes.py)
MODE_CONFIGS = {
    "speed": {"max_sources": 5, "timeout": 15},
    "balanced": {"max_sources": 10, "timeout": 45},
    "deep": {"max_sources": 20, "timeout": 60},
}

def test_temporal_queries():
    """Test various temporal query patterns."""
    
    test_cases = [
        {
            "name": "Specific Year 2023",
            "query": "GitHub Universe 2023 announcements",
            "mode": "deep",
            "expected_year": 2023,
            "description": "Should return only 2023 sources"
        },
        {
            "name": "Latest/Recent (2025)",
            "query": "GitHub Universe latest conference with new product launches",
            "mode": "deep",
            "expected_year": 2025,
            "description": "Should prioritize 2025 sources"
        },
        {
            "name": "Specific Year 2022",
            "query": "AI developments in 2022",
            "mode": "balanced",
            "expected_year": 2022,
            "description": "Should return 2022 sources"
        },
        {
            "name": "Historical Query",
            "query": "History of GitHub",
            "mode": "balanced",
            "expected_year": None,
            "description": "No temporal filtering, any year acceptable"
        }
    ]
    
    print("\n" + "="*80)
    print("TEMPORAL QUERY TESTING")
    print("="*80)
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n{'-'*80}")
        print(f"Test {i}/{len(test_cases)}: {test['name']}")
        print(f"{'-'*80}")
        print(f"Query: {test['query']}")
        print(f"Mode: {test['mode'].upper()}")
        mode_config = MODE_CONFIGS[test['mode']]
        print(f"Config: {mode_config['max_sources']} sources | {mode_config['timeout']} seconds")
        print(f"Expected: {test['expected_year'] or 'Any year'}")
        print(f"Description: {test['description']}")
        print()
        
        try:
            response = httpx.post(
                f"{API_BASE_URL}/search",
                json={
                    "query": test["query"],
                    "mode": test["mode"],
                    "model": "deepseek/deepseek-r1-distill-llama-70b",
                },
                timeout=120,
            )
            
            if response.status_code == 200:
                data = response.json()
                sources = data.get("sources", [])
                answer = data.get("answer", "")
                
                print(f"SUCCESS - Got {len(sources)} sources")
                print()
                
                # Analyze source years
                years_found = {}
                for source in sources[:10]:  # Check top 10
                    url = source.get("url", "")
                    title = source.get("title", "")
                    
                    # Extract year from URL or title
                    import re
                    year_match = re.search(r'\b(20[2-3][0-9])\b', url + " " + title)
                    if year_match:
                        year = int(year_match.group(1))
                        years_found[year] = years_found.get(year, 0) + 1
                
                print(f"Year Distribution (top 10 sources):")
                for year in sorted(years_found.keys(), reverse=True):
                    count = years_found[year]
                    bar = "#" * count
                    print(f"  {year}: {bar} ({count})")
                
                # Check if expected year is predominant
                if test["expected_year"]:
                    if test["expected_year"] in years_found:
                        expected_count = years_found[test["expected_year"]]
                        total_with_years = sum(years_found.values())
                        percentage = (expected_count / total_with_years * 100) if total_with_years > 0 else 0
                        
                        if percentage >= 50:
                            print(f"\n  PASS: {test['expected_year']} is predominant ({percentage:.0f}%)")
                        else:
                            print(f"\n  WARNING: {test['expected_year']} only {percentage:.0f}% of sources")
                    else:
                        print(f"\n  FAIL: Expected year {test['expected_year']} not found in top sources")
                else:
                    print(f"\n  PASS: Historical query, all years acceptable")
                
                # Check answer mentions
                answer_years = re.findall(r'\b(20[2-3][0-9])\b', answer)
                if answer_years:
                    print(f"\nYears mentioned in answer: {', '.join(set(answer_years))}")
                
                print(f"\nAnswer preview:")
                print(f"  {answer[:200]}...")
                
            else:
                print(f"FAILED - Status {response.status_code}")
                print(f"Error: {response.json()}")
        
        except Exception as e:
            print(f"EXCEPTION: {str(e)}")
    
    print(f"\n{'='*80}")
    print("TESTING COMPLETE")
    print("="*80)


if __name__ == "__main__":
    test_temporal_queries()
