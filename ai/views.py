from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from core.permissions import IsOwner
from .services import chat_with_ai, get_daily_usage


class AIChatView(APIView):
    """
    Endpoint for Admin AI Assistant chat
    POST /api/v1/ai/chat/
    Body: {"prompt": "...", "history": [...]}
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request):
        prompt = request.data.get('prompt')
        history = request.data.get('history', [])

        if not prompt:
            return Response({"error": "Prompt is required"}, status=status.HTTP_400_BAD_REQUEST)

        # To prevent Render's 100-second Load Balancer timeout during slow 136s+ GLM requests,
        # we process the AI in a background thread and stream a "heartbeat" space every 15 seconds.
        # This keeps the connection alive and resets the Render 100s kill-switch timer continuously!
        import threading
        import queue
        import json
        from django.http import StreamingHttpResponse
        from django.db import close_old_connections

        q = queue.Queue()

        def ai_worker():
            try:
                close_old_connections()
                response_text = chat_with_ai(prompt, history)
                q.put(('result', response_text))
            except Exception as e:
                import traceback
                traceback.print_exc()
                q.put(('error', str(e)))
            finally:
                close_old_connections()

        threading.Thread(target=ai_worker, daemon=True).start()

        def stream_generator():
            while True:
                try:
                    # Wait 15 seconds. If no result, throw Empty and yield a space!
                    msg_type, data = q.get(timeout=15)
                    
                    if msg_type == 'result':
                        is_rate_limited = (
                            'Rate Limit Reached' in data or
                            ('rate' in data.lower() and 'quota' in data.lower())
                        )
                        # Yield the final JSON block
                        yield json.dumps({
                            "response": data,
                            "role": "assistant",
                            "rate_limited": is_rate_limited
                        })
                        break
                    
                    elif msg_type == 'error':
                        err_str = data
                        if '429' in err_str or 'quota' in err_str.lower() or 'concurrent' in err_str.lower():
                            yield json.dumps({
                                "error": "rate_limit",
                                "response": "⏳ **Rate Limit / Concurrency Reached**\n\nThe AI service is currently very busy. Please wait about **30 seconds** and try again.",
                                "role": "assistant",
                                "rate_limited": True
                            })
                        elif '503' in err_str:
                            yield json.dumps({
                                "error": "service_unavailable",
                                "response": "🏛️ **AI Service Busy**\n\nThe GLM-5.1 provider is temporarily unavailable (503).",
                                "role": "assistant"
                            })
                        else:
                            yield json.dumps({
                                "error": "internal_error",
                                "detail": f"AI Engine Error: {err_str[:200]}",
                                "response": "⚠️ **AI Engine Error**: I encountered an issue while processing your request. Please try again in a moment."
                            })
                        break

                except queue.Empty:
                    # HEARTBEAT: Send a single space character to trick the Render Load Balancer
                    # into keeping the connection open! Leading spaces are safely ignored by JSON.parse() on the frontend.
                    yield " "

        response = StreamingHttpResponse(stream_generator(), content_type='application/json')
        # CRITICAL: Prevent Nginx and Render's load balancers from buffering the heartbeat spaces!
        # This forces Nginx to flush every byte immediately, keeping the connection alive.
        response['X-Accel-Buffering'] = 'no'
        response['Cache-Control'] = 'no-cache, must-revalidate'
        return response



class AISuggestionsView(APIView):
    """
    Get quick action suggestions based on current CRM state
    GET /api/v1/ai/suggestions/
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        suggestions = [
            "Give me a summary of today's sales.",
            "Are there any hot leads needing urgent follow-up?",
            "Show me campaign ROI and performance data.",
            "Which lead source is bringing the most conversions?",
            "Show me branch performance comparison.",
            "How is the staff attendance today?",
            "Who has upcoming birthdays this month?",
            "Show me staff performance this month.",
            "What external integrations (Meta, Instagram) are connected?",
        ]
        return Response({"suggestions": suggestions})
class AIUsageView(APIView):
    """
    Get current AI usage stats (GLM daily limit tracking)
    GET /api/v1/ai/usage/
    """
    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request):
        usage = get_daily_usage()
        return Response(usage)
