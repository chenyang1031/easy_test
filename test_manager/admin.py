from django.contrib import admin
from django.contrib.admin import AdminSite
# Register your models here.
from django.contrib import admin
from django.contrib.auth.models import AbstractUser

from .models import (
    Project, Environment, TestCase, TestSuite,
    TestRun, TestResult, TestReport, TestCaseGroup, TestSuiteGroup, EmailConfig,
    PerformanceTestTask, PerformanceTestResult,
)


class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_by', 'created_at', 'updated_at')
    search_fields = ('name', 'description')
    list_filter = ('created_at', 'updated_at')
    list_per_page = 10


class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'base_url', 'created_at')
    search_fields = ('name', 'base_url')
    list_filter = ('project', 'created_at')
    list_per_page = 10


class TestCaseAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'request_method', 'request_url', 'expected_status_code', 'created_by',
                    'upload_file', 'upload_field_name')     # ← 新增
    search_fields = ('name', 'description', 'request_url',
                     'upload_file', 'upload_field_name')    # ← 新增
    list_filter = ('project', 'request_method', 'expected_status_code', 'created_at')
    list_per_page = 10


class TestSuiteAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'created_by', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('project', 'created_at')
    list_per_page = 10


class TestRunAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'test_suite', 'environment', 'status', 'start_time', 'end_time', 'created_by')
    search_fields = ('name',)
    list_filter = ('project', 'status', 'created_at')
    list_per_page = 10


class TestResultAdmin(admin.ModelAdmin):
    list_display = ('test_run', 'test_case', 'status', 'response_time', 'response_status_code', 'created_at')
    search_fields = ('test_case__name', 'error_message')
    list_filter = ('test_run', 'status', 'created_at')
    list_per_page = 10


class TestReportAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'report_type', 'report_format', 'scene_execution', 'created_at')
    search_fields = ('name', 'description')
    list_filter = ('project', 'report_type', 'created_at')
    raw_id_fields = ('scene_execution',)
    # date_hierarchy = 'created_at'


class TestCaseGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'parent', 'created_at')
    search_fields = ('name', 'project')
    list_filter = ('project', 'created_at')
    list_per_page = 10


class TestSuiteGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'parent', 'created_at')
    search_fields = ('name', 'project')
    list_filter = ('project', 'created_at')
    list_per_page = 10


class EmailConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'email_backend', 'default_from_email',
                    'default_from_name', 'smtp_host', 'smtp_port',
                    'smtp_username', 'is_active', 'created_at')
    search_fields = ('name', 'email_backend', 'default_from_email', 'default_from_name')
    list_filter = ('email_backend', 'is_active', 'created_at')
    list_per_page = 10


class PerformanceTestTaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'project', 'environment', 'interface', 'total_users', 'spawn_rate', 'run_time', 'target_rps', 'status', 'csv_file', 'creator', 'created_at')
    search_fields = ('name',)
    list_filter = ('project', 'status', 'created_at')
    list_per_page = 10


class PerformanceTestResultAdmin(admin.ModelAdmin):
    list_display = ('task', 'timestamp', 'active_users', 'requests_per_second', 'response_time_50', 'response_time_90', 'p95', 'p99', 'max_response_time', 'failure_rate')
    list_filter = ('task',)
    list_per_page = 20


admin.site.register(Project, ProjectAdmin)
admin.site.register(Environment, EnvironmentAdmin)
admin.site.register(TestCase, TestCaseAdmin)
admin.site.register(TestSuite, TestSuiteAdmin)
admin.site.register(TestCaseGroup, TestCaseGroupAdmin)
admin.site.register(TestSuiteGroup, TestSuiteGroupAdmin)
admin.site.register(TestRun, TestRunAdmin)
admin.site.register(TestResult, TestResultAdmin)
admin.site.register(TestReport, TestReportAdmin)
admin.site.register(EmailConfig, EmailConfigAdmin)
admin.site.register(PerformanceTestTask, PerformanceTestTaskAdmin)
admin.site.register(PerformanceTestResult, PerformanceTestResultAdmin)

admin.site.site_header = 'EastTesting测试管理后台'
admin.site.site_title = 'EastTesting测试管理后台'
admin.site.index_title = 'EastTesting测试管理后台'
