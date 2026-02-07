#!/bin/bash
# Instagram Username Extractor - Modern Setup Script
# One-command installation with pip install -e .

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${CYAN}"
echo "========================================"
echo "Instagram Username Extractor - Setup"
echo "========================================"
echo -e "${NC}"

# Check Python
echo -e "${YELLOW}[1/4] Checking Python...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "  ${RED}❌ Python 3 not found${NC}"
    echo -e "  ${YELLOW}Install: brew install python@3.11 (macOS) or apt install python3 (Linux)${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+' | head -1)
echo -e "  ${GREEN}✅ Python $PYTHON_VERSION${NC}"

# Install package
echo ""
echo -e "${YELLOW}[2/4] Installing package...${NC}"
if python3 -m pip install -e . --quiet; then
    echo -e "  ${GREEN}✅ Package installed${NC}"
else
    echo -e "  ${RED}❌ Installation failed${NC}"
    exit 1
fi

# Check Ollama
echo ""
echo -e "${YELLOW}[3/4] Checking Ollama...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "  ${GREEN}✅ Ollama installed${NC}"
    OLLAMA_OK=true
    
    # Pull GLM-OCR model
    echo -e "  ${CYAN}Downloading GLM-OCR model (~2.2GB)...${NC}"
    if ollama pull glm-ocr:bf16 2>&1 | grep -q "success\|already"; then
        echo -e "  ${GREEN}✅ Model ready${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Model download incomplete${NC}"
    fi
else
    echo -e "  ${YELLOW}⚠️  Ollama not found (VLM mode unavailable)${NC}"
    echo -e "  ${YELLOW}Install: brew install ollama${NC}"
    OLLAMA_OK=false
fi

# Validate
echo ""
echo -e "${YELLOW}[4/4] Validating...${NC}"
if extract-usernames --version &> /dev/null; then
    echo -e "  ${GREEN}✅ CLI ready${NC}"
else
    echo -e "  ${RED}❌ Validation failed${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${CYAN}========================================${NC}"
echo -e "${GREEN}✅ Setup Complete!${NC}"
echo -e "${CYAN}========================================${NC}"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo -e "  1. Place screenshots on your Desktop"
echo -e "  2. Run: ${GREEN}extract-usernames${NC}"
echo -e "  3. Follow interactive prompts"
echo ""
echo -e "${CYAN}Or use flags:${NC}"
echo -e "  ${GREEN}extract-usernames --input my_screenshots --output results${NC}"
echo ""
if [ "$OLLAMA_OK" = false ]; then
    echo -e "${YELLOW}💡 For best accuracy, install Ollama:${NC}"
    echo -e "  brew install ollama && ollama pull glm-ocr:bf16"
    echo ""
fi
echo -e "${CYAN}Documentation:${NC} https://github.com/beyourahi/extract_usernames"
echo ""
