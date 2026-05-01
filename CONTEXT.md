# Bindu Jewellery Backend — AI Code Generation Master Prompt

> **Use this document with any AI IDE (Cursor, Windsurf, Copilot, Claude, etc.)**
> Paste the relevant section as your prompt when generating each file.
> All code targets: **Django 5.0.6 · DRF 3.15 · Python 3.13 · Development environment**
> Production changes (S3, RDS, Nginx) are marked separately — do not generate them now.

***

## ⚡ Master Context (Paste This First — Every Session)

```
Project: Bindu Jewellery Business Growth System
Stack: Django 5.0.6, DRF 3.15, PostgreSQL (local), Redis (local), Celery 5.3
Python: 3.13
Settings module: bindu_jewellery_backend.settings.development
Auth: JWT via djangorestframework-simplejwt, AUTH_USER_MODEL = 'accounts.User'
Celery app: bindu_jewellery_backend (defined in celery_config.py)
Task package: celery_app.tasks

Roles (exact strings): owner | manager | staff | telecaller | field
Branches: Trivandrum, Kollam
Segments: bridal | daily | investment | diamond

Rules:
- Development only — no S3, no RDS, no Gunicorn, no Sentry
- All model imports inside Celery task function bodies (no top-level imports)
- Use get_object_or_404 in views, never raw .get()
- Soft delete only — never user.delete(), set is_active=False
- All list views must use StandardPagination (PAGE_SIZE=20)
- Role-based queryset filtering on every ViewSet
- password field: write_only=True in all serializers, never readable
- Related name for campaign→leads is campaign_leads (not leads)
- Campaign date fields: scheduled_at, sent_at (no start_date / end_date)
- bind=True, max_retries=3 on every Celery task
- try/except around every WhatsApp send — log error to CampaignLead.error
```

***

## FILE 1 — `core/pagination.py`

```
Generate core/pagination.py for the Bindu Jewellery Django backend.

Create:
- StandardPagination(PageNumberPagination)
  - page_size = 20
  - page_size_query_param = 'page_size'
  - max_page_size = 100
  - Returns: {"count": N, "next": url, "previous": url, "results": [...]}
```

***

## FILE 2 — `core/permissions.py`

```
Generate core/permissions.py for the Bindu Jewellery Django backend.

Create these DRF BasePermission subclasses:
- IsOwner         → user.role == 'owner'
- IsManager       → user.role in ['owner', 'manager']
- IsStaff         → user.role in ['owner', 'manager', 'staff', 'telecaller', 'field']
- IsSameBranch    → user.branch == obj.branch OR user.role == 'owner'
- IsOwnerOrManager (alias for IsManager)

All classes: set message = '...' with a helpful error string.
```

***

## FILE 3 — `core/exceptions.py`

```
Generate core/exceptions.py for the Bindu Jewellery Django backend.

Create a custom DRF exception handler:
- Function: custom_exception_handler(exc, context)
- Wraps DRF's default handler
- Always returns JSON: {"error": true, "message": "...", "details": {...}}
- Handles: ValidationError, NotFound, PermissionDenied, AuthenticationFailed
- Register in settings: EXCEPTION_HANDLER = 'core.exceptions.custom_exception_handler'
```

***

## FILE 4 — `accounts/serializers.py`

```
Generate accounts/serializers.py for the Bindu Jewellery Django backend.

Models available: User (AUTH_USER_MODEL), SubManagerPermission
User fields: email, phone, role, branch(FK), is_active, full_name,
             date_of_birth, join_date, employee_id, staff_type,
             staff_type_label, address, emergency_contact_name,
             emergency_contact_phone, notes

Create:
1. StaffListSerializer — lightweight: id, full_name, role, branch name, phone
2. UserSerializer — full read serializer, NO password, branch as nested object
3. UserCreateSerializer — write serializer
   - Fields: email, phone, role, branch, password, full_name
   - password: write_only=True, min length 8
   - create(): uses user.set_password(), never stores plain text
4. UserUpdateSerializer — partial update, no password, no role change
5. SubManagerPermissionSerializer — user(id), permission, branch(id)
6. ChangePasswordSerializer — old_password, new_password, confirm_password
   - validate(): checks old_password correct, new != old, confirm matches
```

***

## FILE 5 — `accounts/views.py`

