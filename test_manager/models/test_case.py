import uuid
from django.db import models
from django.contrib.auth.models import User
from test_manager.models.project import Project
from test_manager.models.environment import Environment


# 测试用例分组
class TestCaseGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name="分组名称", db_comment="分组名称")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_case_groups',
                                verbose_name="所属项目", db_comment="所属项目")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
                               verbose_name="父分组", db_comment="父分组")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_case_groups',
                                   verbose_name="创建人", db_comment="创建人")

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name

    class Meta:
        unique_together = ('name', 'project', 'parent')
        ordering = ['name']
        verbose_name = "用例分组"
        verbose_name_plural = verbose_name


class TestCase(models.Model):
    REQUEST_BODY_FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('form-data', 'Form Data'),
    ]

    name = models.CharField(max_length=100, verbose_name="用例名称", db_comment="用例名称")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_cases', verbose_name="所属项目",
                                db_comment="所属项目")
    group = models.ForeignKey(TestCaseGroup, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='test_cases', verbose_name="用例分组", db_comment="用例分组")
    description = models.TextField(blank=True, verbose_name="用例描述", db_comment="用例描述")
    request_method = models.CharField(max_length=10, choices=[
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ], verbose_name="请求方法", db_comment="请求方法")
    request_url = models.CharField(max_length=500, verbose_name="请求URL", db_comment="请求URL")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="请求头", db_comment="请求头")
    request_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="请求体", db_comment="请求体")
    request_body_format = models.CharField(max_length=20, choices=REQUEST_BODY_FORMAT_CHOICES, default='json',
                                           verbose_name="请求体格式", db_comment="请求体格式")
    expected_status_code = models.IntegerField(default=200, verbose_name="期望状态码", db_comment="期望状态码")
    validation_rules = models.JSONField(default=list, blank=True, verbose_name="验证规则", db_comment="验证规则")
    extract_params = models.JSONField(default=list, blank=True, verbose_name="提取参数",
                                      db_comment="提取参数")  # 新增字段，用于存储提取的参数
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_cases',
                                   verbose_name="创建人", db_comment="创建人")

    upload_file = models.FileField(
        upload_to='testcase_files/%Y/%m/%d/',
        blank=True,
        null=True,
        verbose_name="上传文件",
        help_text="随请求一起发送的文件"
    )
    upload_field_name = models.CharField(
        max_length=128,
        blank=True,
        verbose_name="文件字段名",
        help_text="multipart/form-data 中的字段名，例如 file"
    )
    timeout = models.PositiveIntegerField(
        verbose_name='超时时间(秒)',
        blank=True,
        null=True,
        help_text='为空时使用项目/全局默认'
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "测试用例"
        verbose_name_plural = verbose_name


# 新增测试套件分组模型
class TestSuiteGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name="分组名称", db_comment="分组名称")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_suite_groups',
                                verbose_name="所属项目", db_comment="所属项目")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
                               verbose_name="父分组", db_comment="父分组")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_suite_groups',
                                   verbose_name="创建人", db_comment="创建人")

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name

    class Meta:
        unique_together = ('name', 'project', 'parent')
        ordering = ['name']
        verbose_name = "套件分组"
        verbose_name_plural = verbose_name


class TestSuite(models.Model):
    name = models.CharField(max_length=100, verbose_name="套件名称", db_comment="套件名称")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_suites', verbose_name="所属项目",
                                db_comment="所属项目")
    group = models.ForeignKey(TestSuiteGroup, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='test_suites', verbose_name="套件分组", db_comment="套件分组")
    description = models.TextField(blank=True, verbose_name="套件描述", db_comment="套件描述")
    test_cases = models.ManyToManyField(TestCase, through='TestSuiteCase', verbose_name="关联用例",
                                        db_comment="关联用例")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_suites',
                                   verbose_name="创建人", db_comment="创建人")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "测试套件"
        verbose_name_plural = verbose_name


class TestSuiteCase(models.Model):
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE)
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE)
    environment = models.ForeignKey(Environment, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='test_suite_cases')
    order = models.IntegerField(default=0)

    class Meta:
        ordering = ['order']


class TestRun(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]

    name = models.CharField(max_length=100, verbose_name="运行名称", db_comment="运行名称")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_runs', verbose_name="所属项目",
                                db_comment="所属项目")
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='test_runs', null=True, blank=True,
                                   verbose_name="测试套件", db_comment="测试套件")
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='test_runs',
                                    verbose_name="运行环境", db_comment="运行环境")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="运行状态",
                              db_comment="运行状态")
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="开始时间", db_comment="开始时间")
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="结束时间", db_comment="结束时间")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_runs',
                                   verbose_name="创建人", db_comment="创建人")

    def __str__(self):
        return self.name

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    class Meta:
        verbose_name = "测试运行"
        verbose_name_plural = verbose_name


class TestResult(models.Model):
    STATUS_CHOICES = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ]

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='test_results',
                                 verbose_name="测试运行", db_comment="测试运行")
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='test_results',
                                  verbose_name="测试用例", db_comment="测试用例")
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='test_results',
                                    verbose_name="运行环境", db_comment="运行环境")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="运行状态", db_comment="运行状态")
    response_time = models.FloatField(null=True, blank=True, verbose_name="响应时间",
                                      db_comment="响应时间")  # in milliseconds
    response_status_code = models.IntegerField(null=True, blank=True, verbose_name="响应状态码",
                                               db_comment="响应状态码")
    response_headers = models.JSONField(default=dict, blank=True, verbose_name="响应头", db_comment="响应头")
    response_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="响应体", db_comment="响应体")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="请求头", db_comment="请求头")
    request_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="请求体", db_comment="请求体")
    error_message = models.TextField(blank=True, verbose_name="错误信息", db_comment="错误信息")
    extracted_params = models.JSONField(default=dict, blank=True, verbose_name="提取参数", db_comment="提取参数")
    validators = models.JSONField(default=list, blank=True, verbose_name="验证器", db_comment="验证器")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")

    def __str__(self):
        return f"{self.test_case.name} - {self.status}"

    class Meta:
        verbose_name = "测试结果"
        verbose_name_plural = verbose_name


class TestSuiteRun(models.Model):
    name = models.CharField(max_length=100)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_suite_runs')
    test_suite = models.ForeignKey(TestSuite, on_delete=models.SET_NULL, null=True, blank=True,
                                   related_name='test_suite_runs')
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='test_suite_runs')
    status = models.CharField(max_length=20, choices=TestRun.STATUS_CHOICES, default='pending')
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_test_suite_runs')

    def __str__(self):
        return self.name

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
