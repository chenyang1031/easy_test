from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("test_manager", "0038_testscenenode_param_type_body_type"),
    ]

    operations = [
        migrations.AddField(
            model_name="environment",
            name="category",
            field=models.CharField(
                choices=[("default", "默认环境"), ("third_party", "第三方环境")],
                db_comment="环境分类",
                default="default",
                max_length=20,
                verbose_name="环境分类",
            ),
        ),
        migrations.AddField(
            model_name="environment",
            name="is_global_visible",
            field=models.BooleanField(
                db_comment="全局可见",
                default=False,
                verbose_name="全局可见",
            ),
        ),
        migrations.AddField(
            model_name="testscenenode",
            name="environment",
            field=models.ForeignKey(
                blank=True,
                db_comment="接口专属环境",
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="scene_nodes",
                to="test_manager.environment",
                verbose_name="接口专属环境",
            ),
        ),
        migrations.AddField(
            model_name="testscenenode",
            name="custom_base_url",
            field=models.CharField(
                blank=True,
                db_comment="接口自定义域名",
                default="",
                max_length=512,
                verbose_name="接口自定义域名",
            ),
        ),
    ]
