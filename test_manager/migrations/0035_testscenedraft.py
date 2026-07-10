from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0034_rename_scene_tables_to_new_names"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="TestSceneDraft",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("draft_data", models.JSONField(blank=True, db_comment="草稿数据", default=dict, verbose_name="草稿数据")),
                ("expires_at", models.DateTimeField(db_comment="过期时间", verbose_name="过期时间")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_comment="创建时间", verbose_name="创建时间")),
                ("updated_at", models.DateTimeField(auto_now=True, db_comment="更新时间", verbose_name="更新时间")),
                (
                    "created_by",
                    models.ForeignKey(
                        db_comment="创建人",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="test_scene_drafts",
                        to=settings.AUTH_USER_MODEL,
                        verbose_name="创建人",
                    ),
                ),
                (
                    "scene",
                    models.ForeignKey(
                        db_comment="所属场景",
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="drafts",
                        to="test_manager.testscene",
                        verbose_name="所属场景",
                    ),
                ),
            ],
            options={
                "verbose_name": "场景草稿",
                "verbose_name_plural": "场景草稿",
                "db_table": "test_scene_draft",
                "ordering": ["-updated_at"],
                "unique_together": {("scene", "created_by")},
            },
        ),
        migrations.AddIndex(
            model_name="testscenedraft",
            index=models.Index(fields=["created_by", "expires_at"], name="scene_draft_user_exp_idx"),
        ),
        migrations.AddIndex(
            model_name="testscenedraft",
            index=models.Index(fields=["scene", "created_by"], name="scene_draft_scene_user_idx"),
        ),
    ]
