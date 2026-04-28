# Insighta Labs+ Backend API

[![Django](https://img.shields.io/badge/Django-5.1.3-092E20?logo=django)](https://www.djangoproject.com/)
[![Deployed on Vercel](https://img.shields.io/badge/Deployed%20on-Vercel-000000?logo=vercel)](https://vercel.com)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## 📋 Overview

Insighta Labs+ is a secure, multi-interface demographic intelligence platform. This backend API provides:

- 🔐 **GitHub OAuth Authentication** with PKCE
- 👥 **Role-Based Access Control** (Admin/Analyst)
- 📊 **Profile Intelligence** (filtering, sorting, pagination, NLP search)
- 🔄 **Token Management** (Access: 3min, Refresh: 5min)
- 📈 **CSV Export** for data analysis
- ⏱️ **Rate Limiting** & Request Logging

## 🚀 Live API

| Environment | URL |
|-------------|-----|
| **Production** | `https://insighta-labs-backend.vercel.app` |
| **Documentation** | `https://insighta-labs-backend.vercel.app` |

## 📡 API Endpoints

### Authentication

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/auth/github` | Initiate GitHub OAuth |
| GET | `/auth/github/callback` | OAuth callback |
| POST | `/auth/refresh` | Refresh access token |
| POST | `/auth/logout` | Logout |
| GET | `/auth/whoami` | Get current user |

### Profiles

| Method | Endpoint | Description | Role |
|--------|----------|-------------|------|
| GET | `/api/profiles/` | List profiles with filters | Admin/Analyst |
| POST | `/api/profiles/` | Create profile | Admin only |
| GET | `/api/profiles/search/` | Natural language search | Admin/Analyst |
| GET | `/api/profiles/export/` | Export to CSV | Admin only |
| GET | `/api/profiles/{id}/` | Get single profile | Admin/Analyst |
| DELETE | `/api/profiles/{id}/` | Delete profile | Admin only |

## 🔧 Filtering Parameters

| Parameter | Type | Example |
|-----------|------|---------|
| `gender` | string | `male`, `female` |
| `age_group` | string | `child`, `teenager`, `adult`, `senior` |
| `country_id` | string | `NG`, `KE`, `ZA` |
| `min_age` | integer | `18` |
| `max_age` | integer | `65` |
| `min_gender_probability` | float | `0.8` |
| `min_country_probability` | float | `0.7` |
| `sort_by` | string | `age`, `created_at`, `gender_probability` |
| `order` | string | `asc`, `desc` |
| `page` | integer | `1` |
| `limit` | integer | `10` (max 50) |

## 🔍 Natural Language Search Examples

| Query | Interpretation |
|-------|----------------|
| `young males from nigeria` | `gender=male`, `min_age=16`, `max_age=24`, `country_id=NG` |
| `females above 30` | `gender=female`, `min_age=30` |
| `adult males from kenya` | `gender=male`, `age_group=adult`, `country_id=KE` |

## 👥 Role-Based Access Control

| Endpoint | Admin | Analyst |
|----------|-------|---------|
| GET `/api/profiles/` | ✅ | ✅ |
| POST `/api/profiles/` | ✅ | ❌ |
| DELETE `/api/profiles/{id}/` | ✅ | ❌ |
| GET `/api/profiles/export/` | ✅ | ❌ |

## ⏱️ Rate Limiting

| Endpoint Group | Limit |
|----------------|-------|
| `/auth/*` | 10 requests/minute |
| All others | 60 requests/minute per user |

## 🛠️ Local Development

### Prerequisites
- Python 3.11+
- PostgreSQL (or SQLite for development)

### Setup

```bash
# Clone repository
git clone https://github.com/FavieCodes/Hng14_backend_python_task_three_backend.git
cd hng-stage3-backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your values

# Run migrations
python manage.py migrate

# Seed database
python manage.py seed_data

# Start server
python manage.py runserver
```

## 🚀 Deployment
This backend is deployed on Vercel.
Deploy to Vercel

```bash
# Install Vercel CLI
npm install -g vercel

# Deploy
vercel --prod
Environment Variables Required
Variable	Description
SECRET_KEY	Django secret key
DATABASE_URL	PostgreSQL connection URL
GITHUB_CLIENT_ID	GitHub OAuth Client ID
GITHUB_CLIENT_SECRET	GitHub OAuth Client Secret
JWT_SECRET_KEY	JWT signing key
WEB_CALLBACK_URL	Web portal callback URL
📊 Database Schema
sql
users (
    id UUID PRIMARY KEY,
    github_id BIGINT UNIQUE,
    username VARCHAR(100),
    email VARCHAR(200),
    avatar_url VARCHAR(500),
    role VARCHAR(10),  -- admin / analyst
    is_active BOOLEAN,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP
)

refresh_tokens (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    token VARCHAR(500) UNIQUE,
    expires_at TIMESTAMP,
    is_revoked BOOLEAN
)

profiles (
    id UUID PRIMARY KEY,
    name VARCHAR(100) UNIQUE,
    gender VARCHAR(20),
    gender_probability FLOAT,
    age INTEGER,
    age_group VARCHAR(20),
    country_id VARCHAR(2),
    country_name VARCHAR(100),
    country_probability FLOAT,
    created_at TIMESTAMP
)
```
## 🔒 Security Features
✅ GitHub OAuth with PKCE
✅ JWT tokens with short expiry (3 min access, 5 min refresh)
✅ HTTP-only cookies for web portal
✅ Role-based access control
✅ Rate limiting
✅ CORS configured
✅ Environment variables for secrets

## 📝 License
MIT

## 👤 Author
Imo Emmanuel Udoh - HNG Cohort 14 Backend Track
Live API: https://insighta-labs-backend.vercel.app

