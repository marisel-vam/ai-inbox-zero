#!/bin/bash

# AI Inbox Zero - Setup Script
# This script helps you set up the application quickly

set -e  # Exit on error

echo "=================================="
echo "AI Inbox Zero - Setup Script"
echo "=================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check Python version
echo "Checking Python version..."
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2 | cut -d'.' -f1,2)
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo ""
    echo "Creating virtual environment..."
    python3 -m venv venv
    echo -e "${GREEN}✓ Virtual environment created${NC}"
else
    echo -e "${YELLOW}! Virtual environment already exists${NC}"
fi

# Activate virtual environment
echo ""
echo "Activating virtual environment..."
source venv/bin/activate || . venv/Scripts/activate
echo -e "${GREEN}✓ Virtual environment activated${NC}"

# Install dependencies
echo ""
echo "Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Setup .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "Creating .env file from template..."
    cp .env.example .env
    echo -e "${GREEN}✓ .env file created${NC}"
    echo -e "${YELLOW}! Please edit .env and add your API keys${NC}"
else
    echo -e "${YELLOW}! .env file already exists${NC}"
fi

# Check for credentials.json
echo ""
if [ ! -f "credentials.json" ]; then
    echo -e "${YELLOW}! Warning: credentials.json not found${NC}"
    echo "  Please download OAuth credentials from Google Cloud Console"
    echo "  and save as credentials.json in this directory"
else
    echo -e "${GREEN}✓ credentials.json found${NC}"
fi

# Check .env configuration
echo ""
echo "Checking configuration..."
if grep -q "your_groq_api_key_here" .env; then
    echo -e "${YELLOW}! Please set GROQ_API_KEY in .env file${NC}"
else
    echo -e "${GREEN}✓ GROQ_API_KEY is configured${NC}"
fi

if grep -q "your_secret_key_here" .env; then
    echo -e "${YELLOW}! Please set FLASK_SECRET_KEY in .env file${NC}"
    echo "  Generate one with: python -c 'import secrets; print(secrets.token_hex(32))'"
else
    echo -e "${GREEN}✓ FLASK_SECRET_KEY is configured${NC}"
fi

# Run configuration validation
echo ""
echo "Validating configuration..."
if python3 config.py; then
    echo -e "${GREEN}✓ Configuration is valid${NC}"
else
    echo -e "${RED}✗ Configuration validation failed${NC}"
    echo "  Please fix the errors above before running the app"
fi

# Setup complete
echo ""
echo "=================================="
echo -e "${GREEN}Setup Complete!${NC}"
echo "=================================="
echo ""
echo "Next steps:"
echo "1. Edit .env and add your GROQ_API_KEY"
echo "2. Download credentials.json from Google Cloud Console"
echo "3. Run the application:"
echo "   python app.py"
echo ""
echo "Or use the quick start:"
echo "   ./start.sh"
echo ""