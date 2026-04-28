import sys
import os
from pathlib import Path

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'insighta_backend.settings')

# Initialize Django
import django
django.setup()

from django.core.wsgi import get_wsgi_application
from django.http import JsonResponse
from django.urls import path
from django.urls import include, re_path
from django.conf import settings

# Create the WSGI application
application = get_wsgi_application()

# Also create an ASGI app for Vercel
app = application

# Health check endpoint
def health(request):
    return JsonResponse({
        "status": "healthy",
        "service": "Insighta Labs+ API",
        "version": "3.0.0"
    })

# Vercel requires a 'handler' function
async def handler(request, context):
    from urllib.parse import parse_qs
    import json
    
    # Determine the path
    path = request.get('path', '/')
    method = request.get('method', 'GET')
    headers = request.get('headers', {})
    body = request.get('body', '')
    
    # Create a WSGI environment
    environ = {
        'REQUEST_METHOD': method,
        'PATH_INFO': path,
        'QUERY_STRING': request.get('query', ''),
        'SERVER_NAME': 'vercel',
        'SERVER_PORT': '443',
        'SERVER_PROTOCOL': 'HTTP/1.1',
        'wsgi.version': (1, 0),
        'wsgi.url_scheme': 'https',
        'wsgi.input': body if isinstance(body, bytes) else body.encode(),
        'wsgi.errors': sys.stderr,
        'wsgi.multithread': False,
        'wsgi.multiprocess': True,
        'wsgi.run_once': True,
    }
    
    # Add headers
    for key, value in headers.items():
        environ[f'HTTP_{key.upper().replace("-", "_")}'] = value
    
    # Add content length
    if body:
        environ['CONTENT_LENGTH'] = str(len(body))
    
    # Call Django
    response_body = []
    response_status = '200 OK'
    response_headers = []
    
    def start_response(status, headers):
        nonlocal response_status, response_headers
        response_status = status
        response_headers = headers
    
    result = application(environ, start_response)
    
    # Collect response body
    for chunk in result:
        response_body.append(chunk)
    
    return {
        'statusCode': int(response_status.split()[0]),
        'headers': dict(response_headers),
        'body': ''.join([b.decode() if isinstance(b, bytes) else b for b in response_body])
    }