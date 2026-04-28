import json
import csv
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render
from django.views import View
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from .models import Profile
from .nlp_parser import NaturalLanguageParser

def api_docs(request):
    """Render the API documentation page"""
    return render(request, 'docs.html')

def add_cors(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    return response

def error_response(status, message):
    res = JsonResponse({'status': 'error', 'message': message}, status=status)
    return add_cors(res)

def json_response(data, status=200):
    res = JsonResponse(data, status=status)
    return add_cors(res)


def get_paginated_response(request, queryset, page, limit, total, data):
    """Helper function for paginated responses with links"""
    total_pages = (total + limit - 1) // limit if limit > 0 else 1
    
    request_path = request.path
    query_params = request.GET.copy()
    query_params.pop('page', None)
    query_params.pop('limit', None)
    base_query = f"?{query_params.urlencode()}" if query_params else ""
    
    return {
        'status': 'success',
        'page': page,
        'limit': limit,
        'total': total,
        'total_pages': total_pages,
        'links': {
            'self': f"{request_path}{base_query}&page={page}&limit={limit}" if base_query else f"{request_path}?page={page}&limit={limit}",
            'next': f"{request_path}{base_query}&page={page+1}&limit={limit}" if page < total_pages else None,
            'prev': f"{request_path}{base_query}&page={page-1}&limit={limit}" if page > 1 else None,
        },
        'data': data
    }


@method_decorator(csrf_exempt, name='dispatch')
class ProfileListCreateView(View):
    
    def options(self, request, *args, **kwargs):
        res = HttpResponse(status=204)
        res['Access-Control-Allow-Origin'] = '*'
        res['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        res['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return res
    
    def get(self, request):
        if hasattr(request, 'user_role') and request.user_role not in ['admin', 'analyst']:
            return error_response(403, 'Insufficient permissions')
        
        queryset = Profile.objects.all()
        
        # Apply filters
        gender = request.GET.get('gender', '').strip().lower()
        if gender:
            if gender not in ['male', 'female']:
                return error_response(422, 'Invalid gender value')
            queryset = queryset.filter(gender=gender)
        
        age_group = request.GET.get('age_group', '').strip().lower()
        if age_group:
            valid_groups = ['child', 'teenager', 'adult', 'senior']
            if age_group not in valid_groups:
                return error_response(422, 'Invalid age_group')
            queryset = queryset.filter(age_group=age_group)
        
        country_id = request.GET.get('country_id', '').strip().upper()
        if country_id:
            queryset = queryset.filter(country_id=country_id)
        
        min_age = request.GET.get('min_age', '').strip()
        if min_age:
            try:
                min_age = int(min_age)
                queryset = queryset.filter(age__gte=min_age)
            except ValueError:
                return error_response(422, 'min_age must be an integer')
        
        max_age = request.GET.get('max_age', '').strip()
        if max_age:
            try:
                max_age = int(max_age)
                queryset = queryset.filter(age__lte=max_age)
            except ValueError:
                return error_response(422, 'max_age must be an integer')
        
        min_gender_prob = request.GET.get('min_gender_probability', '').strip()
        if min_gender_prob:
            try:
                min_gender_prob = float(min_gender_prob)
                queryset = queryset.filter(gender_probability__gte=min_gender_prob)
            except ValueError:
                return error_response(422, 'min_gender_probability must be a number')
        
        min_country_prob = request.GET.get('min_country_probability', '').strip()
        if min_country_prob:
            try:
                min_country_prob = float(min_country_prob)
                queryset = queryset.filter(country_probability__gte=min_country_prob)
            except ValueError:
                return error_response(422, 'min_country_probability must be a number')
        
        # Apply sorting
        sort_by = request.GET.get('sort_by', '').strip().lower()
        order = request.GET.get('order', '').strip().lower()
        
        allowed_sort_fields = ['age', 'created_at', 'gender_probability']
        
        if sort_by:
            if sort_by not in allowed_sort_fields:
                return error_response(422, 'Invalid sort_by field')
            
            if order == 'desc':
                sort_by = f'-{sort_by}'
            elif order and order != 'asc':
                return error_response(422, 'Invalid order value. Use asc or desc')
            
            queryset = queryset.order_by(sort_by)
        else:
            queryset = queryset.order_by('-created_at')
        
        # Apply pagination
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)
        
        try:
            page = int(page)
            limit = int(limit)
            if limit > 50:
                limit = 50
            if limit < 1:
                limit = 10
            if page < 1:
                page = 1
        except ValueError:
            return error_response(422, 'page and limit must be integers')
        
        paginator = Paginator(queryset, limit)
        total = paginator.count
        
        try:
            profiles_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            return error_response(404, 'Page not found')
        
        profiles = [p.to_dict(full=False) for p in profiles_page]
        
        # Use updated paginated response format
        response_data = get_paginated_response(request, queryset, page, limit, total, profiles)
        return json_response(response_data, status=200)
    
    def post(self, request):
        """Create a new profile - Admin only"""
        if not hasattr(request, 'user_role') or request.user_role != 'admin':
            return error_response(403, 'Admin access required. Only administrators can create profiles.')
        
        # Parse JSON body
        try:
            body_str = request.body.decode('utf-8')
            if not body_str:
                return error_response(400, 'Empty request body')
            body = json.loads(body_str)
        except json.JSONDecodeError:
            return error_response(400, 'Invalid JSON body')
        
        name = body.get('name', '').strip().lower()
        
        if not name:
            return error_response(400, 'Missing or empty name')
        
        if not isinstance(name, str):
            return error_response(422, 'Invalid type')
        
        # Check if profile already exists
        existing = Profile.objects.filter(name=name).first()
        if existing:
            return json_response({
                'status': 'success',
                'message': 'Profile already exists',
                'data': existing.to_dict(full=True),
            }, status=200)
        
        from .services import fetch_genderize_data, fetch_agify_data, fetch_nationalize_data
        
        gender_data, gender_error = fetch_genderize_data(name)
        if gender_error:
            return error_response(502, gender_error)
        
        age_data, age_error = fetch_agify_data(name)
        if age_error:
            return error_response(502, age_error)
        
        country_data, country_error = fetch_nationalize_data(name)
        if country_error:
            return error_response(502, country_error)
        
        # Create profile
        profile = Profile.objects.create(
            name=name,
            **gender_data,
            **age_data,
            **country_data
        )
        
        return json_response({'status': 'success', 'data': profile.to_dict(full=True)}, status=201)


@method_decorator(csrf_exempt, name='dispatch')
class ProfileSearchView(View):
    
    def options(self, request, *args, **kwargs):
        res = HttpResponse(status=204)
        res['Access-Control-Allow-Origin'] = '*'
        res['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        res['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return res
    
    def get(self, request):
        if hasattr(request, 'user_role') and request.user_role not in ['admin', 'analyst']:
            return error_response(403, 'Insufficient permissions')
        
        q = request.GET.get('q', '').strip()
        
        if not q:
            return error_response(400, 'Missing or empty query parameter')
        
        # Parse natural language query
        filters, error = NaturalLanguageParser.parse(q)
        
        if error:
            return error_response(400, error)
        
        queryset = Profile.objects.all()
        
        # Apply parsed filters
        if 'gender' in filters:
            queryset = queryset.filter(gender=filters['gender'])
        
        if 'age_group' in filters:
            queryset = queryset.filter(age_group=filters['age_group'])
        
        if 'country_id' in filters:
            queryset = queryset.filter(country_id=filters['country_id'])
        
        if 'min_age' in filters:
            queryset = queryset.filter(age__gte=filters['min_age'])
        
        if 'max_age' in filters:
            queryset = queryset.filter(age__lte=filters['max_age'])
        
        # Apply pagination
        page = request.GET.get('page', 1)
        limit = request.GET.get('limit', 10)
        
        try:
            page = int(page)
            limit = int(limit)
            if limit > 50:
                limit = 50
            if limit < 1:
                limit = 10
            if page < 1:
                page = 1
        except ValueError:
            return error_response(422, 'page and limit must be integers')
        
        paginator = Paginator(queryset, limit)
        total = paginator.count
        
        try:
            profiles_page = paginator.page(page)
        except (PageNotAnInteger, EmptyPage):
            return error_response(404, 'Page not found')
        
        profiles = [p.to_dict(full=False) for p in profiles_page]
        
        # Use updated paginated response format
        response_data = get_paginated_response(request, queryset, page, limit, total, profiles)
        response_data['query'] = q
        response_data['interpreted_as'] = filters
        
        return json_response(response_data, status=200)


@method_decorator(csrf_exempt, name='dispatch')
class ProfileDetailView(View):
    
    def options(self, request, *args, **kwargs):
        res = HttpResponse(status=204)
        res['Access-Control-Allow-Origin'] = '*'
        res['Access-Control-Allow-Methods'] = 'GET, POST, DELETE, OPTIONS'
        res['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        return res
    
    def get(self, request, profile_id):
        if hasattr(request, 'user_role') and request.user_role not in ['admin', 'analyst']:
            return error_response(403, 'Insufficient permissions')
        
        try:
            profile = Profile.objects.get(id=profile_id)
        except (Profile.DoesNotExist, ValueError):
            return error_response(404, 'Profile not found')
        
        return json_response({'status': 'success', 'data': profile.to_dict(full=True)}, status=200)
    
    def delete(self, request, profile_id):
        if not hasattr(request, 'user_role') or request.user_role != 'admin':
            return error_response(403, 'Admin access required. Only administrators can delete profiles.')
        
        try:
            profile = Profile.objects.get(id=profile_id)
        except (Profile.DoesNotExist, ValueError):
            return error_response(404, 'Profile not found')
        
        profile.delete()
        res = HttpResponse(status=204)
        res['Access-Control-Allow-Origin'] = '*'
        return res


@require_http_methods(['GET'])
def export_profiles(request):
    """Export profiles to CSV (admin only)"""
    # Check authentication and role
    if not hasattr(request, 'user_role') or request.user_role != 'admin':
        return JsonResponse({'status': 'error', 'message': 'Admin access required'}, status=403)
    
    # Build queryset with filters (same as list endpoint)
    queryset = Profile.objects.all()
    
    # Apply filters (same as ProfileListCreateView)
    gender = request.GET.get('gender', '').strip().lower()
    if gender:
        if gender in ['male', 'female']:
            queryset = queryset.filter(gender=gender)
    
    age_group = request.GET.get('age_group', '').strip().lower()
    if age_group:
        valid_groups = ['child', 'teenager', 'adult', 'senior']
        if age_group in valid_groups:
            queryset = queryset.filter(age_group=age_group)
    
    country_id = request.GET.get('country_id', '').strip().upper()
    if country_id:
        queryset = queryset.filter(country_id=country_id)
    
    min_age = request.GET.get('min_age', '').strip()
    if min_age:
        try:
            min_age = int(min_age)
            queryset = queryset.filter(age__gte=min_age)
        except ValueError:
            pass
    
    max_age = request.GET.get('max_age', '').strip()
    if max_age:
        try:
            max_age = int(max_age)
            queryset = queryset.filter(age__lte=max_age)
        except ValueError:
            pass
    
    min_gender_prob = request.GET.get('min_gender_probability', '').strip()
    if min_gender_prob:
        try:
            min_gender_prob = float(min_gender_prob)
            queryset = queryset.filter(gender_probability__gte=min_gender_prob)
        except ValueError:
            pass
    
    min_country_prob = request.GET.get('min_country_probability', '').strip()
    if min_country_prob:
        try:
            min_country_prob = float(min_country_prob)
            queryset = queryset.filter(country_probability__gte=min_country_prob)
        except ValueError:
            pass
    
    # Create CSV response
    timestamp = timezone.now().strftime('%Y%m%d_%H%M%S')
    filename = f"profiles_{timestamp}.csv"
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    response['Access-Control-Allow-Origin'] = '*'
    
    writer = csv.writer(response)
    writer.writerow(['id', 'name', 'gender', 'gender_probability', 'age', 'age_group', 
                     'country_id', 'country_name', 'country_probability', 'created_at'])
    
    for profile in queryset.iterator():
        writer.writerow([
            str(profile.id), profile.name, profile.gender, profile.gender_probability,
            profile.age, profile.age_group, profile.country_id, profile.country_name,
            profile.country_probability, profile.created_at.isoformat()
        ])
    
    return response