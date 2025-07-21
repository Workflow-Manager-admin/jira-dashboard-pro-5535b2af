#!/usr/bin/env python3
"""
Health check script for Jira Dashboard Pro API
Can be used for monitoring, load balancers, or deployment verification
"""

import sys
import requests
import json
from typing import Dict, Any

def check_health(base_url: str = "http://localhost:8000") -> Dict[str, Any]:
    """
    Check the health of the API
    
    Args:
        base_url: Base URL of the API
        
    Returns:
        Dict: Health check results
    """
    result = {
        "healthy": False,
        "status_code": None,
        "response_time": None,
        "api_info": None,
        "error": None
    }
    
    try:
        import time
        start_time = time.time()
        
        response = requests.get(f"{base_url}/", timeout=10)
        
        result["response_time"] = round((time.time() - start_time) * 1000, 2)  # ms
        result["status_code"] = response.status_code
        
        if response.status_code == 200:
            result["healthy"] = True
            result["api_info"] = response.json()
        else:
            result["error"] = f"HTTP {response.status_code}: {response.text}"
            
    except requests.exceptions.ConnectionError:
        result["error"] = "Connection refused - API may not be running"
    except requests.exceptions.Timeout:
        result["error"] = "Request timeout - API may be overloaded"
    except requests.exceptions.RequestException as e:
        result["error"] = f"Request error: {str(e)}"
    except Exception as e:
        result["error"] = f"Unexpected error: {str(e)}"
    
    return result

def main():
    """Main health check function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Health check for Jira Dashboard Pro API")
    parser.add_argument("--url", default="http://localhost:8000", 
                       help="Base URL of the API (default: http://localhost:8000)")
    parser.add_argument("--json", action="store_true", 
                       help="Output results in JSON format")
    parser.add_argument("--quiet", action="store_true", 
                       help="Suppress output (use exit code only)")
    
    args = parser.parse_args()
    
    result = check_health(args.url)
    
    if not args.quiet:
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print(f"Health Check Results for {args.url}")
            print("-" * 50)
            print(f"Status: {'✅ HEALTHY' if result['healthy'] else '❌ UNHEALTHY'}")
            print(f"HTTP Status: {result['status_code']}")
            print(f"Response Time: {result['response_time']}ms")
            
            if result['api_info']:
                print(f"Service: {result['api_info'].get('service', 'Unknown')}")
                print(f"Version: {result['api_info'].get('version', 'Unknown')}")
            
            if result['error']:
                print(f"Error: {result['error']}")
    
    # Exit with appropriate code
    sys.exit(0 if result['healthy'] else 1)

if __name__ == "__main__":
    main()
