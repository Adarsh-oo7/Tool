import json
import uuid
import requests
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"

collection = {
    "info": {
        "_postman_id": str(uuid.uuid4()),
        "name": "Bindu Jewellery CRM API (with Examples)",
        "description": "Full API Collection with real example responses.",
        "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
    },
    "variable": [
        {"key": "base_url", "value": "http://127.0.0.1:8000/api/v1", "type": "string"},
        {"key": "token", "value": "YOUR_ACCESS_TOKEN", "type": "string"}
    ],
    "item": []
}

class PostmanGenerator:
    def __init__(self):
        self.session = requests.Session()
        self.token = ""
        self.folders = {}
        
        # Stored IDs for chaining requests
        self.company_id = 1
        self.branch_id = 1
        self.segment_id = 1
        self.user_id = 1
        self.lead_id = 1
        self.visit_id = 1
        self.campaign_id = 1

    def set_auth(self, access_token):
        self.token = access_token
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def get_folder(self, name):
        if name not in self.folders:
            self.folders[name] = {"name": name, "item": []}
            collection["item"].append(self.folders[name])
        return self.folders[name]

    def add_request(self, folder_name, name, method, endpoint, payload=None, auth=True):
        url = BASE_URL + endpoint
        
        # 1. Make the real request
        headers = {}
        if auth and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
            
        print(f"Executing {method} {url}")
        
        try:
            if method == "GET":
                resp = self.session.get(url, headers=headers)
            elif method == "POST":
                resp = self.session.post(url, json=payload, headers=headers)
            elif method == "PATCH":
                resp = self.session.patch(url, json=payload, headers=headers)
            elif method == "DELETE":
                resp = self.session.delete(url, headers=headers)
            else:
                resp = self.session.get(url, headers=headers)
                
            resp_body = resp.text
            try:
                # Pretty print JSON response if possible
                resp_body = json.dumps(resp.json(), indent=4)
            except:
                pass
                
            status_code = resp.status_code
            status_text = resp.reason
        except Exception as e:
            resp_body = json.dumps({"error": str(e)}, indent=4)
            status_code = 500
            status_text = "Internal Server Error"
            
        # Extract IDs for subsequent requests if we just created them
        try:
            data = resp.json()
            if method == "POST" and status_code in (200, 201) and isinstance(data, dict):
                if "id" in data:
                    if "/branches/companies/" in endpoint: self.company_id = data["id"]
                    elif "/branches/branches/" in endpoint: self.branch_id = data["id"]
                    elif "/branches/segments/" in endpoint: self.segment_id = data["id"]
                    elif "/accounts/users/" in endpoint: self.user_id = data["id"]
                    elif "/leads/leads/" in endpoint: self.lead_id = data["id"]
                    elif "/field-visits/fieldvisits/" in endpoint: self.visit_id = data["id"]
                    elif "/campaigns/campaigns/" in endpoint: self.campaign_id = data["id"]
        except:
            pass

        # 2. Build Postman Request Object
        req_obj = {
            "method": method,
            "header": [{"key": "Content-Type", "value": "application/json", "type": "text"}],
            "url": {
                "raw": "{{base_url}}" + endpoint,
                "host": ["{{base_url}}"],
                "path": [p for p in endpoint.split("/") if p]
            }
        }
        if auth:
            req_obj["auth"] = {"type": "bearer", "bearer": [{"key": "token", "value": "{{token}}", "type": "string"}]}
        if payload:
            req_obj["body"] = {"mode": "raw", "raw": json.dumps(payload, indent=4)}
            
        # 3. Build Postman Response Example Object
        response_obj = {
            "name": f"Example ({status_code} {status_text})",
            "originalRequest": req_obj,
            "status": status_text,
            "code": status_code,
            "_postman_previewlanguage": "json",
            "header": [{"key": "Content-Type", "value": "application/json"}],
            "cookie": [],
            "body": resp_body
        }

        # 4. Add to folder
        self.get_folder(folder_name)["item"].append({
            "name": name,
            "request": req_obj,
            "response": [response_obj]
        })
        
        return resp

# Generate Flow
TS = str(int(time.time()))[-5:]
gen = PostmanGenerator()

# --- 1. Auth ---
login_resp = gen.add_request("1. Auth", "Login", "POST", "/auth/login/", {"email": "admin@bindu.com", "password": "Admin@123"}, auth=False)
if login_resp.status_code == 200:
    gen.set_auth(login_resp.json()["access"])
    refresh_token = login_resp.json()["refresh"]
else:
    print("FATAL: Admin login failed. Cannot generate authenticated examples.")
    refresh_token = "dummy_refresh"

gen.add_request("1. Auth", "Refresh Token", "POST", "/auth/refresh/", {"refresh": refresh_token}, auth=False)
gen.add_request("1. Auth", "Get Profile", "GET", "/accounts/me/")
gen.add_request("1. Auth", "Update FCM Token", "POST", "/accounts/fcm-token/", {"fcm_token": "token_123", "device_type": "android"})

# --- 2. Branches ---
gen.add_request("2. Branches", "List Companies", "GET", "/branches/companies/")
gen.add_request("2. Branches", "Create Company", "POST", "/branches/companies/", {"name": f"Test Company {TS}", "phone": "0471000000", "email": "info@bindu.com"})
gen.add_request("2. Branches", "List Branches", "GET", "/branches/branches/")
gen.add_request("2. Branches", "Create Branch", "POST", "/branches/branches/", {"company": gen.company_id, "name": f"Test Branch {TS}", "address": "Test Addr", "phone": "0471111111", "lat": "8.5", "lng": "76.9"})
gen.add_request("2. Branches", "List Segments", "GET", "/branches/segments/")
gen.add_request("2. Branches", "Create Segment", "POST", "/branches/segments/", {"branch": gen.branch_id, "name": f"Bridal {TS}"})

