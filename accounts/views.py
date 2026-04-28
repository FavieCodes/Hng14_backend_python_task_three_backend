import os
import json
import base64
import hashlib
import secrets
import requests
from datetime import datetime
from django.shortcuts import redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.conf import settings

from .models import User, RefreshToken
from .tokens import generate_access_token, generate_refresh_token, decode_token, verify_access_token

# PKCE helpers
def generate_code_verifier():
    return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode('utf-8').replace('=', '')

def generate_code_challenge(code_verifier):
    return base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).decode('utf-8').replace('=', '')

# Store PKCE sessions temporarily (use Redis in production)
pkce_sessions = {}

@require_http_methods(['GET'])
def github_login(request):
    """Initiate GitHub OAuth login"""
    # For CLI login
    is_cli = request.GET.get('cli', 'false') == 'true'
    redirect_uri = request.GET.get('redirect_uri', settings.WEB_CALLBACK_URL)
    
    # Generate PKCE values
    code_verifier = generate_code_verifier()
    code_challenge = generate_code_challenge(code_verifier)
    state = secrets.token_urlsafe(32)
    
    # Store session
    session_id = state
    pkce_sessions[session_id] = {
        'code_verifier': code_verifier,
        'redirect_uri': redirect_uri,
        'is_cli': is_cli,
        'created_at': timezone.now().isoformat(),
    }
    
    # Build GitHub OAuth URL
    auth_url = (
        f"{settings.GITHUB_AUTH_URL}?"
        f"client_id={settings.GITHUB_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"state={state}&"
        f"code_challenge={code_challenge}&"
        f"code_challenge_method=S256"
    )
    
    return redirect(auth_url)


@require_http_methods(['GET'])
def github_callback(request):
    """Handle GitHub OAuth callback"""
    code = request.GET.get('code')
    state = request.GET.get('state')
    error = request.GET.get('error')
    
    if error:
        return JsonResponse({'status': 'error', 'message': f'GitHub error: {error}'}, status=400)
    
    # Validate state
    session = pkce_sessions.get(state)
    if not session:
        return JsonResponse({'status': 'error', 'message': 'Invalid state'}, status=400)
    
    code_verifier = session['code_verifier']
    redirect_uri = session['redirect_uri']
    is_cli = session['is_cli']
    
    # Exchange code for access token
    token_response = requests.post(
        settings.GITHUB_TOKEN_URL,
        headers={'Accept': 'application/json'},
        data={
            'client_id': settings.GITHUB_CLIENT_ID,
            'client_secret': settings.GITHUB_CLIENT_SECRET,
            'code': code,
            'redirect_uri': redirect_uri,
            'code_verifier': code_verifier,
        }
    )
    
    token_data = token_response.json()
    github_access_token = token_data.get('access_token')
    
    if not github_access_token:
        return JsonResponse({'status': 'error', 'message': 'Failed to get GitHub token'}, status=400)
    
    # Get GitHub user info
    user_response = requests.get(
        settings.GITHUB_USER_URL,
        headers={'Authorization': f'Bearer {github_access_token}'}
    )
    github_user = user_response.json()
    
    # Create or update user
    user, created = User.objects.update_or_create(
        github_id=github_user['id'],
        defaults={
            'username': github_user['login'],
            'email': github_user.get('email', ''),
            'avatar_url': github_user.get('avatar_url', ''),
            'last_login_at': timezone.now(),
        }
    )
    
    # Generate tokens
    access_token = generate_access_token(user.id, user.role)
    refresh_token_obj = RefreshToken.objects.create(
        user=user,
        token=generate_refresh_token(),
        expires_at=timezone.now() + timezone.timedelta(minutes=settings.REFRESH_TOKEN_EXPIRY_MINUTES),
    )
    
    # Clean up session
    del pkce_sessions[state]
    
    # For CLI, return JSON
    if is_cli:
        return JsonResponse({
            'status': 'success',
            'access_token': access_token,
            'refresh_token': refresh_token_obj.token,
            'user': {
                'id': str(user.id),
                'username': user.username,
                'role': user.role,
            }
        })
    
    # For web, set HTTP-only cookies and redirect
    response = redirect(f"{settings.WEB_CALLBACK_URL.replace('/auth/callback', '')}/dashboard")
    response.set_cookie(
        'access_token', access_token,
        httponly=True, secure=True, samesite='Lax',
        max_age=settings.ACCESS_TOKEN_EXPIRY_MINUTES * 60
    )
    response.set_cookie(
        'refresh_token', refresh_token_obj.token,
        httponly=True, secure=True, samesite='Lax',
        max_age=settings.REFRESH_TOKEN_EXPIRY_MINUTES * 60
    )
    return response


