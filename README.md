# Tunnel AI

Tunnel AI transforms natural language instructions into executable frontend tests using LangGraph, OpenAI, and Browserbase.

## Features

- **Natural Language Processing**: Convert plain English test instructions into automated tests
- **Multi-Agent Architecture**: Specialized AI agents for planning, generation, execution, validation, and self-healing
- **Self-Healing Tests**: Automatically fix broken tests when selectors change
- **Cloud Browser Infrastructure**: Scalable test execution using Browserbase
- **Comprehensive Test Reports**: Detailed results with screenshots and recordings

## Architecture

The system uses a multi-agent workflow orchestrated by LangGraph:

1. **Test Planning Agent**: Analyzes natural language and creates structured test plans
2. **Test Generation Agent**: Converts plans into executable Playwright code
3. **Test Execution Agent**: Runs tests on Browserbase infrastructure
4. **Validation Agent**: Analyzes results and provides insights
5. **Self-Healing Agent**: Automatically repairs failing tests

## Installation

### 1. Clone the repository

```bash
git clone <repository-url>
cd tunnel-ai
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your API keys
```

### 4. Install Playwright browsers

```bash
playwright install
```

## Configuration

Create a `.env` file with the following:

```env
# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-4-turbo-preview

# Browserbase Configuration
BROWSERBASE_API_KEY=your_browserbase_api_key_here
BROWSERBASE_PROJECT_ID=your_project_id_here

# Application Settings
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=True
LOG_LEVEL=INFO
```

## Usage

### Starting the API Server

```bash
python -m api.main
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Run Test (Asynchronous)

```bash
curl -X POST "http://localhost:8000/test/run" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Test the login page with valid credentials",
    "url": "https://example.com",
    "browser": "chromium",
    "headless": true
  }'
```

### Run Test (Synchronous)

```bash
curl -X POST "http://localhost:8000/test/run-sync" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Test the search functionality",
    "url": "https://example.com"
  }'
```

### Create Test Plan

```bash
curl -X POST "http://localhost:8000/test/plan" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Test checkout process",
    "url": "https://shop.example.com"
  }'
```

### Generate Test Code

```bash
curl -X POST "http://localhost:8000/test/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "Test form validation",
    "url": "https://example.com/register"
  }'
```

## Example Test Instructions

### Simple Examples

- "Test the login page"
- "Verify the search functionality works"
- "Check if the shopping cart updates correctly"
- "Test the contact form submission"

### Detailed Examples

- "Test the login page by entering invalid credentials and verify error messages appear"
- "Test the checkout process by adding items to cart and completing purchase"
- "Verify that the password reset flow sends an email and allows setting a new password"

## Project Structure

```plaintext
tunnel-ai/
├── agents/                      # AI agents for different tasks
│   ├── __init__.py
│   ├── planner.py              # Test planning agent
│   ├── generator.py            # Code generation agent
│   ├── executor.py             # Test execution agent
│   ├── validator.py            # Result validation agent
│   └── healer.py               # Self-healing agent
├── orchestrator/                # Workflow orchestration
│   ├── __init__.py
│   └── test_workflow.py        # LangGraph workflow definition
├── core/                        # Core types and utilities
│   ├── types.py                # Data models
│   └── browserbase_client.py   # Browserbase integration
├── api/                         # FastAPI application
│   ├── __init__.py
│   └── main.py                 # API endpoints
├── templates/                   # Test templates
│   ├── playwright_templates.py
│   └── test_examples.json
├── config/                      # Configuration
│   └── settings.py             # Application settings
├── requirements.txt            # Python dependencies
├── pyproject.toml              # Project configuration
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-container setup
└── README.md                   # This file
```

## API Documentation

When the server is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black .
isort .
```

### Type Checking

```bash
mypy .
```

## Advanced Features

### Self-Healing Tests

The system automatically attempts to fix broken tests by:

- Identifying selector issues and suggesting alternatives
- Adding appropriate wait conditions
- Adjusting timeout values
- Using fallback selector strategies

### Test Data Management

Tests can include dynamic data:

```json
{
  "instruction": "Test login with credentials",
  "url": "https://example.com",
  "test_data": {
    "username": "testuser",
    "password": "testpass123"
  }
}
```

### Browser Configuration

Supports multiple browsers and configurations:

- Chromium, Firefox, WebKit
- Custom viewport sizes
- Headless/headful modes
- Proxy configuration

## Troubleshooting

### Common Issues

1. **Timeout Errors**: Increase `TEST_TIMEOUT` in environment variables
2. **Selector Failures**: The self-healing agent will automatically attempt fixes
3. **API Key Issues**: Verify your OpenAI and Browserbase keys are correct

### Logging

Logs are stored in `logs/tunnel_ai.log` with rotation at 500MB.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

For issues and questions:

- Create an issue on GitHub
- Check the documentation at `/docs`
- Review API documentation at `/docs` endpoint
