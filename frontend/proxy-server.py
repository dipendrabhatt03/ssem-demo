#!/usr/bin/env python3
"""
Simple HTTP server with proxy support for API requests
Serves static files and proxies /api/* requests to the backend
"""
import http.server
import socketserver
import urllib.request
import os

BACKEND_URL = os.getenv('BACKEND_URL', 'http://backend:8000')
PORT = 3000

class ProxyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith('/api/'):
            # Proxy API requests to backend
            backend_path = self.path.replace('/api', '', 1)
            self.proxy_request('GET', backend_path)
        else:
            # Serve static files
            super().do_GET()

    def do_POST(self):
        if self.path.startswith('/api/'):
            backend_path = self.path.replace('/api', '', 1)
            self.proxy_request('POST', backend_path)
        else:
            self.send_error(404)

    def do_PUT(self):
        if self.path.startswith('/api/'):
            backend_path = self.path.replace('/api', '', 1)
            self.proxy_request('PUT', backend_path)
        else:
            self.send_error(404)

    def do_DELETE(self):
        if self.path.startswith('/api/'):
            backend_path = self.path.replace('/api', '', 1)
            self.proxy_request('DELETE', backend_path)
        else:
            self.send_error(404)

    def proxy_request(self, method, path):
        url = f'{BACKEND_URL}{path}'

        # Read request body if present
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length) if content_length > 0 else None

        # Create request
        headers = {'Content-Type': 'application/json'} if body else {}
        req = urllib.request.Request(url, data=body, headers=headers, method=method)

        try:
            # Forward request to backend
            with urllib.request.urlopen(req) as response:
                # Send response back to client
                self.send_response(response.status)
                self.send_header('Content-Type', response.headers.get('Content-Type', 'application/json'))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(response.read())
        except urllib.error.HTTPError as e:
            # Forward error response
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(e.read())
        except Exception as e:
            # Internal error
            self.send_error(500, f'Proxy error: {str(e)}')

if __name__ == '__main__':
    os.chdir('frontend')
    with socketserver.TCPServer(('', PORT), ProxyHTTPRequestHandler) as httpd:
        print(f'Serving on port {PORT}, proxying /api/* to {BACKEND_URL}')
        httpd.serve_forever()
