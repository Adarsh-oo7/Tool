
understand this projet very well

Bindu_Jewellery_Architecture_Blueprint.docx

Here's a deep breakdown of the Bindu Jewellery Business Growth System — a full-stack CRM/business management platform built specifically for a jewellery business operating across Trivandrum and Kollam.

What This Project Is
Bindu Jewellery is a custom business growth and CRM system — not an e-commerce store, but an internal operations platform for managing staff, leads, sales, field visits, and marketing campaigns across two physical jewellery showroom branches.

Think of it as a private SaaS tool built for one company, covering everything from lead tracking to GPS attendance to WhatsApp marketing.

Tech Stack at a Glance
Layer	Technology
Backend	Django REST Framework (Python)
Web Frontend	React.js + Vite + Tailwind CSS
Mobile App	React Native (Expo)
Database	PostgreSQL (AWS RDS)
Queue / Cache	Celery + Redis (AWS ElastiCache)
File Storage	AWS S3
Notifications	Firebase FCM (push)
Marketing	WhatsApp Business API
Deployment	AWS EC2 + Docker + Vercel + Expo EAS
Auth	JWT (djangorestframework-simplejwt)

Business Structure
The system is built around this hierarchy:

1 Company → 2 Branches (Trivandrum, Kollam)

Each branch has 4 Segments: Bridal, Daily Wear, Investment Gold, Diamond

5 User Roles: Owner, Branch Manager, Staff/Shop, Telecaller, Field Staff

Core Modules (Django Apps)
Each Django app handles a distinct domain:

accounts — JWT auth, RBAC, user profiles with roles

branches — Company → Branch → Segment hierarchy

leads — Full lead lifecycle: new → contacted → interested → visit scheduled → converted → lost, with an AI buying-intent score field

calls — Telecaller call logging with outcomes and stats

field_visits — GPS tracking, live location updates every 30s, visit reports

attendance — GPS + photo check-in, manager approvals

sales — Sale entries and revenue per branch/segment

campaigns — WhatsApp blast campaigns with ROI tracking

notifications — Firebase push + in-app alerts

reports — EOD reports, dashboards, AI suggestions via Celery

Role-Based Access (RBAC)
Each role sees a strictly scoped view of data:

Role	Access Scope
Owner	All branches, all reports, campaign creation, full staff management
Branch Manager	Own branch — assign leads, approve check-ins, monitor staff GPS
Staff / Shop	Own assigned leads — log calls, record sales, follow-ups
Telecaller	Call queue — initiate calls, log outcomes
Field Staff	GPS visits, check-ins, location-tracked customer visits
Key Features Deep Dive
Lead Pipeline with AI Scoring — Every lead has a score field (AI buying intent, re-calculated via Celery) and passes through 6 stages. Leads are filtered by role: Owner sees all, Manager sees branch leads, Staff sees only assigned leads.

GPS Field Visit Tracking — The mobile app uses expo-location to start a visit, then pushes GPS coordinates to the server every 30 seconds in the background via expo-task-manager. Managers can view a live map on the web dashboard.

WhatsApp Campaign Engine — Built on the Meta WhatsApp Business API (Graph API v19.0). Campaigns are created on the web, then a Celery @shared_task sends templated messages to all active campaign leads asynchronously — never synchronously blocking the API.

Celery Background Tasks — Handles: auto follow-up reminders (Day 1/3/7), daily EOD report generation, WhatsApp blasts, lead score recalculation, Firebase push dispatch, and lost lead recovery triggers.

Monorepo Structure
The entire project lives in one repo bindu-jewellery/ with three independent apps:

text
bindu-jewellery/
├── backend/      # Django REST API
├── frontend/     # React.js web dashboard (Vercel)
├── mobile/       # React Native staff app (Expo EAS)
├── docker-compose.yml
└── .github/workflows/  # CI/CD pipelines
Deployment Architecture
Backend: Docker container on AWS EC2 (t3.medium) behind Nginx + ELB, with auto-scaling

Frontend: Vercel with auto-deploy on main branch push

Mobile: Expo EAS Build → OTA updates + TestFlight/Play Store releases

CI/CD: GitHub Actions — runs tests on develop, deploys to AWS ECS on main

Security Highlights
Notable security implementations:

JWT access tokens expire in 60 minutes, refresh tokens in 7 days with rotation + blacklisting

GPS spoofing detection via server-side speed checks

S3 presigned URLs for attendance photos (S3 not exposed directly)

Rate limiting on login, OTP, and sensitive endpoints via django-ratelimit

AWS Secrets Manager for production secrets (no .env in version control)

Summary in One Line
This is a production-grade internal CRM for a 2-branch jewellery business — combining lead management, staff GPS tracking, WhatsApp marketing, and analytics into one unified system built with Django + React + React Native.

