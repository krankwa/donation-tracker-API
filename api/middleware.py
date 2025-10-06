import bleach
from django.utils.deprecation import MiddlewareMixin
import json


class InputSanitizationMiddleware(MiddlewareMixin):
    """
    Middleware to sanitize all input data to prevent XSS and injection attacks
    """
    
    ALLOWED_TAGS = ['p', 'br', 'strong', 'em', 'u', 'a', 'ul', 'ol', 'li']
    ALLOWED_ATTRIBUTES = {'a': ['href', 'title']}
    
    def process_request(self, request):
        """Sanitize incoming request data"""
        
        if request.method in ['POST', 'PUT', 'PATCH']:
            if request.content_type == 'application/json':
                try:
                    if hasattr(request, '_body') and request._body:
                        data = json.loads(request.body)
                        sanitized_data = self._sanitize_data(data)
                        request._body = json.dumps(sanitized_data).encode('utf-8')
                except (json.JSONDecodeError, UnicodeDecodeError):
                    pass
            
            # Sanitize POST data
            if hasattr(request, 'POST') and request.POST:
                sanitized_post = {}
                for key, value in request.POST.items():
                    if isinstance(value, str):
                        sanitized_post[key] = self._sanitize_string(value)
                    else:
                        sanitized_post[key] = value
                request.POST = sanitized_post
        
        return None
    
    def _sanitize_data(self, data):
        """Recursively sanitize data structures"""
        if isinstance(data, dict):
            return {key: self._sanitize_data(value) for key, value in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, str):
            return self._sanitize_string(data)
        else:
            return data
    
    def _sanitize_string(self, value):
        """Sanitize string values"""
        # Strip dangerous HTML but allow some basic formatting
        cleaned = bleach.clean(
            value,
            tags=self.ALLOWED_TAGS,
            attributes=self.ALLOWED_ATTRIBUTES,
            strip=True
        )
        return cleaned.strip()
