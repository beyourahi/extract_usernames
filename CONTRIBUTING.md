# Contributing to Instagram Username Extractor

Thank you for considering contributing to this project! This guide will help you get started.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How Can I Contribute?](#how-can-i-contribute)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Enhancements](#suggesting-enhancements)

---

## Code of Conduct

This project adheres to a code of conduct that all contributors are expected to follow:

- **Be respectful** and considerate in all interactions
- **Be collaborative** and open to feedback
- **Focus on what is best** for the community and the project
- **Show empathy** towards other community members

---

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title** describing the issue
- **Detailed description** of the problem
- **Steps to reproduce** the behavior
- **Expected vs actual behavior**
- **Environment details** (OS, Python version, GPU, etc.)
- **Log output** if applicable (use `--diagnostics` flag)

### Suggesting Enhancements

Enhancement suggestions are welcome! Please include:

- **Clear title** describing the enhancement
- **Detailed description** of the proposed feature
- **Use case** explaining why this would be useful
- **Potential implementation** if you have ideas

### Pull Requests

We actively welcome pull requests:

1. Fork the repo and create your branch from `main`
2. Make your changes
3. Add tests if applicable
4. Update documentation
5. Ensure tests pass
6. Submit pull request

---

## Development Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub, then:
git clone https://github.com/YOUR_USERNAME/extract_usernames.git
cd extract_usernames
```

### 2. Create Virtual Environment

```bash
# Create virtual environment
python3 -m venv venv

# Activate it
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate      # Windows
```

### 3. Install in Development Mode

```bash
# Install package in editable mode
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

### 4. Install Ollama (Recommended)

```bash
# macOS
brew install ollama
ollama serve &
ollama pull glm-ocr:bf16

# Linux
curl -fsSL https://ollama.com/install.sh | sh
ollama serve &
ollama pull glm-ocr:bf16
```

### 5. Verify Installation

```bash
extract-usernames --version
```

---

## Project Structure

```
extract_usernames/
├── extract_usernames/          # Core package
│   ├── cli.py                 # Click CLI interface
│   ├── config.py              # Configuration management
│   ├── main.py                # Extraction pipeline
│   │
│   ├── ocr/                   # OCR & VLM modules
│   │   └── prompts.py         # Interactive wizards
│   │
│   ├── integrations/          # External services
│   │   ├── instagram_validator.py
│   │   ├── notion_manager.py
│   │   └── notion_sync.py
│   │
│   └── _archive/              # Legacy code
│       └── extract_usernames.py
│
├── scripts/                   # Setup scripts
├── tests/                     # Test suite
└── docs/                      # Documentation
```

### Key Components

- **CLI Layer** (`cli.py`) - User interface and command handling
- **Config Layer** (`config.py`) - JSON configuration persistence
- **OCR Layer** (`ocr/`) - Vision and text extraction
- **Integration Layer** (`integrations/`) - External API clients
- **Pipeline** (`main.py`) - Orchestrates the workflow

---

## Coding Standards

### Python Style Guide

We follow [PEP 8](https://pep8.org/) with some adjustments:

- **Line length:** 100 characters (not 79)
- **Quotes:** Double quotes for strings, single for dict keys
- **Imports:** Grouped (stdlib, third-party, local)
- **Type hints:** Use where it improves clarity

### Code Organization

```python
# 1. Docstring
"""Module description."""

# 2. Imports (grouped)
import sys
from pathlib import Path

import click
from typing import Optional

from .config import ConfigManager

# 3. Constants
DEFAULT_MODEL = 'glm-ocr:bf16'

# 4. Functions/Classes
def extract_username(image_path: Path) -> Optional[str]:
    """Extract username from image.
    
    Args:
        image_path: Path to image file
        
    Returns:
        Extracted username or None
    """
    pass
```

### Naming Conventions

- **Functions/Variables:** `snake_case`
- **Classes:** `PascalCase`
- **Constants:** `UPPER_SNAKE_CASE`
- **Private:** `_leading_underscore`

### Documentation

- All public functions must have docstrings
- Use Google-style docstrings:

```python
def process_image(path: Path, model: str = 'glm-ocr') -> dict:
    """Process image with specified model.
    
    Args:
        path: Path to image file
        model: VLM model name (default: glm-ocr)
        
    Returns:
        Dictionary with extraction results
        
    Raises:
        FileNotFoundError: If image doesn't exist
        ValueError: If model is invalid
    """
```

---

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=extract_usernames

# Run specific test file
pytest tests/test_cli.py

# Run specific test
pytest tests/test_cli.py::test_version
```

### Writing Tests

- Place tests in `tests/` directory
- Name test files `test_*.py`
- Name test functions `test_*`
- Use pytest fixtures for setup

```python
import pytest
from extract_usernames.config import ConfigManager

def test_config_save_and_load(tmp_path):
    """Test config persistence."""
    config = {'input_dir': '/test'}
    manager = ConfigManager(config_dir=tmp_path)
    
    manager.save(config)
    loaded = manager.load()
    
    assert loaded == config
```

---

## Submitting Changes

### Workflow

1. **Create a branch**
   ```bash
   git checkout -b feature/amazing-feature
   ```

2. **Make your changes**
   - Write code
   - Add tests
   - Update docs

3. **Test your changes**
   ```bash
   pytest
   extract-usernames --version  # Smoke test
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "Add amazing feature"
   ```

5. **Push to your fork**
   ```bash
   git push origin feature/amazing-feature
   ```

6. **Open a Pull Request**
   - Go to GitHub and create PR
   - Fill in PR template
   - Link related issues

### Commit Messages

Write clear, concise commit messages:

```
Add feature to validate Instagram profiles

- Implement HTTP client for Instagram API
- Add rate limiting and retry logic
- Update tests and documentation

Closes #42
```

**Format:**
- First line: Brief summary (50 chars or less)
- Blank line
- Detailed explanation if needed
- Reference issues/PRs

### Pull Request Guidelines

**Before submitting:**
- [ ] Tests pass (`pytest`)
- [ ] Code follows style guide
- [ ] Documentation updated
- [ ] Commit messages are clear
- [ ] PR description explains changes

**PR Description Template:**
```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## Testing
How was this tested?

## Checklist
- [ ] Code follows style guide
- [ ] Tests added/updated
- [ ] Documentation updated
- [ ] No breaking changes (or documented)
```

---

## Reporting Bugs

### Before Reporting

1. Check [existing issues](https://github.com/beyourahi/extract_usernames/issues)
2. Try latest version from `main` branch
3. Test with diagnostics mode: `extract-usernames --diagnostics`

### Bug Report Template

```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Run command: `extract-usernames --input test/`
2. See error: ...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Environment
- OS: macOS 14.5
- Python: 3.11.2
- Package version: 2.0.0
- GPU: Apple M2
- Ollama: 0.1.27

## Logs
```
Paste relevant log output here
```

## Additional Context
Any other relevant information
```

---

## Suggesting Enhancements

### Enhancement Template

```markdown
## Feature Description
Clear description of the proposed feature

## Use Case
Why is this needed? What problem does it solve?

## Proposed Solution
How should this work?

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Mockups, examples, references, etc.
```

---

## Areas for Contribution

### Good First Issues

- Documentation improvements
- Adding tests
- Fixing typos
- Improving error messages

### Wanted Features

- Additional VLM model support
- Batch processing improvements
- Web interface
- API endpoint
- Docker containerization
- CI/CD pipeline

### Performance Improvements

- Parallel processing optimization
- Memory usage reduction
- Faster image preprocessing
- Caching strategies

---

## Questions?

Feel free to:

- Open an issue for questions
- Start a discussion on GitHub
- Check existing documentation

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
