import uuid
from django.urls import reverse
from django.db import models
from django.contrib.auth.models import User
import json


class Project(models.Model):
    name = models.CharField(max_length=100, verbose_name="椤圭洰鍚嶇О", db_comment="椤圭洰鍚嶇О")
    description = models.TextField(blank=True, verbose_name="椤圭洰鎻忚堪", db_comment="椤圭洰鎻忚堪")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_projects',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']
        verbose_name = "椤圭洰"
        verbose_name_plural = verbose_name


class Environment(models.Model):
    name = models.CharField(max_length=100, verbose_name="鐜鍚嶇О", db_comment="鐜鍚嶇О")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='environments', verbose_name="鎵€灞為」鐩?,
                                db_comment="鎵€灞炵幆澧?)
    base_url = models.URLField(verbose_name="鐜URL", db_comment="鐜URL")
    variables = models.JSONField(default=dict, blank=True, verbose_name="鐜鍙橀噺", db_comment="鐜鍙橀噺")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")

    def __str__(self):
        return f"{self.project.name} - {self.name}"

    class Meta:
        verbose_name = "鐜"
        verbose_name_plural = verbose_name


# 娴嬭瘯鐢ㄤ緥鍒嗙粍
class TestCaseGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name="鍒嗙粍鍚嶇О", db_comment="鍒嗙粍鍚嶇О")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_case_groups',
                                verbose_name="鎵€灞為」鐩?, db_comment="鎵€灞為」鐩?)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
                               verbose_name="鐖跺垎缁?, db_comment="鐖跺垎缁?)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_case_groups',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name

    class Meta:
        unique_together = ('name', 'project', 'parent')
        ordering = ['name']
        verbose_name = "鐢ㄤ緥鍒嗙粍"
        verbose_name_plural = verbose_name


class TestCase(models.Model):
    REQUEST_BODY_FORMAT_CHOICES = [
        ('json', 'JSON'),
        ('form-data', 'Form Data'),
    ]

    name = models.CharField(max_length=100, verbose_name="鐢ㄤ緥鍚嶇О", db_comment="鐢ㄤ緥鍚嶇О")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_cases', verbose_name="鎵€灞為」鐩?,
                                db_comment="鎵€灞為」鐩?)
    group = models.ForeignKey(TestCaseGroup, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='test_cases', verbose_name="鐢ㄤ緥鍒嗙粍", db_comment="鐢ㄤ緥鍒嗙粍")
    description = models.TextField(blank=True, verbose_name="鐢ㄤ緥鎻忚堪", db_comment="鐢ㄤ緥鎻忚堪")
    request_method = models.CharField(max_length=10, choices=[
        ('GET', 'GET'),
        ('POST', 'POST'),
        ('PUT', 'PUT'),
        ('DELETE', 'DELETE'),
        ('PATCH', 'PATCH'),
    ], verbose_name="璇锋眰鏂规硶", db_comment="璇锋眰鏂规硶")
    request_url = models.CharField(max_length=500, verbose_name="璇锋眰URL", db_comment="璇锋眰URL")
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="璇锋眰澶?, db_comment="璇锋眰澶?)
    request_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="璇锋眰浣?, db_comment="璇锋眰浣?)
    request_body_format = models.CharField(max_length=20, choices=REQUEST_BODY_FORMAT_CHOICES, default='json',
                                           verbose_name="璇锋眰浣撴牸寮?, db_comment="璇锋眰浣撴牸寮?)
    expected_status_code = models.IntegerField(default=200, verbose_name="鏈熸湜鐘舵€佺爜", db_comment="鏈熸湜鐘舵€佺爜")
    validation_rules = models.JSONField(default=list, blank=True, verbose_name="楠岃瘉瑙勫垯", db_comment="楠岃瘉瑙勫垯")
    extract_params = models.JSONField(default=list, blank=True, verbose_name="鎻愬彇鍙傛暟",
                                      db_comment="鎻愬彇鍙傛暟")  # 鏂板瀛楁锛岀敤浜庡瓨鍌ㄦ彁鍙栫殑鍙傛暟
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_cases',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "娴嬭瘯鐢ㄤ緥"
        verbose_name_plural = verbose_name


# 鏂板娴嬭瘯濂椾欢鍒嗙粍妯″瀷
class TestSuiteGroup(models.Model):
    name = models.CharField(max_length=100, verbose_name="鍒嗙粍鍚嶇О", db_comment="鍒嗙粍鍚嶇О")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_suite_groups',
                                verbose_name="鎵€灞為」鐩?, db_comment="鎵€灞為」鐩?)
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children',
                               verbose_name="鐖跺垎缁?, db_comment="鐖跺垎缁?)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_suite_groups',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        if self.parent:
            return f"{self.parent} / {self.name}"
        return self.name

    class Meta:
        unique_together = ('name', 'project', 'parent')
        ordering = ['name']
        verbose_name = "濂椾欢鍒嗙粍"
        verbose_name_plural = verbose_name


