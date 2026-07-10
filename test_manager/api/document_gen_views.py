"""
DocumentGenRecord ViewSet — 文档上传 → 格式转换 → AI 提取 API → 导入 API 资产
"""
import os
import logging

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response

from test_manager.models import (
    DocumentGenRecord,
    ApiProject,
    ApiAsset,
    ApiGroup,
    PromptTemplate,
    AIModelProvider,
)
from test_manager.utils.document_converter import convert_to_md, save_converted_md
from test_manager.tasks import extract_apis_from_document_async as _extract_apis_task
from .api_asset_views import _normalize_kv_payload
from .serializers import (
    DocumentGenRecordSerializer,
    DocumentGenRecordUploadSerializer,
)

logger = logging.getLogger(__name__)


from .pagination import StandardResultsSetPagination


class DocumentGenRecordViewSet(viewsets.ModelViewSet):
    """文档AI生成记录管理。

    端点: /api/ai/document-gen-records/
    """
    serializer_class = DocumentGenRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = DocumentGenRecord.objects.filter(created_by=self.request.user)
        project_id = self.request.query_params.get('project_id')
        if project_id:
            qs = qs.filter(project_id=project_id)
        status_filter = self.request.query_params.get('status')
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    def perform_destroy(self, instance):
        """删除记录及关联文件"""
        # 删除原始文件
        if instance.original_file:
            try:
                if os.path.isfile(instance.original_file.path):
                    os.remove(instance.original_file.path)
            except (OSError, PermissionError) as e:
                logger.warning("删除原始文件失败: %s", e)
        # 删除转换后的 md 文件
        if instance.converted_md_path:
            abs_path = os.path.join(settings.MEDIA_ROOT, instance.converted_md_path)
            try:
                if os.path.isfile(abs_path):
                    os.remove(abs_path)
            except (OSError, PermissionError) as e:
                logger.warning("删除转换文件失败: %s", e)
        instance.delete()

    @action(detail=False, methods=['post'], url_path='upload')
    def upload(self, request):
        """上传文档 → 转换 → AI 提取 API（同步流程）"""
        ser = DocumentGenRecordUploadSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        data = ser.validated_data
        uploaded_file = data['file']
        ext = uploaded_file.name.rsplit('.', 1)[-1].lower()
        project = get_object_or_404(ApiProject, id=data['project_id'])

        # 1. 创建记录（status=uploading）
        record = DocumentGenRecord.objects.create(
            task_name=data['task_name'],
            project=project,
            original_file=uploaded_file,
            original_filename=uploaded_file.name,
            file_type=ext,
            status='uploading',
            created_by=request.user,
        )

        try:
            # 2. 转换（status=converting）
            record.status = 'converting'
            record.save(update_fields=['status'])
            file_path = record.original_file.path
            md_content = convert_to_md(file_path, ext)
            converted_path = save_converted_md(md_content, record.id)
            record.converted_md_path = converted_path
            record.md_content = md_content

            # 3. 解析模型和模板
            provider = None
            provider_id = data.get('model_provider_id')
            if provider_id:
                provider = get_object_or_404(AIModelProvider, id=provider_id)
                record.model_provider = provider

            prompt_template_obj = None
            template_id = data.get('prompt_template_id')
            if template_id:
                prompt_template_obj = get_object_or_404(PromptTemplate, id=template_id)
                record.prompt_template = prompt_template_obj
            else:
                # 未指定模板时，使用 api_gen 分类的默认模板
                default_template = PromptTemplate.objects.filter(
                    category=PromptTemplate.CATEGORY_API_GEN,
                    is_default=True,
                    is_enabled=True,
                ).first()
                if default_template:
                    prompt_template_obj = default_template
                    record.prompt_template = default_template

            if not provider:
                provider = AIModelProvider.objects.filter(is_enabled=True).first()

            # 保存模型名和模板名（快照）
            if provider:
                record.model_name = provider.model_name
            if prompt_template_obj:
                record.template_name = prompt_template_obj.name

            # 4. 异步 AI 提取（status=generating）
            record.status = 'generating'
            record.save(update_fields=[
                'status', 'model_provider', 'prompt_template',
                'converted_md_path', 'md_content',
                'model_name', 'template_name',
            ])

            # 放入 Celery 队列
            _extract_apis_task.delay(record.id)
            logger.info("文档AI提取任务已入队列: record_id=%s", record.id)
        except Exception as e:
            record.status = 'failed'
            record.error_message = str(e)[:2000]
            record.save(update_fields=['status', 'error_message'])
            logger.exception("文档处理失败: record_id=%s", record.id)

        return Response(
            DocumentGenRecordSerializer(record, context={'request': request}).data,
            status=status.HTTP_200_OK,
        )

    @action(detail=True, methods=['post'], url_path='regenerate')
    def regenerate(self, request, pk=None):
        """重新生成：跳过转换，直接重新调用 AI（使用已有的 md 内容）"""
        record = self.get_object()
        if record.status == 'generating':
            return Response(
                {"detail": "该记录正在生成中，请等待完成"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        md_content = record.md_content
        if not md_content and record.converted_md_path:
            abs_path = os.path.join(settings.MEDIA_ROOT, record.converted_md_path)
            if os.path.isfile(abs_path):
                with open(abs_path, 'r', encoding='utf-8') as f:
                    md_content = f.read()
                record.md_content = md_content

        if not md_content:
            return Response(
                {"detail": "没有可用的文档内容，请重新上传"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        provider = record.model_provider
        if not provider:
            provider = AIModelProvider.objects.filter(is_enabled=True).first()
        if not provider:
            return Response(
                {"detail": "没有可用的 AI 模型供应商，请先配置"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 如果记录没有指定模板，尝试使用 api_gen 默认模板
        if not record.prompt_template:
            default_template = PromptTemplate.objects.filter(
                category=PromptTemplate.CATEGORY_API_GEN,
                is_default=True,
                is_enabled=True,
            ).first()
            if default_template:
                record.prompt_template = default_template

        # 保存最新的模型名和模板名（快照）
        if record.model_provider:
            record.model_name = record.model_provider.model_name
        if record.prompt_template:
            record.template_name = record.prompt_template.name

        # 重置导入状态（提取结果可能变化）
        record.import_status = 'pending'
        record.imported_asset_ids = []
        record.status = 'generating'
        record.save(update_fields=[
            'status', 'import_status', 'imported_asset_ids',
            'model_name', 'template_name', 'md_content',
        ])

        # 放入 Celery 队列
        _extract_apis_task.delay(record.id)
        logger.info("文档AI重新生成任务已入队列: record_id=%s", record.id)

        return Response(
            DocumentGenRecordSerializer(record, context={'request': request}).data,
        )

    @action(detail=True, methods=['get'], url_path='apis')
    def apis(self, request, pk=None):
        """获取提取的 API 列表详情"""
        record = self.get_object()
        return Response({
            "api_count": record.api_count,
            "apis": record.extracted_apis,
            "import_status": record.import_status,
            "imported_asset_ids": record.imported_asset_ids,
        })

    @action(detail=True, methods=['post'], url_path='preview-import')
    def preview_import(self, request, pk=None):
        """导入预览：检测冲突"""
        record = self.get_object()
        api_indices = request.data.get('api_indices', [])
        group_id = request.data.get('group_id')
        if not api_indices:
            return Response({"detail": "请选择要导入的 API"}, status=status.HTTP_400_BAD_REQUEST)

        apis = record.extracted_apis
        selected = []
        for idx in api_indices:
            if 0 <= idx < len(apis):
                selected.append({**apis[idx], '_index': idx})

        base_qs = ApiAsset.objects.filter(
            project=record.project,
            is_deleted=False,
        )
        if group_id:
            base_qs = base_qs.filter(group_id=group_id)

        # 检测冲突（按 url + method 匹配）
        conflicts = []
        no_conflict = []
        for item in selected:
            method = item.get('method', '').upper()
            url = item.get('url', '')
            qs = base_qs.filter(method=method, url=url)
            existing = qs.first()
            if existing:
                conflicts.append({
                    'index': item['_index'],
                    'name': item.get('name', ''),
                    'method': method,
                    'url': url,
                    'existing_asset_id': existing.id,
                    'existing_asset_name': existing.name,
                })
            else:
                no_conflict.append({
                    'index': item['_index'],
                    'name': item.get('name', ''),
                    'method': method,
                    'url': url,
                })

        return Response({
            "total": len(selected),
            "conflict_count": len(conflicts),
            "no_conflict_count": len(no_conflict),
            "conflicts": conflicts,
            "no_conflict": no_conflict,
        })

    @action(detail=True, methods=['post'], url_path='confirm-import')
    def confirm_import(self, request, pk=None):
        """确认导入：创建 ApiAsset 记录"""
        record = self.get_object()
        api_indices = request.data.get('api_indices', [])
        conflict_strategy = request.data.get('conflict_strategy', 'skip')  # skip / overwrite / keep_both
        group_id = request.data.get('group_id')

        if not api_indices:
            return Response({"detail": "请选择要导入的 API"}, status=status.HTTP_400_BAD_REQUEST)

        apis = record.extracted_apis
        if not isinstance(apis, list):
            return Response(
                {"detail": f"提取的 API 数据格式异常，期望列表，实际为 {type(apis).__name__}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_count = 0
        updated_count = 0
        skipped_count = 0
        imported_ids = list(record.imported_asset_ids or [])
        errors = []

        # 如果指定了分组，预校验
        target_group = None
        if group_id:
            try:
                target_group = ApiGroup.objects.get(id=group_id, project=record.project)
            except ApiGroup.DoesNotExist:
                return Response(
                    {"detail": f"指定的分组 id={group_id} 不存在或不属于当前项目"},
                    status=status.HTTP_400_BAD_REQUEST,
                )

        try:
            with transaction.atomic():
                for idx in api_indices:
                    if not (0 <= idx < len(apis)):
                        errors.append({"index": idx, "error": "索引越界"})
                        continue

                    item = apis[idx]
                    if not isinstance(item, dict):
                        errors.append({"index": idx, "error": f"API 数据格式异常，期望 dict，实际为 {type(item).__name__}"})
                        continue

                    method = item.get('method', 'GET').upper()
                    url = item.get('url', '')

                    if not url:
                        errors.append({"index": idx, "error": "URL 为空"})
                        continue

                    # 检查冲突
                    conflict_qs = ApiAsset.objects.filter(
                        project=record.project,
                        method=method,
                        url=url,
                        is_deleted=False,
                    )
                    if group_id:
                        conflict_qs = conflict_qs.filter(group_id=group_id)
                    existing = conflict_qs.first()

                    if existing:
                        if conflict_strategy == 'skip':
                            skipped_count += 1
                            imported_ids.append(existing.id)
                            apis[idx]['_imported'] = True
                            apis[idx]['_imported_asset_id'] = existing.id
                            continue
                        elif conflict_strategy == 'overwrite':
                            updated = self._update_asset_from_item(existing, item)
                            if updated:
                                existing.save(update_fields=updated)
                            updated_count += 1
                            imported_ids.append(existing.id)
                            apis[idx]['_imported'] = True
                            apis[idx]['_imported_asset_id'] = existing.id
                            continue
                        # keep_both: 不当作冲突，继续创建

                    # 获取分组
                    if target_group:
                        group = target_group
                    else:
                        group = self._resolve_group(record.project, item)

                    asset = ApiAsset(
                        project=record.project,
                        group=group,
                        name=item.get('name', url)[:150],
                        method=method,
                        url=url,
                        interface_desc=item.get('interface_desc', ''),
                        request_headers=_normalize_kv_payload(item.get('request_headers')),
                        request_params=item.get('request_params') or [],
                        request_body_format=item.get('request_body_format') or 'json',
                        request_body=item.get('request_body') or {},
                        response_schema=item.get('response_schema') or {},
                        error_code=item.get('error_code') or [],
                        auth_config=item.get('auth_config') or {},
                        source=ApiAsset.SOURCE_AI_DOCUMENT,
                        created_by=request.user,
                    )
                    asset.save()
                    created_count += 1
                    imported_ids.append(asset.id)
                    apis[idx]['_imported'] = True
                    apis[idx]['_imported_asset_id'] = asset.id

                # 更新记录
                record.extracted_apis = apis
                record.imported_asset_ids = imported_ids
                total_apis = len(apis)
                imported_count = sum(1 for a in apis if a.get('_imported'))
                if imported_count >= total_apis:
                    record.import_status = 'imported'
                elif imported_count > 0:
                    record.import_status = 'partial_imported'
                record.save(update_fields=['extracted_apis', 'imported_asset_ids', 'import_status'])

        except Exception as e:
            logger.exception("导入失败: record_id=%s", record.id)
            return Response(
                {"detail": f"导入过程发生异常: {type(e).__name__}: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return Response({
            "created_count": created_count,
            "updated_count": updated_count,
            "skipped_count": skipped_count,
            "errors": errors,
            "import_status": record.import_status,
            "imported_asset_ids": imported_ids,
        })

    @staticmethod
    def _update_asset_from_item(asset, item):
        """用提取的 API 数据更新已有资产，返回变动的字段列表（供 update_fields 使用）"""
        updated_fields = []
        new_name = item.get('name')
        if new_name:
            asset.name = new_name[:150]
            updated_fields.append('name')
        if item.get('interface_desc'):
            asset.interface_desc = item['interface_desc']
            updated_fields.append('interface_desc')
        if item.get('request_headers'):
            asset.request_headers = _normalize_kv_payload(item['request_headers'])
            updated_fields.append('request_headers')
        if item.get('request_params'):
            asset.request_params = item['request_params']
            updated_fields.append('request_params')
        if item.get('request_body_format'):
            asset.request_body_format = item['request_body_format']
            updated_fields.append('request_body_format')
        if item.get('request_body'):
            asset.request_body = item['request_body']
            updated_fields.append('request_body')
        if item.get('response_schema'):
            asset.response_schema = item['response_schema']
            updated_fields.append('response_schema')
        if item.get('error_code'):
            asset.error_code = item['error_code']
            updated_fields.append('error_code')
        if item.get('auth_config'):
            asset.auth_config = item['auth_config']
            updated_fields.append('auth_config')
        return updated_fields

    @staticmethod
    def _resolve_group(project, item):
        """根据 API 名称解析或创建默认分组"""
        # 如果 item 中指定了 group_name，尝试匹配
        group_name = item.get('group_name', '')
        if group_name:
            group, _ = ApiGroup.objects.get_or_create(
                project=project,
                name=group_name,
                defaults={'parent': None},
            )
            return group
        # 使用默认分组
        default_name = "AI文档导入"
        group, _ = ApiGroup.objects.get_or_create(
            project=project,
            name=default_name,
            defaults={'parent': None},
        )
        return group
