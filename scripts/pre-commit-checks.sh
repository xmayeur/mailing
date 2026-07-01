#!/bin/bash
# Pre-commit validation script for local testing before push
# Runs all quality checks: pymarkdown, black, ruff, vulture, pyright, mypy, pytest
# Exit with status code indicating which checks passed/failed

set -euo pipefail

export PATH="$HOME/.local/bin:$PATH"

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

echo "🔍 Running pre-commit quality checks..."
echo ""

FAILED_CHECKS=()

run_check() {
    local label="$1"; shift
    echo "▶ $label..."
    if "$@" 2>&1 | tail -10; then
        echo "✓ $label passed"
    else
        echo "✗ $label failed"
        FAILED_CHECKS+=("$label")
    fi
    echo ""
}

run_check "pymarkdown lint"  poetry run pymarkdownlnt fix ./*.md ./specs/*.md

run_check "black"            poetry run black --check . --target-version py312 \
                               --exclude='(venv|env|\.venv|release|\.git)'

run_check "ruff"             poetry run ruff check src/ tests/ --fix

run_check "vulture"          poetry run vulture src/ --min-confidence 80

run_check "pyright"          poetry run pyright src/

run_check "mypy"             poetry run mypy --strict src/

run_check "pytest"           poetry run pytest tests/unit/ -q --tb=short \
                               --cov=src --cov-report=term-missing

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [[ ${#FAILED_CHECKS[@]} -eq 0 ]]; then
    echo "✅ All checks passed! Ready to commit."
    exit 0
else
    echo "❌ Failed checks: ${FAILED_CHECKS[*]}"
    echo "Fix the issues and re-run this script."
    exit 1
fi
