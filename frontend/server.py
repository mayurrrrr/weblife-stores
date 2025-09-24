#!/usr/bin/env python3
"""
Simple HTTP server for the frontend on port 3000.
This serves the static files independently from the backend.
"""

import http.server
import socketserver
import os
from pathlib import Path

# Change to the static directory
static_dir = Path(__file__).parent / "static"
os.chdir(static_dir)

PORT = 3001

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        # Add CORS headers to allow API calls to localhost:8000
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()
    
    def do_OPTIONS(self):
        # Handle preflight requests
        self.send_response(200)
        self.end_headers()

def run_server():
    """Start the frontend server on port 3000."""
    
    print("🎯 Starting Frontend Server")
    print("=" * 40)
    print(f"📁 Serving from: {static_dir}")
    print(f"🌐 Frontend URL: http://localhost:{PORT}")
    print(f"🔗 Backend API: http://localhost:8000/api/v1")
    print("=" * 40)
    print("Press Ctrl+C to stop the server\n")
    
    try:
        with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
            print(f"✅ Frontend server running at http://localhost:{PORT}")
            print("📱 Open this URL in your browser")
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 Frontend server stopped")
    except OSError as e:
        if "Address already in use" in str(e):
            print(f"❌ Port {PORT} is already in use!")
            print("Try a different port or close the application using port 3000")
        else:
            print(f"❌ Error starting server: {e}")

if __name__ == "__main__":
    run_server()
