"""
从 AIGenerationRecord.response_raw 中提取 description，
回填到 AICaseDraft.case_data.description（仅对 description 为空的历史数据生效）。

用法: python manage.py backfill_draft_description
"""
import json
import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "回填 AI 草稿箱中缺失的用例描述"

    def handle(self, *args, **options):
        from test_manager._models_flat import AICaseDraft, AIGenerationRecord

        # 找到 description 为空/missing 的草稿
        drafts = AICaseDraft.objects.filter(
            import_status__in=["pending", "partial_imported", "imported", "failed"],
        )
        target_drafts = []
        for d in drafts:
            cd = d.case_data or {}
            if not cd.get("description"):
                target_drafts.append(d)

        if not target_drafts:
            self.stdout.write(self.style.SUCCESS("没有需要回填的草稿"))
            return

        self.stdout.write(f"找到 {len(target_drafts)} 条需要回填描述的草稿")

        # 按草稿组分组，方便匹配
        from collections import defaultdict
        drafts_by_group = defaultdict(list)
        for d in target_drafts:
            drafts_by_group[d.draft_group_id].append(d)

        group_ids = list(drafts_by_group.keys())

        # 获取所有成功的生成记录（按 created_by + 时间粗略匹配）
        records = AIGenerationRecord.objects.filter(
            success=True,
        ).exclude(
            response_raw__in=["", "null", "[]"]
        ).order_by("-created_at")

        self.stdout.write(f"共有 {records.count()} 条成功生成记录可用来匹配")

        updated_count = 0
        matched_group_count = 0

        for record in records:
            # 解析 response_raw
            try:
                items = json.loads(record.response_raw)
                if not isinstance(items, list):
                    continue
            except (json.JSONDecodeError, TypeError):
                continue

            # 为每个 response item 构建 name→item 的映射
            item_map = {}
            for item in items:
                name = (item.get("name") or "").strip()
                url = (item.get("request_url") or "").strip()
                if name:
                    item_map[name] = item
                elif url:
                    item_map[url] = item

            if not item_map:
                continue

            # 尝试匹配这个 record 对应的草稿组
            # 匹配策略：同 case_type + 相近时间 + 同 user
            for gid in list(drafts_by_group.keys()):
                group_drafts = drafts_by_group[gid]
                first_draft = group_drafts[0]
                group = first_draft.draft_group

                # 用 created_by + case_type 做初步匹配
                if group.created_by_id != record.created_by_id:
                    continue
                if group.case_type != record.case_type:
                    continue

                # 时间差在 5 分钟内认为是同一批生成
                time_diff = abs(
                    (group.created_at - record.created_at).total_seconds()
                )
                if time_diff > 300:
                    continue

                # 匹配成功：用 item_map 回填 description
                for draft in group_drafts:
                    cd = draft.case_data or {}
                    name = cd.get("name", "")
                    url = cd.get("request_url", "")
                    matched_item = item_map.get(name) or item_map.get(url)
                    if matched_item and matched_item.get("description"):
                        cd["description"] = matched_item["description"]
                        draft.case_data = cd
                        draft.save(update_fields=["case_data"])
                        updated_count += 1

                matched_group_count += 1
                # 避免重复匹配
                del drafts_by_group[gid]

        self.stdout.write(
            self.style.SUCCESS(
                f"完成：匹配了 {matched_group_count} 个草稿组，"
                f"更新了 {updated_count} 条草稿的 description"
            )
        )