@csrf_exempt
@require_http_methods(['POST'])
def refresh_token(request):
    """Refresh access token using refresh token"""
    try:
        body = json.loads(request.body)
        refresh_token_str = body.get('refresh_token')
    except json.JSONDecodeError:
        return JsonResponse({'status': 'error', 'message': 'Invalid request body'}, status=400)
    
    if not refresh_token_str:
        return JsonResponse({'status': 'error', 'message': 'Refresh token required'}, status=400)
    
    # Find refresh token in database
    try:
        refresh_token_obj = RefreshToken.objects.get(token=refresh_token_str, is_revoked=False)
    except RefreshToken.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Invalid refresh token'}, status=401)
    
    # Check expiry
    if refresh_token_obj.is_expired():
        refresh_token_obj.is_revoked = True
        refresh_token_obj.save()
        return JsonResponse({'status': 'error', 'message': 'Refresh token expired'}, status=401)
    
    # Revoke old token
    refresh_token_obj.is_revoked = True
    refresh_token_obj.save()
    
    # Generate new tokens
    user = refresh_token_obj.user
    
    # Check if user is active
    if not user.is_active:
        return JsonResponse({'status': 'error', 'message': 'Account disabled'}, status=403)
    
    new_access_token = generate_access_token(user.id, user.role)
    new_refresh_token_obj = RefreshToken.objects.create(
        user=user,
        token=generate_refresh_token(),
        expires_at=timezone.now() + timezone.timedelta(minutes=settings.REFRESH_TOKEN_EXPIRY_MINUTES),
    )
    
    return JsonResponse({
        'status': 'success',
        'access_token': new_access_token,
        'refresh_token': new_refresh_token_obj.token,
    })


@csrf_exempt
@require_http_methods(['POST'])
def logout(request):
    """Logout - revoke refresh token"""
    # Try to get refresh token from body or cookie
    refresh_token_str = None
    
    # Check body
    try:
        body = json.loads(request.body)
        refresh_token_str = body.get('refresh_token')
    except:
        pass
    
    # Check cookie
    if not refresh_token_str:
        refresh_token_str = request.COOKIES.get('refresh_token')
    
    if refresh_token_str:
        try:
            refresh_token_obj = RefreshToken.objects.get(token=refresh_token_str, is_revoked=False)
            refresh_token_obj.is_revoked = True
            refresh_token_obj.save()
        except RefreshToken.DoesNotExist:
            pass
    
    response = JsonResponse({'status': 'success', 'message': 'Logged out'})
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


@require_http_methods(['GET'])
def whoami(request):
    """Get current user info"""
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return JsonResponse({'status': 'error', 'message': 'Unauthorized'}, status=401)
    
    token = auth_header.split(' ')[1]
    user_id, error = verify_access_token(token)
    
    if error:
        return JsonResponse({'status': 'error', 'message': error}, status=401)
    
    try:
        user = User.objects.get(id=user_id, is_active=True)
    except User.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'User not found'}, status=404)
    
    return JsonResponse({
        'status': 'success',
        'data': {
            'id': str(user.id),
            'username': user.username,
            'email': user.email,
            'avatar_url': user.avatar_url,
            'role': user.role,
            'is_active': user.is_active,
            'last_login_at': user.last_login_at.isoformat() if user.last_login_at else None,
            'created_at': user.created_at.isoformat(),
        }
    })