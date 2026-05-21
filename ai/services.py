"""
Bindu Jewellery AI Service
Primary: GLM-5.1 via Modal.com (OpenAI-compatible API, no rate limits)
Fallback: Gemini (if GLM key not configured)
"""
import re
import requests
import time
from django.conf import settings
from django.db.models import Sum, Count
from django.utils import timezone
from datetime import timedelta, date


# ─── Data Fetchers ────────────────────────────────────────────────────────────

def _leads_context():
    from leads.models import Lead
    from django.db.models import Count as C, Q
    since_7d = timezone.now() - timedelta(days=7)
    
    metrics = Lead.objects.aggregate(
        total=C('id'),
        new_7d=C('id', filter=Q(created_at__gte=since_7d)),
        hot=C('id', filter=Q(is_hot=True)),
        converted=C('id', filter=Q(stage='converted'))
    )
    
    total     = metrics['total'] or 0
    new_7d    = metrics['new_7d'] or 0
    hot       = metrics['hot'] or 0
    converted = metrics['converted'] or 0
    conv_rate = round((converted / total * 100), 1) if total else 0

    by_stage  = list(Lead.objects.values('stage').annotate(n=C('id')).order_by('-n'))
    by_source = list(Lead.objects.values('source').annotate(n=C('id')).order_by('-n'))

    # Only take top 5 hot leads to keep prompt size tiny
    hot_leads = list(Lead.objects.filter(is_hot=True)
                     .select_related('assigned_to', 'branch')
                     .values('name', 'phone', 'stage', 'source',
                             'assigned_to__full_name', 'branch__name')[:5])

    return {
        "total": total, "new_last_7_days": new_7d, "hot": hot,
        "converted": converted, "conversion_rate_pct": conv_rate,
        "by_stage": by_stage[:4], "by_source": by_source[:4],
        "hot_leads_sample": hot_leads
    }


def normalize_grams(val):
    if not val: return 0.0
    val = float(val)
    # Legacy data was stored in INR. If value is unusually large for grams (>1000), convert it.
    if val > 1000:
        return round(val / 7500, 2)
    return round(val, 2)

def _sales_context():
    from sales.models import Sale
    now = timezone.now()
    since_7d  = now - timedelta(days=7)
    since_30d = now - timedelta(days=30)
    today     = timezone.localdate()

    today_sales = Sale.objects.filter(created_at__date=today)
    week_sales  = Sale.objects.filter(created_at__gte=since_7d)
    month_sales = Sale.objects.filter(created_at__gte=since_30d)
    
    # Only take top 5 recent sales to keep prompt size tiny
    recent_sales = list(Sale.objects.filter(created_at__gte=since_30d).order_by('-created_at').values('created_at', 'amount', 'staff__full_name', 'branch__name')[:5])

    def fmt(d): return d.strftime('%d %b')

    return {
        "today":   {"date": fmt(today), "count": today_sales.count(), "gold_sold_g": normalize_grams(today_sales.aggregate(t=Sum('amount'))['t'])},
        "week":    {"start_date": fmt(since_7d), "end_date": fmt(now), "count": week_sales.count(),  "gold_sold_g": normalize_grams(week_sales.aggregate(t=Sum('amount'))['t'])},
        "month":   {"start_date": fmt(since_30d), "end_date": fmt(now), "count": month_sales.count(), "gold_sold_g": normalize_grams(month_sales.aggregate(t=Sum('amount'))['t'])},
        "recent_sales_log": [
            {"date": r['created_at'].strftime('%d %b, %H:%M'), "gold_sold_g": normalize_grams(r['amount']), "staff": r['staff__full_name'], "branch": r['branch__name']}
            for r in recent_sales
        ]
    }


def _attendance_context():
    from attendance.models import Attendance
    today = timezone.localdate()
    qs    = Attendance.objects.filter(date=today)
    return {
        "date": str(today),
        "present": qs.filter(status='present').count(),
        "late":    qs.filter(status='late').count(),
        "absent":  qs.filter(status='absent').count(),
        "pending": qs.filter(status='pending').count(),
        "total":   qs.count(),
    }


