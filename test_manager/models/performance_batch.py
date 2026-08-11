"""
性能测试批量执行模块

提供批量压测任务的管理和执行功能，支持：
1. 批量创建和管理多个性能测试任务
2. 批量启动执行（串行或并行）
3. 生成批量整体报告
"""
from django.conf import settings
from django.db import models

from test_manager.models.project import Project
from test_manager.models.performance import PerformanceTestTask


class PerformanceBatchTask(models.Model):
    """
    性能测试批量任务
    
    用于管理和执行一组性能测试任务的集合
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_PARTIAL_SUCCESS = "partial_success"
    STATUS_COMPLETED = "completed"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_PARTIAL_SUCCESS, "部分成功"),
        (STATUS_COMPLETED, "全部完成"),
        (STATUS_FAILED, "执行失败"),
    ]
    
    EXECUTE_MODE_SERIAL = "serial"  # 串行执行
    EXECUTE_MODE_PARALLEL = "parallel"  # 并行执行
    EXECUTE_MODE_CHOICES = [
        (EXECUTE_MODE_SERIAL, "串行执行"),
        (EXECUTE_MODE_PARALLEL, "并行执行"),
    ]

    # 基本信息
    name = models.CharField(
        max_length=255,
        verbose_name="批量任务名称",
        db_comment="批量任务名称",
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        verbose_name="所属项目",
        db_comment="所属项目",
    )
    execute_mode = models.CharField(
        max_length=20,
        choices=EXECUTE_MODE_CHOICES,
        default=EXECUTE_MODE_SERIAL,
        verbose_name="执行模式",
        db_comment="执行模式：串行/并行",
    )
    max_concurrent = models.IntegerField(
        default=5,
        verbose_name="最大并发数",
        db_comment="并行执行时的最大并发数（仅并行模式有效）",
        help_text="并行模式下同时执行的任务数量上限",
    )

    # 状态统计
    total_tasks = models.IntegerField(
        default=0,
        verbose_name="总任务数",
        db_comment="批量中包含的任务总数",
    )
    completed_tasks = models.IntegerField(
        default=0,
        verbose_name="已完成任务数",
        db_comment="已完成的任务数量",
    )
    successful_tasks = models.IntegerField(
        default=0,
        verbose_name="成功任务数",
        db_comment="成功执行的任务数量",
    )
    failed_tasks = models.IntegerField(
        default=0,
        verbose_name="失败任务数",
        db_comment="执行失败的任务数量",
    )
    running_tasks = models.IntegerField(
        default=0,
        verbose_name="运行中任务数",
        db_comment="当前正在执行的任务数量",
    )

    # 状态与时间
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="状态",
        db_comment="批量任务状态",
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
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="开始时间",
        db_comment="批量任务开始执行时间",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="结束时间",
        db_comment="批量任务全部完成时间",
    )

    # 备注说明
    description = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="描述",
        db_comment="批量任务描述说明",
    )

    class Meta:
        db_table = "performance_batch_task"
        verbose_name = "性能测试批量任务"
        verbose_name_plural = verbose_name
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["project", "status"], name="perf_batch_proj_status_idx"),
            models.Index(fields=["creator", "created_at"], name="perf_batch_creator_idx"),
            models.Index(fields=["status", "created_at"], name="perf_batch_status_created_idx"),
        ]

    def __str__(self):
        return f"{self.name} ({self.total_tasks}/{self.completed_tasks})"
    
    @property
    def success_rate(self):
        """计算成功率"""
        if self.total_tasks == 0:
            return 0.0
        return round((self.successful_tasks / self.total_tasks) * 100, 2)
    
    @property
    def progress(self):
        """计算进度百分比"""
        if self.total_tasks == 0:
            return 0.0
        return round((self.completed_tasks / self.total_tasks) * 100, 2)


class PerformanceBatchItem(models.Model):
    """
    批量任务中的单个任务项
    
    关联批量任务和具体的性能测试任务，跟踪执行状态
    """

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_SKIPPED = "skipped"
    STATUS_CHOICES = [
        (STATUS_PENDING, "待执行"),
        (STATUS_RUNNING, "执行中"),
        (STATUS_SUCCESS, "成功"),
        (STATUS_FAILED, "失败"),
        (STATUS_SKIPPED, "跳过"),
    ]

    # 关联关系
    batch = models.ForeignKey(
        PerformanceBatchTask,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="所属批量任务",
        db_comment="所属批量任务",
    )
    performance_task = models.ForeignKey(
        PerformanceTestTask,
        on_delete=models.CASCADE,
        verbose_name="性能测试任务",
        db_comment="关联的性能测试任务 ID",
    )

    # 执行状态
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        verbose_name="状态",
        db_comment="任务项执行状态",
    )
    order_index = models.IntegerField(
        default=0,
        verbose_name="执行顺序",
        db_comment="在批量中的执行顺序（串行模式有效）",
    )

    # 执行信息
    started_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="开始时间",
        db_comment="单个任务开始执行时间",
    )
    finished_at = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="结束时间",
        db_comment="单个任务执行结束时间",
    )
    error_message = models.CharField(
        max_length=500,
        blank=True,
        default="",
        verbose_name="错误信息",
        db_comment="执行失败的错误信息",
    )
    result_summary = models.JSONField(
        null=True,
        blank=True,
        verbose_name="结果摘要",
        db_comment="执行结果的概要信息（QPS、响应时间等）",
    )

    class Meta:
        db_table = "performance_batch_item"
        verbose_name = "批量任务项"
        verbose_name_plural = verbose_name
        ordering = ["batch", "order_index"]
        indexes = [
            models.Index(fields=["batch", "status"], name="perf_bitem_batch_sts_idx"),
            models.Index(fields=["batch", "order_index"], name="perf_bitem_batch_ord_idx"),
        ]

    def __str__(self):
        task_name = self.performance_task.name if self.performance_task else "未知任务"
        return f"{self.batch.name} - {task_name}"
    
    @property
    def is_finished(self):
        """判断任务是否已完成"""
        return self.status in [self.STATUS_SUCCESS, self.STATUS_FAILED, self.STATUS_SKIPPED]
