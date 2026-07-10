from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0032_apiasset_interface_desc_apiasset_error_code"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TestScene",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_comment="场景名称", max_length=150, verbose_name="场景名称")),
                ("description", models.TextField(blank=True, db_comment="场景描述", default="", verbose_name="场景描述")),
                ("variables", models.JSONField(blank=True, db_comment="场景变量池", default=dict, verbose_name="场景变量池")),
                ("runtime_config", models.JSONField(blank=True, db_comment="运行配置", default=dict, verbose_name="运行配置")),
                ("is_active", models.BooleanField(db_comment="是否启用", default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_test_scenes",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        db_comment="所属API项目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_scenes",
                        to="test_manager.apiproject",
                        verbose_name="所属API项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "测试场景",
                "verbose_name_plural": "测试场景",
                "db_table": "test_scene",
                "ordering": ["-updated_at", "-id"],
                "indexes": [
                    models.Index(fields=["project", "is_active"], name="test_scene_proj_active_idx"),
                    models.Index(fields=["project", "updated_at"], name="test_scene_proj_update_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TestSceneNode",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("node_key", models.CharField(db_comment="节点标识", max_length=80, verbose_name="节点标识")),
                ("name", models.CharField(db_comment="节点名称", max_length=150, verbose_name="节点名称")),
                ("description", models.TextField(blank=True, db_comment="节点描述", default="", verbose_name="节点描述")),
                ("request_headers", models.JSONField(blank=True, db_comment="请求头覆盖", default=dict, verbose_name="请求头覆盖")),
                ("request_params", models.JSONField(blank=True, db_comment="请求参数覆盖", default=dict, verbose_name="请求参数覆盖")),
                ("request_body", models.JSONField(blank=True, db_comment="请求体覆盖", default=dict, verbose_name="请求体覆盖")),
                ("assert_rules", models.JSONField(blank=True, db_comment="断言规则", default=list, verbose_name="断言规则")),
                ("extract_rules", models.JSONField(blank=True, db_comment="提取规则", default=list, verbose_name="提取规则")),
                ("expected_status_code", models.PositiveIntegerField(db_comment="预期状态码", default=200, verbose_name="预期状态码")),
                ("timeout", models.PositiveIntegerField(blank=True, db_comment="超时时间(秒)", null=True, verbose_name="超时时间(秒)")),
                (
                    "on_failed",
                    models.CharField(
                        choices=[("stop", "失败终止"), ("continue", "失败继续")],
                        db_comment="失败策略",
                        default="stop",
                        max_length=20,
                        verbose_name="失败策略",
                    ),
                ),
                ("sort", models.IntegerField(db_comment="排序", default=0, verbose_name="排序")),
                ("is_enabled", models.BooleanField(db_comment="是否启用", default=True, verbose_name="是否启用")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "api_asset",
                    models.ForeignKey(
                        blank=True,
                        db_comment="关联API资产",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="scene_nodes",
                        to="test_manager.apiasset",
                        verbose_name="关联API资产",
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey(
                        db_comment="所属场景",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nodes",
                        to="test_manager.testscene",
                        verbose_name="所属场景",
                    ),
                ),
            ],
            options={
                "verbose_name": "测试场景节点",
                "verbose_name_plural": "测试场景节点",
                "db_table": "test_scene_node",
                "ordering": ["sort", "id"],
                "unique_together": {("scene", "node_key")},
                "indexes": [
                    models.Index(fields=["scene", "sort"], name="test_scene_node_sort_idx"),
                    models.Index(fields=["scene", "is_enabled"], name="test_scene_node_enable_idx"),
                ],
            },
        ),
        migrations.CreateModel(
            name="TestSceneExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "run_mode",
                    models.CharField(
                        choices=[("all", "全流程"), ("single", "单步")],
                        db_comment="执行模式",
                        default="all",
                        max_length=20,
                        verbose_name="执行模式",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[("running", "执行中"), ("success", "成功"), ("failed", "失败")],
                        db_comment="执行状态",
                        default="running",
                        max_length=20,
                        verbose_name="执行状态",
                    ),
                ),
                ("total_nodes", models.PositiveIntegerField(db_comment="总节点数", default=0, verbose_name="总节点数")),
                ("passed_nodes", models.PositiveIntegerField(db_comment="成功节点数", default=0, verbose_name="成功节点数")),
                ("failed_nodes", models.PositiveIntegerField(db_comment="失败节点数", default=0, verbose_name="失败节点数")),
                ("skipped_nodes", models.PositiveIntegerField(db_comment="跳过节点数", default=0, verbose_name="跳过节点数")),
                ("duration_ms", models.PositiveIntegerField(db_comment="执行耗时毫秒", default=0, verbose_name="执行耗时毫秒")),
                ("summary", models.JSONField(blank=True, db_comment="执行汇总", default=dict, verbose_name="执行汇总")),
                ("node_results", models.JSONField(blank=True, db_comment="节点执行结果", default=list, verbose_name="节点执行结果")),
                ("error_message", models.TextField(blank=True, db_comment="错误信息", default="", verbose_name="错误信息")),
                ("started_at", models.DateTimeField(auto_now_add=True, db_comment="开始时间", verbose_name="开始时间")),
                ("finished_at", models.DateTimeField(blank=True, db_comment="结束时间", null=True, verbose_name="结束时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        blank=True,
                        db_comment="执行人",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="test_scene_executions",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="执行人",
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey(
                        db_comment="场景",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="executions",
                        to="test_manager.testscene",
                        verbose_name="场景",
                    ),
                ),
                (
                    "target_node",
                    models.ForeignKey(
                        blank=True,
                        db_comment="目标节点",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="executions",
                        to="test_manager.testscenenode",
                        verbose_name="目标节点",
                    ),
                ),
            ],
            options={
                "verbose_name": "场景执行记录",
                "verbose_name_plural": "场景执行记录",
                "db_table": "test_scene_execution",
                "ordering": ["-created_at"],
                "indexes": [
                    models.Index(fields=["scene", "created_at"], name="test_scene_exec_scene_idx"),
                    models.Index(fields=["status", "created_at"], name="test_scene_exec_status_idx"),
                ],
            },
        ),
    ]