class TestSuite(models.Model):
    name = models.CharField(max_length=100, verbose_name="濂椾欢鍚嶇О", db_comment="濂椾欢鍚嶇О")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_suites', verbose_name="鎵€灞為」鐩?,
                                db_comment="鎵€灞為」鐩?)
    group = models.ForeignKey(TestSuiteGroup, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='test_suites', verbose_name="濂椾欢鍒嗙粍", db_comment="濂椾欢鍒嗙粍")
    description = models.TextField(blank=True, verbose_name="濂椾欢鎻忚堪", db_comment="濂椾欢鎻忚堪")
    test_cases = models.ManyToManyField(TestCase, through='TestSuiteCase', verbose_name="鍏宠仈鐢ㄤ緥",
                                        db_comment="鍏宠仈鐢ㄤ緥")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_suites',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "娴嬭瘯濂椾欢"
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

    name = models.CharField(max_length=100, verbose_name="杩愯鍚嶇О", db_comment="杩愯鍚嶇О")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_runs', verbose_name="鎵€灞為」鐩?,
                                db_comment="鎵€灞為」鐩?)
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='test_runs', null=True, blank=True,
                                   verbose_name="娴嬭瘯濂椾欢", db_comment="娴嬭瘯濂椾欢")
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='test_runs',
                                    verbose_name="杩愯鐜", db_comment="杩愯鐜")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="杩愯鐘舵€?,
                              db_comment="杩愯鐘舵€?)
    start_time = models.DateTimeField(null=True, blank=True, verbose_name="寮€濮嬫椂闂?, db_comment="寮€濮嬫椂闂?)
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="缁撴潫鏃堕棿", db_comment="缁撴潫鏃堕棿")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_test_runs',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        return self.name

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    class Meta:
        verbose_name = "娴嬭瘯杩愯"
        verbose_name_plural = verbose_name


class TestResult(models.Model):
    STATUS_CHOICES = [
        ('passed', 'Passed'),
        ('failed', 'Failed'),
        ('error', 'Error'),
        ('skipped', 'Skipped'),
    ]

    test_run = models.ForeignKey(TestRun, on_delete=models.CASCADE, related_name='test_results',
                                 verbose_name="娴嬭瘯杩愯", db_comment="娴嬭瘯杩愯")
    test_case = models.ForeignKey(TestCase, on_delete=models.CASCADE, related_name='test_results',
                                  verbose_name="娴嬭瘯鐢ㄤ緥", db_comment="娴嬭瘯鐢ㄤ緥")
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='test_results',
                                    verbose_name="杩愯鐜", db_comment="杩愯鐜")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, verbose_name="杩愯鐘舵€?, db_comment="杩愯鐘舵€?)
    response_time = models.FloatField(null=True, blank=True, verbose_name="鍝嶅簲鏃堕棿",
                                      db_comment="鍝嶅簲鏃堕棿")  # in milliseconds
    response_status_code = models.IntegerField(null=True, blank=True, verbose_name="鍝嶅簲鐘舵€佺爜",
                                               db_comment="鍝嶅簲鐘舵€佺爜")
    response_headers = models.JSONField(default=dict, blank=True, verbose_name="鍝嶅簲澶?, db_comment="鍝嶅簲澶?)
    response_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="鍝嶅簲浣?, db_comment="鍝嶅簲浣?)
    request_headers = models.JSONField(default=dict, blank=True, verbose_name="璇锋眰澶?, db_comment="璇锋眰澶?)
    request_body = models.JSONField(default=dict, blank=True, null=True, verbose_name="璇锋眰浣?, db_comment="璇锋眰浣?)
    error_message = models.TextField(blank=True, verbose_name="閿欒淇℃伅", db_comment="閿欒淇℃伅")
    extracted_params = models.JSONField(default=dict, blank=True, verbose_name="鎻愬彇鍙傛暟", db_comment="鎻愬彇鍙傛暟")
    validators = models.JSONField(default=list, blank=True, verbose_name="楠岃瘉鍣?, db_comment="楠岃瘉鍣?)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")

    def __str__(self):
        return f"{self.test_case.name} - {self.status}"

    class Meta:
        verbose_name = "娴嬭瘯缁撴灉"
        verbose_name_plural = verbose_name


