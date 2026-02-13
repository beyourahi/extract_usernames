#!/usr/bin/env bash
# Instagram Username Extractor - Universal Setup Script
# Supports: macOS, Linux (Debian/Ubuntu, Fedora/RHEL, Arch), WSL, Git Bash

# Global variables
SCRIPT_VERSION="3.0.0"
SKIP_OLLAMA=false
SKIP_MODEL=false
VERBOSE=false
DRY_RUN=false
PYTHON_CMD=""
OS_TYPE=""
DISTRO=""
PKG_MANAGER=""

# ANSI color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;90m'
NC='\033[0m' # No Color

#==============================================================================
# Output Functions
#==============================================================================

print_success() {
    echo -e "  ${GREEN}✅ $1${NC}"
}

print_error() {
    echo -e "  ${RED}❌ $1${NC}"
}

print_warning() {
    echo -e "  ${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "  ${CYAN}💡 $1${NC}"
}

print_step() {
    echo ""
    echo -e "${YELLOW}[$1/4] $2${NC}"
}

print_header() {
    echo -e "${CYAN}"
    echo "========================================"
    echo "$1"
    echo "========================================"
    echo -e "${NC}"
}

#==============================================================================
# Help & Usage
#==============================================================================

show_help() {
    cat << EOF
Instagram Username Extractor - Universal Setup Script v${SCRIPT_VERSION}

USAGE:
    ./scripts/setup.sh [OPTIONS]

OPTIONS:
    --skip-ollama       Skip Ollama installation and model download (EasyOCR-only mode)
    --skip-model        Install Ollama but skip model download
    --verbose           Show detailed output during installation
    --dry-run           Preview installation steps without executing
    --help, -h          Display this help message

EXAMPLES:
    ./scripts/setup.sh                    # Full installation (recommended)
    ./scripts/setup.sh --skip-ollama      # EasyOCR-only mode
    ./scripts/setup.sh --dry-run          # Preview installation steps
    ./scripts/setup.sh --verbose          # Detailed output

SUPPORTED PLATFORMS:
    - macOS (Intel and Apple Silicon)
    - Linux (Ubuntu, Debian, Fedora, RHEL, Arch)
    - Windows Subsystem for Linux (WSL)
    - Git Bash for Windows

For native Windows PowerShell/CMD users, please install WSL or Git Bash first:
    WSL:      https://docs.microsoft.com/windows/wsl/install
    Git Bash: https://gitforwindows.org

Documentation: https://github.com/beyourahi/extract_usernames
EOF
}

#==============================================================================
# Platform Detection
#==============================================================================

detect_os() {
    # Check for native Windows (no Unix environment)
    if [[ -n "$WINDIR" && ! -f /proc/version ]]; then
        OS_TYPE="windows"
        DISTRO="windows"
        return
    fi

    # Detect WSL
    if grep -qiE "microsoft|wsl" /proc/version 2>/dev/null; then
        OS_TYPE="wsl"
        # WSL typically uses Ubuntu
        if [[ -f /etc/os-release ]]; then
            DISTRO=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
        else
            DISTRO="ubuntu"
        fi
        return
    fi

    # Detect Git Bash
    local uname_s=$(uname -s)
    if [[ "$uname_s" == MINGW* || "$uname_s" == MSYS* || "$uname_s" == CYGWIN* ]]; then
        OS_TYPE="gitbash"
        DISTRO="gitbash"
        return
    fi

    # Detect macOS
    if [[ "$uname_s" == "Darwin" ]]; then
        OS_TYPE="macos"
        DISTRO="macos"
        return
    fi

    # Detect Linux distribution
    if [[ -f /etc/os-release ]]; then
        OS_TYPE="linux"
        DISTRO=$(grep "^ID=" /etc/os-release | cut -d'=' -f2 | tr -d '"')
    else
        OS_TYPE="linux"
        DISTRO="unknown"
    fi
}

