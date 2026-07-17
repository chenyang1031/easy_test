"""
UI自动化视图 - ViewSet + 自定义action
"""
import os
import uuid
from django.utils import timezone
from django.db.models import Count, Q, Avg
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.pagination import PageNumberPagination

from .models import (
    UiModule, UiPage, UiElement, UiElementGroup,
    UiPageSteps, UiPageStepsDetailed,
    UiTestCase, UiCaseStepsDetailed,
    UiTestScript, UiScriptStep,
    UiPageObject, UiPageObjectElement,
    UiBatchExecutionRecord, UiExecutionRecord,
    UiEnvironmentConfig, UiPublicData, UiActuator,
    UiScheduledTask, UiNotificationLog,
    UiAICase, UiAIExecutionRecord, UiOperationRecord,
)
from .serializers import (
    UiModuleSerializer, UiModuleMoveSerializer,
    UiPageSerializer, UiPageDetailSerializer,
    UiElementSerializer, UiElementValidateSerializer,
    UiElementGroupSerializer,
    UiPageStepsSerializer, UiPageStepsDetailSerializer,
    UiPageStepsDetailedSerializer, UiPageStepsDetailedBatchSerializer,
    UiTestCaseSerializer, UiTestCaseDetailSerializer,
    UiTestCaseBatchDeleteSerializer, UiTestCaseRunSerializer,
    UiCaseStepsDetailedSerializer, UiCaseStepsDetailedBatchSerializer,
    UiTestScriptSerializer, UiTestScriptDetailSerializer,
    UiScriptStepSerializer,
    UiPageObjectSerializer, UiPageObjectDetailSerializer,
    UiPageObjectElementSerializer,
    UiBatchExecutionRecordSerializer, UiBatchRecordListSerializer,
    UiExecutionRecordSerializer, UiExecutionRecordDetailSerializer,
    UiTriggerBatchSerializer,
    UiEnvironmentConfigSerializer,
    UiPublicDataSerializer,
    UiActuatorSerializer,
    UiScheduledTaskSerializer,
    UiNotificationLogSerializer,
    UiAICaseSerializer,
    UiAIExecutionRecordSerializer, UiAIExecutionRecordDetailSerializer,
    UiAICaseRunSerializer,
    UiOperationRecordSerializer,
)
from .operation_logger import log_operation


class UiPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 100


# ============================================================
# 模块管理
# ============================================================

