import uuid
from django.urls import reverse
from django.db import models
from django.contrib.auth.models import User
import json
from test_manager.models.project import Project
from test_manager.models.test_case import TestRun, TestSuiteRun, TestResult
from test_manager.models.scene import TestSceneExecution


class TestReport(models.Model):
    """测试报告模型"""
    REPORT_TYPE_CHOICES = [
        ('test_run', 'Test Run'),
        ('test_suite_run', 'Test Suite Run'),
        ('scene_execution', 'Scene Execution'),
        ('custom', 'Custom'),
    ]

    REPORT_FORMAT_CHOICES = [
        ('html', 'HTML'),
        ('pdf', 'PDF'),
        ('json', 'JSON'),
    ]

    name = models.CharField(max_length=255, verbose_name="报告名称", db_comment="报告名称")
    description = models.TextField(null=True, blank=True, verbose_name="报告描述", db_comment="报告描述")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间", db_comment="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间", db_comment="更新时间")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='test_reports', verbose_name="项目",
                                db_comment="项目")
    report_type = models.CharField(max_length=20, choices=REPORT_TYPE_CHOICES, default='test_run',
                                   verbose_name="报告类型", db_comment="报告类型")
    report_format = models.CharField(max_length=10, choices=REPORT_FORMAT_CHOICES, default='html',
                                     verbose_name="报告格式", db_comment="报告格式")
    content = models.TextField(verbose_name="报告内容", db_comment="报告内容")
    test_run = models.ForeignKey(TestRun, on_delete=models.SET_NULL, null=True, blank=True, related_name='reports',
                                 verbose_name="测试运行", db_comment="测试运行")
    test_suite_run = models.ForeignKey(TestSuiteRun, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name='reports', verbose_name="测试套件运行", db_comment="测试套件运行")
    # 关联 TestSceneExecution：删除执行记录时仅置空本字段，不级联删除报告（on_delete=SET_NULL）。
    scene_execution = models.ForeignKey(
        TestSceneExecution,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reports",
        verbose_name="场景执行记录",
        db_comment="场景执行记录，删除执行时报告保留",
    )
    test_results = models.ForeignKey(TestResult, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='reports', verbose_name="测试结果", db_comment="测试结果")
    is_public = models.BooleanField(default=False, verbose_name="公开", db_comment="公开")
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True,
                                   related_name='created_test_reports', verbose_name="创建者", db_comment="创建者")

    class Meta:
        ordering = ['-created_at']
        verbose_name = "测试报告"
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('test_report_detail', kwargs={'pk': self.pk})

    def get_delete_url(self):
        return reverse('test_report_delete', kwargs={'pk': self.pk})

    def get_summary(self):
        """返回报告的摘要信息"""
        # 场景执行报告（scene_execution）：优先解析 JSON；HTML 格式可回退到关联执行或 JSON 子结构。
        if self.report_type == 'scene_execution':
            summary = {'_source': 'scene_execution_report'}  # 场景执行报告专属标记
            if self.report_format == 'json':
                try:
                    data = json.loads(self.content)
                except (json.JSONDecodeError, TypeError, ValueError):
                    return summary
                exec_block = data.get('execution') or {}
                scene_block = data.get('scene') or {}
                nodes = data.get('nodes') or []
                failed_nodes = sum(1 for n in nodes if (n or {}).get('status') in ('failed', 'failure', 'error'))
                summary.update({
                    'scene_name': scene_block.get('name', ''),
                    'status': exec_block.get('status', ''),
                    'duration_sec': exec_block.get('duration'),
                    'failed_nodes': failed_nodes,
                    'total_nodes': len(nodes),
                })
                return summary
            if self.scene_execution_id:
                ex = self.scene_execution
                if ex is not None:
                    nodes = ex.node_results or []
                    failed_nodes = sum(
                        1 for n in nodes if (n or {}).get('status') in ('failed', 'failure', 'error')
                    )
                    summary.update({
                        'scene_name': ex.scene.name if ex.scene_id else '',
                        'status': ex.status,
                        'duration_sec': (ex.duration_ms or 0) / 1000.0,
                        'failed_nodes': failed_nodes,
                        'total_nodes': len(nodes),
                    })
                    return summary
            return summary
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
            except (json.JSONDecodeError, TypeError, ValueError):
                pass

        # 测试运行报告（test_run + HTML）：通过关联的 TestRun.test_results 聚合统计数据
        if self.report_type == 'test_run' and self.test_run_id:
            test_run = self.test_run
            if test_run is not None:
                total = passed = failed = error = skipped = 0
                for tr in test_run.test_results.all():
                    total += 1
                    if tr.status == 'passed':
                        passed += 1
                    elif tr.status == 'failed':
                        failed += 1
                    elif tr.status == 'error':
                        error += 1
                    elif tr.status == 'skipped':
                        skipped += 1
                success_rate = f"{passed / total * 100:.1f}%" if total > 0 else "0%"
                return {
                    'total': total,
                    'passed': passed,
                    'failed': failed,
                    'error': error,
                    'skipped': skipped,
                    'success_rate': success_rate,
                }

        return {}
