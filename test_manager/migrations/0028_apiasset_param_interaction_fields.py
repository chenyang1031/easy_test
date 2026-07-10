from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0027_apiasset_filter_indexes"),
    ]

    operations = [
        migrations.AddField(
            model_name="apiasset",
            name="param_status",
            field=models.CharField(
                choices=[("enabled", "启用"), ("disabled", "禁用")],
                db_comment="参数启用状态",
                default="enabled",
                max_length=20,
                verbose_name="参数启用状态",
            ),
        ),
        migrations.AddField(
            model_name="apiasset",
            name="param_type",
            field=models.CharField(
                db_comment="参数类型",
                default="string",
                max_length=30,
                verbose_name="参数类型",
            ),
        ),
        migrations.AddField(
            model_name="apiasset",
            name="required",
            field=models.BooleanField(
                db_comment="参数必填",
                default=False,
                verbose_name="参数必填",
            ),
        ),
        migrations.AddField(
            model_name="apiasset",
            name="sort",
            field=models.IntegerField(
                db_comment="参数排序",
                default=0,
                verbose_name="参数排序",
            ),
        ),
    ]