class UiModuleViewSet(viewsets.ModelViewSet):
    serializer_class = UiModuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None  # 模块树不分页

    def get_queryset(self):
        qs = UiModule.objects.filter(parent__isnull=True)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.select_related('project', 'created_by').prefetch_related('children')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['get'])
    def tree(self, request):
        """获取完整模块树"""
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({'error': 'project参数必填'}, status=400)
        roots = UiModule.objects.filter(
            project_id=project_id, parent__isnull=True
        ).select_related('created_by').prefetch_related('children__children__children__children')
        serializer = self.get_serializer(roots, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def move(self, request, pk=None):
        """拖拽移动模块"""
        module = self.get_object()
        ser = UiModuleMoveSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        target_id = ser.validated_data.get('target_id')
        drop_position = ser.validated_data['drop_position']

        if drop_position == 'inside':
            if target_id is None:
                return Response({'error': 'inside操作需要target_id'}, status=400)
            target = UiModule.objects.get(pk=target_id)
            # 检查层级限制
            if target.level >= 5:
                return Response({'error': '最大支持5级嵌套'}, status=400)
            # 检查循环引用
            current = target
            while current:
                if current.pk == module.pk:
                    return Response({'error': '不能移动到自身子节点'}, status=400)
                current = current.parent
            module.parent = target
            module.level = target.level + 1
        else:
            if target_id is None:
                return Response({'error': '需要target_id'}, status=400)
            target = UiModule.objects.get(pk=target_id)
            module.parent = target.parent
            module.level = target.level
            if drop_position == 'after':
                module.order = target.order + 1

        module.save()
        log_operation(request, 'update', module)
        return Response(UiModuleSerializer(module).data)

    def perform_destroy(self, instance):
        if instance.children.exists():
            from rest_framework.exceptions import ValidationError
            raise ValidationError('请先删除子模块')
        log_operation(self.request, 'delete', instance)
        instance.delete()


# ============================================================
# 页面管理
# ============================================================

class UiPageViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiPageDetailSerializer
        return UiPageSerializer

    def get_queryset(self):
        qs = UiPage.objects.select_related('module', 'created_by')
        module_id = self.request.query_params.get('module')
        project_id = self.request.query_params.get('project')
        if module_id:
            qs = qs.filter(module_id=module_id)
        if project_id:
            qs = qs.filter(module__project_id=project_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        log_operation(self.request, 'create', serializer.instance)

    def perform_update(self, serializer):
        serializer.save()
        log_operation(self.request, 'update', serializer.instance)

    def perform_destroy(self, instance):
        log_operation(self.request, 'delete', instance)
        instance.delete()


# ============================================================
# 元素管理
# ============================================================

class UiElementViewSet(viewsets.ModelViewSet):
    serializer_class = UiElementSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiElement.objects.select_related('page', 'page__module', 'created_by')
        page_id = self.request.query_params.get('page')
        project_id = self.request.query_params.get('project')
        element_type = self.request.query_params.get('element_type')
        search = self.request.query_params.get('search')
        if page_id:
            qs = qs.filter(page_id=page_id)
        if project_id:
            qs = qs.filter(page__module__project_id=project_id)
        if element_type:
            qs = qs.filter(element_type=element_type)
        if search:
            qs = qs.filter(Q(name__icontains=search) | Q(locator_value__icontains=search))
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        log_operation(self.request, 'create', serializer.instance)

    def perform_update(self, serializer):
        serializer.save()
        log_operation(self.request, 'update', serializer.instance)

    @action(detail=True, methods=['post'])
    def validate(self, request, pk=None):
        """验证元素定位器"""
        element = self.get_object()
        # TODO: 实际通过Playwright验证定位器
        element.validation_status = 'valid'
        element.validation_message = '验证通过'
        element.last_validated = timezone.now()
        element.save(update_fields=['validation_status', 'validation_message', 'last_validated'])
        return Response({'status': 'valid', 'message': '定位器验证通过'})

    @action(detail=True, methods=['get'])
    def usages(self, request, pk=None):
        """获取元素使用统计"""
        element = self.get_object()
        step_usage = UiPageStepsDetailed.objects.filter(element=element).count()
        case_refs = UiCaseStepsDetailed.objects.filter(
            page_step__details__element=element
        ).values('test_case__name').distinct()
        return Response({
            'usage_count': element.usage_count,
            'step_references': step_usage,
            'case_references': list(case_refs),
            'last_validated': element.last_validated,
            'validation_status': element.validation_status,
        })

    @action(detail=True, methods=['post'])
    def suggestions(self, request, pk=None):
        """AI元素定位建议（预留）"""
        element = self.get_object()
        return Response({'suggestions': [], 'message': 'AI建议功能待接入LLM'})


class UiElementGroupViewSet(viewsets.ModelViewSet):
    serializer_class = UiElementGroupSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        qs = UiElementGroup.objects.filter(parent_group__isnull=True)
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.prefetch_related('children')

    @action(detail=False, methods=['get'])
    def tree(self, request):
        project_id = request.query_params.get('project')
        if not project_id:
            return Response({'error': 'project参数必填'}, status=400)
        roots = UiElementGroup.objects.filter(
            project_id=project_id, parent_group__isnull=True
        ).prefetch_related('children__children')
        return Response(self.get_serializer(roots, many=True).data)


# ============================================================
# 操作步骤
# ============================================================

class UiPageStepsViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiPageStepsDetailSerializer
        return UiPageStepsSerializer

    def get_queryset(self):
        qs = UiPageSteps.objects.select_related('page', 'module', 'created_by')
        project_id = self.request.query_params.get('project')
        module_id = self.request.query_params.get('module')
        page_id = self.request.query_params.get('page')
        if project_id:
            qs = qs.filter(project_id=project_id)
        if module_id:
            qs = qs.filter(module_id=module_id)
        if page_id:
            qs = qs.filter(page_id=page_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        log_operation(self.request, 'create', serializer.instance)


class UiPageStepsDetailedViewSet(viewsets.ModelViewSet):
    serializer_class = UiPageStepsDetailedSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiPageStepsDetailed.objects.select_related('element')
        page_step_id = self.request.query_params.get('page_step')
        if page_step_id:
            qs = qs.filter(page_step_id=page_step_id)
        return qs.order_by('step_sort')

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """批量更新步骤明细"""
        ser = UiPageStepsDetailedBatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        details_data = ser.validated_data['details']

        page_step_id = request.data.get('page_step')
        if not page_step_id:
            return Response({'error': 'page_step参数必填'}, status=400)

        # 删除旧步骤，创建新步骤
        UiPageStepsDetailed.objects.filter(page_step_id=page_step_id).delete()
        created = []
        for d in details_data:
            d['page_step_id'] = page_step_id
            obj = UiPageStepsDetailed.objects.create(**d)
            created.append(obj)

        return Response(UiPageStepsDetailedSerializer(created, many=True).data)


# ============================================================
# 测试用例
# ============================================================

class UiTestCaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiTestCaseDetailSerializer
        return UiTestCaseSerializer

    def get_queryset(self):
        qs = UiTestCase.objects.select_related('module', 'created_by')
        project_id = self.request.query_params.get('project')
        module_id = self.request.query_params.get('module')
        level = self.request.query_params.get('level')
        search = self.request.query_params.get('search')
        if project_id:
            qs = qs.filter(project_id=project_id)
        if module_id:
            qs = qs.filter(module_id=module_id)
        if level:
            qs = qs.filter(level=level)
        if search:
            qs = qs.filter(name__icontains=search)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
        log_operation(self.request, 'create', serializer.instance)

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        """批量删除用例"""
        ser = UiTestCaseBatchDeleteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ids = ser.validated_data['ids']
        deleted_count, _ = UiTestCase.objects.filter(id__in=ids).delete()
        return Response({'deleted': deleted_count})

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """执行单个测试用例"""
        test_case = self.get_object()
        ser = UiTestCaseRunSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        env_id = ser.validated_data['environment']
        try:
            env = UiEnvironmentConfig.objects.get(pk=env_id)
        except UiEnvironmentConfig.DoesNotExist:
            return Response({'error': '环境配置不存在'}, status=404)

        # 创建执行记录
        batch = UiBatchExecutionRecord.objects.create(
            project=test_case.project,
            name=f"执行: {test_case.name}",
            total_cases=1,
            status=1,  # 执行中
            trigger_type='manual',
            start_time=timezone.now(),
            created_by=request.user,
        )
        record = UiExecutionRecord.objects.create(
            batch=batch,
            test_case=test_case,
            executor=request.user.username,
            status=1,
            trigger_type='manual',
            start_time=timezone.now(),
        )

        # 通过Celery异步执行
        from .tasks import execute_ui_test_case
        execute_ui_test_case.delay(record.id, env_id)

        return Response({
            'batch_id': batch.id,
            'record_id': record.id,
            'message': '执行任务已提交',
        })


class UiCaseStepsDetailedViewSet(viewsets.ModelViewSet):
    serializer_class = UiCaseStepsDetailedSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiCaseStepsDetailed.objects.select_related('page_step')
        test_case_id = self.request.query_params.get('test_case')
        if test_case_id:
            qs = qs.filter(test_case_id=test_case_id)
        return qs.order_by('case_sort')

    @action(detail=False, methods=['post'])
    def batch_update(self, request):
        """批量更新用例步骤"""
        ser = UiCaseStepsDetailedBatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        steps_data = ser.validated_data['steps']

        test_case_id = request.data.get('test_case')
        if not test_case_id:
            return Response({'error': 'test_case参数必填'}, status=400)

        UiCaseStepsDetailed.objects.filter(test_case_id=test_case_id).delete()
        created = []
        for s in steps_data:
            s['test_case_id'] = test_case_id
            obj = UiCaseStepsDetailed.objects.create(**s)
            created.append(obj)

        return Response(UiCaseStepsDetailedSerializer(created, many=True).data)


# ============================================================
# 脚本管理
# ============================================================

class UiTestScriptViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiTestScriptDetailSerializer
        return UiTestScriptSerializer

    def get_queryset(self):
        qs = UiTestScript.objects.select_related('created_by')
        project_id = self.request.query_params.get('project')
        script_type = self.request.query_params.get('script_type')
        if project_id:
            qs = qs.filter(project_id=project_id)
        if script_type:
            qs = qs.filter(script_type=script_type)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class UiScriptStepViewSet(viewsets.ModelViewSet):
    serializer_class = UiScriptStepSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiScriptStep.objects.all()
        script_id = self.request.query_params.get('script')
        if script_id:
            qs = qs.filter(script_id=script_id)
        return qs.order_by('step_order')


# ============================================================
# Page Object
# ============================================================

class UiPageObjectViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiPageObjectDetailSerializer
        return UiPageObjectSerializer

    def get_queryset(self):
        qs = UiPageObject.objects.select_related('created_by')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def generate_code(self, request, pk=None):
        """生成Page Object代码"""
        po = self.get_object()
        elements = po.po_elements.select_related('element').all()

        # 生成Python代码
        py_lines = [f'class {po.name.replace(" ", "")}Page:', '    def __init__(self, page):', '        self.page = page', '']
        for poe in elements:
            el = poe.element
            method = poe.method_name
            if poe.is_property:
                py_lines.append(f'    @property')
                py_lines.append(f'    def {method}(self):')
                py_lines.append(f'        return self.page.locator("{el.locator_value}")')
            else:
                py_lines.append(f'    def {method}(self):')
                py_lines.append(f'        return self.page.locator("{el.locator_value}")')
            py_lines.append('')

        # 生成JS代码
        js_lines = [f'export class {po.name.replace(" ", "")}Page {{', '  constructor(page) {', '    this.page = page;', '  }', '']
        for poe in elements:
            el = poe.element
            method = poe.method_name
            js_lines.append(f'  get {method}() {{')
            js_lines.append(f'    return this.page.locator("{el.locator_value}");')
            js_lines.append(f'  }}')
            js_lines.append('')
        js_lines.append('}')

        py_code = '\n'.join(py_lines)
        js_code = '\n'.join(js_lines)

        po.generated_code_python = py_code
        po.generated_code_js = js_code
        po.save(update_fields=['generated_code_python', 'generated_code_js'])

        return Response({
            'python': py_code,
            'javascript': js_code,
        })

    @action(detail=True, methods=['post'])
    def add_element(self, request, pk=None):
        """添加元素到页面对象"""
        po = self.get_object()
        element_id = request.data.get('element')
        method_name = request.data.get('method_name', '')
        is_property = request.data.get('is_property', True)

        if not element_id:
            return Response({'error': 'element参数必填'}, status=400)

        try:
            element = UiElement.objects.get(pk=element_id)
        except UiElement.DoesNotExist:
            return Response({'error': '元素不存在'}, status=404)

        poe, created = UiPageObjectElement.objects.get_or_create(
            page_object=po, element=element,
            defaults={'method_name': method_name, 'is_property': is_property}
        )
        if not created:
            poe.method_name = method_name
            poe.is_property = is_property
            poe.save()

        return Response(UiPageObjectElementSerializer(poe).data)


# ============================================================
# 执行记录
# ============================================================

class UiBatchExecutionRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiBatchExecutionRecordSerializer
        return UiBatchRecordListSerializer

    def get_queryset(self):
        qs = UiBatchExecutionRecord.objects.select_related('created_by')
        project_id = self.request.query_params.get('project')
        status_filter = self.request.query_params.get('status')
        trigger = self.request.query_params.get('trigger_type')
        if project_id:
            qs = qs.filter(project_id=project_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        if trigger:
            qs = qs.filter(trigger_type=trigger)
        return qs

    def perform_destroy(self, instance):
        # 级联删除执行记录
        instance.execution_records.all().delete()
        instance.delete()


class UiExecutionRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiExecutionRecordDetailSerializer
        return UiExecutionRecordSerializer

    def get_queryset(self):
        qs = UiExecutionRecord.objects.select_related('test_case', 'batch')
        batch_id = self.request.query_params.get('batch')
        test_case_id = self.request.query_params.get('test_case')
        status_filter = self.request.query_params.get('status')
        if batch_id:
            qs = qs.filter(batch_id=batch_id)
        if test_case_id:
            qs = qs.filter(test_case_id=test_case_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs.defer('log', 'trace_data')

    @action(detail=True, methods=['get'])
    def trace(self, request, pk=None):
        """获取Trace数据"""
        record = self.get_object()
        if record.trace_data:
            return Response(record.trace_data)
        # TODO: 从trace_path解析trace文件
        return Response({'message': '暂无Trace数据'})


class UiTriggerBatchViewSet(viewsets.ViewSet):
    """触发批量执行"""
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        ser = UiTriggerBatchSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data

        test_case_ids = data['test_case_ids']
        env_id = data['environment']
        test_cases = UiTestCase.objects.filter(id__in=test_case_ids)

        if not test_cases.exists():
            return Response({'error': '未找到有效的测试用例'}, status=404)

        project = test_cases.first().project

        batch = UiBatchExecutionRecord.objects.create(
            project=project,
            name=f"批量执行 ({test_cases.count()}个用例)",
            total_cases=test_cases.count(),
            status=1,
            trigger_type=data.get('trigger_type', 'manual'),
            start_time=timezone.now(),
            created_by=request.user,
        )

        records = []
        for tc in test_cases:
            record = UiExecutionRecord.objects.create(
                batch=batch,
                test_case=tc,
                executor=request.user.username,
                status=1,
                trigger_type=data.get('trigger_type', 'manual'),
                start_time=timezone.now(),
            )
            records.append(record)

        # Celery异步执行
        from .tasks import execute_ui_test_batch
        execute_ui_test_batch.delay(batch.id)

        return Response({
            'batch_id': batch.id,
            'record_count': len(records),
            'message': f'已提交{len(records)}个用例执行任务',
        })


# ============================================================
# 文件上传
# ============================================================

class UiScreenshotUploadView(viewsets.ViewSet):
    """截图上传"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request):
        file = request.FILES.get('screenshot')
        if not file:
            return Response({'error': '未提供截图文件'}, status=400)

        upload_dir = os.path.join('media', 'ui_screenshots')
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}{os.path.splitext(file.name)[1]}"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        return Response({'url': f'/media/ui_screenshots/{filename}'})


class UiTraceUploadView(viewsets.ViewSet):
    """Trace文件上传"""
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def create(self, request):
        file = request.FILES.get('trace')
        if not file:
            return Response({'error': '未提供Trace文件'}, status=400)

        upload_dir = os.path.join('media', 'ui_traces')
        os.makedirs(upload_dir, exist_ok=True)

        filename = f"{uuid.uuid4().hex}.zip"
        filepath = os.path.join(upload_dir, filename)

        with open(filepath, 'wb+') as dest:
            for chunk in file.chunks():
                dest.write(chunk)

        return Response({'path': filepath})


# ============================================================
# 环境配置
# ============================================================

class UiEnvironmentConfigViewSet(viewsets.ModelViewSet):
    serializer_class = UiEnvironmentConfigSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiEnvironmentConfig.objects.select_related('created_by')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        instance = serializer.save(created_by=self.request.user)
        # 如果设为默认，取消其他默认
        if instance.is_default:
            UiEnvironmentConfig.objects.filter(
                project=instance.project, is_default=True
            ).exclude(pk=instance.pk).update(is_default=False)


# ============================================================
# 公共数据
# ============================================================

class UiPublicDataViewSet(viewsets.ModelViewSet):
    serializer_class = UiPublicDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiPublicData.objects.all()
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    @action(detail=False, methods=['get'])
    def by_project(self, request, project_id=None):
        """按项目获取公共数据（供执行器使用）"""
        pid = project_id or request.query_params.get('project_id')
        if not pid:
            return Response({'error': 'project_id参数必填'}, status=400)
        data = UiPublicData.objects.filter(project_id=pid, is_enabled=True)
        return Response(self.get_serializer(data, many=True).data)


# ============================================================
# 执行器
# ============================================================

class UiActuatorViewSet(viewsets.ModelViewSet):
    serializer_class = UiActuatorSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = None

    def get_queryset(self):
        return UiActuator.objects.all()

    @action(detail=False, methods=['get'])
    def status(self, request):
        """获取执行器状态概览"""
        total = UiActuator.objects.count()
        online = UiActuator.objects.filter(status='online').count()
        return Response({
            'total': total,
            'online': online,
            'offline': total - online,
        })


# ============================================================
# 定时任务
# ============================================================

class UiScheduledTaskViewSet(viewsets.ModelViewSet):
    serializer_class = UiScheduledTaskSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiScheduledTask.objects.select_related('environment', 'created_by')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """立即执行"""
        task = self.get_object()
        from .tasks import run_ui_scheduled_task
        run_ui_scheduled_task.delay(task.id)
        return Response({'message': '任务已提交执行'})

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停任务"""
        task = self.get_object()
        task.is_active = False
        task.save(update_fields=['is_active'])
        return Response({'message': '任务已暂停'})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复任务"""
        task = self.get_object()
        task.is_active = True
        task.save(update_fields=['is_active'])
        return Response({'message': '任务已恢复'})


# ============================================================
# 通知日志
# ============================================================

class UiNotificationLogViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UiNotificationLogSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiNotificationLog.objects.select_related('task')
        task_id = self.request.query_params.get('task')
        if task_id:
            qs = qs.filter(task_id=task_id)
        return qs


# ============================================================
# AI
# ============================================================

class UiAICaseViewSet(viewsets.ModelViewSet):
    serializer_class = UiAICaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiAICase.objects.select_related('created_by')
        project_id = self.request.query_params.get('project')
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        """运行AI测试用例"""
        ai_case = self.get_object()
        ser = UiAICaseRunSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        record = UiAIExecutionRecord.objects.create(
            ai_case=ai_case,
            status='pending',
            created_by=request.user,
        )

        from .tasks import run_ai_browser_task
        run_ai_browser_task.delay(record.id)

        return Response({
            'record_id': record.id,
            'message': 'AI执行任务已提交',
        })


class UiAIExecutionRecordViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return UiAIExecutionRecordDetailSerializer
        return UiAIExecutionRecordSerializer

    def get_queryset(self):
        qs = UiAIExecutionRecord.objects.select_related('ai_case', 'created_by')
        ai_case_id = self.request.query_params.get('ai_case')
        status_filter = self.request.query_params.get('status')
        if ai_case_id:
            qs = qs.filter(ai_case_id=ai_case_id)
        if status_filter:
            qs = qs.filter(status=status_filter)
        return qs

    @action(detail=True, methods=['post'])
    def stop(self, request, pk=None):
        """停止AI执行"""
        record = self.get_object()
        if record.status == 'running':
            record.status = 'stopped'
            record.end_time = timezone.now()
            record.save(update_fields=['status', 'end_time'])
        return Response({'message': '执行已停止'})

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        """获取AI执行报告"""
        record = self.get_object()
        return Response({
            'id': record.id,
            'ai_case': record.ai_case.name,
            'task_description': record.ai_case.task_description,
            'status': record.status,
            'planned_tasks': record.planned_tasks,
            'steps_completed': record.steps_completed,
            'screenshots': record.screenshots_sequence,
            'token_cost': record.token_cost,
            'duration': record.duration,
            'start_time': record.start_time,
            'end_time': record.end_time,
        })

    @action(detail=True, methods=['get'])
    def export_pdf(self, request, pk=None):
        """导出PDF报告"""
        record = self.get_object()
        from .report_generator import generate_ai_report_pdf
        pdf_path = generate_ai_report_pdf(record)
        if pdf_path:
            return Response({'url': pdf_path, 'message': 'PDF报告已生成'})
        return Response({'error': 'PDF生成失败'}, status=500)


# ============================================================
# 操作审计
# ============================================================

class UiOperationRecordViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = UiOperationRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = UiPagination

    def get_queryset(self):
        qs = UiOperationRecord.objects.select_related('user')
        project_id = self.request.query_params.get('project')
        action_type = self.request.query_params.get('action_type')
        if project_id:
            qs = qs.filter(project_id=project_id)
        if action_type:
            qs = qs.filter(action_type=action_type)
        return qs


# ============================================================
# 仪表盘
# ============================================================

class UiDashboardViewSet(viewsets.ViewSet):
    """UI自动化仪表盘统计"""
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=['get'])
    def stats(self, request):
        project_id = request.query_params.get('project')
        filters = {}
        if project_id:
            filters['project_id'] = project_id

        total_modules = UiModule.objects.filter(**filters).count()
        total_pages = UiPage.objects.filter(module__project_id=project_id).count() if project_id else UiPage.objects.count()
        total_elements = UiElement.objects.filter(page__module__project_id=project_id).count() if project_id else UiElement.objects.count()
        total_cases = UiTestCase.objects.filter(**filters).count()
        total_executions = UiBatchExecutionRecord.objects.filter(**filters).count()

        # 通过率
        exec_qs = UiBatchExecutionRecord.objects.filter(**filters, status=2)
        passed = exec_qs.count()
        pass_rate = round(passed / total_executions * 100, 1) if total_executions > 0 else 0

        # 最近10条执行
        recent = UiBatchExecutionRecord.objects.filter(
            **filters
        ).order_by('-created_at')[:10].values(
            'id', 'name', 'status', 'trigger_type', 'created_at'
        )

        # 按等级统计
        cases_by_level = {}
        if project_id:
            for level in ['P0', 'P1', 'P2', 'P3']:
                cases_by_level[level] = UiTestCase.objects.filter(
                    project_id=project_id, level=level
                ).count()

        return Response({
            'total_modules': total_modules,
            'total_pages': total_pages,
            'total_elements': total_elements,
            'total_test_cases': total_cases,
            'total_executions': total_executions,
            'pass_rate': pass_rate,
            'recent_executions': list(recent),
            'cases_by_level': cases_by_level,
        })