Prepared using Claude Sonnet 4.6 Thinking
now complte prject app set up for backend first
:\\Users\\adars\\Desktop\\bectree\\code\\Project1>
Completed 4 steps
Answer skipped
Prepared using Claude Sonnet 4.6 Thinking
create it by proper code like startapp , startproject,etc
Completed 3 steps
Answer skipped
Prepared using Claude Sonnet 4.6 Thinking
from django.db import models


class Company(models.Model):
name = models.CharField(max_length=200)
logo = models.ImageField(upload_to='company/', null=True, blank=True)
address = models.TextField(blank=True)
phone = models.CharField(max_length=15, blank=True)
email = models.EmailField(blank=True)
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
verbose_name_plural = 'Companies'

def __str__(self): return self.name


class Branch(models.Model):
company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
name = models.CharField(max_length=100) # e.g., Trivandrum, Kollam
address = models.TextField()
phone = models.CharField(max_length=15, blank=True)
lat = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
lng = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
is_active = models.BooleanField(default=True)
created_at = models.DateTimeField(auto_now_add=True)

class Meta:
verbose_name_plural = 'Branches'
ordering = ['name']

def __str__(self): return f'{self.name} — {self.company.name}'


class Segment(models.Model):
SEGMENT_CHOICES = [
('bridal', 'Bridal Jewellery'),
('daily_wear', 'Daily Wear'),
('investment', 'Investment Gold'),
('diamond', 'Diamond Collection'),
]
branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='segments')
name = models.CharField(max_length=50, choices=SEGMENT_CHOICES)
description= models.TextField(blank=True)
is_active = models.BooleanField(default=True)

class Meta:
unique_together = ['branch', 'name']

def __str__(self): return f'{self.get_name_display()} @ {self.branch.name}'

✅ Perfect model! The jewellery-specific SEGMENT_CHOICES (Bridal, Daily Wear, Investment Gold, Diamond) is exactly right for Bindu. unique_together on [branch, name] is also a smart constraint.

Now run check:

powershell
python manage.py check
If it passes → here are all 8 remaining models at once:

leads/models.py
python
from django.db import models
from django.conf import settings


class Lead(models.Model):
    SOURCE_CHOICES = [
        ('walk_in',   'Walk-in'),
        ('instagram', 'Instagram'),
        ('facebook',  'Facebook'),
        ('whatsapp',  'WhatsApp'),
        ('referral',  'Referral'),
        ('website',   'Website'),
        ('other',     'Other'),
    ]
    STAGE_CHOICES = [
        ('new',        'New'),
        ('contacted',  'Contacted'),
        ('interested', 'Interested'),
        ('visit_done', 'Visit Done'),
        ('converted',  'Converted'),
        ('lost',       'Lost'),
    ]

    name        = models.CharField(max_length=200)
    phone       = models.CharField(max_length=15)
    email       = models.EmailField(blank=True)
    source      = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='walk_in')
    stage       = models.CharField(max_length=20, choices=STAGE_CHOICES, default='new')
    segment     = models.ForeignKey('branches.Segment', null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='leads')
    branch      = models.ForeignKey('branches.Branch', on_delete=models.CASCADE,
                                    related_name='leads')
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='assigned_leads')
    created_by  = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                    on_delete=models.SET_NULL, related_name='created_leads')
    budget      = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    notes       = models.TextField(blank=True)
    score       = models.IntegerField(default=0)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.stage})'


class LeadActivity(models.Model):
    TYPE_CHOICES = [
        ('stage_change', 'Stage Changed'),
        ('note_added',   'Note Added'),
        ('call_logged',  'Call Logged'),
        ('visit_done',   'Visit Done'),
        ('followup_set', 'Follow-up Set'),
    ]
    lead          = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    description   = models.TextField()
    created_by    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                      on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']


class FollowUp(models.Model):
    lead         = models.ForeignKey(Lead, on_delete=models.CASCADE, related_name='followups')
    scheduled_at = models.DateTimeField()
    notes        = models.TextField(blank=True)
    is_done      = models.BooleanField(default=False)
    created_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                     on_delete=models.SET_NULL)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['scheduled_at']
calls/models.py
python
from django.db import models
from django.conf import settings


class CallLog(models.Model):
    OUTCOME_CHOICES = [
        ('no_answer',      'No Answer'),
        ('callback',       'Call Back Later'),
        ('interested',     'Interested'),
        ('not_interested', 'Not Interested'),
        ('converted',      'Converted'),
    ]

    lead             = models.ForeignKey('leads.Lead', on_delete=models.CASCADE,
                                         related_name='calls')
    called_by        = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                         on_delete=models.SET_NULL, related_name='calls_made')
    outcome          = models.CharField(max_length=20, choices=OUTCOME_CHOICES)
    duration_seconds = models.PositiveIntegerField(default=0)
    notes            = models.TextField(blank=True)
    called_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-called_at']

    def __str__(self):
        return f'{self.lead.name} → {self.outcome}'
