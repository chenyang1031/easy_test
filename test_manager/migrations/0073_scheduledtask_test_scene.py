"""
Migration 0073: Add test_scene FK to ScheduledTask, make test_suite nullable.

- Add test_scene FK → TestScene
- Make test_suite FK nullable (null=True, blank=True)
"""

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0072_add_default_prompt_template"),
    ]

    operations = [
        migrations.AlterField(
            model_name="scheduledtask",
            name="test_suite",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="scheduled_tasks",
                to="test_manager.testsuite",
                verbose_name="测试套件",
                db_comment="测试套件",
            ),
        ),
        migrations.AddField(
            model_name="scheduledtask",
            name="test_scene",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=models.CASCADE,
                related_name="scheduled_tasks",
                to="test_manager.testscene",
                verbose_name="测试场景",
                db_comment="测试场景",
            ),
        ),
    ]