```
Generate accounts/views.py for the Bindu Jewellery Django backend.

Import from: core.permissions, accounts.serializers, accounts.models

Create:
1. UserViewSet(ModelViewSet)
   - list:     IsManager — owner sees all, manager sees own branch only
   - retrieve: IsManager or self
   - create:   IsOwner only
   - update:   IsOwner only
   - destroy:  IsOwner only → soft delete (is_active=False), NOT user.delete()
   - Filter by: role, branch, is_active via query params

2. SetRoleView(APIView)
   - POST /accounts/users/{id}/set-role/
   - IsOwner only
   - Body: {"role": "manager"}
   - Validates role is one of the 5 valid choices

3. StaffByBranchView(ListAPIView)
   - GET /accounts/staff/?branch_id=1
   - IsManager
   - Returns StaffListSerializer

4. SubManagerPermissionViewSet(ModelViewSet)
   - IsOwner for create/destroy, IsManager for list/retrieve
   - Filter by user and branch

5. ChangePasswordView(APIView)
   - POST /accounts/change-password/
   - Any authenticated user (own password only)
   - Uses ChangePasswordSerializer
```

***

## FILE 6 — `accounts/urls.py`

```
Generate accounts/urls.py for the Bindu Jewellery Django backend.

Register with DefaultRouter:
- UserViewSet → 'users'
- SubManagerPermissionViewSet → 'sub-permissions'

Extra paths:
- POST users/{id}/set-role/ → SetRoleView
- GET  staff/ → StaffByBranchView
- POST change-password/ → ChangePasswordView

Include in root urls.py under: api/v1/accounts/
```

***

## FILE 7 — `branches/serializers.py`

```
Generate branches/serializers.py for the Bindu Jewellery Django backend.

Models: Company, Branch, Segment

Create:
1. CompanySerializer — id, name
2. SegmentSerializer — id, name, branch(id)
3. BranchSerializer — id, name, company(nested), location, lat, lng,
                      segments(nested list of SegmentSerializer)
4. BranchListSerializer — lightweight: id, name, location only
```

***

## FILE 8 — `branches/views.py` + `branches/urls.py`

```
Generate branches/views.py and branches/urls.py for Bindu Jewellery.

Views:
1. BranchViewSet(ModelViewSet)
   - list/retrieve: IsManager
   - create/update/destroy: IsOwner
   - Owner sees all branches, Manager sees own branch only

2. SegmentViewSet(ModelViewSet)
   - list: IsManager, filter by ?branch_id=
   - create/update/destroy: IsOwner

URLs — register under api/v1/branches/
```

***

## FILE 9 — `leads/serializers.py`

```
Generate leads/serializers.py for the Bindu Jewellery Django backend.

Models: Lead, LeadActivity, FollowUp

Lead stage choices (exact): new, contacted, interested, scheduled, converted, lost
Lead source choices (exact): walkin, instagram, facebook, website, referral

Create:
1. LeadSerializer — all fields, score and created_at are read_only
2. LeadCreateSerializer — omit score, created_at, branch (auto-set in view)
3. LeadUpdateSerializer — only: stage, assigned_to, budget, notes
4. LeadActivitySerializer — id, lead(id), action, note, created_by(name), created_at
5. FollowUpSerializer — id, lead(id), scheduled_at, note, completed, created_by
   - validate_scheduled_at(): must be in the future
```

***

## FILE 10 — `leads/views.py` + `leads/urls.py`

```
Generate leads/views.py and leads/urls.py for the Bindu Jewellery Django backend.

Views:
1. LeadViewSet(ModelViewSet)
   - get_queryset() role-based:
     owner     → Lead.objects.all()
     manager   → filter(branch=user.branch)
     others    → filter(assigned_to=user)
   - perform_create(): auto-set branch=request.user.branch,
                       trigger schedule_followup.delay(lead.id)
   - Filter fields: stage, segment, branch, assigned_to, source
   - Custom action: PATCH /{id}/stage/ → update stage only

2. FollowUpViewSet(ModelViewSet)
   - filter by lead, completed
   - perform_create: auto-set created_by=request.user

3. LeadActivityListView(ListAPIView)
   - GET /leads/{lead_id}/activity/
   - Read-only, ordered by -created_at

URLs — register under api/v1/leads/
```

