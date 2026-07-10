"""
性能测试模块 - 阶段1：单接口本地压测

复用 Project / Environment / ApiAsset(接口) 模型，
新增性能测试任务表和结果表，不涉及分布式 Agent。

阶段2（单机增强）：结果表扩展 P95/P99/最大 RT/错误分类；任务表支持 CSV 参数化文件。
阶段3（分布式）：可在本模块增加 runner 模式、多机协调等字段，与单机逻辑解耦。
"""
from django.conf import settings
from django.core.validators import FileExtensionValidator
from django.db import models

from test_manager.models.project import Project
from test_manager.models.environment import Environment
from test_manager.models.api_asset import ApiAsset


class PerformanceTestTask(models.Model):
    """
    性能测试任务表

    用于配置单接口压测参数，支持草稿/执行中/已完成/失败等状态。
    """

    STATUS_DRAFT = "draft"
    STATUS_RUNNING = "running"
    STATUS_STOPPED = "stopped"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "草稿"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_STOPPED, "已停止"),
        (STATUS_COMPLETED, "已完成"),
        (STATUS_FAILED, "执行失败"),
    ]

    # 任务基本信息
    name = models.CharField(
        max_length=255,
        verbose_name="任务名称",
        db_comment="任务名称",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    environment = models.ForeignKey(
        Environment,
        on_delete=models.CASCADE,
        verbose_name="测试环境",
        db_comment="测试环境",
    )
    interface = models.ForeignKey(
        ApiAsset,
        on_delete=models.CASCADE,
        verbose_name="关联单接口",
        db_comment="关联单接口（API资产）",
    )

    # 压测参数
    total_users = models.IntegerField(
        verbose_name="总虚拟用户数",
        db_comment="总虚拟用户数",
    )
    spawn_rate = models.IntegerField(
        verbose_name="用户生成速率",
        db_comment="每秒启动用户数",
    )
    run_time = models.IntegerField(
        verbose_name="压测时长",
        db_comment="压测时长（秒）",
    )
    target_rps = models.FloatField(
        null=True,
        blank=True,
        verbose_name="目标 RPS",
        db_comment="目标全局请求/秒；有值时按当前活跃用户数节流近似该 RPS，空表示不限制（由并发与思考时间决定）",
    )

    # 状态与时间
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_DRAFT,
        verbose_name="状态",
        db_comment="任务状态",
    )
    creator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        verbose_name="创建人",
        db_comment="创建人",
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name="创建时间",
        db_comment="创建时间",
    )
    executed_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="执行开始时间",
        db_comment="执行开始时间",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="执行结束时间",
        db_comment="执行结束时间（自然结束或手动停止）",
    )

    # 手动停止审计（与 Locust 单机停止接口联动）
    stopped_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="停止时间",
        db_comment="手动停止时间",
    )
    stopped_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="stopped_performance_tasks",
        verbose_name="停止人",
        db_comment="手动停止操作人",
    )
    stop_reason = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="停止原因",
        db_comment="手动停止原因说明",
    )
    runner_pid = models.IntegerField(
        null=True,
        blank=True,
        verbose_name="执行进程 PID",
        db_comment="process 模式下 Locust 子进程 PID，用于停止",
    )
    celery_task_id = models.CharField(
        max_length=255,
        null=True,
        blank=True,
        verbose_name="Celery 任务 ID",
        db_comment="celery 模式下异步任务 id，用于 revoke",
    )

    # 额外配置：超时时间、断言、多阶段负载、think_time、CSV 策略等（优先用 JSON 避免频繁迁移）
    extra_config = models.JSONField(
        null=True,
        blank=True,
        verbose_name="额外配置",
        db_comment="额外配置：timeout/assertions/stages/think_time_ms/csv_read_strategy 等",
    )

    # 阶段2：CSV 参数化（可空，兼容旧任务）
    csv_file = models.FileField(
        upload_to="performance_csv/",
        null=True,
        blank=True,
        verbose_name="CSV 参数文件",
        db_comment="CSV 参数化数据文件；列名对应占位符 {{列名}}",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["csv"],
                message="仅支持上传 .csv 文件",
            )
        ],
    )

    class Meta:
        db_table = "performance_test_task"
        verbose_name = "性能测试任务"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"], name="perf_task_proj_status_idx"),
            models.Index(fields=["creator", "created_at"], name="perf_task_creator_idx"),
        ]

    def __str__(self):
        return self.name


class PerformanceTestResult(models.Model):
    """
    性能测试结果表

    存储压测过程中的采样数据：QPS、响应时间、失败率等。
    每个任务可有多条结果记录（按时间戳采样）。
    """

    task = models.ForeignKey(
        PerformanceTestTask,
        on_delete=models.CASCADE,
        related_name="results",
        verbose_name="所属任务",
        db_comment="所属任务",
    )
    timestamp = models.DateTimeField(
        verbose_name="数据时间戳",
        db_comment="数据时间戳",
    )
    active_users = models.IntegerField(
        verbose_name="当前活跃用户数",
        db_comment="当前活跃用户数",
    )
    requests_per_second = models.FloatField(
        verbose_name="QPS",
        db_comment="每秒请求数",
    )
    response_time_50 = models.FloatField(
        verbose_name="50%响应时间",
        db_comment="50%响应时间（ms）",
    )
    response_time_90 = models.FloatField(
        verbose_name="90%响应时间",
        db_comment="90%响应时间（ms）",
    )
    failure_rate = models.FloatField(
        verbose_name="失败率",
        db_comment="失败率（%）",
    )
    # 阶段2：分位数与错误分类（历史迁移默认 0 / {}）
    p95 = models.FloatField(
        default=0,
        verbose_name="P95 响应时间(ms)",
        db_comment="P95 响应时间（ms），来自 Locust StatsEntry 分位数计算",
    )
    p99 = models.FloatField(
        default=0,
        verbose_name="P99 响应时间(ms)",
        db_comment="P99 响应时间（ms）",
    )
    max_response_time = models.FloatField(
        default=0,
        verbose_name="最大响应时间(ms)",
        db_comment="最大响应时间（ms），对应 Locust max_response_time",
    )
    error_classification = models.JSONField(
        blank=True,
        default=dict,
        verbose_name="错误分类",
        db_comment="采样时刻各错误类型累计次数快照，键：http_status_error/timeout/connection_error/assertion_failure 等",
    )

    class Meta:
        db_table = "performance_test_result"
        verbose_name = "性能测试结果"
        verbose_name_plural = verbose_name
        ordering = ["task", "timestamp"]
        indexes = [
            models.Index(fields=["task", "timestamp"], name="perf_result_task_ts_idx"),
        ]

    def __str__(self):
        return f"Result-{self.task_id}-{self.timestamp}"