def _branches_context():
    from branches.models import Branch
    from leads.models import Lead
    from sales.models import Sale
    from django.db.models import Sum, Count as C
    
    # Optimize with annotation
    branches = Branch.objects.annotate(
        leads_count=C('leads'),
        total_revenue=Sum('sales__amount')
    )
    
    rows = []
    for b in branches:
        rows.append({
            "branch": b.name, 
            "leads": b.leads_count, 
            "gold_sold_g": normalize_grams(b.total_revenue)
        })
    return rows


def _campaigns_context():
    try:
        from campaigns.models import Campaign
        # Only take top 5 active/recent campaigns to keep prompt tiny
        camps = list(Campaign.objects.values(
            'name', 'status', 'channel_type',
            'sent_count', 'total_leads', 'roi_percent'
        )[:5])
        active = sum(1 for c in camps if c.get('status') == 'active')
        total_reach = sum(c.get('sent_count') or 0 for c in camps)
        total_leads = sum(c.get('total_leads') or 0 for c in camps)
        return {
            "total": len(camps), "active": active,
            "total_reach": total_reach, "total_leads_generated": total_leads,
            "campaigns": camps
        }
    except Exception as e:
        return {"error": str(e)}


def _staff_context():
    from accounts.models import User
    from leads.models import Lead
    from sales.models import Sale
    from django.db.models import Sum, Count as C
    since_30d = timezone.now() - timedelta(days=30)

    staff = User.objects.filter(
        role__in=['staff', 'manager', 'sub_manager', 'telecaller', 'field_staff']
    ).select_related('branch')

    # Fetch all leads counted by staff in one query
    lead_counts = Lead.objects.filter(
        created_at__gte=since_30d,
        assigned_to__in=staff
    ).values('assigned_to').annotate(c=C('id'))
    lead_map = {x['assigned_to']: x['c'] for x in lead_counts}

    # Fetch all sales counted and summed by staff in one query
    sales_data = Sale.objects.filter(
        created_at__gte=since_30d,
        staff__in=staff
    ).values('staff').annotate(c=C('id'), r=Sum('amount'))
    sales_map = {x['staff']: (x['c'], x['r']) for x in sales_data}

    performers = []
    for u in staff:
        leads = lead_map.get(u.id, 0)
        s_count, s_rev = sales_map.get(u.id, (0, 0))
        amt   = normalize_grams(s_rev)
        
        if leads or s_count:
            performers.append({
                "name": u.full_name, "role": u.role,
                "branch": u.branch.name if u.branch else "—",
                "leads_30d": leads, "sales_30d": s_count, "gold_sold_30d_g": amt
            })
    
    performers.sort(key=lambda x: x['gold_sold_30d_g'], reverse=True)

    # Only take top 4 top performers to keep context tiny
    return {
        "total": staff.count(),
        "top_performers_30d": performers[:4]
    }


def _birthdays_context(days=30):
    from accounts.models import User
    today = date.today()
    upcoming = []
    for u in User.objects.filter(date_of_birth__isnull=False):
        dob = u.date_of_birth
        try:
            bday = date(today.year, dob.month, dob.day)
            if bday < today:
                bday = date(today.year + 1, dob.month, dob.day)
            diff = (bday - today).days
            if 0 <= diff <= days:
                upcoming.append({"name": u.full_name, "role": u.role,
                                  "birthday": bday.strftime("%B %d"), "days_until": diff})
        except ValueError:
            pass
    return sorted(upcoming, key=lambda x: x['days_until'])


def _anniversaries_context(days=30):
    from accounts.models import User
    today = date.today()
    upcoming = []
    for u in User.objects.filter(join_date__isnull=False):
        jd = u.join_date
        try:
            ann = date(today.year, jd.month, jd.day)
            if ann < today:
                ann = date(today.year + 1, jd.month, jd.day)
            diff = (ann - today).days
            if 0 <= diff <= days:
                years = ann.year - jd.year
                upcoming.append({"name": u.full_name, "role": u.role,
                                  "anniversary": ann.strftime("%B %d"),
                                  "years": years, "days_until": diff})
        except ValueError:
            pass
    return sorted(upcoming, key=lambda x: x['days_until'])