***

## FILE 11 — `calls/serializers.py` + `calls/views.py` + `calls/urls.py`

```
Generate the full calls app for the Bindu Jewellery Django backend.

Models (generate if not existing):
- CallLog: lead(FK), called_by(FK User), outcome(choices: interested/callback/
  not_interested/no_answer/converted), duration_seconds, notes, created_at
- CallOutcome: (can be inline as choices on CallLog)

Serializers:
1. CallLogSerializer — all fields, called_by read-only
2. CallStatsSerializer — staff name, total_calls, converted, not_interested counts

Views:
1. CallLogViewSet
   - create: telecaller/staff — auto-set called_by=request.user
   - list: manager sees branch calls, telecaller sees own calls
   - Custom action: GET /calls/stats/ → per-staff call stats for manager

URLs — register under api/v1/calls/
```

***

## FILE 12 — `sales/serializers.py` + `sales/views.py` + `sales/urls.py`

```
Generate the full sales app for the Bindu Jewellery Django backend.

Models (generate if not existing):
- Sale: lead(FK, nullable), branch(FK), recorded_by(FK User),
        amount(DecimalField), item_description, created_at
- Revenue: branch(FK), date, total_amount — daily aggregated (optional, can compute)

Serializers:
1. SaleSerializer — all fields, recorded_by read-only, branch read-only
2. RevenueSerializer — branch, date, total_amount

Views:
1. SaleViewSet
   - create: staff — auto-set branch and recorded_by from request.user
   - list: owner sees all, manager sees branch only, staff sees own
2. RevenueView(ListAPIView)
   - GET /sales/revenue/?branch=&from=&to=
   - IsManager
   - Aggregates Sale by branch + date range

URLs — register under api/v1/sales/
```

***

## FILE 13 — `campaigns/whatsapp.py`

```
Generate campaigns/whatsapp.py for the Bindu Jewellery Django backend.
Development mode: real HTTP calls to Meta, but use test phone numbers.

Create WhatsAppService class:
- BASE_URL = 'https://graph.facebook.com/v19.0'
- Reads from settings: WHATSAPP_PHONE_NUMBER_ID, WHATSAPP_ACCESS_TOKEN, WHATSAPP_API_VERSION

Methods:
1. send_text(phone: str, message: str) → dict
   - POST to /messages with type=text

2. send_template(phone: str, template_name: str, params: list[str]) → dict
   - POST with type=template, language code=en_IN
   - Components: body with text parameters

3. send_media(phone: str, media_url: str, caption: str = '') → dict
   - POST with type=image

All methods:
- Add 'whatsapp' prefix to phone if missing
- Log request + response with logger = logging.getLogger('whatsapp')
- Raise WhatsAppError(message, status_code) on non-2xx
- WhatsAppError is a custom Exception defined in the same file

No retry logic here — retries handled at Celery task level with max_retries=3.
```

***

## FILE 14 — `campaigns/serializers.py`

```
Generate campaigns/serializers.py for the Bindu Jewellery Django backend.

Models: Campaign, CampaignLead, WhatsAppTemplate, SpecialDayMessage

Campaign fields: name, branch, segment, campaign_type, whatsapp_template,
                 template_name, message, status, scheduled_at, sent_at,
                 created_by, created_at, updated_at
Campaign properties: total_leads, sent_count, converted_count, roi_percent

Create:
1. WhatsAppTemplateSerializer — all fields, created_by read-only
2. SpecialDayMessageSerializer — all fields, validate date is valid calendar date
3. CampaignListSerializer — lightweight: id, name, status, campaign_type,
                            total_leads, sent_count, roi_percent, scheduled_at
4. CampaignSerializer — full detail with nested branch name, segment name,
                        whatsapp_template nested, computed stats as read-only fields
5. CampaignCreateSerializer — write: name, branch, segment, campaign_type,
                               template_name, message, scheduled_at, whatsapp_template
6. CampaignLeadSerializer — campaign(id), lead(id+name+phone), sent, delivered,
                             read, converted, sent_at, error
```

***

## FILE 15 — `campaigns/views.py` + `campaigns/urls.py`

