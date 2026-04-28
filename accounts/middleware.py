import re
from django.http import JsonResponse
from django.conf import settings
from .tokens import verify_access_token
from .models import User

# Public endpoints that don't require authentication
PUBLIC_PATHS = [
    r'^/$',                      
    r'^/health/?$',            
    r'^/auth/github',
    r'^/auth/refresh',
    r'^/admin/',
    r'^/static/',
]

# Role permissions
ADMIN_ONLY_PATHS = [
    r'^/api/profiles$',  # POST (create)
    r'^/api/profiles/\d+$',  # DELETE
]

class AuthenticationMiddleware:
    """Middleware to authenticate users via JWT token"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip authentication for public paths
        path = request.path
        for public_path in PUBLIC_PATHS:
            if re.match(public_path, path):
                return self.get_response(request)
        
        # Check for API version header (required for all /api/* endpoints)
        if path.startswith('/api/'):
            api_version = request.headers.get('X-API-Version')
            if not api_version:
                return JsonResponse({
                    'status': 'error',
                    'message': 'API version header required'
                }, status=400)
            if api_version != '1':
                return JsonResponse({
                    'status': 'error',
                    'message': 'Unsupported API version'
                }, status=400)
        
        # Get token from Authorization header or cookie
        token = None
        auth_header = request.headers.get('Authorization', '')
        if auth_header.startswith('Bearer '):
            token = auth_header.split(' ')[1]
        else:
            token = request.COOKIES.get('access_token')
        
        if not token:
            return JsonResponse({'status': 'error', 'message': 'Authentication required'}, status=401)
        
        # Verify token
        user_id, error = verify_access_token(token)
        if error:
            return JsonResponse({'status': 'error', 'message': error}, status=401)
        
        # Get user
        try:
            user = User.objects.get(id=user_id, is_active=True)
            request.user = user
            request.user_id = user_id
            request.user_role = user.role
        except User.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User not found'}, status=401)
        
        return self.get_response(request)


class RolePermissionMiddleware:
    """Middleware to enforce role-based permissions"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Skip if no user (handled by auth middleware)
        if not hasattr(request, 'user'):
            return self.get_response(request)
        
        path = request.method + ':' + request.path
        
        # Check admin-only paths
        if request.method in ['POST', 'DELETE']:
            if request.method == 'POST' and re.match(r'^/api/profiles$', request.path):
                if request.user_role != 'admin':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Admin access required'
                    }, status=403)
            
            if request.method == 'DELETE' and re.match(r'^/api/profiles/[^/]+/$', request.path):
                if request.user_role != 'admin':
                    return JsonResponse({
                        'status': 'error',
                        'message': 'Admin access required'
                    }, status=403)
        
        return self.get_response(request)