import time
from collections import defaultdict
from django.http import JsonResponse
from django.conf import settings

# Store request counts (use Redis in production)
request_counts = defaultdict(list)

def rate_limit(request, limit, window=60):
    """Check if request exceeds rate limit"""
    key = f"{request.user_id if hasattr(request, 'user_id') else request.META.get('REMOTE_ADDR')}"
    now = time.time()
    
    # Clean old requests
    request_counts[key] = [t for t in request_counts[key] if now - t < window]
    
    if len(request_counts[key]) >= limit:
        return True, f"Rate limit exceeded. {limit} requests per {window} seconds."
    
    request_counts[key].append(now)
    return False, None


class RateLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Determine rate limit based on path
        if request.path.startswith('/auth/'):
            limit = settings.RATE_LIMIT_AUTH
        else:
            limit = settings.RATE_LIMIT_DEFAULT
        
        exceeded, message = rate_limit(request, limit)
        if exceeded:
            return JsonResponse({'status': 'error', 'message': message}, status=429)
        
        return self.get_response(request)