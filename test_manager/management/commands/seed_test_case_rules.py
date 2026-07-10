"""管理命令：导入默认的 AI 测试用例生成规则。

用法：
    python manage.py seed_test_case_rules                    # 交互模式，仅导入不存在的规则
    python manage.py seed_test_case_rules --user-id 1        # 指定创建人
    python manage.py seed_test_case_rules --force            # 强制覆盖已存在的同名规则
    python manage.py seed_test_case_rules --dry-run          # 预览将要导入的规则，不实际写入
"""
import json
import os

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

from test_manager.models.test_case_rule import TestCaseGenerationRule


FIXTURE_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
    "fixtures",
    "default_test_case_rules.json",
)


class Command(BaseCommand):
    help = "导入默认的 AI 测试用例生成规则"

    def add_arguments(self, parser):
        parser.add_argument(
            "--user-id",
            type=int,
            default=None,
            help="指定创建人用户 ID，不指定则使用第一个超级用户",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="强制覆盖已存在的同名规则",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="仅预览将要导入的规则，不实际写入数据库",
        )

    def handle(self, **options):
        if not os.path.exists(FIXTURE_PATH):
            self.stderr.write(self.style.ERROR(f"种子数据文件不存在: {FIXTURE_PATH}"))
            return

        with open(FIXTURE_PATH, "r", encoding="utf-8") as f:
            rules_data = json.load(f)

        # 确定创建人
        user = self._get_user(options["user_id"])
        if user is None:
            self.stderr.write(self.style.ERROR("未找到可用的用户，请先创建用户或通过 --user-id 指定"))
            return

        force = options["force"]
        dry_run = options["dry_run"]

        created = 0
        updated = 0
        skipped = 0

        for rule_data in rules_data:
            name = rule_data["name"]
            existing = TestCaseGenerationRule.objects.filter(name=name, created_by=user).first()

            if dry_run:
                action = (
                    "覆盖" if (existing and force)
                    else "跳过（已存在）" if existing
                    else "新建"
                )
                self.stdout.write(f"  [{action}] {name} ({rule_data['category']}/{rule_data['priority']})")
                continue

            if existing:
                if force:
                    existing.category = rule_data["category"]
                    existing.priority = rule_data["priority"]
                    existing.description = rule_data.get("description", "")
                    existing.rule_content = rule_data["rule_content"]
                    existing.is_enabled = rule_data.get("is_enabled", True)
                    existing.save()
                    updated += 1
                    self.stdout.write(self.style.WARNING(f"  已覆盖: {name}"))
                else:
                    skipped += 1
                    self.stdout.write(f"  跳过（已存在）: {name}")
            else:
                TestCaseGenerationRule.objects.create(
                    name=name,
                    description=rule_data.get("description", ""),
                    category=rule_data["category"],
                    priority=rule_data["priority"],
                    rule_content=rule_data["rule_content"],
                    is_enabled=rule_data.get("is_enabled", True),
                    created_by=user,
                )
                created += 1
                self.stdout.write(self.style.SUCCESS(f"  已创建: {name}"))

        if dry_run:
            total = created + updated + skipped
            new_count = sum(
                1 for r in rules_data
                if not TestCaseGenerationRule.objects.filter(name=r["name"], created_by=user).exists()
            )
            overwrite_count = total - new_count - skipped if force else 0
            self.stdout.write(f"\n共 {total} 条规则，将新建 {new_count} 条，跳过 {skipped} 条" +
                              (f"，覆盖 {overwrite_count} 条" if force else ""))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"\n导入完成: 新建 {created} 条, 更新 {updated} 条, 跳过 {skipped} 条"
            ))

    def _get_user(self, user_id):
        if user_id:
            try:
                return User.objects.get(id=user_id)
            except User.DoesNotExist:
                self.stderr.write(f"用户 ID={user_id} 不存在")
                return None
        # 不指定时使用第一个超级用户
        user = User.objects.filter(is_superuser=True).order_by("id").first()
        if user:
            return user
        # 没有超级用户就用第一个用户
        return User.objects.order_by("id").first()
