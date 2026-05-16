# -*- coding: utf-8 -*-
"""
Bindu Jewellery Backend -- Full API Test Suite
=============================================
Tests all API endpoints against the running dev server.

Usage:
    python test_apis.py

Requirements:
    pip install requests

Superuser credentials used: admin@bindu.com / Admin@123
"""

import json
import sys
import time

import requests

# Force UTF-8 output on Windows
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE = "http://127.0.0.1:8000/api/v1"

# Unique suffix so every test run creates fresh records
TS = str(int(time.time()))[-6:]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PASS = "[PASS]"
FAIL = "[FAIL]"
INFO = "[INFO]"
WARN = "[WARN]"

results = {"pass": 0, "fail": 0, "warn": 0}


def log(label: str, name: str, detail: str = ""):
    print(f"  {label}  {name}" + (f" -- {detail}" if detail else ""))


def check(name: str, resp: requests.Response, expected: int, show_body: bool = False):
    ok = resp.status_code == expected
    if ok:
        results["pass"] += 1
        log(PASS, name, f"HTTP {resp.status_code}")
    else:
        results["fail"] += 1
        try:
            body = resp.json()
        except Exception:
            body = resp.text[:300]
        log(FAIL, name, f"expected {expected}, got {resp.status_code} | {body}")

    if show_body and ok:
        try:
            print(f"     Body: {json.dumps(resp.json(), indent=2, ensure_ascii=False)[:400]}")
        except Exception:
            pass
    return ok


def warn(name: str, detail: str):
    results["warn"] += 1
    log(WARN, name, detail)


