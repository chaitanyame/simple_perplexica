"""Standalone test runner for the three new test categories.

Run this script to verify all tests pass:
    python run_new_tests.py
"""

import sys
import importlib.util


def load_module_from_file(module_name: str, file_path: str):
    """Load a Python module from a file path."""
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def run_tests():
    """Run all test functions from the three test files."""
    test_files = [
        ("test_query_normalization", "tests/unit/test_query_normalization.py"),
        ("test_hybrid_retrieval", "tests/unit/test_hybrid_retrieval.py"),
        ("test_language_detection", "tests/unit/test_language_detection.py"),
    ]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for module_name, file_path in test_files:
        print(f"\n{'='*80}")
        print(f"Running: {module_name}")
        print('='*80)
        
        try:
            module = load_module_from_file(module_name, file_path)
            
            # Find all test functions
            test_funcs = [
                (name, func) for name, func in vars(module).items()
                if name.startswith("test_") and callable(func)
            ]
            
            for test_name, test_func in test_funcs:
                total_tests += 1
                try:
                    # Handle async tests
                    import asyncio
                    import inspect
                    if inspect.iscoroutinefunction(test_func):
                        asyncio.run(test_func())
                    else:
                        test_func()
                    
                    print(f"  ✅ {test_name}")
                    passed_tests += 1
                except AssertionError as e:
                    print(f"  ❌ {test_name}: {e}")
                    failed_tests += 1
                except Exception as e:
                    print(f"  ⚠️  {test_name}: {type(e).__name__}: {e}")
                    failed_tests += 1
                    
        except Exception as e:
            print(f"  ❌ Failed to load module: {e}")
            continue
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print('='*80)
    print(f"Total Tests: {total_tests}")
    print(f"✅ Passed: {passed_tests}")
    print(f"❌ Failed: {failed_tests}")
    print(f"Success Rate: {passed_tests/total_tests*100:.1f}%")
    
    return failed_tests == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
