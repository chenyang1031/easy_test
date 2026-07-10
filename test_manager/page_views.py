from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def ai_prompt_template_management(request):
    """AI提示词模板管理页面。"""
    return render(request, 'test_manager/ai_prompt_template_management.html')