def _integrations_context():
    try:
        from campaigns.models import Integration, IntegrationAnalytics
        from django.db.models import Sum
        now = timezone.now()
        since_30d = now - timedelta(days=30)
        
        integrations = list(Integration.objects.all())
        
        # Aggregate analytics in a single query
        analytics_data = IntegrationAnalytics.objects.filter(
            date__gte=since_30d,
            integration__in=integrations
        ).values('integration').annotate(
            imp=Sum('impressions'), clk=Sum('clicks'),
            spd=Sum('spend'), rev=Sum('revenue')
        )
        
        analytics_map = {
            x['integration']: x for x in analytics_data
        }
        
        results = []
        for i in integrations:
            metrics = analytics_map.get(i.id, {})
            results.append({
                "platform": i.get_platform_display(),
                "account": i.account_name,
                "status": i.sync_status,
                "summary_30d": {
                    "impressions": metrics.get('imp') or 0,
                    "clicks": metrics.get('clk') or 0,
                    "spend": float(metrics.get('spd') or 0),
                    "gold_sold_g": normalize_grams(metrics.get('rev')),
                }
            })
        return results
    except Exception as e:
        return {"error": str(e)}


# ─── Context Builder ─────────────────────────────────────────────────────────

def build_crm_context():
    """Gather all CRM data and return as a structured dict."""
    import time
    start = time.time()
    ctx = {}
    
    def log_time(label):
        print(f"AI Context: {label} took {time.time() - start:.2f}s")

    try: ctx['leads']        = _leads_context(); log_time("Leads")
    except Exception as e: ctx['leads'] = {"error": str(e)}
    
    try: ctx['sales']        = _sales_context(); log_time("Sales")
    except Exception as e: ctx['sales'] = {"error": str(e)}
    
    try: ctx['attendance']   = _attendance_context(); log_time("Attendance")
    except Exception as e: ctx['attendance'] = {"error": str(e)}
    
    try: ctx['branches']     = _branches_context(); log_time("Branches")
    except Exception as e: ctx['branches'] = {"error": str(e)}
    
    try: ctx['campaigns']    = _campaigns_context(); log_time("Campaigns")
    except Exception as e: ctx['campaigns'] = {"error": str(e)}
    
    try: ctx['staff']        = _staff_context(); log_time("Staff")
    except Exception as e: ctx['staff'] = {"error": str(e)}
    
    try: ctx['birthdays']    = _birthdays_context(); log_time("Birthdays")
    except Exception as e: ctx['birthdays'] = {"error": str(e)}
    
    try: ctx['anniversaries']= _anniversaries_context(); log_time("Anniversaries")
    except Exception as e: ctx['anniversaries'] = {"error": str(e)}
    
    try: ctx['integrations'] = _integrations_context(); log_time("Integrations")
    except Exception as e: ctx['integrations'] = {"error": str(e)}
    
    print(f"AI Context: Total time {time.time() - start:.2f}s")
    return ctx


def _format_context_as_text(ctx):
    import json
    return json.dumps(ctx, indent=2, default=str)


SYSTEM_PROMPT_TEMPLATE = """You are **Bindu AI**, an elite, highly analytical business intelligence assistant for Bindu Jewellery CRM.
You have access to real-time CRM data injected below, including leads, sales, and **multi-period analytics** (7, 15, and 30-day summaries).

Your Goal:
- Answer the user's questions with HIGH-LEVEL SUMMARY REPORTS. Keep your responses highly concise, clear, and actionable.
- Focus strictly on key highlights, summaries, and bullet points. Do not write extremely long or wordy paragraphs.
- Keep your total response under 250–300 words to ensure rapid, real-time responses.
- When analyzing sales, summarize specifically *when* the sales happened, who made them, and in which branch.
- Always structure your reports beautifully using short markdown tables and clear bullet points.
- IMPORTANT: This platform tracks Gold Volume, NOT currency revenue. ANY value listed as 'amount', 'spent', or 'gold_sold_g' in the JSON data represents Gold Weight in Grams. 
- You MUST report all financial/sales metrics in grams (e.g., '120.5 g' or '120.5 grams'). NEVER use Rs, INR, or the word 'Revenue'. Use terms like 'Total Gold Sold', 'Volume', or 'Gold Quantity'.
- Suggest 1-2 actionable tips based on funnel bottlenecks.

--- LIVE CRM DATA (as of right now) ---
{context}
--- END OF DATA ---

Provide a powerful, error-free, and insightful response based strictly on the data above."""