```
Generate campaigns/views.py and campaigns/urls.py for the Bindu Jewellery Django backend.

Views:
1. CampaignViewSet(ModelViewSet)
   - list/retrieve: IsManager
   - create/destroy: IsOwner only
   - get_serializer_class(): CampaignListSerializer for list,
                             CampaignCreateSerializer for create,
                             CampaignSerializer for retrieve
   - perform_create: auto-set created_by=request.user
   - Custom action: POST /{id}/launch/
     → validates status in ['draft','scheduled']
     → calls send_campaign_blast.delay(campaign.id)
     → sets status='active', returns 202

2. CampaignLeadViewSet(ModelViewSet)
   - list: filter by campaign_id query param
   - update: allow marking delivered/converted via PATCH
   - IsManager for list, IsOwner for update

3. WhatsAppTemplateViewSet(ModelViewSet) — IsOwner CRUD

4. SpecialDayMessageViewSet(ModelViewSet) — IsOwner CRUD

URLs — register under api/v1/campaigns/
```

***

## FILE 16 — `notifications/serializers.py` + `notifications/views.py` + `notifications/urls.py`

```
Generate the full notifications app for the Bindu Jewellery Django backend.

Model: Notification — user(FK), title, message, notif_type, is_read, created_at
notif_type choices: report, alert, reminder, campaign, system

Serializers:
1. NotificationSerializer — all fields, user read-only

Views:
1. NotificationListView(ListAPIView)
   - GET /notifications/
   - Filter: user=request.user only (users CANNOT see others' notifications)
   - Order: is_read ASC (unread first), then -created_at
   - Paginated

2. MarkReadView(UpdateAPIView)
   - PATCH /notifications/{id}/read/
   - Sets is_read=True
   - Validates request.user == notification.user

3. MarkAllReadView(APIView)
   - POST /notifications/read-all/
   - Bulk update is_read=True for request.user

4. UnreadCountView(APIView)
   - GET /notifications/unread-count/
   - Returns {"count": N}

URLs — register under api/v1/notifications/
```

***

## FILE 17 — `reports/serializers.py` + `reports/views.py` + `reports/urls.py`

```
Generate the full reports app for the Bindu Jewellery Django backend.

Model: Report — branch(FK), period(daily/monthly), date, data(JSONField)
data JSON structure: {"leads": N, "calls": N, "sales_count": N, "sales_amount": "0.00"}

Serializers:
1. ReportSerializer — all fields

Views:
1. BranchSnapshotView(APIView)
   - GET /reports/snapshot/?branch_id=&period=daily
   - IsManager; manager auto-filtered to own branch
   - Returns latest Report for that branch+period or 404

2. TriggerEODReportView(APIView)
   - POST /reports/eod/trigger/
   - IsManager
   - Fires generate_branch_snapshot.delay(branch_id, 'daily')
   - Returns {"status": "queued", "branch": name}

3. ReportListView(ListAPIView)
   - GET /reports/?branch_id=&from=&to=&period=
   - IsManager; paginated; date range filter

URLs — register under api/v1/reports/
```

***

## FILE 18 — `attendance/serializers.py` + `attendance/views.py` + `attendance/urls.py`

```
Generate the full attendance app for the Bindu Jewellery Django backend.

Models (generate if not existing):
- Attendance: user(FK), branch(FK), check_in_time, check_out_time(nullable),
              lat, lng, photo(ImageField, nullable), status(present/late/absent),
              date, notes
- Development: photo stored in MEDIA_ROOT locally (not S3 yet)

Serializers:
1. AttendanceSerializer — all fields, user read-only

Views:
1. CheckInView(APIView)
   - POST /attendance/checkin/
   - Any authenticated staff
   - Body: lat, lng, photo(optional file upload)
   - Validates lat/lng range: lat -90 to 90, lng -180 to 180
   - Creates Attendance with date=today, check_in_time=now
   - Prevents duplicate check-in for same date

2. CheckOutView(APIView)
   - POST /attendance/checkout/
   - Sets check_out_time=now on today's Attendance record

3. AttendanceListView(ListAPIView)
   - GET /attendance/?user_id=&date=&branch_id=
   - IsManager; paginated

URLs — register under api/v1/attendance/
```

***

## FILE 19 — `fieldvisits/serializers.py` + `fieldvisits/views.py` + `fieldvisits/urls.py`