from django.db import models
from django.conf import settings
from django.core.mail import EmailMessage
from django.core.exceptions import ValidationError
import smtplib
import ssl


class EmailConfig(models.Model):
    """閭欢閰嶇疆妯″瀷"""
    EMAIL_BACKEND_CHOICES = [
        ('smtp', 'SMTP'),
        ('sendgrid', 'SendGrid API'),
        ('mailgun', 'Mailgun API'),
    ]

    name = models.CharField(max_length=100, verbose_name="閰嶇疆鍚嶇О", db_comment="閰嶇疆鍚嶇О")
    is_active = models.BooleanField(default=False, verbose_name="鏄惁婵€娲?, db_comment="鏄惁婵€娲?)
    email_backend = models.CharField(
        max_length=20,
        choices=EMAIL_BACKEND_CHOICES,
        default='smtp',
        verbose_name="閭欢鍚庣",
        db_comment="閭欢鍚庣"
    )

    # SMTP 璁剧疆
    smtp_host = models.CharField(max_length=255, blank=True, verbose_name="SMTP 鏈嶅姟鍣?, db_comment="SMTP 鏈嶅姟鍣?)
    smtp_port = models.IntegerField(default=587, blank=True, null=True, verbose_name="SMTP 绔彛",
                                    db_comment="SMTP 绔彛")
    smtp_username = models.CharField(max_length=255, blank=True, verbose_name="SMTP 鐢ㄦ埛鍚?, db_comment="SMTP 鐢ㄦ埛鍚?)
    smtp_password = models.CharField(max_length=255, blank=True, verbose_name="SMTP 瀵嗙爜", db_comment="SMTP 瀵嗙爜")
    smtp_use_tls = models.BooleanField(default=True, verbose_name="浣跨敤 TLS", db_comment="浣跨敤 TLS")
    smtp_use_ssl = models.BooleanField(default=False, verbose_name="浣跨敤 SSL", db_comment="浣跨敤 SSL")

    # API 瀵嗛挜璁剧疆
    api_key = models.CharField(max_length=255, blank=True, verbose_name="API 瀵嗛挜", db_comment="API 瀵嗛挜")

    # 閫氱敤璁剧疆
    default_from_email = models.EmailField(verbose_name="榛樿鍙戜欢浜洪偖绠?, db_comment="榛樿鍙戜欢浜洪偖绠?)
    default_from_name = models.CharField(max_length=100, verbose_name="榛樿鍙戜欢浜哄悕绉?, db_comment="榛樿鍙戜欢浜哄悕绉?)

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")

    class Meta:
        verbose_name = "閭欢閰嶇疆"
        verbose_name_plural = "閭欢閰嶇疆"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # 濡傛灉褰撳墠閰嶇疆琚缃负婵€娲伙紝鍒欏皢鍏朵粬閰嶇疆璁剧疆涓洪潪婵€娲?        if self.is_active:
            EmailConfig.objects.filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    def clean(self):
        """楠岃瘉閭欢閰嶇疆"""
        if self.email_backend == 'smtp':
            if not self.smtp_host or not self.smtp_username or not self.smtp_password:
                raise ValidationError("SMTP 閰嶇疆闇€瑕佸～鍐欐湇鍔″櫒銆佺敤鎴峰悕鍜屽瘑鐮?)
        elif self.email_backend in ['sendgrid', 'mailgun']:
            if not self.api_key:
                raise ValidationError(f"{self.get_email_backend_display()} 閰嶇疆闇€瑕佸～鍐?API 瀵嗛挜")

    def test_connection(self):
        """娴嬭瘯閭欢杩炴帴"""
        if self.email_backend == 'smtp':
            try:
                if self.smtp_use_ssl:
                    server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, context=ssl.create_default_context())
                else:
                    server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                    if self.smtp_use_tls:
                        server.starttls(context=ssl.create_default_context())

                server.login(self.smtp_username, self.smtp_password)
                server.quit()
                return True, "SMTP 杩炴帴娴嬭瘯鎴愬姛"
            except Exception as e:
                return False, f"SMTP 杩炴帴娴嬭瘯澶辫触: {str(e)}"
        elif self.email_backend == 'sendgrid':
            # 杩欓噷鍙互娣诲姞 SendGrid API 娴嬭瘯浠ｇ爜
            return True, "SendGrid API 閰嶇疆宸蹭繚瀛?
        elif self.email_backend == 'mailgun':
            # 杩欓噷鍙互娣诲姞 Mailgun API 娴嬭瘯浠ｇ爜
            return True, "Mailgun API 閰嶇疆宸蹭繚瀛?

        return False, "鏈煡鐨勯偖浠跺悗绔?

    def send_test_email(self, to_email):
        """鍙戦€佹祴璇曢偖浠?""
        global current_backend, current_host, current_port, current_user, current_password, current_tls, current_ssl, current_from
        subject = "EasyTesting - 娴嬭瘯閭欢"
        message = "杩欐槸涓€灏佹祴璇曢偖浠讹紝鐢ㄤ簬楠岃瘉 EasyTesting 鐨勯偖浠跺彂閫佸姛鑳芥槸鍚︽甯稿伐浣溿€?
        from_email = f"{self.default_from_name} <{self.default_from_email}>"

        try:
            # 淇濆瓨褰撳墠璁剧疆
            current_backend = settings.EMAIL_BACKEND
            current_host = settings.EMAIL_HOST
            current_port = settings.EMAIL_PORT
            current_user = settings.EMAIL_HOST_USER
            current_password = settings.EMAIL_HOST_PASSWORD
            current_tls = settings.EMAIL_USE_TLS
            current_ssl = getattr(settings, 'EMAIL_USE_SSL', False)
            current_from = settings.DEFAULT_FROM_EMAIL

            # 搴旂敤涓存椂璁剧疆
            if self.email_backend == 'smtp':
                settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
                settings.EMAIL_HOST = self.smtp_host
                settings.EMAIL_PORT = self.smtp_port
                settings.EMAIL_HOST_USER = self.smtp_username
                settings.EMAIL_HOST_PASSWORD = self.smtp_password
                settings.EMAIL_USE_TLS = self.smtp_use_tls
                settings.EMAIL_USE_SSL = self.smtp_use_ssl
            elif self.email_backend == 'sendgrid':
                settings.EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
                settings.SENDGRID_API_KEY = self.api_key
            elif self.email_backend == 'mailgun':
                settings.EMAIL_BACKEND = 'django_mailgun.MailgunBackend'
                settings.MAILGUN_ACCESS_KEY = self.api_key
                settings.MAILGUN_SERVER_NAME = self.smtp_host  # 浣跨敤 smtp_host 瀛樺偍 Mailgun 鍩熷悕

            settings.DEFAULT_FROM_EMAIL = from_email

            # 鍙戦€佹祴璇曢偖浠?            email = EmailMessage(
                subject=subject,
                body=message,
                from_email=from_email,
                to=[to_email],
                reply_to=[self.default_from_email],
            )
            email.send(fail_silently=False)

            # 鎭㈠鍘熷璁剧疆
            settings.EMAIL_BACKEND = current_backend
            settings.EMAIL_HOST = current_host
            settings.EMAIL_PORT = current_port
            settings.EMAIL_HOST_USER = current_user
            settings.EMAIL_HOST_PASSWORD = current_password
            settings.EMAIL_USE_TLS = current_tls
            settings.EMAIL_USE_SSL = current_ssl
            settings.DEFAULT_FROM_EMAIL = current_from

            return True, "娴嬭瘯閭欢鍙戦€佹垚鍔?
        except Exception as e:
            # 鎭㈠鍘熷璁剧疆
            settings.EMAIL_BACKEND = current_backend
            settings.EMAIL_HOST = current_host
            settings.EMAIL_PORT = current_port
            settings.EMAIL_HOST_USER = current_user
            settings.EMAIL_HOST_PASSWORD = current_password
            settings.EMAIL_USE_TLS = current_tls
            settings.EMAIL_USE_SSL = current_ssl
            settings.DEFAULT_FROM_EMAIL = current_from

            return False, f"娴嬭瘯閭欢鍙戦€佸け璐? {str(e)}"

    @classmethod
    def get_active_config(cls):
        """鑾峰彇褰撳墠婵€娲荤殑閭欢閰嶇疆"""
        try:
            return cls.objects.get(is_active=True)
        except cls.DoesNotExist:
            return None

    @classmethod
    def apply_active_config(cls):
        """搴旂敤褰撳墠婵€娲荤殑閭欢閰嶇疆鍒?Django 璁剧疆"""
        config = cls.get_active_config()
        if not config:
            return False

        if config.email_backend == 'smtp':
            settings.EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
            settings.EMAIL_HOST = config.smtp_host
            settings.EMAIL_PORT = config.smtp_port
            settings.EMAIL_HOST_USER = config.smtp_username
            settings.EMAIL_HOST_PASSWORD = config.smtp_password
            settings.EMAIL_USE_TLS = config.smtp_use_tls
            settings.EMAIL_USE_SSL = config.smtp_use_ssl
        elif config.email_backend == 'sendgrid':
            settings.EMAIL_BACKEND = 'sendgrid_backend.SendgridBackend'
            settings.SENDGRID_API_KEY = config.api_key
        elif config.email_backend == 'mailgun':
            settings.EMAIL_BACKEND = 'django_mailgun.MailgunBackend'
            settings.MAILGUN_ACCESS_KEY = config.api_key
            settings.MAILGUN_SERVER_NAME = config.smtp_host  # 浣跨敤 smtp_host 瀛樺偍 Mailgun 鍩熷悕

        settings.DEFAULT_FROM_EMAIL = f"{config.default_from_name} <{config.default_from_email}>"
        return True


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


class TestReport(models.Model):
    """娴嬭瘯鎶ュ憡妯″瀷"""
    REPORT_TYPE_CHOICES = [
        ('test_run', 'Test Run'),
        ('test_suite_run', 'Test Suite Run'),
        ('custom', 'Custom'),
    ]

    REPORT_FORMAT_CHOICES = [
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
    ]

    name = models.CharField(max_length=255, verbose_name="鎶ュ憡鍚嶇О", db_comment="鎶ュ憡鍚嶇О")
    description = models.TextField(null=True, blank=True, verbose_name="鎶ュ憡鎻忚堪", db_comment="鎶ュ憡鎻忚堪")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_reports', verbose_name="椤圭洰",
                                db_comment="椤圭洰")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='test_run',
                                   verbose_name="鎶ュ憡绫诲瀷", db_comment="鎶ュ憡绫诲瀷")
    report_format = models.CharField(max_length=10, choices=REPORT_FORMAT_CHOICES, default='html',
                                     verbose_name="鎶ュ憡鏍煎紡", db_comment="鎶ュ憡鏍煎紡")
    content = models.TextField(verbose_name="鎶ュ憡鍐呭", db_comment="鎶ュ憡鍐呭")
    test_run = models.ForeignKey(TestRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports',
                                 verbose_name="娴嬭瘯杩愯", db_comment="娴嬭瘯杩愯")
    test_suite_run = models.ForeignKey(TestSuiteRun, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='reports', verbose_name="娴嬭瘯濂椾欢杩愯", db_comment="娴嬭瘯濂椾欢杩愯")
    test_results = models.ForeignKey(TestResult, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reports', verbose_name="娴嬭瘯缁撴灉", db_comment="娴嬭瘯缁撴灉")
    is_public = models.BooleanField(default=False, verbose_name="鍏紑", db_comment="鍏紑")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='created_test_reports', verbose_name="鍒涘缓鑰?, db_comment="鍒涘缓鑰?)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "娴嬭瘯鎶ュ憡"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('test_report_detail', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('test_report_delete', kwargs={'pk': self.pk})

    def get_summary(self):
        """杩斿洖鎶ュ憡鐨勬憳瑕佷俊鎭?""
        if self.report_format == 'json':
            try:
                data = json.loads(self.content)
                return {
                    'total': data.get('total', 0),
                    'passed': data.get('passed', 0),
                    'failed': data.get('failed', 0),
                    'error': data.get('error', 0),
                    'skipped': data.get('skipped', 0),
                    'success_rate': data.get('success_rate', '0%'),
                }
            except:
                return {}
        return {}