detect_package_manager() {
    case "$DISTRO" in
        macos)
            if command -v brew &> /dev/null; then
                PKG_MANAGER="brew"
            else
                PKG_MANAGER="none"
            fi
            ;;
        ubuntu|debian)
            PKG_MANAGER="apt"
            ;;
        fedora|rhel|centos)
            if command -v dnf &> /dev/null; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi
            ;;
        arch|manjaro)
            PKG_MANAGER="pacman"
            ;;
        gitbash)
            PKG_MANAGER="none"
            ;;
        *)
            PKG_MANAGER="unknown"
            ;;
    esac
}

#==============================================================================
# Installation Guidance Functions
#==============================================================================

show_python_install_instructions() {
    echo ""
    print_error "Python 3.9+ is required but not found"
    echo ""
    echo -e "${CYAN}Installation Instructions:${NC}"

    case "$DISTRO" in
        macos)
            echo -e "  ${YELLOW}macOS:${NC}"
            echo -e "    brew install python@3.11"
            ;;
        ubuntu|debian)
            echo -e "  ${YELLOW}Ubuntu/Debian:${NC}"
            echo -e "    sudo apt update && sudo apt install python3"
            ;;
        fedora|rhel|centos)
            echo -e "  ${YELLOW}Fedora/RHEL:${NC}"
            echo -e "    sudo $PKG_MANAGER install python3"
            ;;
        arch|manjaro)
            echo -e "  ${YELLOW}Arch Linux:${NC}"
            echo -e "    sudo pacman -S python"
            ;;
        gitbash)
            echo -e "  ${YELLOW}Git Bash (Windows):${NC}"
            echo -e "    Download from: https://www.python.org/downloads/"
            echo -e "    ⚠️  Make sure to check 'Add Python to PATH' during installation"
            ;;
        wsl)
            echo -e "  ${YELLOW}WSL:${NC}"
            echo -e "    sudo apt update && sudo apt install python3"
            ;;
        *)
            echo -e "  ${YELLOW}Download from:${NC} https://www.python.org/downloads/"
            ;;
    esac
    echo ""
}

show_ollama_install_instructions() {
    echo ""
    print_warning "Ollama not found (VLM mode unavailable)"
    echo ""
    echo -e "${CYAN}Installation Instructions:${NC}"

    case "$DISTRO" in
        macos)
            echo -e "  ${YELLOW}macOS:${NC}"
            echo -e "    brew install ollama"
            echo -e "    ollama serve &  # Start Ollama service"
            echo -e "    ollama pull glm-ocr:bf16"
            ;;
        ubuntu|debian|fedora|rhel|centos|arch|wsl)
            echo -e "  ${YELLOW}Linux/WSL:${NC}"
            echo -e "    curl -fsSL https://ollama.com/install.sh | sh"
            echo -e "    ollama pull glm-ocr:bf16"
            ;;
        gitbash)
            echo -e "  ${YELLOW}Git Bash (Windows):${NC}"
            echo -e "    Download from: https://ollama.com/download"
            echo -e "    After installation: ollama pull glm-ocr:bf16"
            ;;
        *)
            echo -e "  ${YELLOW}Visit:${NC} https://ollama.com/download"
            ;;
    esac

    echo ""
    print_info "EasyOCR will be used as fallback (88% accuracy vs VLM 96%)"
    echo ""
}

#==============================================================================
# Pre-flight Checks
#==============================================================================

check_project_root() {
    if [[ ! -f "pyproject.toml" ]]; then
        print_error "Must run from project root (pyproject.toml not found)"
        echo ""
        echo -e "${CYAN}Try:${NC}"
        echo -e "  cd extract_usernames"
        echo -e "  ./scripts/setup.sh"
        echo ""
        exit 1
    fi
}