field_visits/models.py
python
from django.db import models
from django.conf import settings


class FieldVisit(models.Model):
    STATUS_CHOICES = [
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ]
    lead        = models.ForeignKey('leads.Lead', on_delete=models.CASCADE,
                                    related_name='field_visits')
    field_staff = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                    on_delete=models.SET_NULL, related_name='field_visits')
    start_lat   = models.DecimalField(max_digits=10, decimal_places=7)
    start_lng   = models.DecimalField(max_digits=10, decimal_places=7)
    status      = models.CharField(max_length=15, choices=STATUS_CHOICES, default='active')
    started_at  = models.DateTimeField(auto_now_add=True)
    ended_at    = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'Visit: {self.lead.name} by {self.field_staff}'


class GPSCheckIn(models.Model):
    visit         = models.ForeignKey(FieldVisit, on_delete=models.CASCADE,
                                      related_name='checkins')
    lat           = models.DecimalField(max_digits=10, decimal_places=7)
    lng           = models.DecimalField(max_digits=10, decimal_places=7)
    checked_in_at = models.DateTimeField(auto_now_add=True)


class VisitReport(models.Model):
    visit        = models.OneToOneField(FieldVisit, on_delete=models.CASCADE,
                                        related_name='report')
    summary      = models.TextField()
    outcome      = models.CharField(max_length=100, blank=True)
    next_action  = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
sales/models.py
python
from django.db import models
from django.conf import settings


class Sale(models.Model):
    lead        = models.ForeignKey('leads.Lead', null=True, blank=True,
                                    on_delete=models.SET_NULL, related_name='sales')
    branch      = models.ForeignKey('branches.Branch', on_delete=models.CASCADE,
                                    related_name='sales')
    segment     = models.ForeignKey('branches.Segment', null=True,
                                    on_delete=models.SET_NULL, related_name='sales')
    sold_by     = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                    on_delete=models.SET_NULL, related_name='sales')
    amount      = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    sold_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-sold_at']

    def __str__(self):
        return f'₹{self.amount} — {self.branch.name}'
campaigns/models.py
python
from django.db import models
from django.conf import settings


class Campaign(models.Model):
    STATUS_CHOICES = [
        ('draft',     'Draft'),
        ('active',    'Active'),
        ('completed', 'Completed'),
        ('paused',    'Paused'),
    ]
    name          = models.CharField(max_length=200)
    branch        = models.ForeignKey('branches.Branch', on_delete=models.CASCADE,
                                      related_name='campaigns')
    template_name = models.CharField(max_length=100)
    message_body  = models.TextField()
    status        = models.CharField(max_length=15, choices=STATUS_CHOICES, default='draft')
    created_by    = models.ForeignKey(settings.AUTH_USER_MODEL, null=True,
                                      on_delete=models.SET_NULL)
    created_at    = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class CampaignLead(models.Model):
    campaign  = models.ForeignKey(Campaign, on_delete=models.CASCADE,
                                  related_name='campaign_leads')
    lead      = models.ForeignKey('leads.Lead', on_delete=models.CASCADE)
    sent      = models.BooleanField(default=False)
    delivered = models.BooleanField(default=False)
    opened    = models.BooleanField(default=False)
    sent_at   = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ['campaign', 'lead']
notifications/models.py
python
from django.db import models
from django.conf import settings


class Notification(models.Model):
    TYPE_CHOICES = [
        ('push',   'Push'),
        ('in_app', 'In-App'),
        ('alert',  'Alert'),
    ]
    user              = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                          related_name='notifications')
    title             = models.CharField(max_length=200)
    body              = models.TextField()
    notification_type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='in_app')
    is_read           = models.BooleanField(default=False)
    created_at        = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
attendance/models.py
python
from django.db import models
from django.conf import settings