# Daily usage limits for GLM free tier (100 req/day before slowdowns)
GLM_DAILY_LIMIT    = 100
GLM_WARN_THRESHOLD = 80
GLM_CACHE_KEY      = 'glm_daily_usage_{date}'

# ─── Daily Usage Tracker ─────────────────────────────────────────────────────

def _get_cache_key():
    from django.utils import timezone
    today = timezone.localdate().isoformat()  # e.g. "2026-05-08"
    return GLM_CACHE_KEY.format(date=today)

def get_daily_usage():
    """Return {used, limit, remaining, warn} for today's GLM usage."""
    from django.core.cache import cache
    used = cache.get(_get_cache_key(), 0)
    remaining = max(0, GLM_DAILY_LIMIT - used)
    return {
        "used": used,
        "limit": GLM_DAILY_LIMIT,
        "remaining": remaining,
        "warn": used >= GLM_WARN_THRESHOLD,
        "exceeded": used >= GLM_DAILY_LIMIT,
        "pct": round((used / GLM_DAILY_LIMIT) * 100, 1),
    }

def _increment_usage():
    """Increment today's GLM request count. Expires at end of day."""
    from django.core.cache import cache
    from django.utils import timezone
    import datetime
    key = _get_cache_key()
    try:
        cache.add(key, 0, timeout=86400)  # ensure key exists
        cache.incr(key)
    except Exception:
        pass  # never block the AI call over a counter failure


# ─── GLM-5.1 Chat (OpenAI-compatible) ────────────────────────────────────────

def _chat_glm(prompt, history, context_text, api_key_override=None):
    api_key = (api_key_override or getattr(settings, 'GLM_API_KEY', '')).strip(' "\'\r\n')
    api_url = getattr(settings, 'GLM_API_URL', 'https://api.us-west-2.modal.direct/v1').strip(' "\'\r\n')
    model   = getattr(settings, 'GLM_MODEL',   'zai-org/GLM-5.1-FP8').strip(' "\'\r\n')

    if not api_key:
        raise ValueError("GLM_API_KEY not configured")

    usage    = get_daily_usage()
    exceeded = usage['exceeded']

    system_msg = SYSTEM_PROMPT_TEMPLATE.format(context=context_text)

    # Build message list: system + history (last 6) + current user prompt
    messages = [{"role": "system", "content": system_msg}]
    for h in history[-6:]:
        role = h.get('role', 'user')
        content = h.get('content') or (h.get('parts', [''])[0] if h.get('parts') else '')
        if role in ('user', 'assistant') and content:
            messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": prompt})

    # With the new StreamingHttpResponse heartbeat hack in ai/views.py, Render's 100s limit is safely bypassed!
    # We can now allow GLM a full 300s (5 minutes) to think. Slow response times are no longer a problem!
    timeout = 300

    # 5 attempts. This is safe because Timeouts do NOT retry, so we only retry on fast 429/503 errors!
    max_retries = 5
    last_resp = None
    
    for i in range(max_retries):
        try:
            resp = requests.post(
                f"{api_url.rstrip('/')}/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
                json={
                    "model": model,
                    "messages": messages,
                    "max_tokens": 4096,
                    "temperature": 0.5,
                },
                timeout=timeout,
            )
            last_resp = resp
            if resp.status_code == 200:
                break
            
            # Retry on 429 (rate limit) or 503 (service unavailable / Modal overloaded)
            if resp.status_code in (429, 503):
                if i < max_retries - 1:
                    # Exponential backoff: 5s, 10s, 15s, 20s to allow the GPU concurrent queue to clear
                    wait_time = 5 if resp.status_code == 503 else (5 * (i + 1))
                    print(f"AI Service: GLM {resp.status_code}, retrying in {wait_time}s (attempt {i+1}/{max_retries})...")
                    time.sleep(wait_time)
                    continue
                else:
                    break  # all retries exhausted — exit to trigger fallback
            
            break  # other errors (400, 401, etc.) — don't retry
        except requests.exceptions.Timeout:
            # Do not retry on timeout; raise immediately to trigger fast Gemini fallback
            raise RuntimeError(
                "TIMEOUT: GLM response timed out. The reasoning model is currently slow."
            )
        except Exception as e:
            if i < max_retries - 1:
                continue
            raise RuntimeError(f"GLM Request failed: {e}")

    resp = last_resp

    if resp.status_code == 200:
        _increment_usage()  # count successful request
        data    = resp.json()
        choice  = data['choices'][0]['message']
        content = choice.get('content') or choice.get('reasoning_content') or ''
        text    = content.strip() if content else "I processed your request but got an empty response. Please try again."

        # Append usage warning as a footer if approaching limit
        new_usage = get_daily_usage()
        if new_usage['exceeded']:
            text += (
                "\n\n---\n> \u26a0\ufe0f **Daily limit reached** ({used}/{limit} requests used today). "
                "Responses may be slower. Limit resets at midnight.".format(**new_usage)
            )
        elif new_usage['warn']:
            text += (
                "\n\n---\n> \U0001f4ca **Usage:** {used}/{limit} daily requests used "
                "({remaining} remaining).".format(**new_usage)
            )
        return text
    else:
        raise RuntimeError(f"GLM API error {resp.status_code}: {resp.text[:300]}")


