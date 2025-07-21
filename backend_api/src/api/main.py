"""
Jira Dashboard Pro Backend API
FastAPI application for secure Jira REST API integration
"""

import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
import io
import csv
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.httpsredirect import HTTPSRedirectMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr, Field

from .config import settings
from .auth import session_manager
from .jira_client import create_jira_client

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Models
class JiraCredentials(BaseModel):
    """Model for Jira authentication credentials"""
    email: EmailStr = Field(..., description="Jira account email")
    api_token: str = Field(..., description="Jira API token")
    domain: str = Field(..., description="Jira domain (e.g., yourcompany.atlassian.net)")

class LoginRequest(BaseModel):
    """Model for login request"""
    credentials: JiraCredentials

class LoginResponse(BaseModel):
    """Model for login response"""
    success: bool = Field(..., description="Whether login was successful")
    session_token: str = Field(..., description="Session token for authenticated requests")
    message: str = Field(..., description="Response message")

class Project(BaseModel):
    """Model for Jira project"""
    id: str = Field(..., description="Project ID")
    key: str = Field(..., description="Project key")
    name: str = Field(..., description="Project name")
    description: Optional[str] = Field(None, description="Project description")
    project_type_key: str = Field(..., description="Project type")
    lead: Optional[Dict[str, Any]] = Field(None, description="Project lead information")
    avatar_urls: Optional[Dict[str, str]] = Field(None, description="Project avatar URLs")
    url: Optional[str] = Field(None, description="Project URL")

class ProjectDetail(Project):
    """Extended model for detailed project information"""
    components: Optional[List[Dict[str, Any]]] = Field(None, description="Project components")
    versions: Optional[List[Dict[str, Any]]] = Field(None, description="Project versions")
    issue_types: Optional[List[Dict[str, Any]]] = Field(None, description="Available issue types")
    roles: Optional[Dict[str, Any]] = Field(None, description="Project roles")

class IssueStatistics(BaseModel):
    """Model for issue statistics"""
    total_issues: int = Field(..., description="Total number of issues")
    open_issues: int = Field(..., description="Number of open issues")
    in_progress_issues: int = Field(..., description="Number of in-progress issues")
    resolved_issues: int = Field(..., description="Number of resolved issues")
    closed_issues: int = Field(..., description="Number of closed issues")
    by_priority: Dict[str, int] = Field(..., description="Issues grouped by priority")
    by_type: Dict[str, int] = Field(..., description="Issues grouped by type")

class SessionInfo(BaseModel):
    """Model for session information"""
    authenticated: bool = Field(..., description="Whether user is authenticated")
    user_email: Optional[str] = Field(None, description="Authenticated user email")
    domain: Optional[str] = Field(None, description="Jira domain")
    expires_at: Optional[datetime] = Field(None, description="Session expiration time")

