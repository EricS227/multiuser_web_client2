#!/usr/bin/env python3
"""
Railway-compatible startup script for FastAPI application
"""
import os
import sys
import uvicorn

def main():
    """Main startup function"""
    try:
        print("=== Railway FastAPI Startup ===")
        print(f"Python version: {sys.version}")
        print(f"Current working directory: {os.getcwd()}")
        
        # Get port from environment (Railway/Docker sets this)
        port = int(os.environ.get("PORT", 8000))
        host = os.environ.get("HOST", "0.0.0.0")
        
        print(f"Starting server on {host}:{port}")
        print(f"PORT env var: {os.environ.get('PORT', 'not set')}")
        print(f"Available environment variables: {[k for k in os.environ.keys() if 'PORT' in k.upper()]}")
        
        # Import here to ensure all modules are loaded properly
        from backend.main import app
        
        print("FastAPI app imported successfully")
        print("Starting uvicorn server...")
        
        # Run the server
        uvicorn.run(
            app, 
            host=host, 
            port=port,
            access_log=True,
            log_level="info"
        )
        
    except Exception as e:
        print(f"ERROR: Failed to start application: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()