class MockData(models.Model):
    """妯℃嫙鏁版嵁妯″瀷"""
    aim = models.CharField(max_length=255, verbose_name="鐢ㄩ€?, db_comment="鐢ㄩ€?)
    data = models.TextField(verbose_name="mock鏁版嵁", db_comment="mock鏁版嵁")
    description = models.TextField(verbose_name="鏁版嵁鎻忚堪", db_comment="鏁版嵁鎻忚堪", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_mock_data',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        return self.description
    @property
    def count_data(self):
        return len(json.loads(self.data))

    class Meta:
        verbose_name = "妯℃嫙鏁版嵁"
        verbose_name_plural = verbose_name


# 鏂板瀹氭椂浠诲姟鐩稿叧妯″瀷
class ScheduledTask(models.Model):
    """瀹氭椂浠诲姟妯″瀷"""
    SCHEDULE_TYPE_CHOICES = [
        ('once', '鍗曟鎵ц'),
        ('daily', '姣忔棩鎵ц'),
        ('weekly', '姣忓懆鎵ц'),
        ('monthly', '姣忔湀鎵ц'),
        ('cron', 'Cron琛ㄨ揪寮?),
    ]

    STATUS_CHOICES = [
        ('active', '婵€娲?),
        ('inactive', '鍋滅敤'),
        ('paused', '鏆傚仠'),
    ]

    name = models.CharField(max_length=200, verbose_name="浠诲姟鍚嶇О", db_comment="浠诲姟鍚嶇О")
    description = models.TextField(blank=True, verbose_name="浠诲姟鎻忚堪", db_comment="浠诲姟鎻忚堪")
    test_suite = models.ForeignKey(TestSuite, on_delete=models.CASCADE, related_name='scheduled_tasks',
                                   verbose_name="娴嬭瘯濂椾欢", db_comment="娴嬭瘯濂椾欢")
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='scheduled_tasks',
                                    verbose_name="鎵ц鐜", db_comment="鎵ц鐜",null=True, blank=True)

    # 璋冨害閰嶇疆
    schedule_type = models.CharField(max_length=20, choices=SCHEDULE_TYPE_CHOICES, default='daily',
                                     verbose_name="璋冨害绫诲瀷", db_comment="璋冨害绫诲瀷")
    cron_expression = models.CharField(max_length=100, blank=True, verbose_name="Cron琛ㄨ揪寮?,
                                       db_comment="Cron琛ㄨ揪寮?, help_text="浠呭綋璋冨害绫诲瀷涓篊ron鏃朵娇鐢?)

    # 鏃堕棿閰嶇疆
    scheduled_time = models.TimeField(null=True, blank=True, verbose_name="鎵ц鏃堕棿",
                                      db_comment="鎵ц鏃堕棿", help_text="姣忔棩/姣忓懆/姣忔湀鎵ц鐨勫叿浣撴椂闂?)
    scheduled_date = models.DateField(null=True, blank=True, verbose_name="鎵ц鏃ユ湡",
                                      db_comment="鎵ц鏃ユ湡", help_text="鍗曟鎵ц鐨勬棩鏈?)
    weekday = models.IntegerField(null=True, blank=True, verbose_name="鏄熸湡鍑?,
                                  db_comment="鏄熸湡鍑?, help_text="姣忓懆鎵ц鏃剁殑鏄熸湡鍑?1-7)")
    day_of_month = models.IntegerField(null=True, blank=True, verbose_name="姣忔湀绗嚑澶?,
                                       db_comment="姣忔湀绗嚑澶?, help_text="姣忔湀鎵ц鏃剁殑鏃ユ湡(1-31)")

    # 浠诲姟鐘舵€?    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active',
                              verbose_name="浠诲姟鐘舵€?, db_comment="浠诲姟鐘舵€?)
    is_enabled = models.BooleanField(default=True, verbose_name="鏄惁鍚敤", db_comment="鏄惁鍚敤")

    # 閫氱煡閰嶇疆
    send_email_notification = models.BooleanField(default=True, verbose_name="鍙戦€侀偖浠堕€氱煡",
                                                  db_comment="鍙戦€侀偖浠堕€氱煡")
    notification_emails = models.TextField(blank=True, verbose_name="閫氱煡閭",
                                           db_comment="閫氱煡閭", help_text="澶氫釜閭鐢ㄩ€楀彿鍒嗛殧")
    notify_on_success = models.BooleanField(default=False, verbose_name="鎴愬姛鏃堕€氱煡",
                                            db_comment="鎴愬姛鏃堕€氱煡")
    notify_on_failure = models.BooleanField(default=True, verbose_name="澶辫触鏃堕€氱煡",
                                            db_comment="澶辫触鏃堕€氱煡")


    max_retries = models.IntegerField(default=3, verbose_name="鏈€澶ч噸璇曟鏁?, db_comment="鏈€澶ч噸璇曟鏁?)
    retry_delay = models.IntegerField(default=300, verbose_name="閲嶈瘯闂撮殧(绉?", db_comment="閲嶈瘯闂撮殧(绉?")

    # 鎵ц缁熻
    last_run_time = models.DateTimeField(null=True, blank=True, verbose_name="涓婃鎵ц鏃堕棿",
                                         db_comment="涓婃鎵ц鏃堕棿")
    next_run_time = models.DateTimeField(null=True, blank=True, verbose_name="涓嬫鎵ц鏃堕棿",
                                         db_comment="涓嬫鎵ц鏃堕棿")
    total_runs = models.IntegerField(default=0, verbose_name="鎬绘墽琛屾鏁?, db_comment="鎬绘墽琛屾鏁?)
    successful_runs = models.IntegerField(default=0, verbose_name="鎴愬姛娆℃暟", db_comment="鎴愬姛娆℃暟")
    failed_runs = models.IntegerField(default=0, verbose_name="澶辫触娆℃暟", db_comment="澶辫触娆℃暟")

    # Celery浠诲姟ID
    celery_task_id = models.CharField(max_length=255, blank=True, verbose_name="Celery浠诲姟ID",
                                      db_comment="Celery浠诲姟ID")

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="鍒涘缓鏃堕棿", db_comment="鍒涘缓鏃堕棿")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="鏇存柊鏃堕棿", db_comment="鏇存柊鏃堕棿")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_scheduled_tasks',
                                   verbose_name="鍒涘缓浜?, db_comment="鍒涘缓浜?)

    def __str__(self):
        return f"{self.name} - {self.test_suite.name}"

    class Meta:
        verbose_name = "瀹氭椂浠诲姟"
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def get_notification_email_list(self):
        """鑾峰彇閫氱煡閭鍒楄〃"""
        if not self.notification_emails:
            return []
        return [email.strip() for email in self.notification_emails.split(',') if email.strip()]

    def calculate_next_run_time(self):
        """璁＄畻涓嬫鎵ц鏃堕棿"""
        from datetime import datetime, timedelta
        import calendar

        now = datetime.now()

        if self.schedule_type == 'once':
            if self.scheduled_date and self.scheduled_time:
                next_run = datetime.combine(self.scheduled_date, self.scheduled_time)
                return next_run if next_run > now else None

        elif self.schedule_type == 'daily':
            if self.scheduled_time:
                next_run = datetime.combine(now.date(), self.scheduled_time)
                if next_run <= now:
                    next_run += timedelta(days=1)
                return next_run

        elif self.schedule_type == 'weekly':
            if self.weekday and self.scheduled_time:
                days_ahead = self.weekday - now.weekday()
                if days_ahead <= 0:  # Target day already happened this week
                    days_ahead += 7
                next_run = datetime.combine(now.date(), self.scheduled_time) + timedelta(days=days_ahead)
                return next_run

        elif self.schedule_type == 'monthly':
            if self.day_of_month and self.scheduled_time:
                # 璁＄畻涓嬩釜鏈堢殑鎵ц鏃堕棿
                if now.day < self.day_of_month:
                    # 鏈湀杩樻病鍒版墽琛屾棩鏈?                    try:
                        next_run = datetime.combine(
                            now.replace(day=self.day_of_month).date(),
                            self.scheduled_time
                        )
                        return next_run
                    except ValueError:
                        # 褰撴湀娌℃湁杩欎竴澶╋紝璺冲埌涓嬩釜鏈?                        pass

                # 璁＄畻涓嬩釜鏈?                if now.month == 12:
                    next_year = now.year + 1
                    next_month = 1
                else:
                    next_year = now.year
                    next_month = now.month + 1

                # 纭繚涓嬩釜鏈堟湁杩欎竴澶?                max_day = calendar.monthrange(next_year, next_month)[1]
                target_day = min(self.day_of_month, max_day)

                next_run = datetime.combine(
                    datetime(next_year, next_month, target_day).date(),
                    self.scheduled_time
                )
                return next_run

        elif self.schedule_type == 'cron' and self.cron_expression:
            # 杩欓噷闇€瑕佷娇鐢╟ron瑙ｆ瀽搴擄紝濡俢roniter
            try:
                from croniter import croniter
                cron = croniter(self.cron_expression, now)
                return cron.get_next(datetime)
            except ImportError:
                # 濡傛灉娌℃湁瀹夎croniter锛岃繑鍥濶one
                pass

        return None

    def update_next_run_time(self):
        """鏇存柊涓嬫鎵ц鏃堕棿"""
        self.next_run_time = self.calculate_next_run_time()
        self.save(update_fields=['next_run_time'])

    @property
    def success_rate(self):
        """鎴愬姛鐜?""
        if self.total_runs == 0:
            return 0
        return (self.successful_runs / self.total_runs) * 100


class TaskExecutionLog(models.Model):
    """浠诲姟鎵ц鏃ュ織"""
    STATUS_CHOICES = [
        ('running', '杩愯涓?),
        ('success', '鎴愬姛'),
        ('failed', '澶辫触'),
        ('timeout', '瓒呮椂'),
        ('cancelled', '宸插彇娑?),
    ]

    scheduled_task = models.ForeignKey(ScheduledTask, on_delete=models.CASCADE, related_name='execution_logs',
                                       verbose_name="瀹氭椂浠诲姟", db_comment="瀹氭椂浠诲姟")
    test_run = models.ForeignKey(TestRun, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='task_execution_logs', verbose_name="娴嬭瘯杩愯", db_comment="娴嬭瘯杩愯")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running',
                              verbose_name="鎵ц鐘舵€?, db_comment="鎵ц鐘舵€?)
    start_time = models.DateTimeField(auto_now_add=True, verbose_name="寮€濮嬫椂闂?, db_comment="寮€濮嬫椂闂?)
    end_time = models.DateTimeField(null=True, blank=True, verbose_name="缁撴潫鏃堕棿", db_comment="缁撴潫鏃堕棿")
    duration = models.FloatField(null=True, blank=True, verbose_name="鎵ц鏃堕暱(绉?", db_comment="鎵ц鏃堕暱(绉?")

    # 鎵ц缁撴灉缁熻
    total_test_cases = models.IntegerField(default=0, verbose_name="鎬绘祴璇曠敤渚嬫暟", db_comment="鎬绘祴璇曠敤渚嬫暟")
    passed_test_cases = models.IntegerField(default=0, verbose_name="閫氳繃鐢ㄤ緥鏁?, db_comment="閫氳繃鐢ㄤ緥鏁?)
    failed_test_cases = models.IntegerField(default=0, verbose_name="澶辫触鐢ㄤ緥鏁?, db_comment="澶辫触鐢ㄤ緥鏁?)
    error_test_cases = models.IntegerField(default=0, verbose_name="閿欒鐢ㄤ緥鏁?, db_comment="閿欒鐢ㄤ緥鏁?)

    error_message = models.TextField(blank=True, verbose_name="閿欒淇℃伅", db_comment="閿欒淇℃伅")
    retry_count = models.IntegerField(default=0, verbose_name="閲嶈瘯娆℃暟", db_comment="閲嶈瘯娆℃暟")

    # 閫氱煡鐘舵€?    email_sent = models.BooleanField(default=False, verbose_name="閭欢宸插彂閫?, db_comment="閭欢宸插彂閫?)
    email_sent_time = models.DateTimeField(null=True, blank=True, verbose_name="閭欢鍙戦€佹椂闂?,
                                           db_comment="閭欢鍙戦€佹椂闂?)

    def __str__(self):
        return f"{self.scheduled_task.name} - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"

    class Meta:
        verbose_name = "浠诲姟鎵ц鏃ュ織"
        verbose_name_plural = verbose_name
        ordering = ['-start_time']

    @property
    def success_rate(self):
        """鎴愬姛鐜?""
        if self.total_test_cases == 0:
            return 0
        return (self.passed_test_cases / self.total_test_cases) * 100

    def calculate_duration(self):
        """璁＄畻鎵ц鏃堕暱"""
        if self.start_time and self.end_time:
            self.duration = (self.end_time - self.start_time).total_seconds()
            return self.duration
        return None
#
#
# # 淇″彿澶勭悊鍣?# from django.db.models.signals import post_save, post_delete
# from django.dispatch import receiver
#
#
# @receiver(post_save, sender=ScheduledTask)
# def handle_scheduled_task_save(sender, instance, created, **kwargs):
#     """澶勭悊瀹氭椂浠诲姟淇濆瓨淇″彿"""
#     from .scheduler import TaskScheduler
#
#     # 鍒涘缓鎴栨洿鏂癈elery浠诲姟
#     TaskScheduler.create_or_update_celery_task(instance)
#
#
# @receiver(post_delete, sender=ScheduledTask)
# def handle_scheduled_task_delete(sender, instance, **kwargs):
#     """澶勭悊瀹氭椂浠诲姟鍒犻櫎淇″彿 - 浼樺寲鐗堟湰"""
#     import logging
#     logger = logging.getLogger(__name__)
#
#     try:
#         logger.info(f"淇″彿澶勭悊鍣? 寮€濮嬪鐞嗗畾鏃朵换鍔″垹闄?- {instance.name}")
#
#         # 鍒犻櫎瀵瑰簲鐨凜elery浠诲姟
#         if instance.celery_task_id:
#             try:
#                 from django_celery_beat.models import PeriodicTask
#                 celery_task = PeriodicTask.objects.get(name=instance.celery_task_id)
#                 celery_task.delete()
#                 logger.info(f"淇″彿澶勭悊鍣? 鎴愬姛鍒犻櫎Celery Beat浠诲姟 - {instance.celery_task_id}")
#             except PeriodicTask.DoesNotExist:
#                 logger.warning(f"淇″彿澶勭悊鍣? Celery Beat浠诲姟涓嶅瓨鍦?- {instance.celery_task_id}")
#             except Exception as e:
#                 logger.error(f"淇″彿澶勭悊鍣? 鍒犻櫎Celery Beat浠诲姟澶辫触 - {str(e)}")
#         else:
#             logger.info(f"淇″彿澶勭悊鍣? 浠诲姟娌℃湁鍏宠仈鐨凜elery Beat浠诲姟 - {instance.name}")
#
#     except Exception as e:
#         logger.error(f"淇″彿澶勭悊鍣? 澶勭悊瀹氭椂浠诲姟鍒犻櫎澶辫触 - {str(e)}")
