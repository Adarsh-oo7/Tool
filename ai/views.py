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

        try:
            response_text = chat_with_ai(prompt, history)

            # Detect rate-limit response and return 429 so frontend can handle it
            is_rate_limited = (
                'Rate Limit Reached' in response_text or
                ('rate' in response_text.lower() and 'quota' in response_text.lower())
            )
            http_status = status.HTTP_429_TOO_MANY_REQUESTS if is_rate_limited else status.HTTP_200_OK

            return Response({
                "response": response_text,
                "role": "assistant",
                "rate_limited": is_rate_limited,
            }, status=http_status)

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_str = str(e)

            # Surface 429 with friendly message
            if '429' in err_str or 'quota' in err_str.lower() or 'concurrent' in err_str.lower():
                return Response({
                    "error": "rate_limit",
                    "response": (
                        "⏳ **Rate Limit / Concurrency Reached**\n\n"
                        "The AI service is currently very busy. "
                        "Please wait about **30 seconds** and try again.\n\n"
                        "**Tip:** If you see this often, your daily 100-request limit might be near."
                    ),
                    "role": "assistant",
                    "rate_limited": True,
                }, status=status.HTTP_429_TOO_MANY_REQUESTS)

            # Check for GLM 503 errors specifically
            if '503' in err_str:
                return Response({
                    "error": "service_unavailable",
                    "response": (
                        "🏛️ **AI Service Busy**\n\n"
                        "The GLM-5.1 provider is temporarily unavailable (503). "
                        "I'll automatically try the fallback model if this continues."
                    ),
                    "role": "assistant"
                }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

            return Response({
                "error": "internal_error",
                "detail": f"AI Engine Error: {err_str[:200]}",
                "response": "⚠️ **AI Engine Error**: I encountered an issue while processing your request. Please try again in a moment."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