# Security
security = HTTPBearer(auto_error=False)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler"""
    logger.info("Starting Jira Dashboard Pro API")
    yield
    logger.info("Shutting down Jira Dashboard Pro API")

# FastAPI app with metadata
app = FastAPI(
    title="Jira Dashboard Pro API",
    description="Secure API for Jira project management and analytics",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
    openapi_tags=[
        {"name": "health", "description": "Health check endpoints"},
        {"name": "auth", "description": "Authentication operations"},
        {"name": "projects", "description": "Project management operations"},
        {"name": "statistics", "description": "Analytics and statistics"},
        {"name": "export", "description": "Data export operations"},
        {"name": "session", "description": "Session management operations"},
    ]
)

# Middleware configuration
if settings.is_production:
    app.add_middleware(HTTPSRedirectMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Dependencies
async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """Dependency to get current authenticated session"""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    session_data = session_manager.validate_session(credentials.credentials)
    if not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    return session_data

# Routes

# PUBLIC_INTERFACE
@app.get("/", tags=["health"])
async def health_check():
    """
    Health check endpoint
    
    Returns the API status and basic information.
    """
    return {
        "status": "healthy",
        "service": "Jira Dashboard Pro API",
        "version": "1.0.0",
        "timestamp": datetime.now().isoformat()
    }

# PUBLIC_INTERFACE
@app.post("/api/auth/login", response_model=LoginResponse, tags=["auth"])
async def login(request: LoginRequest):
    """
    Authenticate with Jira credentials
    
    Validates the provided Jira credentials and creates a session token.
    
    Args:
        request: Login request containing Jira credentials
        
    Returns:
        LoginResponse: Contains session token and authentication status
        
    Raises:
        HTTPException: If authentication fails
    """
    try:
        # Create temporary Jira client to test credentials
        jira_client = create_jira_client({
            "domain": request.credentials.domain,
            "email": request.credentials.email,
            "api_token": request.credentials.api_token
        })
        
        # Test connection
        await jira_client.test_connection()
        
        # Create session
        session_token = session_manager.create_session(
            email=request.credentials.email,
            api_token=request.credentials.api_token,
            domain=request.credentials.domain,
            timeout_hours=settings.session_timeout_hours
        )
        
        logger.info(f"User {request.credentials.email} authenticated successfully")
        
        return LoginResponse(
            success=True,
            session_token=session_token,
            message="Authentication successful"
        )
    
    except HTTPException:
        # Re-raise HTTP exceptions from Jira client
        raise
    except Exception as e:
        logger.error(f"Unexpected error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication failed due to an unexpected error"
        )

# PUBLIC_INTERFACE
@app.post("/api/auth/logout", tags=["auth"])
async def logout(session: Dict[str, Any] = Depends(get_current_session)):
    """
    Logout and invalidate session
    
    Removes the current session token from active sessions.
    
    Returns:
        dict: Logout confirmation message
    """
    # Remove all sessions for this user
    session_manager.remove_user_sessions(session["email"])
    
    logger.info(f"User {session['email']} logged out")
    
    return {"message": "Logged out successfully"}

# PUBLIC_INTERFACE
@app.get("/api/session", response_model=SessionInfo, tags=["session"])
async def get_session_info(session: Dict[str, Any] = Depends(get_current_session)):
    """
    Get current session information
    
    Returns information about the current authenticated session.
    
    Returns:
        SessionInfo: Current session details
    """
    return SessionInfo(
        authenticated=True,
        user_email=session["email"],
        domain=session["domain"],
        expires_at=session["expires_at"]
    )

# PUBLIC_INTERFACE
@app.get("/api/projects", response_model=List[Project], tags=["projects"])
async def get_projects(
    search: Optional[str] = None,
    project_type: Optional[str] = None,
    expand: Optional[str] = None,
    session: Dict[str, Any] = Depends(get_current_session)
):
    """
    Get list of Jira projects
    
    Retrieves projects from Jira with optional filtering and expansion.
    
    Args:
        search: Search term for project name or key
        project_type: Filter by project type
        expand: Comma-separated list of fields to expand
        
    Returns:
        List[Project]: List of accessible projects
    """
    jira_client = create_jira_client(session)
    projects_data = await jira_client.get_projects(expand=expand)
    
    # Apply client-side filtering if needed
    filtered_projects = projects_data
    
    if search:
        search_lower = search.lower()
        filtered_projects = [
            p for p in filtered_projects
            if search_lower in p.get("name", "").lower() or 
               search_lower in p.get("key", "").lower()
        ]
    
    if project_type:
        filtered_projects = [
            p for p in filtered_projects
            if p.get("projectTypeKey") == project_type
        ]
    
    # Convert to Project models
    projects = []
    for project_data in filtered_projects:
        project = Project(
            id=project_data["id"],
            key=project_data["key"],
            name=project_data["name"],
            description=project_data.get("description"),
            project_type_key=project_data.get("projectTypeKey", "unknown"),
            lead=project_data.get("lead"),
            avatar_urls=project_data.get("avatarUrls"),
            url=project_data.get("self")
        )
        projects.append(project)
    
    return projects

# PUBLIC_INTERFACE
@app.get("/api/projects/{project_key}", response_model=ProjectDetail, tags=["projects"])
async def get_project_details(
    project_key: str,
    session: Dict[str, Any] = Depends(get_current_session)
):
    """
    Get detailed information for a specific project
    
    Retrieves comprehensive project information including components, versions, and issue types.
    
    Args:
        project_key: The project key (e.g., 'PROJ')
        
    Returns:
        ProjectDetail: Detailed project information
    """
    jira_client = create_jira_client(session)
    
    # Get basic project info
    project_data = await jira_client.get_project(
        project_key, 
        expand="description,lead,issueTypes,url,projectKeys,permissions,insight"
    )
    
    # Get additional details
    components = await jira_client.get_project_components(project_key)
    versions = await jira_client.get_project_versions(project_key)
    roles = await jira_client.get_project_roles(project_key)
    
    return ProjectDetail(
        id=project_data["id"],
        key=project_data["key"],
        name=project_data["name"],
        description=project_data.get("description"),
        project_type_key=project_data.get("projectTypeKey", "unknown"),
        lead=project_data.get("lead"),
        avatar_urls=project_data.get("avatarUrls"),
        url=project_data.get("self"),
        components=components,
        versions=versions,
        issue_types=project_data.get("issueTypes", []),
        roles=roles
    )

# PUBLIC_INTERFACE
@app.get("/api/projects/{project_key}/statistics", response_model=IssueStatistics, tags=["statistics"])
async def get_project_statistics(
    project_key: str,
    session: Dict[str, Any] = Depends(get_current_session)
):
    """
    Get issue statistics for a project
    
    Retrieves comprehensive statistics about issues in the specified project.
    
    Args:
        project_key: The project key (e.g., 'PROJ')
        
    Returns:
        IssueStatistics: Issue statistics and breakdowns
    """
    jira_client = create_jira_client(session)
    
    # Search for issues in the project
    jql = f"project = {project_key}"
    search_results = await jira_client.search_issues(
        jql=jql,
        fields="status,priority,issuetype",
        max_results=1000
    )
    
    issues = search_results.get("issues", [])
    total_issues = len(issues)
    
    # Initialize counters
    status_counts = {"Open": 0, "In Progress": 0, "Resolved": 0, "Closed": 0}
    priority_counts = {}
    type_counts = {}
    
    # Process issues
    for issue in issues:
        fields = issue.get("fields", {})
        
        # Status categorization
        status = fields.get("status", {})
        status_name = status.get("name", "Unknown")
        status_category = status.get("statusCategory", {}).get("name", "Unknown")
        
        if status_category == "To Do":
            status_counts["Open"] += 1
        elif status_category == "In Progress":
            status_counts["In Progress"] += 1
        elif status_category == "Done":
            if "resolved" in status_name.lower():
                status_counts["Resolved"] += 1
            else:
                status_counts["Closed"] += 1
        else:
            status_counts["Open"] += 1  # Default fallback
        
        # Priority breakdown
        priority = fields.get("priority", {})
        priority_name = priority.get("name", "Unknown")
        priority_counts[priority_name] = priority_counts.get(priority_name, 0) + 1
        
        # Issue type breakdown
        issue_type = fields.get("issuetype", {})
        type_name = issue_type.get("name", "Unknown")
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
    
    return IssueStatistics(
        total_issues=total_issues,
        open_issues=status_counts["Open"],
        in_progress_issues=status_counts["In Progress"],
        resolved_issues=status_counts["Resolved"],
        closed_issues=status_counts["Closed"],
        by_priority=priority_counts,
        by_type=type_counts
    )

# PUBLIC_INTERFACE
@app.get("/api/projects/{project_key}/export", tags=["export"])
async def export_project_data(
    project_key: str,
    format: str = "csv",
    session: Dict[str, Any] = Depends(get_current_session)
):
    """
    Export project data
    
    Exports project issues and statistics in the specified format.
    
    Args:
        project_key: The project key (e.g., 'PROJ')
        format: Export format (currently only 'csv' supported)
        
    Returns:
        StreamingResponse: File download response
    """
    if format.lower() != "csv":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only CSV format is currently supported"
        )
    
    jira_client = create_jira_client(session)
    
    # Get project issues
    jql = f"project = {project_key}"
    search_results = await jira_client.search_issues(
        jql=jql,
        fields="summary,status,priority,issuetype,assignee,created,updated,resolution",
        max_results=1000
    )
    issues = search_results.get("issues", [])
    
    # Create CSV content
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        "Key", "Summary", "Issue Type", "Status", "Priority", 
        "Assignee", "Created", "Updated", "Resolution"
    ])
    
    # Write data
    for issue in issues:
        fields = issue.get("fields", {})
        assignee = fields.get("assignee", {})
        assignee_name = assignee.get("displayName", "") if assignee else ""
        
        resolution = fields.get("resolution", {})
        resolution_name = resolution.get("name", "") if resolution else ""
        
        writer.writerow([
            issue.get("key", ""),
            fields.get("summary", ""),
            fields.get("issuetype", {}).get("name", ""),
            fields.get("status", {}).get("name", ""),
            fields.get("priority", {}).get("name", ""),
            assignee_name,
            fields.get("created", ""),
            fields.get("updated", ""),
            resolution_name
        ])
    
    # Prepare response
    output.seek(0)
    content = output.getvalue()
    output.close()
    
    filename = f"{project_key}_issues_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        io.BytesIO(content.encode()),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging"""
    logger.error(f"HTTP {exc.status_code}: {exc.detail} - Path: {request.url.path}")
    return {"error": exc.detail, "status_code": exc.status_code}

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {str(exc)} - Path: {request.url.path}")
    return {"error": "Internal server error", "status_code": 500}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_production
    )
