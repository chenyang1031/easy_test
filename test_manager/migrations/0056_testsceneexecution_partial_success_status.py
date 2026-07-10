# -*- coding: utf-8 -*-
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0055_alter_performancetesttask_target_rps"),
    ]

    operations = [
        migrations.AlterField(
            model_name="testsceneexecution",
            name="status",
            field=models.CharField(
                choices=[
                    ("running", "执行中"),
                    ("success", "成功"),
                    ("failed", "失败"),
                    ("partial_success", "部分成功"),
                ],
                db_comment="执行状态",
                default="running",
                max_length=20,
                verbose_name="执行状态",
            ),
        ),
    ]