check_python_version() {
    # Try python3 first (Unix standard), then python (Windows/WSL)
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        show_python_install_instructions
        exit 1
    fi

    # Get version using POSIX-compliant awk (not grep -P)
    local version_output=$($PYTHON_CMD --version 2>&1)
    local version=$(echo "$version_output" | awk '{print $2}')
    local major=$(echo "$version" | awk -F. '{print $1}')
    local minor=$(echo "$version" | awk -F. '{print $2}')

    if [[ "$major" -lt 3 ]] || { [[ "$major" -eq 3 ]] && [[ "$minor" -lt 9 ]]; }; then
        print_error "Python 3.9+ required (found $version)"
        show_python_install_instructions
        exit 1
    fi

    print_success "Python $version ($PYTHON_CMD)"
}

#==============================================================================
# Installation Functions
#==============================================================================

install_package() {
    # Validate project files exist
    local required_files=("pyproject.toml" "requirements.txt" "extract_usernames/cli.py")
    for file in "${required_files[@]}"; do
        if [[ ! -f "$file" ]]; then
            print_error "Required file missing: $file"
            exit 1
        fi
    done

    # Check pip availability
    if ! $PYTHON_CMD -m pip --version &> /dev/null; then
        print_error "pip not found"
        echo ""
        echo -e "${CYAN}Try:${NC}"
        echo -e "  $PYTHON_CMD -m ensurepip"
        echo ""
        exit 1
    fi

    # Install package
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would run: $PYTHON_CMD -m pip install -e ."
        return
    fi

    local pip_flags=""
    if [[ "$VERBOSE" == false ]]; then
        pip_flags="--quiet"
    fi

    if $PYTHON_CMD -m pip install -e . $pip_flags; then
        print_success "Package installed"
    else
        print_error "Installation failed"
        echo ""
        echo -e "${CYAN}Troubleshooting:${NC}"
        echo -e "  - Try: $PYTHON_CMD -m pip install -e . --user"
        echo -e "  - Check permissions in current directory"
        echo -e "  - Ensure pip is up to date: $PYTHON_CMD -m pip install --upgrade pip"
        echo ""
        exit 1
    fi
}

setup_ollama() {
    if [[ "$SKIP_OLLAMA" == true ]]; then
        print_info "Skipping Ollama setup (--skip-ollama flag)"
        return
    fi

    if ! command -v ollama &> /dev/null; then
        show_ollama_install_instructions
        return
    fi

    print_success "Ollama installed"

    if [[ "$SKIP_MODEL" == true ]]; then
        print_info "Skipping model download (--skip-model flag)"
        return
    fi

    # Download GLM-OCR model
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would run: ollama pull glm-ocr:bf16"
        return
    fi

    echo -e "  ${CYAN}Downloading GLM-OCR model (~2.2GB)...${NC}"

    local pull_output
    pull_output=$(ollama pull glm-ocr:bf16 2>&1)

    # Verify success (check for "success" or "already" in output)
    if echo "$pull_output" | grep -qiE "success|already"; then
        print_success "Model ready"
    else
        print_warning "Model download incomplete"
        if [[ "$VERBOSE" == true ]]; then
            echo -e "${GRAY}$pull_output${NC}"
        fi
    fi
}

validate_cli() {
    if [[ "$DRY_RUN" == true ]]; then
        print_info "[DRY RUN] Would test: extract-usernames --version"
        return
    fi

    if extract-usernames --version &> /dev/null; then
        print_success "CLI ready"
    else
        print_warning "CLI command not found in PATH"
        echo ""
        echo -e "${CYAN}Try:${NC}"
        echo -e "  1. Reload shell: ${GREEN}source ~/.bashrc${NC} or ${GREEN}source ~/.zshrc${NC}"
        echo -e "  2. Or use: ${GREEN}$PYTHON_CMD -m extract_usernames.cli${NC}"
        echo ""
    fi
}

#==============================================================================
# Summary Output
#==============================================================================