# --- 3. Accounts ---
gen.add_request("3. Accounts", "List Users", "GET", "/accounts/users/")
gen.add_request("3. Accounts", "Create Staff", "POST", "/accounts/users/", {"full_name": f"Staff {TS}", "email": f"staff{TS}@bindu.com", "phone": f"90000{TS}", "role": "staff", "branch": gen.branch_id, "password": "Staff@123", "password2": "Staff@123"})
gen.add_request("3. Accounts", "Set Role", "POST", f"/accounts/users/{gen.user_id}/set-role/", {"role": "manager"})
gen.add_request("3. Accounts", "Get User Details", "GET", f"/accounts/users/{gen.user_id}/")
gen.add_request("3. Accounts", "List Staff By Branch", "GET", f"/accounts/staff/?branch_id={gen.branch_id}")

# --- 4. Leads ---
gen.add_request("4. Leads", "List Leads", "GET", "/leads/leads/")
gen.add_request("4. Leads", "Create Lead", "POST", "/leads/leads/", {"name": f"Lead {TS}", "phone": f"91000{TS}", "email": f"lead{TS}@test.com", "source": "walkin", "stage": "new", "branch": gen.branch_id})
gen.add_request("4. Leads", "Change Lead Stage", "PATCH", f"/leads/leads/{gen.lead_id}/stage/", {"stage": "contacted"})
gen.add_request("4. Leads", "Assign Lead", "POST", f"/leads/leads/{gen.lead_id}/assign/", {"user_id": gen.user_id})
gen.add_request("4. Leads", "Create Followup", "POST", "/leads/followups/", {"lead": gen.lead_id, "scheduled_date": "2026-06-01", "note": "Call back"})
gen.add_request("4. Leads", "Get Lead Activities", "GET", f"/leads/activities/?lead={gen.lead_id}")

# --- 5. Calls ---
gen.add_request("5. Calls", "List Call Logs", "GET", "/calls/call-logs/")
gen.add_request("5. Calls", "Create Call Log", "POST", "/calls/call-logs/", {"lead": gen.lead_id, "outcome": "interested", "duration_seconds": 120, "notes": "Test call"})

# --- 6. Field Visits ---
gen.add_request("6. Field Visits", "List Field Visits", "GET", "/field-visits/fieldvisits/")
gen.add_request("6. Field Visits", "Create Field Visit", "POST", "/field-visits/fieldvisits/", {"lead": gen.lead_id, "start_lat": "8.5", "start_lng": "76.9"})
gen.add_request("6. Field Visits", "GPS Check-in", "POST", f"/field-visits/{gen.visit_id}/checkin/", {"lat": "8.52", "lng": "76.92"})
gen.add_request("6. Field Visits", "Submit Visit Report", "POST", "/field-visits/visit-reports/", {"visit": gen.visit_id, "outcome": "interested", "time_spent_minutes": 30, "notes": "Test visit"})

# --- 7. Sales ---
gen.add_request("7. Sales", "List Sales", "GET", "/sales/sales/")
gen.add_request("7. Sales", "Create Sale", "POST", "/sales/sales/", {"lead": gen.lead_id, "segment": gen.segment_id, "product_name": "Test Ring", "amount": "15000.00", "weight_grams": "5.00", "notes": "Test sale"})

# --- 8. Campaigns ---
gen.add_request("8. Campaigns", "List Templates", "GET", "/campaigns/templates/")
gen.add_request("8. Campaigns", "Create Template", "POST", "/campaigns/templates/", {"name": f"Template {TS}", "trigger": "birthday", "message": "Hi!", "is_active": True})
gen.add_request("8. Campaigns", "List Campaigns", "GET", "/campaigns/campaigns/")
gen.add_request("8. Campaigns", "Create Campaign", "POST", "/campaigns/campaigns/", {"name": f"Campaign {TS}", "branch": gen.branch_id, "campaign_type": "festival", "message": "Promo!"})

# --- 9. Notifications ---
gen.add_request("9. Notifications", "List Notifications", "GET", "/notifications/notifications/")
gen.add_request("9. Notifications", "Get Unread Count", "GET", "/notifications/notifications/unread-count/")
gen.add_request("9. Notifications", "Mark All Read", "POST", "/notifications/read-all/")

# --- 10. Attendance ---
gen.add_request("10. Attendance", "List Attendance", "GET", "/attendance/attendance/")
gen.add_request("10. Attendance", "Check In", "POST", "/attendance/checkin/", {"lat": 8.5, "lng": 76.9})

# --- 11. Reports ---
gen.add_request("11. Reports", "List Reports", "GET", "/reports/reports/")
gen.add_request("11. Reports", "Get Daily Snapshot", "GET", f"/reports/snapshot/?branch_id={gen.branch_id}&period=daily")

# Save file
with open("C:/Users/adars/Desktop/bectree/code/Project1/bindu_jewellery_backend/postman_collection.json", "w") as f:
    json.dump(collection, f, indent=2)

print("Collection created successfully with real example responses.")
