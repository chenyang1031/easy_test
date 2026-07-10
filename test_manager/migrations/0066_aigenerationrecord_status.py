"""为 AIGenerationRecord 添加 status 字段，并回填历史数据"""

from django.db import migrations, models


def backfill_status(apps, schema_editor):
    AIGenerationRecord = apps.get_model("test_manager", "AIGenerationRecord")
    # 已有失败记录
    AIGenerationRecord.objects.filter(success=False).update(status="failed")
    # 已有成功记录（默认值已经是 success，但显式设置确保一致）
    AIGenerationRecord.objects.filter(success=True).update(status="success")


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0065_update_prompt_template_with_example"),
    ]

    operations = [
        migrations.AddField(
            model_name="aigenerationrecord",
            name="status",
            field=models.CharField(
                choices=[
                    ("generating", "生成中"),
                    ("success", "成功"),
                    ("failed", "失败"),
                ],
                default="success",
                max_length=20,
                verbose_name="状态",
                db_comment="生成状态：generating-生成中 success-成功 failed-失败",
            ),
        ),
        migrations.RunPython(backfill_status, migrations.RunPython.noop),
    ]