# ─── Gemini Fallback ──────────────────────────────────────────────────────────

def _chat_gemini_fallback(prompt, context_text):
    """Simple Gemini fallback using direct REST HTTP requests to bypass SDK bugs and gRPC/REST hangs."""
    try:
        import requests
        api_key = getattr(settings, 'GEMINI_API_KEY', '').strip(' "\'\r\n')
        if not api_key:
            raise ValueError("GEMINI_API_KEY not configured")
        
        full_prompt = SYSTEM_PROMPT_TEMPLATE.format(context=context_text) + f"\n\nUser: {prompt}"
        
        headers = {
            "Content-Type": "application/json"
        }
        
        payload = {
            "contents": [
                {
                    "parts": [
                        {
                            "text": full_prompt
                        }
                    ]
                }
            ]
        }
        
        # gemini-2.0-flash has a higher free-tier quota (15 RPM) vs gemini-2.5-flash (10 RPM)
        # Try 2.0-flash first to preserve quota, fall back to 2.5-flash
        models = ['gemini-2.0-flash', 'gemini-2.5-flash']
        errors = []
        
        for model in models:
            try:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
                # OS/Socket level strict 10.0 second timeout to protect the Gunicorn worker
                response = requests.post(url, json=payload, headers=headers, timeout=10.0)
                
                if response.status_code == 200:
                    data = response.json()
                    try:
                        text = data['candidates'][0]['content']['parts'][0]['text']
                        return text.strip()
                    except (KeyError, IndexError) as e:
                        errors.append(f"{model}: Unexpected structure {data}")
                else:
                    errors.append(f"{model}: Status {response.status_code} - {response.text[:150]}")
            except Exception as e:
                errors.append(f"{model}: {str(e)}")
                continue
                
        raise RuntimeError(" | ".join(errors))
            
    except Exception as e:
        raise RuntimeError(f"Gemini raw HTTP fallback failed: {e}")


# ─── Public Entry Point ───────────────────────────────────────────────────────

def _is_simple_conversational(prompt):
    p = prompt.lower().strip(' ?.!\r\n')
    # If the prompt is short or a standard greeting, do not load the massive CRM context.
    greetings = {'hi', 'hello', 'hey', 'test', 'yo', 'status', 'ping', 'who are you', 'how are you', 'help'}
    return p in greetings or len(p) < 10