show_summary() {
    echo ""
    print_header "✅ Setup Complete!"
    echo ""
    echo -e "${CYAN}Quick Start:${NC}"
    echo -e "  1. Place screenshots on your Desktop"
    echo -e "  2. Run: ${GREEN}extract-usernames${NC}"
    echo -e "  3. Follow interactive prompts"
    echo ""
    echo -e "${CYAN}Or use flags:${NC}"
    echo -e "  ${GREEN}extract-usernames --input my_screenshots --output results${NC}"
    echo ""

    # Platform-specific notes
    if [[ "$OS_TYPE" == "wsl" ]]; then
        echo -e "${CYAN}WSL Note:${NC}"
        echo -e "  Access Windows files via: ${YELLOW}/mnt/c/Users/...${NC}"
        echo ""
    elif [[ "$OS_TYPE" == "gitbash" ]]; then
        echo -e "${CYAN}Git Bash Note:${NC}"
        echo -e "  Windows paths work: ${YELLOW}C:/Users/...${NC}"
        echo ""
    fi

    # Ollama recommendations
    if [[ "$SKIP_OLLAMA" == true ]] || ! command -v ollama &> /dev/null; then
        echo -e "${YELLOW}💡 For best accuracy (96% vs 88%), install Ollama:${NC}"
        case "$DISTRO" in
            macos)
                echo -e "  brew install ollama && ollama pull glm-ocr:bf16"
                ;;
            *)
                echo -e "  curl -fsSL https://ollama.com/install.sh | sh"
                echo -e "  ollama pull glm-ocr:bf16"
                ;;
        esac
        echo ""
    fi

    echo -e "${CYAN}Documentation:${NC} https://github.com/beyourahi/extract_usernames"
    echo ""
}

#==============================================================================
# Argument Parsing
#==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-ollama)
                SKIP_OLLAMA=true
                shift
                ;;
            --skip-model)
                SKIP_MODEL=true
                shift
                ;;
            --verbose)
                VERBOSE=true
                shift
                ;;
            --dry-run)
                DRY_RUN=true
                shift
                ;;
            --help|-h)
                show_help
                exit 0
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                echo ""
                show_help
                exit 1
                ;;
        esac
    done
}

#==============================================================================
# Main Execution
#==============================================================================

main() {
    # Parse arguments
    parse_args "$@"

    # Detect platform
    detect_os
    detect_package_manager

    # Handle native Windows
    if [[ "$OS_TYPE" == "windows" ]]; then
        echo ""
        print_error "Native Windows PowerShell/CMD not supported"
        echo ""
        echo -e "${CYAN}This script requires a Unix-like environment.${NC}"
        echo -e "Please install one of the following:"
        echo ""
        echo -e "${YELLOW}Option 1 - WSL (Recommended):${NC}"
        echo -e "  https://docs.microsoft.com/windows/wsl/install"
        echo ""
        echo -e "${YELLOW}Option 2 - Git Bash:${NC}"
        echo -e "  https://gitforwindows.org"
        echo ""
        echo -e "After installation, run this script again:"
        echo -e "  ${GREEN}./scripts/setup.sh${NC}"
        echo ""
        exit 1
    fi

    # Display header
    print_header "Instagram Username Extractor - Setup"

    if [[ "$DRY_RUN" == true ]]; then
        print_info "DRY RUN MODE - No changes will be made"
    fi

    # Pre-flight checks
    check_project_root

    # Step 1: Check Python
    print_step "1" "Checking Python..."
    check_python_version

    # Step 2: Install Package
    print_step "2" "Installing package..."
    install_package

    # Step 3: Setup Ollama
    print_step "3" "Checking Ollama..."
    setup_ollama

    # Step 4: Validate CLI
    print_step "4" "Validating..."
    validate_cli

    # Summary
    if [[ "$DRY_RUN" == false ]]; then
        show_summary
    else
        echo ""
        print_info "[DRY RUN] Preview complete. Run without --dry-run to install."
        echo ""
    fi
}

# Execute main function with all arguments
main "$@"