```
Generate the full fieldvisits app for the Bindu Jewellery Django backend.

Models (generate if not existing):
- FieldVisit: staff(FK User), lead(FK), branch(FK), started_at, ended_at(nullable),
              start_lat, start_lng, status(in_progress/completed/cancelled), notes
- GPSCheckIn: visit(FK), lat, lng, checked_in_at
- VisitReport: visit(OneToOne), summary, outcome, follow_up_required, created_at

Serializers:
1. FieldVisitSerializer
2. GPSCheckInSerializer — validate coords in range
3. VisitReportSerializer

Views:
1. StartVisitView(APIView)
   - POST /fieldvisits/start/
   - field staff role only
   - Body: lead_id, lat, lng
   - Creates FieldVisit with status=in_progress

2. GPSCheckInView(APIView)
   - POST /fieldvisits/{id}/checkin/
   - Creates GPSCheckIn record for that visit

3. SubmitReportView(APIView)
   - POST /fieldvisits/{id}/report/
   - Creates VisitReport, sets visit.status=completed, sets ended_at=now

4. FieldVisitListView(ListAPIView)
   - GET /fieldvisits/?staff_id=&date=&status=
   - IsManager; manager sees own branch only

URLs — register under api/v1/fieldvisits/
```

***

## FILE 20 — `celery_app/tasks/leads.py`

```
Generate celery_app/tasks/leads.py for the Bindu Jewellery Django backend.

All tasks: bind=True, max_retries=3, logger = logging.getLogger('leads')
All model imports INSIDE the function body (not at module top level).

Tasks:
1. send_birthday_wishes(self)
   - Runs daily at 00:00 (see celery_config.py)
   - Matches User.date_of_birth month+day == today (NOT full date, yearly repeat)
   - Gets WhatsAppTemplate with trigger='birthday', is_active=True
   - Calls template.render(user) → sends via WhatsAppService.send_text()
   - Logs: logger.info(f'Birthday wishes sent to {count} users')

2. send_anniversary_wishes(self)
   - Runs daily at 00:01
   - Matches User.join_date month+day == today
   - Gets WhatsAppTemplate with trigger='anniversary'
   - Same send pattern as birthday

3. send_followup_reminders(self)
   - Runs daily at 09:00
   - FollowUp.objects.filter(scheduled_at__date=today, completed=False)
   - WhatsApp message to lead.phone with lead.assigned_to name
   - Also creates Notification for the assigned staff member

4. mark_overdue_leads(self)
   - Runs every 30 mins
   - FollowUp past scheduled_at and not completed → update related lead score -5
   - Log count of overdue follow-ups found

5. send_eod_report(self)
   - Runs daily at 19:00
   - For each active Branch: aggregate today's leads, calls, sales
   - Create Notification for branch manager with summary text
   - Log: logger.info(f'EOD report sent for {branch_count} branches')
```

***

## FILE 21 — `bindu_jewellery_backend/settings/base.py` (additions only)

```
Generate ONLY the additions needed in settings/base.py for the Bindu Jewellery backend.
Do NOT regenerate the whole file — output only the blocks to add/replace.

Add/confirm these blocks:

1. INSTALLED_APPS additions:
   'rest_framework',
   'rest_framework_simplejwt.token_blacklist',
   'corsheaders',
   'django_filters',
   'django_celery_beat',
   'django_celery_results',
   accounts, branches, leads, calls, fieldvisits,
   sales, campaigns, notifications, reports, attendance, core

2. MIDDLEWARE: add 'corsheaders.middleware.CorsMiddleware' before CommonMiddleware

3. REST_FRAMEWORK block (full)

4. SIMPLE_JWT block (full)

5. CELERY block:
   CELERY_BROKER_URL = env('REDIS_URL', default='redis://localhost:6379/0')
   CELERY_RESULT_BACKEND = env('REDIS_URL', default='redis://localhost:6379/0')
   CELERY_ACCEPT_CONTENT = ['json']
   CELERY_TASK_SERIALIZER = 'json'
   CELERY_TIMEZONE = 'Asia/Kolkata'
   CELERY_BEAT_SCHEDULER = 'django_celery_beat.schedulers:DatabaseScheduler'

6. WHATSAPP block:
   WHATSAPP_PHONE_NUMBER_ID = env('WHATSAPP_PHONE_NUMBER_ID', default='')
   WHATSAPP_ACCESS_TOKEN = env('WHATSAPP_ACCESS_TOKEN', default='')
   WHATSAPP_API_VERSION = env('WHATSAPP_API_VERSION', default='v19.0')

7. LOGGING block: loggers for 'leads', 'campaigns', 'whatsapp' writing to console

8. MEDIA_URL = '/media/'
   MEDIA_ROOT = BASE_DIR / 'media'
   (development only — S3 added later in production.py)
```

