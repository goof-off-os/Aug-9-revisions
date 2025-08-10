#!/bin/bash
# setup_quality_tools.sh
# Setup script for ProposalOS code quality tools

echo "=================================================="
echo "ProposalOS Code Quality Tools Setup"
echo "=================================================="
echo ""

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.11"

echo "Checking Python version..."
if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" = "$required_version" ]; then 
    echo "✓ Python $python_version meets minimum requirement ($required_version)"
else
    echo "✗ Python $python_version is below minimum requirement ($required_version)"
    echo "Please upgrade Python to 3.11 or higher"
    exit 1
fi

echo ""
echo "Installing code quality tools..."
echo "----------------------------------"

# Install development dependencies
pip install --upgrade pip
pip install pre-commit black ruff mypy pytest pytest-cov isort bandit pydocstyle

echo ""
echo "Setting up pre-commit hooks..."
echo "----------------------------------"

# Install pre-commit hooks
pre-commit install

# Create secrets baseline (for detect-secrets)
echo "Creating secrets baseline..."
detect-secrets scan --baseline .secrets.baseline 2>/dev/null || echo "Detect-secrets not installed (optional)"

echo ""
echo "Running initial quality checks..."
echo "----------------------------------"

# Run pre-commit on all files
echo "Running pre-commit checks..."
pre-commit run --all-files || true

echo ""
echo "Running specific tool checks..."
echo "----------------------------------"

# Run individual tools with more detail
echo "1. Ruff (linting)..."
ruff check . --statistics 2>/dev/null || echo "Some linting issues found"

echo ""
echo "2. Black (formatting)..."
black --check . 2>/dev/null || echo "Some formatting issues found"

echo ""
echo "3. isort (import sorting)..."
isort --check-only . 2>/dev/null || echo "Some import ordering issues found"

echo ""
echo "4. MyPy (type checking)..."
mypy proposalos_rge --ignore-missing-imports 2>/dev/null || echo "Some type issues found"

echo ""
echo "5. Bandit (security)..."
bandit -r proposalos_rge -ll 2>/dev/null || echo "Some security concerns found"

echo ""
echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "Available commands:"
echo "  pre-commit run --all-files    # Run all checks"
echo "  ruff check . --fix           # Auto-fix linting issues"
echo "  black .                      # Auto-format code"
echo "  isort .                      # Auto-sort imports"
echo "  mypy proposalos_rge          # Check types"
echo "  pytest -q                    # Run tests"
echo "  bandit -r proposalos_rge     # Security scan"
echo ""
echo "Pre-commit will now run automatically on git commit"
echo "=================================================="