class Attendance(models.Model):
    STATUS_CHOICES = [
        ('pending',  'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    user          = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                      related_name='attendance_records')
    date          = models.DateField(auto_now_add=True)
    check_in_lat  = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    check_in_lng  = models.DecimalField(max_digits=10, decimal_places=7, null=True)
    photo         = models.ImageField(upload_to='attendance/photos/', null=True, blank=True)
    status        = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    approved_by   = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                      on_delete=models.SET_NULL, related_name='approvals')
    checked_in_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['user', 'date']
        ordering        = ['-checked_in_at']
reports/models.py
python
from django.db import models


class DailyReport(models.Model):
    branch            = models.ForeignKey('branches.Branch', on_delete=models.CASCADE,
                                          related_name='daily_reports')
    date              = models.DateField()
    total_leads       = models.IntegerField(default=0)
    total_calls       = models.IntegerField(default=0)
    total_conversions = models.IntegerField(default=0)
    total_revenue     = models.DecimalField(max_digits=14, decimal_places=2, default=0)
    generated_at      = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['branch', 'date']
        ordering        = ['-date']
After pasting all files, run:
powershell
python manage.py check
python manage.py makemigrations
python manage.py migrate
Prepared using Claude Sonnet 4.6 Thinking
PS C:\\Users\\adars\\Desktop\\bectree\\code\\Project1\\bindu_jewellery_backend>
python manage.py check
System check identified no issues (0 silenced).
PS C:\\Users\\adars\\Desktop\\bectree\\code\\Project1\\bindu_jewellery_backend>

🎉 System check identified no issues (0 silenced). — Perfect! Now run these in order:

Step 1 — Make Migrations
powershell
python manage.py makemigrations accounts
python manage.py makemigrations branches
python manage.py makemigrations leads
python manage.py makemigrations calls
python manage.py makemigrations field_visits
python manage.py makemigrations sales
python manage.py makemigrations campaigns
python manage.py makemigrations notifications
python manage.py makemigrations attendance
python manage.py makemigrations reports
Step 2 — Apply Migrations
powershell
python manage.py migrate
Step 3 — Create Superuser
powershell
python manage.py createsuperuser
It will ask:

text
Email: admin@bindu.com
Full name: Admin
Phone: 9999999999
Password: xxxxxxxx
Step 4 — Run Server
powershell
python manage.py runserver
Then open:

Admin panel → http://127.0.0.1:8000/admin/ ✅

API root → http://127.0.0.1:8000/api/v1/ ✅

Share the output here and we move to the next phase — serializers + views + urls for all apps. 🚀

Prepared using Claude Sonnet 4.6 Thinking
NOW I NEED TO CREATE THE MD(CONTEXT) FILE FOR THE THIS PROJECT CODEVLEP THE BACKEND CODE PERFECTLY I AM USING ANTIGRAVITY IDE
Completed 2 steps
CONTEXT
Bindu Jewellery Backend — Project Context
IDE: Antigravity | Framework: Django 5.1.6 + Django REST Framework | Python: 3.13

Project Overview
A full-stack CRM + field-sales management backend for Bindu Jewellery, a multi-branch jewellery chain in Kerala. The system manages leads, telecalling, field visits, WhatsApp campaigns, attendance, and sales analytics across multiple branches and staff roles.

Tech Stack
Layer	Technology
Language	Python 3.13
Framework	Django 5.1.6
API	Django REST Framework (DRF)
Auth	JWT via djangorestframework-simplejwt
Database	SQLite (dev) → PostgreSQL (prod)
Task Queue	Celery + Redis
Scheduler	django-celery-beat
Push Notifications	Firebase Cloud Messaging (FCM)
WhatsApp	Meta Cloud API
Storage	Local (dev) → AWS S3 (prod)
CORS	django-cors-headers
Filtering	django-filter
Config	python-decouple (.env)
Folder Structure
text
bindu_jewellery_backend/          ← Django project root (manage.py lives here)
│
├── manage.py
├── db.sqlite3
├── .env
│
├── bindu_jewellery_backend/      ← Django config package
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   ├── celery.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py               ← All shared settings
│       └── development.py        ← DEBUG=True, CORS allow all
│
├── core/                         ← Shared utilities (no models)
│   ├── __init__.py
│   ├── pagination.py             ← StandardPagination
│   ├── exceptions.py             ← custom_exception_handler
│   └── permissions.py            ← IsOwner, IsManager, IsStaffOrAbove, IsTelecaller, IsFieldStaff
│
├── accounts/                     ← Custom User model + auth
├── branches/                     ← Company, Branch, Segment
├── leads/                        ← Lead, LeadActivity, FollowUp
├── calls/                        ← CallLog
├── field_visits/                 ← FieldVisit, GPSCheckIn, VisitReport
├── sales/                        ← Sale
├── campaigns/                    ← Campaign, CampaignLead
├── notifications/                ← Notification
├── attendance/                   ← Attendance
└── reports/                      ← DailyReport
Settings Architecture
Settings are split into a package at bindu_jewellery_backend/settings/:

base.py — all shared settings (apps, DRF, JWT, Celery, CORS, AWS, Firebase)

development.py — imports base, sets DEBUG=True, CORS_ALLOW_ALL_ORIGINS=True

manage.py uses: bindu_jewellery_backend.settings.development
wsgi.py / asgi.py use: bindu_jewellery_backend.settings.production (to be created)

Custom User Model
App: accounts | Model: accounts.User | Set in: AUTH_USER_MODEL = "accounts.User"

python
class User(AbstractBaseUser, PermissionsMixin):
    email      # USERNAME_FIELD — unique login identifier
    full_name  # single name field (no first/last split)
    phone      # unique, used for WhatsApp
    role       # owner | manager | staff | telecaller | field_staff
    branch     # FK → branches.Branch (null = owner/unassigned)
    avatar     # ImageField
    fcm_token  # Firebase push token (stored on user)
    is_active, is_staff, created_at, updated_at

    # Properties
    is_owner   → role == 'owner'
    is_manager → role == 'manager'
Authentication: JWT Bearer tokens via rest_framework_simplejwt

Access token lifetime: 60 minutes

Refresh token lifetime: 7 days

Rotate + blacklist on refresh: enabled

Role Hierarchy
text
owner
  └── manager (branch-level)
        ├── staff        (shop/counter)
        ├── telecaller   (calls + campaigns)
        └── field_staff  (GPS visits)
Role	Can Do
owner	Full access to all branches, reports, settings
manager	Branch-scoped access, approve attendance, assign leads
staff	Add/view leads, log sales for their branch
telecaller	Call logs, campaigns, follow-ups
field_staff	GPS check-in, field visits, visit reports
App Models Reference
branches
Company — top-level entity (name, logo, address, phone, email)

Branch — belongs to Company (name, address, lat/lng, phone, is_active)

Segment — jewellery category per branch (bridal | daily_wear | investment | diamond)

unique_together = ['branch', 'name']

leads
Lead — core CRM record

Sources: walk_in | instagram | facebook | whatsapp | referral | website | other

Stages: new → contacted → interested → visit_done → converted → lost

FKs: branch, segment, assigned_to (User), created_by (User)

Fields: name, phone, email, budget, notes, score

LeadActivity — audit trail of all actions on a lead

FollowUp — scheduled callbacks with is_done flag

calls
CallLog — telecaller call record

Outcomes: no_answer | callback | interested | not_interested | converted

Fields: lead, called_by, outcome, duration_seconds, notes, called_at

field_visits
FieldVisit — GPS-tracked visit to a lead

Statuses: active | completed | cancelled

Fields: lead, field_staff, start_lat/lng, started_at, ended_at

GPSCheckIn — periodic GPS ping during a visit

VisitReport — outcome summary submitted after visit

sales
Sale — closed sale record

FKs: lead (optional), branch, segment, sold_by

Fields: amount, description, sold_at

campaigns
Campaign — WhatsApp broadcast campaign

Statuses: draft | active | completed | paused

Fields: name, branch, template_name, message_body, created_by

CampaignLead — per-lead message status (sent, delivered, opened)

unique_together = ['campaign', 'lead']

notifications
Notification — in-app + push notification

Types: push | in_app | alert

Fields: user, title, body, is_read, created_at

attendance
Attendance — daily check-in with selfie + GPS

Statuses: pending | approved | rejected

unique_together = ['user', 'date']

Fields: user, date, check_in_lat/lng, photo, approved_by

reports
DailyReport — auto-generated daily summary per branch

Fields: branch, date, total_leads, total_calls, total_conversions, total_revenue

unique_together = ['branch', 'date']

API Structure
All endpoints are prefixed: /api/v1/

App	Base URL
Auth	/api/v1/auth/
Accounts	/api/v1/accounts/
Branches	/api/v1/branches/
Leads	/api/v1/leads/
Calls	/api/v1/calls/
Field Visits	/api/v1/field-visits/
Sales	/api/v1/sales/
Campaigns	/api/v1/campaigns/
Notifications	/api/v1/notifications/
Attendance	/api/v1/attendance/
Reports	/api/v1/reports/
Authentication: All endpoints require Authorization: Bearer <access_token> header except login/register.

Pagination: All list endpoints return:

json
{
  "count": 100,
  "next": "...",
  "previous": null,
  "total_pages": 5,
  "current_page": 1,
  "results": [...]
}
Error Response Format (via custom_exception_handler):

json
{
  "success": false,
  "error": {
    "status_code": 400,
    "detail": { ... }
  }
}
DRF Global Settings
python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS":        [DjangoFilterBackend, SearchFilter, OrderingFilter],
    "DEFAULT_PAGINATION_CLASS":       "core.pagination.StandardPagination",
    "PAGE_SIZE":                      20,
    "EXCEPTION_HANDLER":              "core.exceptions.custom_exception_handler",
}
Custom Permissions (core/permissions.py)
Class	Allowed Roles
IsOwner	owner
IsManager	owner, manager
IsStaffOrAbove	all roles
IsTelecaller	owner, manager, telecaller
IsFieldStaff	owner, manager, field_staff
Environment Variables (.env)
text
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Redis / Celery
REDIS_URL=redis://localhost:6379/0

