# Generated manually for target RPS pacing

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0053_performance_task_stop_and_status"),
    ]

    operations = [
        migrations.AddField(
            model_name="performancetesttask",
            name="target_rps",
            field=models.FloatField(
                blank=True,
                null=True,
                verbose_name="目标 RPS",
                db_comment="目标全局请求/秒；有值时按当前并发节流，空表示不限制",
            ),
        ),
    ]
