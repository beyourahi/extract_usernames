#!/bin/bash
# Instagram Username Extractor - Unix Setup Script
# Bash script for automated installation on macOS and Linux

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "========================================"
echo "Instagram Username Extractor - Setup"
echo "========================================"
echo -e "${NC}"

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    OS="macOS"
    PACKAGE_MANAGER="brew"
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    OS="Linux"
    if command -v apt-get &> /dev/null; then
        PACKAGE_MANAGER="apt"
    elif command -v yum &> /dev/null; then
        PACKAGE_MANAGER="yum"
    elif command -v pacman &> /dev/null; then
        PACKAGE_MANAGER="pacman"
    else
        PACKAGE_MANAGER="unknown"
    fi
else
    OS="Unknown"
    PACKAGE_MANAGER="unknown"
fi

echo -e "${GRAY}Detected OS: $OS${NC}"
echo ""

# Check Python installation
echo -e "${YELLOW}[1/5] Checking Python installation...${NC}"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)
    
    if [ "$PYTHON_MAJOR" -ge 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
        echo -e "  ${GREEN}✅ Found Python $PYTHON_VERSION${NC}"
    else
        echo -e "  ${RED}❌ Python 3.9+ required, found $PYTHON_VERSION${NC}"
        echo -e "  ${YELLOW}Please upgrade Python${NC}"
        exit 1
    fi
else
    echo -e "  ${RED}❌ Python 3 not found${NC}"
    echo -e "  ${YELLOW}Installation instructions:${NC}"
    if [ "$OS" = "macOS" ]; then
        echo -e "  ${GRAY}brew install python@3.11${NC}"
    elif [ "$PACKAGE_MANAGER" = "apt" ]; then
        echo -e "  ${GRAY}sudo apt update && sudo apt install python3 python3-pip python3-venv${NC}"
    elif [ "$PACKAGE_MANAGER" = "yum" ]; then
        echo -e "  ${GRAY}sudo yum install python3 python3-pip${NC}"
    else
        echo -e "  ${GRAY}Visit https://www.python.org/downloads/${NC}"
    fi
    exit 1
fi

# Check pip
if ! command -v pip3 &> /dev/null; then
    echo -e "  ${YELLOW}⚠️  pip3 not found, installing...${NC}"
    python3 -m ensurepip --upgrade 2>/dev/null || true
fi

# Offer virtual environment for Linux
if [ "$OS" = "Linux" ] && [ ! -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}💡 Tip: Virtual environment recommended for Linux${NC}"
    read -p "Create virtual environment? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo -e "  ${GRAY}Creating virtual environment...${NC}"
        python3 -m venv venv
        source venv/bin/activate
        echo -e "  ${GREEN}✅ Virtual environment created and activated${NC}"
        echo -e "  ${GRAY}To activate later: source venv/bin/activate${NC}"
    fi
fi

# Install Python dependencies
echo ""
echo -e "${YELLOW}[2/5] Installing Python dependencies...${NC}"
echo -e "  ${GRAY}This may take 5-10 minutes (downloading ~2-3GB)...${NC}"

python3 -m pip install --upgrade pip --quiet
if python3 -m pip install -r requirements.txt; then
    echo -e "  ${GREEN}✅ Dependencies installed successfully${NC}"
else
    echo -e "  ${YELLOW}⚠️  Some dependencies failed to install${NC}"
    echo -e "  ${GRAY}Try: pip3 install --user -r requirements.txt${NC}"
fi

# Check Ollama installation
echo ""
echo -e "${YELLOW}[3/5] Checking Ollama installation...${NC}"
if command -v ollama &> /dev/null; then
    echo -e "  ${GREEN}✅ Ollama is installed${NC}"
    OLLAMA_INSTALLED=true
    
    # Check if Ollama is running
    if ollama list &> /dev/null; then
        echo -e "  ${GREEN}✅ Ollama service is running${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Ollama service not running${NC}"
        echo -e "  ${GRAY}Starting Ollama service...${NC}"
        if [ "$OS" = "macOS" ]; then
            brew services start ollama 2>/dev/null || ollama serve &> /dev/null &
        else
            ollama serve &> /dev/null &
        fi
        sleep 3
    fi
else
    echo -e "  ${YELLOW}⚠️  Ollama not found${NC}"
    echo -e "  ${GRAY}VLM-primary mode requires Ollama for maximum accuracy${NC}"
    echo -e "  ${GRAY}Installation instructions:${NC}"
    if [ "$OS" = "macOS" ]; then
        echo -e "  ${GRAY}brew install ollama${NC}"
    else
        echo -e "  ${GRAY}curl -fsSL https://ollama.com/install.sh | sh${NC}"
    fi
    echo -e "  ${GRAY}Note: You can use --no-vlm flag for EasyOCR-only mode${NC}"
    OLLAMA_INSTALLED=false
fi

# Download GLM-OCR model if Ollama is available
if [ "$OLLAMA_INSTALLED" = true ]; then
    echo ""
    echo -e "${YELLOW}[4/5] Downloading GLM-OCR model...${NC}"
    echo -e "  ${GRAY}Model size: ~2.2GB (this may take a few minutes)...${NC}"
    
    if ollama pull glm-ocr:bf16; then
        echo -e "  ${GREEN}✅ GLM-OCR model downloaded successfully${NC}"
    else
        echo -e "  ${YELLOW}⚠️  Model download had issues${NC}"
        echo -e "  ${GRAY}You can download it later with: ollama pull glm-ocr:bf16${NC}"
    fi
else
    echo ""
    echo -e "${YELLOW}[4/5] Skipping model download (Ollama not installed)${NC}"
fi

# Validate installation
echo ""
echo -e "${YELLOW}[5/5] Validating installation...${NC}"
if python3 extract_usernames.py --help &> /dev/null; then
    echo -e "  ${GREEN}✅ Installation validated successfully${NC}"
else
    echo -e "  ${RED}❌ Validation failed${NC}"
    echo -e "  ${YELLOW}Run these commands for diagnostics:${NC}"
    echo -e "  ${GRAY}  python3 --version${NC}"
    echo -e "  ${GRAY}  pip3 list${NC}"
    echo -e "  ${GRAY}  ollama list${NC}"
fi

# Print summary
echo ""
echo -e "${CYAN}"
echo "========================================"
echo "Setup Complete!"
echo "========================================"
echo -e "${NC}"

echo -e "${GREEN}✅ Python: Installed${NC}"
echo -e "${GREEN}✅ Dependencies: Installed${NC}"
if [ "$OLLAMA_INSTALLED" = true ]; then
    echo -e "${GREEN}✅ Ollama: Installed${NC}"
    echo -e "${GREEN}✅ GLM-OCR Model: Ready${NC}"
    echo -e "${GREEN}✅ VLM-Primary Mode: Enabled${NC}"
else
    echo -e "${YELLOW}⚠️  Ollama: Not installed${NC}"
    echo -e "${YELLOW}⚠️  VLM-Primary Mode: Unavailable${NC}"
fi

echo ""
echo -e "${CYAN}Next steps:${NC}"
echo -e "${NC}1. Place Instagram screenshots in a folder on your Desktop${NC}"
echo -e "${NC}2. Run: python3 extract_usernames.py folder_name${NC}"
echo -e "${NC}3. Check results in ~/Desktop/leads/${NC}"

if [ "$OLLAMA_INSTALLED" = false ]; then
    echo ""
    echo -e "${YELLOW}💡 Tip: Install Ollama for VLM-primary mode (recommended)${NC}"
    if [ "$OS" = "macOS" ]; then
        echo -e "${GRAY}   brew install ollama${NC}"
    else
        echo -e "${GRAY}   curl -fsSL https://ollama.com/install.sh | sh${NC}"
    fi
    echo -e "${GRAY}   ollama pull glm-ocr:bf16${NC}"
    echo -e "${GRAY}   Or use EasyOCR-only: python3 extract_usernames.py folder --no-vlm${NC}"
fi

if [ -d "venv" ]; then
    echo ""
    echo -e "${YELLOW}💡 Virtual environment created${NC}"
    echo -e "${GRAY}   Activate with: source venv/bin/activate${NC}"
fi

echo ""
echo -e "${GRAY}For help: python3 extract_usernames.py --help${NC}"
echo -e "${GRAY}Documentation: https://github.com/beyourahi/extract_usernames${NC}"
echo ""
