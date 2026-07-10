from django.urls import path
from test_manager.views import ai_prompt_template_management

urlpatterns = [
    path('ai-prompt-template-management/', ai_prompt_template_management, name='ai-prompt-template-management'),
]