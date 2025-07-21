# Jira Dashboard Pro - Backend API

A secure FastAPI backend for the Jira Dashboard Pro application that provides RESTful APIs for Jira project management, authentication, and analytics.

## Features

- 🔐 **Secure Authentication**: JWT-based session management with Jira API token authentication
- 📊 **Project Management**: List, filter, and retrieve detailed project information
- 📈 **Analytics**: Comprehensive issue statistics and breakdowns
- 📤 **Data Export**: CSV export functionality for project data
- 🛡️ **Security**: HTTPS enforcement, CORS protection, input validation
- 📚 **API Documentation**: Auto-generated OpenAPI/Swagger documentation
- ⚡ **Performance**: Async/await support with httpx for optimal performance

## API Endpoints

### Authentication
- `POST /api/auth/login` - Authenticate with Jira credentials
- `POST /api/auth/logout` - Logout and invalidate session
- `GET /api/session` - Get current session information

### Projects
- `GET /api/projects` - List accessible projects with filtering
- `GET /api/projects/{project_key}` - Get detailed project information
- `GET /api/projects/{project_key}/statistics` - Get project issue statistics
- `GET /api/projects/{project_key}/export` - Export project data as CSV

### Health
- `GET /` - Health check endpoint

## Quick Start

### Prerequisites

- Python 3.8+
- Jira Cloud instance with API access
- Jira API token (generated from Atlassian account settings)

### Installation

1. Clone the repository and navigate to the backend directory:
```bash
cd jira-dashboard-pro-5535b2af/backend_api
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

4. Start the development server:
```bash
python start.py
```

The API will be available at `http://localhost:8000`

## Environment Configuration

Create a `.env` file with the following variables:

```env
# Application Settings
ENVIRONMENT=development
PORT=8000
DEBUG=True

# Security Settings
SECRET_KEY=your-secret-key-here
SESSION_TIMEOUT_HOURS=8

# CORS Settings (comma-separated origins)
ALLOWED_ORIGINS=http://localhost:3000,https://localhost:3000

# Logging
LOG_LEVEL=INFO
```

## Authentication Flow

1. **Login**: Send Jira credentials (email, API token, domain) to `/api/auth/login`
2. **Session**: Receive a session token for subsequent requests
3. **Authorization**: Include token in `Authorization: Bearer <token>` header
4. **Logout**: Call `/api/auth/logout` to invalidate the session

### Example Login Request

```json
POST /api/auth/login
{
  "credentials": {
    "email": "user@company.com",
    "api_token": "your-jira-api-token",
    "domain": "yourcompany.atlassian.net"
  }
}
```

### Example Response

```json
{
  "success": true,
  "session_token": "secure-session-token",
  "message": "Authentication successful"
}
```

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI Spec: `http://localhost:8000/openapi.json`

## Architecture

The backend follows a modular architecture:

```
src/api/
├── main.py           # FastAPI application and route definitions
├── config.py         # Configuration management with pydantic-settings
├── auth.py           # Session management and authentication utilities
├── jira_client.py    # Jira REST API client with error handling
└── generate_openapi.py # OpenAPI specification generation
```

### Key Components

- **Main Application** (`main.py`): FastAPI app with route definitions and middleware
- **Configuration** (`config.py`): Environment-based settings management
- **Authentication** (`auth.py`): Session management with in-memory storage
- **Jira Client** (`jira_client.py`): Async HTTP client for Jira API interactions

## Security Features

- **Session Management**: Secure token-based sessions with configurable timeout
- **Input Validation**: Pydantic models for request/response validation
- **CORS Protection**: Configurable CORS middleware
- **HTTPS Enforcement**: Automatic HTTPS redirect in production
- **Error Handling**: Comprehensive error handling with appropriate status codes
- **Credential Security**: Jira credentials never exposed to frontend

## Development

### Running Tests

```bash
pytest
```

### Code Quality

```bash
# Linting
flake8 src/

# Type checking (if mypy is installed)
mypy src/
```

### Generating OpenAPI Spec

```bash
python src/api/generate_openapi.py
```

## Production Deployment

1. Set environment variables:
```env
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=secure-random-key
ALLOWED_ORIGINS=https://yourdomain.com
```

2. Use a production WSGI server:
```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4
```

3. Configure reverse proxy (nginx) for SSL termination

## Troubleshooting

### Common Issues

1. **Import Errors**: Ensure all dependencies are installed: `pip install -r requirements.txt`
2. **Jira Connection**: Verify API token and domain are correct
3. **CORS Errors**: Check `ALLOWED_ORIGINS` environment variable
4. **Session Timeout**: Adjust `SESSION_TIMEOUT_HOURS` as needed

### Logging

The application logs to stdout with configurable log levels. Set `LOG_LEVEL=DEBUG` for detailed debugging information.

## API Usage Examples

### Get Projects
```bash
curl -H "Authorization: Bearer <session_token>" \
  "http://localhost:8000/api/projects?search=test&project_type=software"
```

### Get Project Statistics
```bash
curl -H "Authorization: Bearer <session_token>" \
  "http://localhost:8000/api/projects/PROJ/statistics"
```

### Export Project Data
```bash
curl -H "Authorization: Bearer <session_token>" \
  "http://localhost:8000/api/projects/PROJ/export?format=csv" \
  -o project_data.csv
```

## License

This project is part of the Jira Dashboard Pro application.
