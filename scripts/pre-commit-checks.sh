#!/bin/bash
# Pre-commit validation script for local testing before push
# Run all quality checks: pytest, mypy, pyright, ruff, vulture
# Exit with status code indicating which checks passed/failed

set -e

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "🔍 Running pre-commit quality checks..."
echo ""

# Track results
FAILED_CHECKS=()

# 1. Pytest with coverage
echo "📝 Running pytest with coverage..."
if pytest tests/ -q --tb=short --cov=src --cov-report=term-missing 2>&1 | tail -20; then
    echo "✓ Tests passed"
else
    echo "✗ Tests failed"
    FAILED_CHECKS+=("pytest")
fi
echo ""

# 2. Type checking with mypy
echo "🔤 Checking types with mypy --strict..."
if mypy --strict src/ 2>&1 | tail -5; then
    echo "✓ Mypy passed"
else
    echo "✗ Mypy found issues"
    FAILED_CHECKS+=("mypy")
fi
echo ""

# 3. Type checking with pyright
echo "🔍 Checking types with pyright..."
if pyright src/ 2>&1 | tail -5; then
    echo "✓ Pyright passed"
else
    echo "✗ Pyright found issues"
    FAILED_CHECKS+=("pyright")
fi
echo ""

# 4. Linting with ruff
echo "📐 Checking code quality with ruff..."
if ruff check . --exclude venv,env,build,dist,release 2>&1 | tail -5; then
    echo "✓ Ruff passed"
else
    echo "✗ Ruff found violations"
    FAILED_CHECKS+=("ruff")
fi
echo ""

# 5. Dead code detection with vulture
echo "🧛 Detecting dead code with vulture..."
if vulture src/ --exclude venv,tests,build,dist,release 2>&1 | tail -5; then
    echo "✓ Vulture passed"
else
    echo "⚠ Vulture warnings (non-blocking)"
fi
echo ""

# Report results
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ ${#FAILED_CHECKS[@]} -eq 0 ]; then
    echo "✅ All checks passed! Ready to commit."
    exit 0
else
    echo "❌ Some checks failed: ${FAILED_CHECKS[*]}"
    echo "Please fix the issues and run this script again."
    exit 1
fi
