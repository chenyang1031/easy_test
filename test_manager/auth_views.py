from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from django.contrib.auth.models import User
from django import forms
from django.urls import reverse


class CustomUserCreationForm(UserCreationForm):
    """扩展默认的用户创建表单，添加电子邮件字段"""
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        if commit:
            user.save()
        return user


def login_redirect_view(request):
    """将旧的 Django 登录页面重定向到 SPA 登录页"""
    # 如果已登录，直接跳转到仪表盘
    if request.user.is_authenticated:
        return redirect('/app/#/dashboard')
    # GET 请求 → 重定向到 SPA 登录
    # POST 请求 → 告诉用户使用 API（不应再有人直接 POST 到此 URL）
    if request.method == 'POST':
        return redirect('/app/#/login')
    return redirect('/app/#/login')


def register_view(request):
    """用户注册视图 — 已迁移至 SPA，重定向到 /app/#/register"""
    if request.method == 'POST':
        # 旧 POST 兼容 — 但前端已使用 API，此处保留防护
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"账户创建成功！欢迎 {user.username}！")
            return redirect('/app/#/dashboard')
        # 表单无效时也转到 SPA 注册页
    return redirect('/app/#/register')


def profile_view(request):
    """用户个人资料视图 — 已迁移至 SPA"""
    return redirect('/app/#/settings/profile')


class UserProfileForm(forms.ModelForm):
    """用户个人资料表单"""
    first_name = forms.CharField(max_length=30, required=False, label='名字')
    last_name = forms.CharField(max_length=30, required=False, label='姓氏')
    email = forms.EmailField(required=True, label='电子邮件')

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']


def edit_profile_view(request):
    """编辑用户个人资料视图 — 已迁移至 SPA"""
    return redirect('/app/#/settings/profile')
