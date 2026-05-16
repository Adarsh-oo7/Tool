from django.urls import path
from .views import AIChatView, AISuggestionsView, AIUsageView

urlpatterns = [
    path('chat/', AIChatView.as_view(), name='ai-chat'),
    path('suggestions/', AISuggestionsView.as_view(), name='ai-suggestions'),
    path('usage/', AIUsageView.as_view(), name='ai-usage'),
]
