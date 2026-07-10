from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0030_apiasset_param_status_apiasset_param_type_and_more"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="ApiPreset",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(db_comment="预设名称", max_length=100, verbose_name="预设名称")),
                (
                    "preset_type",
                    models.CharField(
                        choices=[("request_headers", "请求头"), ("request_params", "请求参数"), ("form_data", "Form Data")],
                        db_comment="预设类型",
                        max_length=30,
                        verbose_name="预设类型",
                    ),
                ),
                ("data", models.JSONField(blank=True, db_comment="预设数据", default=list, verbose_name="预设数据")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="created_api_presets",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        db_comment="所属项目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="presets",
                        to="test_manager.apiproject",
                        verbose_name="所属项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "API预设",
                "verbose_name_plural": "API预设",
                "ordering": ["-updated_at"],
                "unique_together": {("project", "preset_type", "name", "created_by")},
            },
        ),
        migrations.CreateModel(
            name="ApiAssetDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("draft_key", models.CharField(blank=True, db_comment="草稿键", default="", max_length=120, verbose_name="草稿键")),
                ("draft_data", models.JSONField(blank=True, db_comment="草稿数据", default=dict, verbose_name="草稿数据")),
                ("expires_at", models.DateTimeField(db_comment="过期时间", verbose_name="过期时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "asset",
                    models.ForeignKey(
                        blank=True,
                        db_comment="接口资产",
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drafts",
                        to="test_manager.apiasset",
                        verbose_name="接口资产",
                    ),
                ),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="api_asset_drafts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "project",
                    models.ForeignKey(
                        db_comment="所属项目",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="asset_drafts",
                        to="test_manager.apiproject",
                        verbose_name="所属项目",
                    ),
                ),
            ],
            options={
                "verbose_name": "API资产草稿",
                "verbose_name_plural": "API资产草稿",
                "ordering": ["-updated_at"],
            },
        ),
        migrations.AddIndex(
            model_name="apiassetdraft",
            index=models.Index(fields=["created_by", "expires_at"], name="api_asset_draft_user_exp_idx"),
        ),
        migrations.AddIndex(
            model_name="apiassetdraft",
            index=models.Index(fields=["project", "asset"], name="api_asset_draft_proj_asset_idx"),
        ),
    ]
