from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("test_manager", "0031_apipreset_apiassetdraft"),
    ]

    operations = [
        migrations.AddField(
            model_name="apiasset",
            name="interface_desc",
            field=models.TextField(blank=True, db_comment="接口描述", default="", verbose_name="接口描述"),
        ),
        migrations.AddField(
            model_name="apiasset",
            name="error_code",
            field=models.JSONField(blank=True, db_comment="错误码", default=list, verbose_name="错误码"),
        ),
    ]
