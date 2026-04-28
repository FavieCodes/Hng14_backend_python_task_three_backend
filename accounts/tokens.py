import jwt
import uuid
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone

def generate_access_token(user_id, role):
    """Generate access token (expires in 3 minutes)"""
    payload = {
        'user_id': str(user_id),
        'role': role,
        'type': 'access',
        'exp': datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRY_MINUTES),
        'iat': datetime.utcnow(),
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

def generate_refresh_token():
    """Generate refresh token (expires in 5 minutes)"""
    payload = {
        'type': 'refresh',
        'exp': datetime.utcnow() + timedelta(minutes=settings.REFRESH_TOKEN_EXPIRY_MINUTES),
        'iat': datetime.utcnow(),
        'jti': str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm='HS256')

def decode_token(token):
    """Decode and validate JWT token"""
    try:
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=['HS256'])
        return payload, None
    except jwt.ExpiredSignatureError:
        return None, 'Token expired'
    except jwt.InvalidTokenError:
        return None, 'Invalid token'

def verify_access_token(token):
    """Verify access token and return user_id"""
    payload, error = decode_token(token)
    if error:
        return None, error
    
    if payload.get('type') != 'access':
        return None, 'Invalid token type'
    
    return payload.get('user_id'), None