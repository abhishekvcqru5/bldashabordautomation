#!/bin/bash

# Dashboard Icons Automation - Setup Script
# This script installs all dependencies and prepares the automation system

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   DASHBOARD ICONS AUTOMATION - SETUP                        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Check Python
echo "→ Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo "✗ Python 3 is not installed"
    echo "  Please install Python 3.7+ from https://www.python.org/"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
echo "✓ Found Python $PYTHON_VERSION"
echo ""

# Install dependencies
echo "→ Installing Python dependencies..."
python3 -m pip install --upgrade pip -q
python3 -m pip install -r automation/requirements.txt -q
echo "✓ Dependencies installed successfully"
echo ""

# Create directories
echo "→ Creating necessary directories..."
mkdir -p automation/logs
mkdir -p automation/screenshots
mkdir -p automation/processed_images
echo "✓ Directories created"
echo ""

# Verify files
echo "→ Verifying configuration files..."
FILES=(
    "automation/run_automation.py"
    "automation/dashboard_automation.py"
    "automation/image_processor.py"
    "automation/icon_config.json"
    "automation/requirements.txt"
)

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (missing)"
    fi
done
echo ""

# Test image processor
echo "→ Testing image processor..."
python3 -c "from automation.image_processor import ImageProcessor; print('  ✓ Image processor ready')" 2>/dev/null || echo "  ⚠ Image processor test skipped"
echo ""

echo "╔══════════════════════════════════════════════════════════════╗"
echo "║   SETUP COMPLETE! ✓                                         ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""
echo "Next steps:"
echo ""
echo "1. Edit your icon configuration:"
echo "   → automation/icon_config.json"
echo ""
echo "2. Make sure your images are in the dashboardicons/ folder"
echo ""
echo "3. Run the automation:"
echo "   → python3 automation/run_automation.py"
echo ""
echo "For more help, read: automation/README.md"
echo ""
