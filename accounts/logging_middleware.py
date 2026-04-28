import logging
import time

logger = logging.getLogger('django.request')


class RequestLoggingMiddleware:
    """Middleware to log all requests"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        start_time = time.time()
        
        response = self.get_response(request)
        
        duration = time.time() - start_time
        
        logger.info(
            f"{request.method} {request.path} "
            f"{response.status_code} "
            f"{duration:.3f}s"
        )
        
        return response