def chat_with_ai(prompt, history=[]):
    """
    Main AI chat function with context caching.
    """
    from django.core.cache import cache
    
    glm_key    = getattr(settings, 'GLM_API_KEY', '').strip(' "\'\r\n')
    gemini_key = getattr(settings, 'GEMINI_API_KEY', '').strip(' "\'\r\n')

    if not glm_key and not gemini_key:
        return (
            "⚠️ **AI Not Configured**\n\n"
            "Please set `GLM_API_KEY` in your `.env` file."
        )

    # ── Context Caching ──────────────────────────────────────────────────────
    # We cache the heavy CRM context for 2 minutes to prevent timeouts.
    # We use a global key for now, as context is currently shared (admin data).
    if _is_simple_conversational(prompt):
        print("AI Service: Conversational prompt detected. Skipping heavy CRM context load.")
        context_text = "The user is saying a simple greeting or brief message. Respond in a friendly, conversational manner as a CRM business assistant."
    else:
        cache_key = "ai_crm_context_cache"
        context_text = cache.get(cache_key)
        
        if not context_text:
            try:
                print("AI Service: Cache miss, building fresh context...")
                ctx = build_crm_context()
                context_text = _format_context_as_text(ctx)
                # Cache for 120 seconds (2 mins)
                cache.set(cache_key, context_text, 120)
            except Exception as e:
                print(f"AI Service: Context building failed: {e}")
                context_text = f'{{"error": "Could not load CRM data: {e}"}}'
        else:
            print("AI Service: Using cached context.")

    # ── Try GLM-5.1 (Primary) ───────────────────────────────────────────────
    if glm_key:
        try:
            return _chat_glm(prompt, history, context_text)
        except Exception as e:
            err = str(e)
            
            # If 429 OR 503 (Modal overloaded), try the fallback GLM key before giving up on GLM entirely
            glm_fallback_key = getattr(settings, 'GLM_API_KEY_FALLBACK', '')
            if ('429' in err or '503' in err or 'busy' in err.lower()) and glm_fallback_key:
                print("AI Service: Primary GLM failed, trying Fallback GLM Key 1...")
                try:
                    return _chat_glm(prompt, history, context_text, api_key_override=glm_fallback_key)
                except Exception as fe:
                    err = f"Primary: {err} | Fallback 1: {str(fe)}"

            # Try Fallback GLM Key 2 if it's still busy
            glm_fallback_key_2 = getattr(settings, 'GLM_API_KEY_FALLBACK_2', '')
            if ('429' in err or '503' in err or 'busy' in err.lower()) and glm_fallback_key_2:
                print("AI Service: Fallback GLM Key 1 failed, trying Fallback GLM Key 2...")
                try:
                    return _chat_glm(prompt, history, context_text, api_key_override=glm_fallback_key_2)
                except Exception as fe2:
                    err = f"Primary/Fallback 1: {err} | Fallback 2: {str(fe2)}"

            # Don't fall through on auth errors
            if '401' in err or 'Unauthorized' in err:
                return (
                    "⚠️ **GLM API Key Invalid**\n\n"
                    f"Error: `{err[:200]}`\n\n"
                    "Please check your `GLM_API_KEY` in `.env`."
                )
            
            # All GLM attempts exhausted — fall back to Gemini
            print(f"AI Service: All GLM attempts failed ({err[:120]}), falling back to Gemini...")
            glm_error = err
    else:
        glm_error = "GLM_API_KEY not set"

    # ── Fallback to Gemini ──────────────────────────────────────────────────
    if gemini_key:
        try:
            return _chat_gemini_fallback(prompt, context_text)
        except Exception as e:
            gem_err = str(e)
            if '429' in gem_err or 'quota' in gem_err.lower():
                return (
                    "⏳ **Rate Limit Reached**\n\n"
                    "Both AI providers are temporarily unavailable.\n"
                    "- GLM error: `{}`\n"
                    "- Gemini: quota exceeded — wait ~35 seconds.\n\n"
                    "Please try again shortly.".format(glm_error[:100])
                )
            return (
                f"⚠️ **AI Service Busy**\n\n"
                f"The primary engine (GLM) is busy with high traffic (429).\n"
                f"The fallback (Gemini) also reported an issue: `{gem_err[:100]}`\n\n"
                "**Action:** Please wait **30 seconds** for the queue to clear and try your request again."
            )

    return (
        f"⚠️ **AI Unavailable**\n\n"
        f"GLM error: `{glm_error[:200]}`\n\n"
        "Please check your API keys in `.env`."
    )