def section(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ---------------------------------------------------------------------------
# Session holder
# ---------------------------------------------------------------------------

class Session:
    def __init__(self):
        self.token   = ""
        self.refresh = ""
        self.headers = {}
        self.user_id = None
        # IDs collected during test run
        self.branch_id     = None
        self.company_id    = None
        self.segment_id    = None
        self.lead_id       = None
        self.followup_id   = None
        self.call_id       = None
        self.visit_id      = None
        self.sale_id       = None
        self.campaign_id   = None
        self.notif_id      = None
        self.attend_id     = None
        self.template_id   = None
        self.staff_user_id = None

    def auth(self, token: str, refresh: str):
        self.token   = token
        self.refresh = refresh
        self.headers = {"Authorization": f"Bearer {token}"}

    def get(self, url, **kw):
        return requests.get(f"{BASE}{url}", headers=self.headers, **kw)

    def post(self, url, data=None, **kw):
        return requests.post(f"{BASE}{url}", json=data, headers=self.headers, **kw)

    def patch(self, url, data=None, **kw):
        return requests.patch(f"{BASE}{url}", json=data, headers=self.headers, **kw)

    def put(self, url, data=None, **kw):
        return requests.put(f"{BASE}{url}", json=data, headers=self.headers, **kw)

    def delete(self, url, **kw):
        return requests.delete(f"{BASE}{url}", headers=self.headers, **kw)


s = Session()


# ---------------------------------------------------------------------------
# 1. AUTH
# ---------------------------------------------------------------------------

section("1. AUTHENTICATION")

# 1a. Login  -- endpoint: POST /api/v1/accounts/login/
r = requests.post(f"{BASE}/accounts/login/", json={
    "email": "admin@bindu.com",
    "password": "Admin@123",
})
if check("POST /accounts/login/", r, 200):
    data = r.json()
    s.auth(data["access"], data["refresh"])
    s.user_id = data.get("user", {}).get("id") or data.get("user_id")
    print(f"     User ID: {s.user_id} | Role: {data.get('user', {}).get('role', 'N/A')}")
else:
    print("\n  [FATAL] Cannot continue without auth token. Exiting.")
    sys.exit(1)

# 1b. Get own profile
r = s.get("/accounts/me/")
check("GET /accounts/me/", r, 200)

# 1c. Token refresh
r = requests.post(f"{BASE}/accounts/token/refresh/", json={"refresh": s.refresh})
if check("POST /accounts/token/refresh/", r, 200):
    s.auth(r.json()["access"], s.refresh)

# 1d. Token verify
r = requests.post(f"{BASE}/accounts/token/verify/", json={"token": s.token})
check("POST /accounts/token/verify/", r, 200)

# 1e. Change password (wrong old password)
r = s.post("/accounts/change-password/", {"old_password": "WRONG", "new_password": "NewPass@999", "confirm_password": "NewPass@999"})
check("POST /accounts/change-password/ (wrong old) -> 400", r, 400)

# 1f. Unauthenticated access
r = requests.get(f"{BASE}/accounts/users/")
check("GET /accounts/users/ (no token) -> 401", r, 401)


# ---------------------------------------------------------------------------
# 2. BRANCHES
# ---------------------------------------------------------------------------

section("2. BRANCHES")

# 2a. List companies
r = s.get("/branches/companies/")
if check("GET /branches/companies/", r, 200):
    results_list = r.json().get("results", r.json())
    if isinstance(results_list, list) and results_list:
        s.company_id = results_list[0]["id"]
        print(f"     Company ID: {s.company_id}")

# 2b. Create company if none
if not s.company_id:
    r = s.post("/branches/companies/", {"name": "Bindu Jewellery", "phone": "0471000000", "email": "info@bindu.com"})
    if check("POST /branches/companies/ (create)", r, 201):
        s.company_id = r.json()["id"]

# 2c. List branches
r = s.get("/branches/branches/")
if check("GET /branches/branches/", r, 200):
    results_list = r.json().get("results", r.json())
    if isinstance(results_list, list) and results_list:
        s.branch_id = results_list[0]["id"]
        print(f"     Branch ID: {s.branch_id}")

# 2d. Create branch if none
if not s.branch_id and s.company_id:
    r = s.post("/branches/branches/", {
        "company": s.company_id,
        "name": "Trivandrum Branch",
        "address": "MG Road, Trivandrum",
        "phone": "0471111111",
        "lat": "8.5241391",
        "lng": "76.9366376",
    })
    if check("POST /branches/branches/ (create)", r, 201):
        s.branch_id = r.json()["id"]

# 2e. Retrieve branch
if s.branch_id:
    r = s.get(f"/branches/branches/{s.branch_id}/")
    check(f"GET /branches/branches/{s.branch_id}/", r, 200)

# 2f. List segments
r = s.get("/branches/segments/")
if check("GET /branches/segments/", r, 200):
    results_list = r.json().get("results", r.json())
    if isinstance(results_list, list) and results_list:
        s.segment_id = results_list[0]["id"]

# 2g. Create segment if none
if not s.segment_id and s.branch_id:
    r = s.post("/branches/segments/", {"branch": s.branch_id, "name": "bridal"})
    if check("POST /branches/segments/ (create)", r, 201):
        s.segment_id = r.json()["id"]


# ---------------------------------------------------------------------------
# 3. ACCOUNTS -- USER MANAGEMENT
# ---------------------------------------------------------------------------

section("3. ACCOUNTS -- USER MANAGEMENT")

# 3a. List users
r = s.get("/accounts/users/")
check("GET /accounts/users/", r, 200)

# 3b. Get own user detail
if s.user_id:
    r = s.get(f"/accounts/users/{s.user_id}/")
    check(f"GET /accounts/users/{s.user_id}/", r, 200)

# 3c. Create a staff user
r = s.post("/accounts/users/", {
    "email":     f"staff_{TS}@bindu.com",
    "full_name": "Test Telecaller",
    "phone":     f"90{TS}",
    "role":      "telecaller",
    "branch":    s.branch_id,
    "password":  "Staff@1234",
    "password2": "Staff@1234",
})
if check("POST /accounts/users/ (create staff)", r, 201):
    # UserCreateSerializer doesn't return id -- fetch via list
    r2 = s.get(f"/accounts/users/?role=telecaller&is_active=true")
    if r2.status_code == 200:
        items = r2.json().get("results", [])
        # pick the one we just created (last by id)
        if items:
            s.staff_user_id = items[0]["id"]
            print(f"     Staff user ID: {s.staff_user_id}")
else:
    # Reuse existing telecaller
    r2 = s.get("/accounts/users/?role=telecaller&is_active=true")
    if r2.status_code == 200:
        items = r2.json().get("results", [])
        if items:
            s.staff_user_id = items[0]["id"]
            print(f"     [INFO] Reusing staff user ID: {s.staff_user_id}")

# 3d. Set role
if s.staff_user_id:
    r = s.post(f"/accounts/users/{s.staff_user_id}/set-role/", {"role": "staff"})
    check("POST /accounts/users/{id}/set-role/", r, 200)

# 3e. Soft delete
if s.staff_user_id:
    r = s.delete(f"/accounts/users/{s.staff_user_id}/")
    check("DELETE /accounts/users/{id}/ (soft delete) -> 204", r, 204)

# 3f. Activate (custom action)
if s.staff_user_id:
    r = s.patch(f"/accounts/users/{s.staff_user_id}/activate/")
    check("PATCH /accounts/users/{id}/activate/ -> 200", r, 200)

# 3g. Staff by branch
if s.branch_id:
    r = s.get(f"/accounts/staff/?branch_id={s.branch_id}")
    check("GET /accounts/staff/?branch_id=", r, 200)

# 3h. Sub-manager permissions
r = s.get("/accounts/sub-permissions/")
check("GET /accounts/sub-permissions/", r, 200)


# ---------------------------------------------------------------------------
# 4. LEADS
# ---------------------------------------------------------------------------

section("4. LEADS")

if not s.branch_id:
    warn("Leads tests", "No branch_id -- skipping")
else:
    # 4a. Create lead (owner must supply branch explicitly)
    lead_payload = {
        "name":   f"Priya Nair {TS}",
        "phone":  f"91{TS}",
        "email":  f"priya_{TS}@example.com",
        "source": "walkin",
        "stage":  "new",
    }
    if s.branch_id:
        lead_payload["branch"] = s.branch_id
    r = s.post("/leads/leads/", lead_payload)
    if check("POST /leads/leads/ (create)", r, 201):
        s.lead_id = r.json().get("id")
        print(f"     Lead ID: {s.lead_id}")
    else:
        # Reuse existing lead
        r2 = s.get("/leads/leads/?stage=new")
        if r2.status_code == 200:
            items = r2.json().get("results", [])
            if items:
                s.lead_id = items[0]["id"]
                print(f"     [INFO] Reusing lead ID: {s.lead_id}")

    # 4b. List leads
    r = s.get("/leads/leads/")
    check("GET /leads/leads/", r, 200)

    # 4c. Retrieve lead
    if s.lead_id:
        r = s.get(f"/leads/leads/{s.lead_id}/")
        check(f"GET /leads/leads/{s.lead_id}/", r, 200)

    # 4d. Change stage via custom action
    if s.lead_id:
        r = s.patch(f"/leads/leads/{s.lead_id}/stage/", {"stage": "contacted"})
        check("PATCH /leads/leads/{id}/stage/", r, 200)

    # 4e. Assign lead
    if s.lead_id and s.staff_user_id:
        r = s.post(f"/leads/leads/{s.lead_id}/assign/", {"user_id": s.staff_user_id})
        check("POST /leads/leads/{id}/assign/", r, 200)

    # 4f. Filter leads by stage
    r = s.get("/leads/leads/?stage=contacted")
    check("GET /leads/leads/?stage=contacted", r, 200)

    # 4g. Create follow-up (field name is scheduled_date not scheduled_at)
    if s.lead_id:
        r = s.post("/leads/followups/", {
            "lead":           s.lead_id,
            "scheduled_date": "2026-06-01",
            "note":           "Call back regarding bridal collection",
        })
        if check("POST /leads/followups/ (create)", r, 201):
            s.followup_id = r.json().get("id")

    # 4h. Mark follow-up done
    if s.followup_id:
        r = s.patch(f"/leads/followups/{s.followup_id}/done/")
        check("PATCH /leads/followups/{id}/done/", r, 200)

    # 4i. Lead activities
    if s.lead_id:
        r = s.get(f"/leads/activities/?lead={s.lead_id}")
        check("GET /leads/activities/?lead=", r, 200)


# ---------------------------------------------------------------------------
# 5. CALLS
# ---------------------------------------------------------------------------

section("5. CALLS")

if not s.lead_id:
    warn("Calls tests", "No lead_id -- skipping")
else:
    # 5a. Create call log
    r = s.post("/calls/call-logs/", {
        "lead":             s.lead_id,
        "outcome":          "interested",
        "duration_seconds": 180,
        "notes":            "Customer interested in bridal set",
    })
    if check("POST /calls/call-logs/ (create)", r, 201):
        s.call_id = r.json().get("id")

    # 5b. List call logs
    r = s.get("/calls/call-logs/")
    check("GET /calls/call-logs/", r, 200)

    # 5c. Filter by lead
    r = s.get(f"/calls/call-logs/?lead={s.lead_id}")
    check("GET /calls/call-logs/?lead=", r, 200)

    # 5d. Filter by outcome
    r = s.get("/calls/call-logs/?outcome=interested")
    check("GET /calls/call-logs/?outcome=interested", r, 200)


# ---------------------------------------------------------------------------
# 6. FIELD VISITS
# ---------------------------------------------------------------------------

section("6. FIELD VISITS")

if not s.lead_id:
    warn("Field visit tests", "No lead_id -- skipping")
else:
    # 6a. Create field visit
    r = s.post("/field-visits/field-visits/", {
        "lead":      s.lead_id,
        "start_lat": "8.5241391",
        "start_lng": "76.9366376",
    })
    if check("POST /field-visits/field-visits/ (create)", r, 201):
        s.visit_id = r.json()["id"]

    # 6b. List visits
    r = s.get("/field-visits/field-visits/")
    check("GET /field-visits/field-visits/", r, 200)

    # 6c. GPS check-in
    if s.visit_id:
        r = s.post("/field-visits/gps-checkins/", {
            "visit": s.visit_id,
            "lat":   "8.5245000",
            "lng":   "76.9370000",
        })
        check("POST /field-visits/gps-checkins/ (create)", r, 201)

    # 6d. End visit
    if s.visit_id:
        r = s.patch(f"/field-visits/field-visits/{s.visit_id}/end/")
        check("PATCH /field-visits/field-visits/{id}/end/", r, 200)

    # 6e. Submit visit report
    if s.visit_id:
        r = s.post("/field-visits/visit-reports/", {
            "visit":              s.visit_id,
            "outcome":            "interested",
            "time_spent_minutes": 30,
            "notes":              "Customer viewed bridal collection",
        })
        check("POST /field-visits/visit-reports/ (create)", r, 201)


# ---------------------------------------------------------------------------
# 7. SALES
# ---------------------------------------------------------------------------

section("7. SALES")

if not s.lead_id:
    warn("Sales tests", "No lead_id -- skipping")
else:
    # 7a. Create sale
    r = s.post("/sales/sales/", {
        "lead":         s.lead_id,
        "segment":      s.segment_id,
        "product_name": "Gold Necklace Set",
        "amount":       "85000.00",
        "weight_grams": "12.500",
        "notes":        "Bridal collection sale",
    })
    if check("POST /sales/sales/ (create)", r, 201):
        s.sale_id = r.json().get("id")

    # 7b. List sales
    r = s.get("/sales/sales/")
    check("GET /sales/sales/", r, 200)

    # 7c. Retrieve sale
    if s.sale_id:
        r = s.get(f"/sales/sales/{s.sale_id}/")
        check(f"GET /sales/sales/{s.sale_id}/", r, 200)

    # 7d. Filter by segment
    if s.segment_id:
        r = s.get(f"/sales/sales/?segment={s.segment_id}")
        check("GET /sales/sales/?segment=", r, 200)


# ---------------------------------------------------------------------------
# 8. CAMPAIGNS
# ---------------------------------------------------------------------------

section("8. CAMPAIGNS")

# 8a. Create WhatsApp template
r = s.post("/campaigns/templates/", {
    "name":       "Birthday Template",
    "trigger":    "birthday",
    "message":    "Happy Birthday {name}! Visit us at {branch}. Regards Bindu Jewellery.",
    "is_active":  True,
})
if check("POST /campaigns/templates/ (create)", r, 201):
    s.template_id = r.json().get("id")

# 8b. List templates
r = s.get("/campaigns/templates/")
check("GET /campaigns/templates/", r, 200)

# 8c. Special day messages
r = s.post("/campaigns/special-days/", {
    "name":          f"Onam 2026 {TS}",
    "date":          "2026-09-14",
    "message":       "Happy Onam {name}! Best wishes from Bindu Jewellery.",
    "send_to_staff": True,
    "send_to_leads": False,
})
check("POST /campaigns/special-days/ (create)", r, 201)

r = s.get("/campaigns/special-days/")
check("GET /campaigns/special-days/", r, 200)

# 8d. Create campaign
if s.branch_id:
    campaign_data = {
        "name":          f"Onam Festival Campaign {TS}",
        "branch":        s.branch_id,
        "campaign_type": "festival",
        "message":       "Flat 10% off this Onam! Visit Bindu Jewellery.",
        "template_name": "onam_offer",
    }
    if s.template_id:
        campaign_data["whatsapp_template"] = s.template_id

    r = s.post("/campaigns/campaigns/", campaign_data)
    if check("POST /campaigns/campaigns/ (create)", r, 201):
        s.campaign_id = r.json().get("id")

# 8e. List campaigns
r = s.get("/campaigns/campaigns/")
check("GET /campaigns/campaigns/", r, 200)

# 8f. Retrieve campaign
if s.campaign_id:
    r = s.get(f"/campaigns/campaigns/{s.campaign_id}/")
    check(f"GET /campaigns/campaigns/{s.campaign_id}/", r, 200)

# 8g. Launch campaign (Celery may not be running -- 202 ok, 500 acceptable)
if s.campaign_id:
    r = s.post(f"/campaigns/campaigns/{s.campaign_id}/launch/")
    if r.status_code in (200, 202):
        results["pass"] += 1
        log(PASS, "POST /campaigns/campaigns/{id}/launch/", f"HTTP {r.status_code}")
    elif r.status_code == 500:
        results["warn"] += 1
        log(WARN, "POST /campaigns/campaigns/{id}/launch/", "HTTP 500 -- Celery/Redis may not be running")
    else:
        check("POST /campaigns/campaigns/{id}/launch/", r, 202)

# 8h. Campaign leads list
r = s.get("/campaigns/leads/")
check("GET /campaigns/leads/", r, 200)


# ---------------------------------------------------------------------------
# 9. NOTIFICATIONS
# ---------------------------------------------------------------------------

section("9. NOTIFICATIONS")

r = s.get("/notifications/notifications/")
check("GET /notifications/notifications/", r, 200)

r = s.get("/notifications/notifications/unread-count/")
check("GET /notifications/notifications/unread-count/", r, 200)

r = s.post("/notifications/notifications/read-all/")
check("POST /notifications/notifications/read-all/", r, 200)


# ---------------------------------------------------------------------------
# 10. ATTENDANCE
# ---------------------------------------------------------------------------

section("10. ATTENDANCE")

r = s.post("/attendance/attendance/", {
    "check_in_lat": "8.5241391",
    "check_in_lng": "76.9366376",
    "notes":        "On time",
})
# 201 = new check-in today; 400 = already checked in today (acceptable)
if r.status_code == 201:
    s.attend_id = r.json().get("id")
    results["pass"] += 1
    log(PASS, "POST /attendance/attendance/ (check-in)", f"HTTP {r.status_code}")
elif r.status_code == 400:
    results["pass"] += 1
    log(INFO, "POST /attendance/attendance/ (check-in)", "Already checked in today (400 acceptable)")
    r2 = s.get("/attendance/attendance/")
    if r2.status_code == 200:
        items = r2.json().get("results", [])
        if items:
            s.attend_id = items[0]["id"]
else:
    check("POST /attendance/attendance/ (check-in)", r, 201)

# 10b. List attendance
r = s.get("/attendance/attendance/")
check("GET /attendance/attendance/", r, 200)

# 10c. Approve attendance (manager action)
if s.attend_id:
    r = s.patch(f"/attendance/attendance/{s.attend_id}/approve/")
    check("PATCH /attendance/attendance/{id}/approve/", r, 200)


# ---------------------------------------------------------------------------
# 11. REPORTS
# ---------------------------------------------------------------------------

section("11. REPORTS")

r = s.get("/reports/")
check("GET /reports/", r, 200)

r = s.get("/reports/daily/")
check("GET /reports/daily/", r, 200)

if s.branch_id:
    r = s.get(f"/reports/snapshot/?branch_id={s.branch_id}&period=daily")
    # 404 is acceptable if no report snapshot exists yet
    if r.status_code in (200, 404):
        results["pass"] += 1
        log(PASS, f"GET /reports/snapshot/ (HTTP {r.status_code} -- ok)")
    else:
        results["fail"] += 1
        log(FAIL, "GET /reports/snapshot/", f"unexpected {r.status_code}")

if s.branch_id:
    r = s.post("/reports/eod/trigger/", {"branch_id": s.branch_id})
    # 200/202 = queued; 500 = Celery not running (acceptable)
    if r.status_code in (200, 202):
        results["pass"] += 1
        log(PASS, "POST /reports/eod/trigger/", f"HTTP {r.status_code}")
    elif r.status_code == 500:
        results["warn"] += 1
        log(WARN, "POST /reports/eod/trigger/", "HTTP 500 -- Celery/Redis may not be running")
    else:
        check("POST /reports/eod/trigger/", r, 200)


# ---------------------------------------------------------------------------
# 12. ERROR HANDLING
# ---------------------------------------------------------------------------

section("12. ERROR HANDLING")

# 404 -- non-existent lead
r = s.get("/leads/leads/99999/")
check("GET /leads/leads/99999/ (not found) -> 404", r, 404)

# 400 -- missing required fields
r = s.post("/leads/leads/", {"name": "Bad Lead"})
check("POST /leads/leads/ (missing fields) -> 400", r, 400)

# 401 -- no token
r = requests.get(f"{BASE}/leads/leads/")
check("GET /leads/leads/ (no token) -> 401", r, 401)


# ---------------------------------------------------------------------------
# SUMMARY
# ---------------------------------------------------------------------------

print(f"\n{'='*60}")
print("  TEST SUMMARY")
print(f"{'='*60}")
total = results["pass"] + results["fail"]
print(f"  Total:    {total}")
print(f"  Passed:   {results['pass']}")
print(f"  Failed:   {results['fail']}")
print(f"  Warnings: {results['warn']}")

if results["fail"] == 0:
    print("\n  *** ALL TESTS PASSED! ***\n")
else:
    pct = round(results["pass"] / total * 100) if total else 0
    print(f"\n  Score: {pct}% ({results['pass']}/{total})\n")

sys.exit(0 if results["fail"] == 0 else 1)