# WhatsApp Meta API
WHATSAPP_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# Firebase
FIREBASE_CREDENTIALS_JSON=

# AWS S3 (production)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=bindu-media
AWS_S3_REGION_NAME=ap-south-1
Files Still To Create
High Priority (needed for API to work)
bindu_jewellery_backend/celery.py

bindu_jewellery_backend/__init__.py (import celery app)

bindu_jewellery_backend/urls.py (root URL config)

Each app's serializers.py

Each app's views.py

Each app's urls.py

Each app's admin.py

Medium Priority
accounts/tokens.py — custom JWT claims

core/mixins.py — branch-scoped queryset mixin

Celery tasks per app (follow-up reminders, campaign sending, daily report generation)

Production
settings/production.py

requirements.txt

Procfile / gunicorn config

Nginx config

Coding Conventions
All FKs to User use settings.AUTH_USER_MODEL (not direct import)

All list views use StandardPagination automatically via DRF global setting

Branch-scoped views filter queryset by request.user.branch for non-owner roles

All monetary values use DecimalField(max_digits=12, decimal_places=2)

GPS coordinates use DecimalField(max_digits=10, decimal_places=7)

Timestamps: created_at = auto_now_add, updated_at = auto_now

ordering defined in every Meta class

Role checks via core/permissions.py classes, not inline if user.role ==

