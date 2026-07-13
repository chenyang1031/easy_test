from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('test_manager', '0079_add_method_to_testscenenode'),
    ]

    operations = [
        migrations.AddField(
            model_name='testscene',
            name='category',
            field=models.CharField(
                choices=[('traced', '留痕版'), ('untraced', '不留痕版')],
                default='traced',
                max_length=20,
                verbose_name='场景分类',
                db_comment='场景分类：留痕版/不留痕版',
            ),
        ),
    ]
