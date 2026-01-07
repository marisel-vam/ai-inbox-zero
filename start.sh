#!/bin/bash

# AI Inbox Zero - Quick Start Script

set -e

echo "=================================="
echo "Starting AI Inbox Zero..."
echo "=================================="
echo ""

# Activate virtual environment
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate || . venv/Scripts/activate
    echo "✓ Virtual environment activated"
else
    echo "Error: Virtual environment not found."
    echo "Please run ./setup.sh first"
    exit 1
fi

# Validate configuration
echo ""
echo "Validating configuration..."
if ! python3 config.py; then
    echo "Configuration validation failed!"
    echo "Please check your .env file and credentials.json"
    exit 1
fi

# Start the application
echo ""
echo "Starting Flask application..."
echo "=================================="
echo ""

python3 app.py