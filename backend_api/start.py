#!/usr/bin/env python3
"""
Startup script for Jira Dashboard Pro API
"""

import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

if __name__ == "__main__":
    import uvicorn
    from api.config import settings
    
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=settings.port,
        reload=not settings.is_production,
        log_level=settings.log_level.lower()
    )
