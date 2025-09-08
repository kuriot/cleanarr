# Contributing to Cleanarr

Thank you for your interest in contributing to Cleanarr! This document provides guidelines and information for contributors.

## 🚀 Getting Started

### Prerequisites

- Python 3.8 or higher
- Git
- Access to test instances of Jellyfin, Radarr, Sonarr (optional but recommended)

### Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/maateen/cleanarr.git
   cd cleanarr
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install flake8  # For linting
   ```

3. **Configure for Testing**
   ```bash
   # Run once to create config file
   python run.py --help
   # Edit ~/.config/cleanarr/config.cfg with your test server details
   ```

## 🐛 Bug Reports

When reporting bugs, please include:

- **Cleanarr version** or commit hash
- **Python version** (`python --version`)
- **Operating system** and version
- **Complete error message** and stack trace
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Configuration details** (with sensitive info redacted)

### Log Files

Always include relevant log entries:
```bash
# Enable debug logging
python run.py --log-level DEBUG

# Check log file
tail -f ~/.config/cleanarr/cleanarr.log
```

## 💡 Feature Requests

For feature requests, please describe:
- **Use case** - What problem does this solve?
- **Proposed solution** - How should it work?
- **Alternatives considered** - What other approaches did you think about?
- **Breaking changes** - Would this affect existing functionality?

## 🔧 Development Guidelines

### Code Style

- **PEP 8** compliance (use `flake8` for linting)
- **Type hints** for function parameters and return values
- **Docstrings** for all public functions and classes
- **Clear variable names** and comments for complex logic

### Project Structure

```
cleanarr/
├── core/           # Core application logic
│   └── cli.py      # Command-line interface
├── services/       # External service integrations
│   ├── jellyfin.py
│   ├── radarr.py
│   ├── sonarr.py
│   ├── qbittorrent.py
│   └── cleanup.py
├── utils/          # Utility modules
│   ├── config.py
│   └── logger.py
└── run.py          # Main entry point
```

### Logging

Use the centralized logging system:

```python
from utils import logger

# Different log levels
logger.info("User-facing information")
logger.error("Error messages")
logger.api_debug("Service", "API debugging info")
logger.config_info("Configuration details")
```

### API Clients

When adding or modifying service integrations:

- **Error handling** - Always use try/except for API calls
- **Connection testing** - Implement `test_connection()` method
- **Pagination** - Handle paginated API responses
- **Rate limiting** - Be respectful of API rate limits
- **Authentication** - Support both API keys and Basic Auth where applicable

## 🧪 Testing

### Running Tests

```bash
# Run all tests
python -m pytest

# Run with coverage
python -m pytest --cov=. --cov-report=html

# Test specific functionality
python run.py --dry-run  # Test dry-run mode
```

### Writing Tests

- **Mock external APIs** using `requests-mock`
- **Test both success and failure cases**
- **Include edge cases** (empty responses, network errors)
- **Test configuration handling**

Example test structure:
```python
import pytest
import requests_mock
from services.jellyfin import JellyfinClient

def test_jellyfin_connection():
    with requests_mock.Mocker() as m:
        m.get('/System/Info', json={'Version': '10.8.0'})
        client = JellyfinClient('http://test', 'api_key')
        assert client.test_connection() == True
```

## 📝 Pull Request Process

### Before Submitting

1. **Run tests** and ensure they pass
2. **Run linting** with `flake8`
3. **Test manually** with your changes
4. **Update documentation** if needed
5. **Check for breaking changes**

### PR Guidelines

- **Clear title** describing the change
- **Detailed description** explaining what and why
- **Link related issues** using "Fixes #123" or "Closes #123"
- **Test instructions** for reviewers
- **Screenshots** for UI changes (if applicable)

### Commit Messages

Use conventional commit format:
```
feat: add support for Prowlarr integration
fix: handle empty API responses gracefully
docs: update configuration examples
refactor: simplify matching algorithm
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`

## 🛡️ Security

### Reporting Security Issues

**Do not** open public issues for security vulnerabilities. Instead:
- Email security concerns to [maintainer email]
- Provide detailed reproduction steps
- Allow time for fixes before public disclosure

### Security Guidelines

- **Never log sensitive data** (API keys, passwords)
- **Validate user input** properly
- **Use secure defaults** in configuration
- **Handle authentication securely**

## 📚 Documentation

### Code Documentation

- **Docstrings** for all public APIs
- **Type hints** for better IDE support
- **Inline comments** for complex logic
- **README updates** for new features

### API Documentation

When adding new service integrations, document:
- **Required permissions** for API keys
- **Supported versions** of the service
- **Configuration options**
- **Limitations** or known issues

## 🎯 Contribution Ideas

Good first contributions:
- **Documentation improvements**
- **Test coverage** for existing code
- **Error message clarity**
- **Configuration validation**
- **New service integrations**

Advanced contributions:
- **Performance optimizations**
- **Advanced matching algorithms**
- **Bulk operations**
- **Web interface**
- **Plugin system**

## 📋 Release Process

For maintainers:

1. **Update version** in relevant files
2. **Update CHANGELOG.md**
3. **Create release tag**: `git tag v1.0.0`
4. **Push tag**: `git push origin v1.0.0`
5. **GitHub Actions** will create the release

## 💬 Community

- **GitHub Discussions** for questions and ideas
- **Issues** for bugs and feature requests
- **Be respectful** and constructive
- **Help newcomers** get started

## 📄 License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**Thank you for contributing to Cleanarr!** 🧹✨