Current Status
Django project created

Settings split into base.py + development.py

All 10 apps created

All models written

core/ utilities created (pagination, exceptions, permissions)

python manage.py check passes — 0 issues

Migrations pending (makemigrations + migrate)

Serializers not yet written

Views not yet written

URLs not yet configured

Admin not yet registered

Here's your complete CONTEXT.md for the Bindu Jewellery Backend project — drop this file into your project root in Antigravity IDE. It gives the AI full awareness of your entire backend.

What's included in the context file
Full project overview — purpose, tech stack, folder structure

Settings architecture — base.py / development.py split explained

Custom User model — all fields, properties, and auth strategy documented

Role hierarchy — owner → manager → staff/telecaller/field_staff with what each can do

All 10 app models — every model, its fields, FK relationships, and constraints

API structure — all /api/v1/ endpoint prefixes + pagination/error response format

DRF global settings — auth, permissions, filtering, pagination, exception handler

Custom permissions — all 5 classes from core/permissions.py

Environment variables — full .env template

Files still to create — checklist of what's pending (serializers, views, urls, celery, etc.)

Coding conventions — standards to follow throughout the project

How to use in Antigravity
Place CONTEXT.md in your project root (bindu_jewellery_backend/) and reference it in the IDE's context/AI panel. When asking for serializers, views, or any new feature — the AI will have full knowledge of your models, roles, and conventions without you having to re-explain every time.

Next step → Run migrations, then I'll generate all serializers + views as a batch.

Prepared using Claude Sonnet 4.6 Thinking
Follow-ups

Run migrations worked now show me all serializers

Show me accounts serializers and views first

Generate the celery.py and urls.py files next
CONTEXT


# Bindu Jewellery Backend — Project Context

> **IDE**: Antigravity | **Framework**: Django 5.1.6 + Django REST Framework | **Python**: 3.13

***

## Project Overview

A full-stack CRM + field-sales management backend for **Bindu Jewellery**, a multi-branch jewellery chain in Kerala. The system manages leads, telecalling, field visits, WhatsApp campaigns, attendance, and sales analytics across multiple branches and staff roles.

***

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.13 |
| Framework | Django 5.1.6 |
| API | Django REST Framework (DRF) |
| Auth | JWT via `djangorestframework-simplejwt` |
| Database | SQLite (dev) → PostgreSQL (prod) |
| Task Queue | Celery + Redis |
| Scheduler | django-celery-beat |
| Push Notifications | Firebase Cloud Messaging (FCM) |
| WhatsApp | Meta Cloud API |
| Storage | Local (dev) → AWS S3 (prod) |
| CORS | django-cors-headers |
| Filtering | django-filter |
| Config | python-decouple (`.env`) |

***

## Folder Structure

```
bindu_jewellery_backend/          ← Django project root (manage.py lives here)
│
├── manage.py
├── db.sqlite3
├── .env
│
├── bindu_jewellery_backend/      ← Django config package
│   ├── __init__.py
│   ├── asgi.py
│   ├── wsgi.py
│   ├── urls.py
│   ├── celery.py
│   └── settings/
│       ├── __init__.py
│       ├── base.py               ← All shared settings
│       └── development.py        ← DEBUG=True, CORS allow all
│
├── core/                         ← Shared utilities (no models)
│   ├── __init__.py
│   ├── pagination.py             ← StandardPagination
│   ├── exceptions.py             ← custom_exception_handler
│   └── permissions.py            ← IsOwner, IsManager, IsStaffOrAbove, IsTelecaller, IsFieldStaff
│
├── accounts/                     ← Custom User model + auth
├── branches/                     ← Company, Branch, Segment
├── leads/                        ← Lead, LeadActivity, FollowUp
├── calls/                        ← CallLog
├── field_visits/                 ← FieldVisit, GPSCheckIn, VisitReport
├── sales/                        ← Sale
├── campaigns/                    ← Campaign, CampaignLead
├── notifications/                ← Notification
├── attendance/                   ← Attendance
└── reports/                      ← DailyReport
```