***

## FILE 22 — Root `urls.py`

```
Generate the root urls.py for the Bindu Jewellery Django backend.

Include all apps under api/v1/:
- api/v1/auth/login/          → TokenObtainPairView
- api/v1/auth/refresh/        → TokenRefreshView
- api/v1/auth/logout/         → TokenBlacklistView
- api/v1/accounts/            → accounts.urls
- api/v1/branches/            → branches.urls
- api/v1/leads/               → leads.urls
- api/v1/calls/               → calls.urls
- api/v1/fieldvisits/         → fieldvisits.urls
- api/v1/sales/               → sales.urls
- api/v1/campaigns/           → campaigns.urls
- api/v1/notifications/       → notifications.urls
- api/v1/reports/             → reports.urls
- api/v1/attendance/          → attendance.urls

Development only:
- Add MEDIA_URL serving via static() for local file uploads
- Add __debug__ = True guard for django-debug-toolbar (if installed)
```

***

## FILE 23 — `.env.development` template

```
Generate a .env.development file template for the Bindu Jewellery backend.
Development values only — not production.

Include:
- DJANGO_SECRET_KEY (generate a random one)
- DEBUG=True
- ALLOWED_HOSTS=localhost,127.0.0.1
- DB_NAME, DB_USER, DB_PASSWORD, DB_HOST=localhost, DB_PORT=5432
- REDIS_URL=redis://localhost:6379/0
- WHATSAPP_PHONE_NUMBER_ID=your-test-phone-number-id
- WHATSAPP_ACCESS_TOKEN=your-test-access-token
- WHATSAPP_API_VERSION=v19.0
- JWT_ACCESS_TOKEN_LIFETIME_MINUTES=60
- JWT_REFRESH_TOKEN_LIFETIME_DAYS=7

Add a comment block at the top:
# Development environment — DO NOT commit to Git
# Copy to .env and fill in real values
# Production overrides go in .env.production (S3, RDS etc.)
```

***

## Generation Order (Follow This Sequence)

| Step | File | Why This Order |
|---|---|---|
| 1 | `core/pagination.py` | Used by all views |
| 2 | `core/permissions.py` | Used by all views |
| 3 | `core/exceptions.py` | Used by settings |
| 4 | `settings/base.py` additions | Must exist before running server |
| 5 | `.env.development` | Needed for settings to load |
| 6 | `accounts/serializers.py` | Auth foundation |
| 7 | `accounts/views.py` + `urls.py` | |
| 8 | `branches/serializers.py` + `views.py` + `urls.py` | |
| 9 | `leads/serializers.py` + `views.py` + `urls.py` | Depends on branches |
| 10 | `calls/` all files | Depends on leads |
| 11 | `sales/` all files | Depends on leads |
| 12 | `campaigns/whatsapp.py` | Needed by tasks |
| 13 | `campaigns/serializers.py` + `views.py` + `urls.py` | |
| 14 | `notifications/` all files | Needed by tasks |
| 15 | `reports/` all files | |
| 16 | `attendance/` all files | |
| 17 | `fieldvisits/` all files | |
| 18 | `celery_app/tasks/leads.py` | Needs all models ready |
| 19 | Root `urls.py` | Wire everything together |

***

## After Each File — Run This

```bash
python manage.py check
# Must show: System check identified no issues (0 silenced).
```

```bash
# After all files done:
python manage.py makemigrations
python manage.py migrate
python manage.py runserver
```

***

## Production Changes (Do NOT Generate Now — Later)

When ready for production, generate separately:
- `settings/production.py` — S3 storage, RDS database, Sentry, DEBUG=False
- `Dockerfile` + `entrypoint.sh`
- `nginx.conf`
- `.env.production` template
- GitHub Actions CI/CD workflow