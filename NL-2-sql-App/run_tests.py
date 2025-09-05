#!/usr/bin/env python3
"""
Test Runner Script for NL-2-SQL Application
This script runs all tests and generates comprehensive coverage reports.
"""

import subprocess
import sys
import os
from pathlib import Path

def run_tests():
    """Run all tests with coverage"""
    print("🧪 Running NL-2-SQL Application Tests")
    print("=" * 50)
    
    # Change to the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    # Run tests with coverage
    cmd = [
        "uv", "run", "pytest", 
        "tests/", 
        "--cov=backend", 
        "--cov-report=term-missing",
        "--cov-report=html:htmlcov",
        "--cov-report=xml:coverage.xml",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("📊 Test Results:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  Errors/Warnings:")
            print(result.stderr)
        
        print(f"✅ Tests completed with exit code: {result.returncode}")
        
        # Generate summary
        if result.returncode == 0:
            print("\n🎉 All tests passed!")
        else:
            print("\n❌ Some tests failed. Check the output above for details.")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running tests: {e}")
        return False

def run_specific_test_suite(suite_name):
    """Run a specific test suite"""
    print(f"🧪 Running {suite_name} Tests")
    print("=" * 30)
    
    cmd = [
        "uv", "run", "pytest", 
        f"tests/test_{suite_name.lower()}.py",
        "-v"
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        print("📊 Test Results:")
        print(result.stdout)
        
        if result.stderr:
            print("⚠️  Errors/Warnings:")
            print(result.stderr)
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error running {suite_name} tests: {e}")
        return False

def main():
    """Main function"""
    if len(sys.argv) > 1:
        suite = sys.argv[1]
        if suite in ["planner", "retriever", "sql_generator", "validator", "executor", "summarizer"]:
            success = run_specific_test_suite(suite)
        else:
            print(f"❌ Unknown test suite: {suite}")
            print("Available suites: planner, retriever, sql_generator, validator, executor, summarizer")
            return 1
    else:
        success = run_tests()
    
    if success:
        print("\n📈 Coverage reports generated:")
        print("  - HTML: htmlcov/index.html")
        print("  - XML: coverage.xml")
        print("  - Terminal: See output above")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