***

## Settings Architecture

Settings are split into a package at `bindu_jewellery_backend/settings/`:

- `base.py` — all shared settings (apps, DRF, JWT, Celery, CORS, AWS, Firebase)
- `development.py` — imports `base`, sets `DEBUG=True`, `CORS_ALLOW_ALL_ORIGINS=True`

`manage.py` uses: `bindu_jewellery_backend.settings.development`
`wsgi.py` / `asgi.py` use: `bindu_jewellery_backend.settings.production` (to be created)

***

## Custom User Model

**App**: `accounts` | **Model**: `accounts.User` | **Set in**: `AUTH_USER_MODEL = "accounts.User"`

```python
class User(AbstractBaseUser, PermissionsMixin):
    email      # USERNAME_FIELD — unique login identifier
    full_name  # single name field (no first/last split)
    phone      # unique, used for WhatsApp
    role       # owner | manager | staff | telecaller | field_staff
    branch     # FK → branches.Branch (null = owner/unassigned)
    avatar     # ImageField
    fcm_token  # Firebase push token (stored on user)
    is_active, is_staff, created_at, updated_at

    # Properties
    is_owner   → role == 'owner'
    is_manager → role == 'manager'
```

**Authentication**: JWT Bearer tokens via `rest_framework_simplejwt`
- Access token lifetime: 60 minutes
- Refresh token lifetime: 7 days
- Rotate + blacklist on refresh: enabled

***

## Role Hierarchy

```
owner
  └── manager (branch-level)
        ├── staff        (shop/counter)
        ├── telecaller   (calls + campaigns)
        └── field_staff  (GPS visits)
```

| Role | Can Do |
|---|---|
| `owner` | Full access to all branches, reports, settings |
| `manager` | Branch-scoped access, approve attendance, assign leads |
| `staff` | Add/view leads, log sales for their branch |
| `telecaller` | Call logs, campaigns, follow-ups |
| `field_staff` | GPS check-in, field visits, visit reports |

***

## App Models Reference

### `branches`
- `Company` — top-level entity (name, logo, address, phone, email)
- `Branch` — belongs to Company (name, address, lat/lng, phone, is_active)
- `Segment` — jewellery category per branch (`bridal | daily_wear | investment | diamond`)
  - `unique_together = ['branch', 'name']`

### `leads`
- `Lead` — core CRM record
  - Sources: `walk_in | instagram | facebook | whatsapp | referral | website | other`
  - Stages: `new → contacted → interested → visit_done → converted → lost`
  - FKs: `branch`, `segment`, `assigned_to` (User), `created_by` (User)
  - Fields: `name`, `phone`, `email`, `budget`, `notes`, `score`
- `LeadActivity` — audit trail of all actions on a lead
- `FollowUp` — scheduled callbacks with `is_done` flag

### `calls`
- `CallLog` — telecaller call record
  - Outcomes: `no_answer | callback | interested | not_interested | converted`
  - Fields: `lead`, `called_by`, `outcome`, `duration_seconds`, `notes`, `called_at`

### `field_visits`
- `FieldVisit` — GPS-tracked visit to a lead
  - Statuses: `active | completed | cancelled`
  - Fields: `lead`, `field_staff`, `start_lat/lng`, `started_at`, `ended_at`
- `GPSCheckIn` — periodic GPS ping during a visit
- `VisitReport` — outcome summary submitted after visit

### `sales`
- `Sale` — closed sale record
  - FKs: `lead` (optional), `branch`, `segment`, `sold_by`
  - Fields: `amount`, `description`, `sold_at`

### `campaigns`
- `Campaign` — WhatsApp broadcast campaign
  - Statuses: `draft | active | completed | paused`
  - Fields: `name`, `branch`, `template_name`, `message_body`, `created_by`
- `CampaignLead` — per-lead message status (`sent`, `delivered`, `opened`)
  - `unique_together = ['campaign', 'lead']`

### `notifications`
- `Notification` — in-app + push notification
  - Types: `push | in_app | alert`
  - Fields: `user`, `title`, `body`, `is_read`, `created_at`

