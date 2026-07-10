from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("test_manager", "0019_testcase_timeout"),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiProject",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_comment="项目名称", max_length=100, verbose_name="项目名称")),
                ("description", models.TextField(blank=True, db_comment="项目描述", verbose_name="项目描述")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_api_projects",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "platform_project",
                    models.OneToOneField(
                        blank=True,
                        db_comment="平台项目",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_project_binding",
                        to="test_manager.project",
                        verbose_name="平台项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "API项目",
                "verbose_name_plural": "API项目",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ParameterConfig",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(db_comment="参数键", max_length=100, unique=True, verbose_name="参数键")),
                ("value", models.TextField(blank=True, db_comment="参数值", default="", verbose_name="参数值")),
                (
                    "description",
                    models.CharField(blank=True, db_comment="参数说明", default="", max_length=255, verbose_name="参数说明"),
                ),
                (
                    "category",
                    models.CharField(blank=True, db_comment="参数分类", default="general", max_length=50, verbose_name="参数分类"),
                ),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
            ],
            options={
                "verbose_name": "参数配置",
                "verbose_name_plural": "参数配置",
                "ordering": ["category", "key"],
            },
        ),
        migrations.CreateModel(
            name="AICaseDraftGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("interface_id", models.PositiveIntegerField(blank=True, db_comment="接口ID", null=True, verbose_name="接口ID")),
                ("case_type", models.CharField(db_comment="用例类型", max_length=50, verbose_name="用例类型")),
                (
                    "status",
                    models.CharField(
                        choices=[("pending", "待导入"), ("partial_imported", "部分导入"), ("imported", "全部导入")],
                        db_comment="导入状态",
                        default="pending",
                        max_length=20,
                        verbose_name="导入状态",
                    ),
                ),
                ("base_info", models.JSONField(blank=True, db_comment="基础信息", default=dict, verbose_name="基础信息")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_ai_case_draft_groups",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        db_comment="用例分组",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_case_draft_groups",
                        to="test_manager.testcasegroup",
                        verbose_name="用例分组",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        db_comment="所属项目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="ai_case_draft_groups",
                        to="test_manager.project",
                        verbose_name="所属项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI用例草稿组",
                "verbose_name_plural": "AI用例草稿组",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ApiGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_comment="分组名称", max_length=100, verbose_name="分组名称")),
                ("sort_order", models.IntegerField(db_comment="排序", default=0, verbose_name="排序")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "parent",
                    models.ForeignKey(
                        blank=True,
                        db_comment="父分组",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="children",
                        to="test_manager.apigroup",
                        verbose_name="父分组",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        db_comment="所属项目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="groups",
                        to="test_manager.apiproject",
                        verbose_name="所属项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "API分组",
                "verbose_name_plural": "API分组",
                "ordering": ["sort_order", "id"],
                "unique_together": {("project", "parent", "name")},
            },
        ),
        migrations.CreateModel(
            name="ApiAsset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_comment="接口名称", max_length=150, verbose_name="接口名称")),
                (
                    "method",
                    models.CharField(
                        choices=[("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE"), ("PATCH", "PATCH")],
                        db_comment="请求方法",
                        max_length=10,
                        verbose_name="请求方法",
                    ),
                ),
                ("url", models.CharField(db_comment="请求URL", max_length=500, verbose_name="请求URL")),
                ("request_headers", models.JSONField(blank=True, db_comment="请求头", default=dict, verbose_name="请求头")),
                ("request_params", models.JSONField(blank=True, db_comment="请求参数", default=dict, verbose_name="请求参数")),
                (
                    "request_body_format",
                    models.CharField(
                        choices=[("json", "JSON"), ("form-data", "Form Data")],
                        db_comment="请求体格式",
                        default="json",
                        max_length=20,
                        verbose_name="请求体格式",
                    ),
                ),
                ("request_body", models.JSONField(blank=True, db_comment="请求体", default=dict, null=True, verbose_name="请求体")),
                ("response_schema", models.JSONField(blank=True, db_comment="响应Schema", default=dict, verbose_name="响应Schema")),
                ("auth_config", models.JSONField(blank=True, db_comment="鉴权配置", default=dict, verbose_name="鉴权配置")),
                (
                    "status",
                    models.CharField(
                        choices=[("draft", "草稿"), ("active", "可用"), ("deprecated", "已废弃")],
                        db_comment="状态",
                        default="draft",
                        max_length=20,
                        verbose_name="状态",
                    ),
                ),
                (
                    "source",
                    models.CharField(
                        choices=[("manual", "手工"), ("postman", "Postman"), ("apifox", "Apifox"), ("openapi", "OpenAPI")],
                        db_comment="来源",
                        default="manual",
                        max_length=20,
                        verbose_name="来源",
                    ),
                ),
                ("external_id", models.CharField(blank=True, db_comment="外部标识", default="", max_length=200, verbose_name="外部标识")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_api_assets",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "group",
                    models.ForeignKey(
                        blank=True,
                        db_comment="分组",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="assets",
                        to="test_manager.apigroup",
                        verbose_name="分组",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        db_comment="所属项目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="assets",
                        to="test_manager.apiproject",
                        verbose_name="所属项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "API资产",
                "verbose_name_plural": "API资产",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.CreateModel(
            name="AICaseDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("case_data", models.JSONField(blank=True, db_comment="用例数据", default=dict, verbose_name="用例数据")),
                ("is_valid", models.BooleanField(db_comment="是否校验通过", default=True, verbose_name="是否校验通过")),
                ("validation_errors", models.JSONField(blank=True, db_comment="校验错误", default=dict, verbose_name="校验错误")),
                (
                    "import_status",
                    models.CharField(
                        choices=[("pending", "待导入"), ("imported", "导入成功"), ("failed", "导入失败")],
                        db_comment="导入状态",
                        default="pending",
                        max_length=20,
                        verbose_name="导入状态",
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "draft_group",
                    models.ForeignKey(
                        db_comment="草稿组",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drafts",
                        to="test_manager.aicasedraftgroup",
                        verbose_name="草稿组",
                    ),
                ),
                (
                    "imported_case",
                    models.ForeignKey(
                        blank=True,
                        db_comment="导入后用例",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_imported_drafts",
                        to="test_manager.testcase",
                        verbose_name="导入后用例",
                    ),
                ),
            ],
            options={
                "verbose_name": "AI用例草稿",
                "verbose_name_plural": "AI用例草稿",
                "ordering": ["id"],
            },
        ),
        migrations.CreateModel(
            name="ApiHistory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("operation", models.CharField(choices=[("create", "创建"), ("update", "更新"), ("rollback", "回滚")], db_comment="操作", max_length=20, verbose_name="操作")),
                ("content", models.JSONField(blank=True, db_comment="内容", default=dict, verbose_name="内容")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                (
                    "asset",
                    models.ForeignKey(
                        db_comment="接口资产",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="histories",
                        to="test_manager.apiasset",
                        verbose_name="接口资产",
                    ),
                ),
                (
                    "operator",
                    models.ForeignKey(
                        blank=True,
                        db_comment="操作人",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="api_asset_histories",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="操作人",
                    ),
                ),
            ],
            options={
                "verbose_name": "API历史",
                "verbose_name_plural": "API历史",
                "ordering": ["-created_at"],
            },
        ),
    ]
