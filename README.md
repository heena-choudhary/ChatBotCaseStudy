# Chat Test Framework

## Overview
This framework is designed for automated testing of chat applications using Playwright and Python. It includes comprehensive test suites for chat functionality, security testing, and widget testing. The framework supports both English and Arabic languages, with features for cross-language consistency validation.

## Prerequisites

- Python 3.8 or higher
- Node.js 14 or higher (for Playwright)
- Git

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install Python dependencies:
```bash
pip install -r requirements.txt
```

4. Install Playwright browsers:
```bash
playwright install
```

## Configuration

1. Update the configuration in `config/config.json`:
```json
{
    "base_url": "your-application-url",
    "auth": {
        "email": "your-email",
        "password": "your-password"
    },
    "viewport_sizes": {
        "desktop": {"width": 1280, "height": 800},
        "mobile": {"width": 375, "height": 667}
    },
    "languages": {
        "en": {"direction": "ltr", "test_data": "data/test-data-en.json"},
        "ar": {"direction": "rtl", "test_data": "data/test-data-ar.json"}
    },
    "timeouts": {
        "page_load": 10000,
        "element_wait": 5000,
        "response_wait": 10000
    }
}
```

## Running Tests

### Running All Tests
```bash
pytest
```

### Running Specific Test Suites

1. Security Tests with HTML Report:
```bash
# Create reports directory if it doesn't exist
mkdir -p reports

# Run security tests with HTML report
python3 -m pytest tests/test_security.py -v --html=reports/security_test_report.html --self-contained-html
```

2. Chat Widget Tests with HTML Report:
```bash
# Run chat widget tests with HTML report
python3 -m pytest tests/test_chat_widget.py -v --html=reports/chat_widget_test_report.html --self-contained-html
```

### Test Options

1. Viewport Selection:
```bash
# Run tests for desktop viewport
pytest -m desktop

# Run tests for mobile viewport
pytest -m mobile
```

2. Language Selection:
```bash
# Run tests in English (default)
pytest --language=en

# Run tests in Arabic
pytest --language=ar
```

3. Parallel Execution:
```bash
# Run tests in parallel
pytest -n auto
```

## Test Reports and Artifacts

After running tests, you can find the following in the `reports` directory:
- `reports/security_test_report.html` - Security test results
- `reports/chat_widget_test_report.html` - Chat widget test results
- `reports/screenshots/` - Test failure screenshots
- `reports/videos/` - Test execution videos (if enabled)

## Project Structure

```
├── config/             # Configuration files
│   └── config.json    # Main configuration
├── data/              # Test data files
│   └── test-data.json # Test cases and validation criteria
├── pages/             # Page Object Models
│   ├── base_page.py   # Base page class
│   └── chat_page.py   # Chat page implementation
├── reports/           # Test reports and artifacts
│   ├── screenshots/   # Failure screenshots
│   └── videos/        # Test execution videos
├── tests/             # Test files
│   ├── test_security.py    # Security test suite
│   ├── test_chat_widget.py # Chat widget test suite
│   └── conftest.py         # Test configuration
├── utils/             # Utility functions
│   ├── response_validator_deepseek.py # Response validation
│   ├── response_storage.py           # Response storage
│   └── retry.py                      # Retry mechanism
├── requirements.txt   # Python dependencies
├── pytest.ini        # Pytest configuration
└── README.md         # This file
```

## Features

- Cross-browser testing with Playwright
- Responsive testing (desktop and mobile viewports)
- Multi-language support (English and Arabic)
- Cross-language consistency validation
- Security testing suite
- Chat widget testing
- HTML test reports with detailed logs
- Screenshot capture on test failures
- Video recording of test execution
- Retry mechanism for flaky tests
- API response validation
- Response caching
- Rate limit handling

## Response Validation

The framework includes comprehensive response validation:
- Clarity scoring
- Hallucination detection
- Formatting validation
- Completeness checking
- Language-specific requirements
- Cross-language consistency

## Troubleshooting

1. Browser Installation Issues:
```bash
playwright install --force
```

2. SSL Certificate Errors:
```bash
# Add --ignore-ssl-errors flag
pytest --ignore-ssl-errors
```

3. Rate Limiting Issues:
```bash
# Add delay between tests
pytest --delay=10
```

4. Timeout Issues:
Adjust timeouts in `config/config.json`:
```json
"timeouts": {
    "page_load": 10000,
    "element_wait": 5000,
    "response_wait": 10000
}
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
