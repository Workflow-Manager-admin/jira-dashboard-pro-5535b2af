"""
Jira REST API client
Handles all communication with Jira Cloud REST API
"""

import base64
import logging
from typing import Dict, Any, Optional, List
import httpx
from fastapi import HTTPException, status

logger = logging.getLogger(__name__)

class JiraAPIClient:
    """Client for interacting with Jira Cloud REST API"""
    
    def __init__(self, domain: str, email: str, api_token: str):
        """
        Initialize Jira API client
        
        Args:
            domain: Jira domain (e.g., yourcompany.atlassian.net)
            email: User's email address
            api_token: Jira API token
        """
        self.domain = domain.replace("https://", "").replace("http://", "")
        self.email = email
        self.api_token = api_token
        self.base_url = f"https://{self.domain}/rest/api/3"
        
        # Create auth header
        auth_string = f"{email}:{api_token}"
        auth_bytes = auth_string.encode('ascii')
        auth_b64 = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Authorization": f"Basic {auth_b64}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
    
    async def _make_request(
        self, 
        endpoint: str, 
        method: str = "GET",
        params: Optional[Dict] = None,
        json_data: Optional[Dict] = None,
        timeout: float = 30.0
    ) -> Dict[str, Any]:
        """
        Make authenticated request to Jira API
        
        Args:
            endpoint: API endpoint (without base URL)
            method: HTTP method
            params: Query parameters
            json_data: JSON data for POST/PUT requests
            timeout: Request timeout in seconds
            
        Returns:
            Dict: API response data
            
        Raises:
            HTTPException: For various API errors
        """
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    headers=self.headers,
                    params=params,
                    json=json_data
                )
                
                # Handle different status codes
                if response.status_code == 401:
                    logger.error(f"Jira authentication failed for {self.email}")
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Jira authentication failed. Please check your credentials."
                    )
                elif response.status_code == 403:
                    logger.error(f"Access denied for {self.email} on endpoint {endpoint}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access denied. You don't have permission to access this resource."
                    )
                elif response.status_code == 404:
                    logger.error(f"Resource not found: {endpoint}")
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="The requested resource was not found."
                    )
                elif response.status_code >= 400:
                    logger.error(f"Jira API error {response.status_code}: {response.text}")
                    raise HTTPException(
                        status_code=response.status_code,
                        detail=f"Jira API error: {response.text}"
                    )
                
                return response.json()
                
            except httpx.TimeoutException:
                logger.error(f"Jira API request timed out: {endpoint}")
                raise HTTPException(
                    status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                    detail="Request to Jira API timed out. Please try again."
                )
            except httpx.RequestError as e:
                logger.error(f"Jira API request error: {e}")
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="Unable to connect to Jira API. Please check your internet connection."
                )
    
    async def test_connection(self) -> Dict[str, Any]:
        """
        Test the connection and credentials
        
        Returns:
            Dict: User information from Jira
        """
        return await self._make_request("myself")
    
    async def get_projects(self, expand: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Get all accessible projects
        
        Args:
            expand: Comma-separated list of fields to expand
            
        Returns:
            List[Dict]: List of projects
        """
        params = {}
        if expand:
            params["expand"] = expand
            
        return await self._make_request("project", params=params)
    
    async def get_project(self, project_key: str, expand: Optional[str] = None) -> Dict[str, Any]:
        """
        Get detailed project information
        
        Args:
            project_key: Project key (e.g., 'PROJ')
            expand: Comma-separated list of fields to expand
            
        Returns:
            Dict: Project information
        """
        params = {}
        if expand:
            params["expand"] = expand
            
        return await self._make_request(f"project/{project_key}", params=params)
    
    async def get_project_components(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get project components
        
        Args:
            project_key: Project key
            
        Returns:
            List[Dict]: Project components
        """
        try:
            return await self._make_request(f"project/{project_key}/components")
        except HTTPException as e:
            if e.status_code == 404:
                return []
            raise
    
    async def get_project_versions(self, project_key: str) -> List[Dict[str, Any]]:
        """
        Get project versions
        
        Args:
            project_key: Project key
            
        Returns:
            List[Dict]: Project versions
        """
        try:
            return await self._make_request(f"project/{project_key}/versions")
        except HTTPException as e:
            if e.status_code == 404:
                return []
            raise
    
    async def get_project_roles(self, project_key: str) -> Dict[str, Any]:
        """
        Get project roles
        
        Args:
            project_key: Project key
            
        Returns:
            Dict: Project roles
        """
        try:
            return await self._make_request(f"project/{project_key}/role")
        except HTTPException as e:
            if e.status_code == 404:
                return {}
            raise
    
    async def search_issues(
        self,
        jql: str,
        fields: Optional[str] = None,
        expand: Optional[str] = None,
        max_results: int = 50,
        start_at: int = 0
    ) -> Dict[str, Any]:
        """
        Search for issues using JQL
        
        Args:
            jql: JQL query string
            fields: Comma-separated list of fields to return
            expand: Comma-separated list of fields to expand
            max_results: Maximum number of results
            start_at: Starting index
            
        Returns:
            Dict: Search results
        """
        params = {
            "jql": jql,
            "maxResults": max_results,
            "startAt": start_at
        }
        
        if fields:
            params["fields"] = fields
        if expand:
            params["expand"] = expand
        
        return await self._make_request("search", params=params)
    
    async def get_issue_types(self) -> List[Dict[str, Any]]:
        """
        Get all available issue types
        
        Returns:
            List[Dict]: Issue types
        """
        return await self._make_request("issuetype")
    
    async def get_priorities(self) -> List[Dict[str, Any]]:
        """
        Get all available priorities
        
        Returns:
            List[Dict]: Priorities
        """
        return await self._make_request("priority")
    
    async def get_statuses(self) -> List[Dict[str, Any]]:
        """
        Get all available statuses
        
        Returns:
            List[Dict]: Statuses
        """
        return await self._make_request("status")

def create_jira_client(session_data: Dict[str, Any]) -> JiraAPIClient:
    """
    Create a Jira API client from session data
    
    Args:
        session_data: Session data containing credentials
        
    Returns:
        JiraAPIClient: Configured client instance
    """
    return JiraAPIClient(
        domain=session_data["domain"],
        email=session_data["email"],
        api_token=session_data["api_token"]
    )