### `attendance`
- `Attendance` — daily check-in with selfie + GPS
  - Statuses: `pending | approved | rejected`
  - `unique_together = ['user', 'date']`
  - Fields: `user`, `date`, `check_in_lat/lng`, `photo`, `approved_by`

### `reports`
- `DailyReport` — auto-generated daily summary per branch
  - Fields: `branch`, `date`, `total_leads`, `total_calls`, `total_conversions`, `total_revenue`
  - `unique_together = ['branch', 'date']`

***

## API Structure

All endpoints are prefixed: `/api/v1/`

| App | Base URL |
|---|---|
| Auth | `/api/v1/auth/` |
| Accounts | `/api/v1/accounts/` |
| Branches | `/api/v1/branches/` |
| Leads | `/api/v1/leads/` |
| Calls | `/api/v1/calls/` |
| Field Visits | `/api/v1/field-visits/` |
| Sales | `/api/v1/sales/` |
| Campaigns | `/api/v1/campaigns/` |
| Notifications | `/api/v1/notifications/` |
| Attendance | `/api/v1/attendance/` |
| Reports | `/api/v1/reports/` |

**Authentication**: All endpoints require `Authorization: Bearer <access_token>` header except login/register.

**Pagination**: All list endpoints return:
```json
{
  "count": 100,
  "next": "...",
  "previous": null,
  "total_pages": 5,
  "current_page": 1,
  "results": [...]
}
```

**Error Response Format** (via `custom_exception_handler`):
```json
{
  "success": false,
  "error": {
    "status_code": 400,
    "detail": { ... }
  }
}
```

***

## DRF Global Settings

```python
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES":     ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_FILTER_BACKENDS":        [DjangoFilterBackend, SearchFilter, OrderingFilter],
    "DEFAULT_PAGINATION_CLASS":       "core.pagination.StandardPagination",
    "PAGE_SIZE":                      20,
    "EXCEPTION_HANDLER":              "core.exceptions.custom_exception_handler",
}
```

***

## Custom Permissions (core/permissions.py)

| Class | Allowed Roles |
|---|---|
| `IsOwner` | `owner` |
| `IsManager` | `owner`, `manager` |
| `IsStaffOrAbove` | all roles |
| `IsTelecaller` | `owner`, `manager`, `telecaller` |
| `IsFieldStaff` | `owner`, `manager`, `field_staff` |

***

## Environment Variables (.env)

```env
DJANGO_SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://localhost:3000

# Redis / Celery
REDIS_URL=redis://localhost:6379/0

# WhatsApp Meta API
WHATSAPP_API_TOKEN=
WHATSAPP_PHONE_NUMBER_ID=

# Firebase
FIREBASE_CREDENTIALS_JSON=

# AWS S3 (production)
AWS_ACCESS_KEY_ID=
AWS_SECRET_ACCESS_KEY=
AWS_STORAGE_BUCKET_NAME=bindu-media
AWS_S3_REGION_NAME=ap-south-1
```

***

## Files Still To Create

### High Priority (needed for API to work)
- [ ] `bindu_jewellery_backend/celery.py`
- [ ] `bindu_jewellery_backend/__init__.py` (import celery app)
- [ ] `bindu_jewellery_backend/urls.py` (root URL config)
- [ ] Each app's `serializers.py`
- [ ] Each app's `views.py`
- [ ] Each app's `urls.py`
- [ ] Each app's `admin.py`

### Medium Priority
- [ ] `accounts/tokens.py` — custom JWT claims
- [ ] `core/mixins.py` — branch-scoped queryset mixin
- [ ] Celery tasks per app (follow-up reminders, campaign sending, daily report generation)

### Production
- [ ] `settings/production.py`
- [ ] `requirements.txt`
- [ ] `Procfile` / `gunicorn` config
- [ ] Nginx config

***

## Coding Conventions

- All FKs to `User` use `settings.AUTH_USER_MODEL` (not direct import)
- All list views use `StandardPagination` automatically via DRF global setting
- Branch-scoped views filter `queryset` by `request.user.branch` for non-owner roles
- All monetary values use `DecimalField(max_digits=12, decimal_places=2)`
- GPS coordinates use `DecimalField(max_digits=10, decimal_places=7)`
- Timestamps: `created_at = auto_now_add`, `updated_at = auto_now`
- `ordering` defined in every `Meta` class
- Role checks via `core/permissions.py` classes, not inline `if user.role ==`

***

## Current Status

- [x] Django project created
- [x] Settings split into `base.py` + `development.py`
- [x] All 10 apps created
- [x] All models written
- [x] `core/` utilities created (pagination, exceptions, permissions)
- [x] `python manage.py check` passes — 0 issues
- [ ] Migrations pending (`makemigrations` + `migrate`)
- [ ] Serializers not yet written
- [ ] Views not yet written
- [ ] URLs not yet configured
- [ ] Admin not yet registered