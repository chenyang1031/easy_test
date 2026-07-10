# 模块 B：TestReport 关联场景执行（删除执行不删报告，SET_NULL）并扩展 report_type。

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0050_alter_apiasset_options_alter_testscene_options"),
    ]

    operations = [
        migrations.AlterField(
            model_name="testreport",
            name="report_type",
            field=models.CharField(
                choices=[
                    ("test_run", "Test Run"),
                    ("test_suite_run", "Test Suite Run"),
                    ("scene_execution", "Scene Execution"),
                    ("custom", "Custom"),
                ],
                db_comment="报告类型",
                default="test_run",
                max_length=20,
                verbose_name="报告类型",
            ),
        ),
        migrations.AddField(
            model_name="testreport",
            name="scene_execution",
            field=models.ForeignKey(
                blank=True,
                db_comment="场景执行记录，删除执行时报告保留",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="reports",
                to="test_manager.testsceneexecution",
                verbose_name="场景执行记录",
            ),
        ),
    ]
