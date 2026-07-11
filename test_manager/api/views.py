from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from django.conf import settings
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from urllib.parse import urljoin, urlencode
import json
import os
import requests
import subprocess
import sys
from test_manager.env_variables_compat import variables_for_runtime
from test_manager.models import (
    Project, Environment, TestCase, TestSuite,
    TestSuiteCase, TestRun, TestResult, AICaseDraftGroup, AICaseDraft, ParameterConfig,
    TestCaseGenerationRule, AICaseDraftRuleUsage, PromptTemplate,
    AIModelProvider, TestCaseGroup, TestSuiteGroup,
    AIGenerationRecord,
)
from .serializers import (
    ProjectSerializer, EnvironmentSerializer, TestCaseSerializer,
    TestSuiteSerializer, TestSuiteCaseSerializer, TestRunSerializer,
    TestRunListSerializer,
    TestResultSerializer, AIGenerateMultiTestCasesRequestSerializer,
    AIImportTestCasesRequestSerializer, AICaseDraftGroupItemSerializer, AICaseDraftItemSerializer,
    TestCaseGenerationRuleSerializer, AICaseDraftRuleUsageSerializer,
    PromptTemplateSerializer,
    AIModelProviderSerializer,
    TestCaseGroupSerializer, TestSuiteGroupSerializer,
    AIGenerationRecordSerializer,
)
from test_manager.httprunner_executor import execute_test_case, execute_test_suite
from test_manager.forms import TestCaseForm


from .pagination import StandardResultsSetPagination  # noqa: F401 — used across module


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        return Project.objects.select_related("created_by").all().order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)


class EnvironmentViewSet(viewsets.ModelViewSet):
    queryset = Environment.objects.select_related("project").all()
    serializer_class = EnvironmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @action(detail=True, methods=['post'], url_path='test-pre-request-script')
    def test_pre_request_script(self, request, pk=None):
        """测试环境前置脚本，模拟执行并返回变量变更日志。使用子进程隔离执行。"""
        env = self.get_object()
        script = request.data.get('script', env.pre_request_script or '')
        env_vars = request.data.get('env_vars')
        if env_vars is None:
            env_vars = variables_for_runtime(env.variables or {})
        timeout_ms = min(1000, max(100, int(request.data.get('script_timeout', env.script_timeout or 1000))))

        payload = {"script": script, "env_vars": env_vars, "timeout_ms": timeout_ms}
        proc_env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "test_manager.pre_request_script_runner"],
                input=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                capture_output=True,
                timeout=15,
                cwd=str(settings.BASE_DIR),
                env=proc_env,
            )
        except subprocess.TimeoutExpired:
            return Response({"success": False, "logs": [], "console": [], "error": "脚本执行超时（15秒）"})
        except Exception as e:
            return Response({"success": False, "logs": [], "console": [], "error": f"子进程启动失败: {e}"})

        if proc.returncode != 0:
            err_msg = proc.stderr.decode("utf-8", errors="replace").strip() or "脚本执行进程异常退出"
            return Response({"success": False, "logs": [], "console": [], "error": err_msg})

        try:
            out = proc.stdout.decode("utf-8", errors="replace")
            result = json.loads(out)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            return Response({"success": False, "logs": [], "console": [], "error": f"解析结果失败: {e}"})
        return Response(result)

    def get_queryset(self):
        from test_manager.models import ApiProject
        project_id = self.request.query_params.get('project', None)
        api_project_id = self.request.query_params.get('api_project', None)
        if api_project_id:
            try:
                api_proj = ApiProject.objects.get(id=api_project_id)
                if api_proj.platform_project_id:
                    project_id = api_proj.platform_project_id
            except ApiProject.DoesNotExist:
                pass
        if project_id and project_id.isdigit():
            from django.db.models import Q
            return Environment.objects.filter(
                Q(project_id=project_id) | Q(is_global_visible=True)
            ).order_by('-created_at')
        return Environment.objects.all().order_by('-created_at')


class TestCaseViewSet(viewsets.ModelViewSet):
    queryset = TestCase.objects.all()
    serializer_class = TestCaseSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        qs = TestCase.objects.select_related("project", "group", "created_by")
        if project_id:
            return qs.filter(project_id=project_id).order_by('-created_at')
        return qs.all().order_by('-created_at')

    @action(detail=False, methods=['post'])
    def batch_delete(self, request):
        case_ids = request.data.get("ids", [])
        if not case_ids or not isinstance(case_ids, list):
            return Response({"detail": "请提供要删除的用例ID列表"}, status=status.HTTP_400_BAD_REQUEST)
        qs = TestCase.objects.filter(id__in=case_ids)
        deleted_count, _ = qs.delete()
        return Response({"deleted_count": deleted_count})

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        test_case = self.get_object()
        environment_id = request.data.get('environment_id')

        if not environment_id:
            return Response({"error": "Environment ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        environment = get_object_or_404(Environment, id=environment_id)

        # Create a test run
        test_run = TestRun.objects.create(
            name=f"Single run: {test_case.name}",
            project=test_case.project,
            environment=environment,
            status='running',
            start_time=timezone.now(),
            created_by=request.user
        )

        # Execute the test case
        result = execute_test_case(test_case, environment)

        # Update test run
        test_run.status = 'completed' if result['status'] == 'passed' else 'failed'
        test_run.end_time = timezone.now()
        test_run.save()

        # Create test result
        test_result = TestResult.objects.create(
            test_run=test_run,
            test_case=test_case,
            environment=environment,
            status=result['status'],
            request_headers=result.get('request_headers', {}),  # 保存请求头
            request_body=result.get('request_body'),  # 保存请求体
            response_time=result.get('response_time'),
            response_status_code=result.get('response_status_code'),
            response_headers=result.get('response_headers', {}),
            response_body=result.get('response_body'),
            error_message=result.get('error_message', ''),
            extracted_params=result.get('extracted_params', {}),
            validators=result.get('validators', [])
        )

        serializer = TestResultSerializer(test_result)
        return Response(serializer.data)


class TestSuiteViewSet(viewsets.ModelViewSet):
    queryset = TestSuite.objects.all()
    serializer_class = TestSuiteSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        qs = TestSuite.objects.select_related("project", "group", "created_by")
        if self.action != 'retrieve':
            qs = qs.annotate(test_case_count=Count("test_cases", distinct=True))
        if project_id:
            return qs.filter(project_id=project_id).order_by('-created_at')
        return qs.all().order_by('-created_at')

    @action(detail=True, methods=['get'])
    def cases(self, request, pk=None):
        """返回该套件下的测试用例列表（分页）"""
        test_suite = self.get_object()
        qs = TestSuiteCase.objects.select_related(
            "test_case", "environment"
        ).filter(test_suite=test_suite).order_by('order', 'id')
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = TestSuiteCaseSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = TestSuiteCaseSerializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_test_case(self, request, pk=None):
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')
        environment_id = request.data.get('environment_id')
        order = request.data.get('order', 0)

        if not test_case_id:
            return Response({"error": "Test case ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        test_case = get_object_or_404(TestCase, id=test_case_id)

        # Check if test case is already in the suite
        if TestSuiteCase.objects.filter(test_suite=test_suite, test_case=test_case).exists():
            return Response({"error": "Test case already in suite"}, status=status.HTTP_400_BAD_REQUEST)

        # 创建测试套件用例关联，并设置环境（如果提供）
        test_suite_case_data = {
            'test_suite': test_suite,
            'test_case': test_case,
            'order': order
        }

        if environment_id:
            environment = get_object_or_404(Environment, id=environment_id)
            test_suite_case_data['environment'] = environment

        test_suite_case = TestSuiteCase.objects.create(**test_suite_case_data)

        serializer = TestSuiteCaseSerializer(test_suite_case)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def update_test_case_environment(self, request, pk=None):
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')
        environment_id = request.data.get('environment_id')

        if not test_case_id:
            return Response({"error": "Test case ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        test_suite_case = get_object_or_404(TestSuiteCase, test_suite=test_suite, test_case_id=test_case_id)

        if environment_id:
            environment = get_object_or_404(Environment, id=environment_id)
            test_suite_case.environment = environment
        else:
            test_suite_case.environment = None

        test_suite_case.save()

        serializer = TestSuiteCaseSerializer(test_suite_case)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def remove_test_case(self, request, pk=None):
        test_suite = self.get_object()
        test_case_id = request.data.get('test_case_id')

        if not test_case_id:
            return Response({"error": "Test case ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        test_suite_case = get_object_or_404(TestSuiteCase, test_suite=test_suite, test_case_id=test_case_id)
        test_suite_case.delete()

        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['post'])
    def run(self, request, pk=None):
        test_suite = self.get_object()
        default_environment_id = request.data.get('environment_id')

        if not default_environment_id:
            return Response({"error": "Default environment ID is required"}, status=status.HTTP_400_BAD_REQUEST)

        default_environment = get_object_or_404(Environment, id=default_environment_id)

        # 获取每个测试用例的环境设置
        case_environments = {}
        for key, value in request.data.items():
            if key.startswith('case_environment_') and value:
                case_id = key.replace('case_environment_', '')
                case_environments[int(case_id)] = int(value)

        # Create a test run
        test_run = TestRun.objects.create(
            name=request.data.get('name', f"Suite run: {test_suite.name}"),
            project=test_suite.project,
            test_suite=test_suite,
            environment=default_environment,  # 默认环境
            status='running',
            start_time=timezone.now(),
            created_by=request.user
        )

        # Execute the test suite with custom environments
        results = execute_test_suite(test_suite, default_environment, case_environments)

        # Create test results
        for result in results:
            # 获取测试用例使用的环境
            environment_id = result.get('environment_id', default_environment_id)
            environment = get_object_or_404(Environment, id=environment_id)

            TestResult.objects.create(
                test_run=test_run,
                test_case_id=result['test_case_id'],
                environment=environment,
                status=result['status'],
                request_headers=result.get('request_headers', {}),
                request_body=result.get('request_body'),
                response_time=result.get('response_time'),
                response_status_code=result.get('response_status_code'),
                response_headers=result.get('response_headers', {}),
                response_body=result.get('response_body'),
                error_message=result.get('error_message', ''),
                extracted_params=result.get('extracted_params', {}),
                validators=result.get('validators', [])
            )

        # Update test run
        failed_results = [r for r in results if r['status'] != 'passed']
        test_run.status = 'failed' if failed_results else 'completed'
        test_run.end_time = timezone.now()
        test_run.save()

        serializer = TestRunSerializer(test_run)
        return Response(serializer.data)


class TestRunViewSet(viewsets.ModelViewSet):
    queryset = TestRun.objects.all()
    serializer_class = TestRunSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'list':
            return TestRunListSerializer
        return TestRunSerializer

    def get_queryset(self):
        project_id = self.request.query_params.get('project', None)
        test_suite_id = self.request.query_params.get('test_suite', None)
        qs = TestRun.objects.select_related(
            "project", "test_suite", "environment", "created_by"
        )
        if project_id:
            qs = qs.filter(project_id=project_id)
        if test_suite_id:
            qs = qs.filter(test_suite_id=test_suite_id)
        return qs.order_by('-created_at')

    @action(detail=True, methods=['get'])
    def results(self, request, pk=None):
        test_run = self.get_object()
        results = TestResult.objects.select_related(
            "test_case", "environment"
        ).filter(test_run=test_run)

        # 使用分页
        paginator = StandardResultsSetPagination()
        paginated_results = paginator.paginate_queryset(results, request)

        serializer = TestResultSerializer(paginated_results, many=True)
        return paginator.get_paginated_response(serializer.data)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """返回测试运行的统计聚合（总数/通过/失败/错误/跳过）"""
        test_run = self.get_object()
        stats = TestResult.objects.filter(test_run=test_run).aggregate(
            total=Count('pk'),
            passed=Count('pk', filter=Q(status='passed')),
            failed=Count('pk', filter=Q(status='failed')),
            error=Count('pk', filter=Q(status='error')),
            skipped=Count('pk', filter=Q(status='skipped')),
        )
        return Response(stats)


class TestResultViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TestResult.objects.all()
    serializer_class = TestResultSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        qs = TestResult.objects.select_related("test_case", "environment")
        test_run_id = self.request.query_params.get('test_run')
        test_case_id = self.request.query_params.get('test_case')
        if test_run_id:
            qs = qs.filter(test_run_id=test_run_id)
        if test_case_id:
            qs = qs.filter(test_case_id=test_case_id)
        return qs.order_by('-created_at')


def _normalize_kv(data):
    """将 KeyValueTable 的 [{key,value}] 数组格式转为 {key:value} 字典格式"""
    if isinstance(data, dict):
        return data
    if isinstance(data, list) and all(isinstance(item, dict) and "key" in item for item in data):
        return {item.get("key", ""): item.get("value", "") for item in data}
    return data


def _format_param_schema(request_params) -> str:
    """将结构化参数数组格式化为 AI prompt 可读的文本"""
    if not request_params or not isinstance(request_params, list):
        return "（无参数定义）"
    lines = []
    for p in request_params:
        if not isinstance(p, dict):
            continue
        key = p.get("key", "")
        if not key:
            continue
        ptype = p.get("type", "string")
        required = "必填" if p.get("required") else "可选"
        default = p.get("default", "")
        value = p.get("value", "")
        desc = p.get("desc", "")
        validation = p.get("validation", "")
        parts = [f"- {key} ({ptype}, {required})"]
        if value:
            parts.append(f"  示例值: {value}")
        if default:
            parts.append(f"  默认值: {default}")
        if desc:
            parts.append(f"  说明: {desc}")
        if validation:
            parts.append(f"  校验规则: {validation}")
        lines.append("  ".join(parts))
    return "\n".join(lines) if lines else "（无参数定义）"


def _normalize_list(data):
    """规范化列表字段：字符串 → [字符串]，dict → [dict]，None → []"""
    if data is None:
        return []
    if isinstance(data, str):
        return [data]
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        return data
    return []


class AIGenerateMultiTestCasesViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "ai_generate"

    def _extract_json_by_path(self, data, path):
        if not path:
            return data
        current = data
        for segment in path.split("."):
            if not isinstance(current, dict):
                return None
            current = current.get(segment)
        return current

    def _call_ai_service(self, payload, prompt_template=None, model_provider=None):
        """调用 AI 服务生成测试用例。
        优先使用指定的模型供应商，其次使用默认供应商，最后回退到 ParameterConfig（旧参数配置）。
        """
        # 先尝试使用指定的模型供应商
        provider = model_provider
        if not provider:
            # 尝试使用新的 AI 大模型供应商系统（默认或第一个启用的）
            provider = AIModelProvider.objects.filter(is_enabled=True, is_default=True).first()
        if not provider:
            provider = AIModelProvider.objects.filter(is_enabled=True).first()

        if provider:
            return self._call_with_provider(provider, payload, prompt_template)

        # 回退到旧的参数配置
        return self._call_with_legacy_params(payload)

    def _call_with_provider(self, provider, payload, prompt_template=None):
        """使用 AIModelProvider + 适配器调用 AI"""
        from test_manager.ai_adapters import get_adapter

        adapter = get_adapter(provider)
        base_info = payload.get("base_info", {})
        rules_text = base_info.get("generation_rules", "")
        case_type = payload.get("case_type", "param_validate")

        # P0-1 修复：传递前端传入的完整接口详情
        raw_params = base_info.get("request_params", {})
        interface_info = {
            "request_method": base_info.get("request_method", ""),
            "request_url": base_info.get("request_url", ""),
            "api_name": base_info.get("api_name", ""),
            "api_desc": base_info.get("api_desc", ""),
            "request_headers": _normalize_kv(base_info.get("request_headers", {})),
            "request_params": _normalize_kv(raw_params),
            "param_schema": _format_param_schema(raw_params),
            "request_body_format": base_info.get("request_body_format", ""),
            "request_body": base_info.get("request_body", {}),
            "response_schema": base_info.get("response_schema", {}),
            "error_codes": _normalize_list(base_info.get("error_codes", [])),
            "auth_config": _normalize_kv(base_info.get("auth_config", {})),
        }

        cases = None
        error_msg = ""
        actual_prompt = ""
        import time as _time
        _start = _time.monotonic()
        try:
            actual_prompt = adapter._render_prompt(interface_info, rules_text, case_type, prompt_template)
            cases = adapter.call(interface_info, rules_text, case_type, prompt_template)
            if isinstance(cases, list) and len(cases) == 0:
                raw_snippet = (adapter.last_raw_response or "")[:200]
                err_msg = f"AI未返回有效用例。AI原始返回: {raw_snippet}"
                raise ValueError(err_msg)
            return cases
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            _elapsed_ms = int((_time.monotonic() - _start) * 1000)
            import json as _json
            # 当 cases 为空列表时，用原始响应兜底，避免丢失 AI 返回内容
            response_raw = ""
            if cases:
                response_raw = _json.dumps(cases, ensure_ascii=False, indent=2)
            elif adapter.last_raw_response:
                response_raw = adapter.last_raw_response
            AIGenerationRecord.objects.create(
                model_provider=provider,
                request_prompt=actual_prompt[:10000],
                response_raw=response_raw,
                case_type=case_type,
                interface_info={
                    "url": interface_info.get("request_url", ""),
                    "method": interface_info.get("request_method", ""),
                    "name": interface_info.get("api_name", ""),
                    "prompt_template_id": prompt_template.id if prompt_template else None,
                    "prompt_template_name": prompt_template.name if prompt_template else None,
                },
                case_count=len(cases) if isinstance(cases, list) else 0,
                duration_ms=_elapsed_ms,
                success=(error_msg == ""),
                error_message=error_msg[:2000],
                created_by=getattr(self.request, 'user', None) if hasattr(self, 'request') else None,
            )

    def _call_with_legacy_params(self, payload):
        """使用旧的 ParameterConfig 方式调用 AI"""
        base_url = (ParameterConfig.get_value("AI_API_BASE_URL", "") or "").strip()
        api_path = (ParameterConfig.get_value("AI_API_GENERATE_MULTI_CASES_PATH", "") or "").strip()
        api_method = (ParameterConfig.get_value("AI_API_METHOD", "POST") or "POST").upper().strip()
        auth_token = (ParameterConfig.get_value("AI_API_AUTH_TOKEN", "") or "").strip()
        timeout_text = (ParameterConfig.get_value("AI_API_TIMEOUT_SECONDS", "30") or "30").strip()
        extra_headers_text = (ParameterConfig.get_value("AI_API_EXTRA_HEADERS_JSON", "{}") or "{}").strip()
        response_cases_path = (
            ParameterConfig.get_value("AI_API_RESPONSE_CASES_PATH", "data.cases") or "data.cases"
        ).strip()

        if not base_url or not api_path:
            raise ValueError("AI接口配置缺失，请检查参数配置或AI大模型管理")

        try:
            timeout_seconds = float(timeout_text)
        except (TypeError, ValueError):
            timeout_seconds = 30.0

        try:
            extra_headers = json.loads(extra_headers_text or "{}")
            if not isinstance(extra_headers, dict):
                raise ValueError("AI_API_EXTRA_HEADERS_JSON 必须是JSON对象")
        except (TypeError, ValueError):
            raise ValueError("AI_API_EXTRA_HEADERS_JSON 不是合法JSON")

        headers = {"Content-Type": "application/json"}
        headers.update(extra_headers)
        if auth_token:
            headers["Authorization"] = f"Bearer {auth_token}"

        # 对发送给外部 AI 服务的 payload 做白名单过滤，去除内部标识字段
        base_info = payload.get("base_info", {})
        case_type = payload.get("case_type", "param_validate")
        safe_payload = {
            "base_info": {
                k: v for k, v in base_info.items()
                if k not in ("project_id", "group_id", "interface_id", "creator_id")
            },
            "case_type": case_type,
        }

        request_prompt = json.dumps(safe_payload, ensure_ascii=False)
        cases = None
        error_msg = ""
        raw_response_text = ""
        try:
            endpoint = urljoin(f"{base_url.rstrip('/')}/", api_path.lstrip("/"))
            resp = requests.request(
                method=api_method,
                url=endpoint,
                headers=headers,
                json=safe_payload,
                timeout=timeout_seconds,
            )
            if resp.status_code >= 400:
                raise ValueError(f"AI服务调用失败，状态码={resp.status_code}")
            raw_response_text = resp.text[:10000]
            try:
                body = resp.json()
            except ValueError:
                raise ValueError("AI服务返回非JSON")

            cases = self._extract_json_by_path(body, response_cases_path)
            if not isinstance(cases, list):
                raise ValueError("AI返回格式不合法：无法解析用例列表")
            return cases
        except Exception as exc:
            error_msg = str(exc)
            raise
        finally:
            import json as _json
            response_raw = ""
            if cases:
                response_raw = _json.dumps(cases, ensure_ascii=False, indent=2)
            elif raw_response_text:
                response_raw = raw_response_text
            AIGenerationRecord.objects.create(
                model_provider=None,
                request_prompt=request_prompt[:10000],
                response_raw=response_raw,
                case_type=case_type,
                interface_info={
                    "url": base_info.get("request_url", ""),
                    "method": base_info.get("request_method", ""),
                    "name": base_info.get("api_name", ""),
                },
                case_count=len(cases) if isinstance(cases, list) else 0,
                success=(error_msg == ""),
                error_message=error_msg[:2000],
                created_by=getattr(self.request, 'user', None) if hasattr(self, 'request') else None,
            )

    def create(self, request):
        serializer = AIGenerateMultiTestCasesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["creator_id"] != request.user.id and not request.user.is_staff:
            return Response({"detail": "无权限为其他用户生成草稿"}, status=status.HTTP_403_FORBIDDEN)

        base_info = data["base_info"]
        # 从已校验的 rule_objs 获取规则对象（由 serializer 注入）
        rule_objs = data.get("rule_objs", [])

        # 将规则渲染为提示词文本，注入到 base_info，供 AI 服务使用
        rules_prompt_parts = [rule.to_prompt_text() for rule in rule_objs if rule.is_enabled]
        rules_prompt = "\n".join(rules_prompt_parts) if rules_prompt_parts else ""
        if rules_prompt:
            base_info = dict(base_info)
            base_info["generation_rules"] = rules_prompt

        try:
            ai_cases = self._call_ai_service(
                {"base_info": base_info, "case_type": data["case_type"]},
                prompt_template=data.get("prompt_template_obj"),
                model_provider=data.get("model_provider_obj"),
            )
        except ValueError as exc:
            # 对 AI 调用异常做友好化处理，避免暴露内部信息
            err_msg = str(exc)
            if "AI服务调用失败" in err_msg or "AI接口配置缺失" in err_msg or "AI未返回有效用例" in err_msg:
                safe_msg = err_msg
            else:
                safe_msg = "AI服务调用失败，请稍后重试或联系管理员"
            return Response({"detail": safe_msg}, status=status.HTTP_400_BAD_REQUEST)
        if len(ai_cases) == 0:
            return Response({"detail": "AI未返回有效用例，请检查接口信息或提示词配置"}, status=status.HTTP_400_BAD_REQUEST)

        low_count_warning = len(ai_cases) < 3

        created_drafts = []
        with transaction.atomic():
            draft_group = AICaseDraftGroup.objects.create(
                project_id=base_info["project_id"],
                interface_id=base_info.get("interface_id"),
                case_type=data["case_type"],
                base_info=base_info,
                created_by=request.user,
            )

            # 记录本次生成使用的规则
            for rule in rule_objs:
                AICaseDraftRuleUsage.objects.create(
                    draft_group=draft_group,
                    rule=rule,
                )

            for index, item in enumerate(ai_cases):
                ai_headers = _normalize_kv(item.get("request_headers") or {})
                ai_rules = _normalize_list(item.get("validation_rules"))
                ai_params = item.get("request_params") or {}
                request_method = item.get("request_method") or base_info["request_method"]
                request_url = item.get("request_url") or base_info["request_url"]
                # GET/DELETE 将查询参数拼接到 URL
                if ai_params and request_method in ("GET", "DELETE"):
                    separator = "&" if "?" in request_url else "?"
                    request_url = f"{request_url}{separator}{urlencode(ai_params, doseq=True)}"
                case_data = {
                    "name": item.get("name") or f"AI生成用例{index + 1}",
                    "description": item.get("description") or "",
                    "project": base_info["project_id"],
                    "request_method": request_method,
                    "request_url": request_url,
                    "request_params": ai_params,
                    "request_headers_json": json.dumps(ai_headers, ensure_ascii=False),
                    "request_body_json": json.dumps(item.get("request_body") or {}, ensure_ascii=False),
                    "request_body_format": item.get("request_body_format") or base_info.get("request_body_format") or "json",
                    "validation_rules_json": json.dumps(ai_rules, ensure_ascii=False),
                    "expected_status_code": item.get("expected_status_code") or 200,
                }
                form = TestCaseForm(data=case_data)
                is_valid = form.is_valid()
                draft = AICaseDraft.objects.create(
                    draft_group=draft_group,
                    case_data=case_data,
                    is_valid=is_valid,
                    validation_errors=form.errors.get_json_data() if not is_valid else {},
                )
                created_drafts.append(draft)

        resp_data = {
            "draft_group_id": draft_group.id,
            "case_count": len(created_drafts),
            "drafts": AICaseDraftItemSerializer(created_drafts, many=True).data,
        }
        if low_count_warning:
            resp_data["warning"] = f"AI仅返回 {len(created_drafts)} 条用例（建议至少3条），草稿已保存可手动补充"
        return Response(resp_data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"])
    def batch(self, request):
        """批量生成：一次请求多个接口，后台 Celery 逐个调用 AI"""
        from test_manager._models_flat import ApiAsset

        project_id = request.data.get("project_id")
        interface_ids = request.data.get("interface_ids", [])
        case_type = request.data.get("case_type", "api")
        rule_ids = request.data.get("rule_ids", [])
        model_provider_id = request.data.get("model_provider_id")
        prompt_template_id = request.data.get("prompt_template_id")

        if not interface_ids or not project_id:
            return Response({"detail": "请选择接口和项目"}, status=status.HTTP_400_BAD_REQUEST)

        # 加载接口资产
        assets = list(ApiAsset.objects.filter(
            id__in=[i for i in interface_ids if i],
            project_id=project_id,
        ))
        if not assets:
            return Response({"detail": "未找到有效的接口信息"}, status=status.HTTP_400_BAD_REQUEST)

        # 加载规则
        rule_objs = TestCaseGenerationRule.objects.filter(
            id__in=[r for r in rule_ids if r > 0],
            is_enabled=True,
        )
        rules_prompt_parts = [rule.to_prompt_text() for rule in rule_objs]
        rules_prompt = "\n".join(rules_prompt_parts) if rules_prompt_parts else ""

        # 确定供应商
        provider = None
        if model_provider_id:
            provider = AIModelProvider.objects.filter(id=model_provider_id, is_enabled=True).first()
        if not provider:
            provider = AIModelProvider.objects.filter(is_enabled=True, is_default=True).first()
        if not provider:
            provider = AIModelProvider.objects.filter(is_enabled=True).first()

        # 确定提示词模板
        prompt_template_obj = None
        if prompt_template_id:
            prompt_template_obj = PromptTemplate.objects.filter(id=prompt_template_id, is_enabled=True).first()
        if not prompt_template_obj:
            prompt_template_obj = PromptTemplate.objects.filter(is_enabled=True, is_default=True).first()

        # 查找业务项目 ID（用于创建草稿）
        from test_manager._models_flat import ApiProject
        api_project = ApiProject.objects.filter(id=project_id).first()
        platform_project_id = api_project.platform_project_id if api_project else None

        # 为每个接口创建记录（status=generating），启动后 Celery 回填
        record_ids = []
        for asset in assets:
            raw_params = asset.request_params or []
            base_info = {
                "project_id": project_id,
                "platform_project_id": platform_project_id,
                "interface_id": asset.id,
                "request_method": asset.method or "GET",
                "request_url": asset.url or "",
                "api_name": asset.name or "",
                "api_desc": asset.interface_desc or "",
                "request_headers": asset.request_headers or {},
                "request_params": raw_params,
                "request_body_format": asset.request_body_format or "json",
                "request_body": asset.request_body or {},
                "response_schema": asset.response_schema or {},
                "error_codes": asset.error_code or [],
                "auth_config": asset.auth_config or {},
            }
            if rules_prompt:
                base_info["generation_rules"] = rules_prompt
            if prompt_template_id:
                base_info["user_requested_prompt_template_id"] = prompt_template_id
            if prompt_template_obj:
                base_info["prompt_template_id"] = prompt_template_obj.id
                base_info["prompt_template_name"] = prompt_template_obj.name
                base_info["prompt_template_text"] = prompt_template_obj.template_text

            record = AIGenerationRecord.objects.create(
                model_provider=provider,
                status="generating",
                case_type=case_type,
                interface_info=base_info,
                created_by=request.user,
            )
            record_ids.append(record.id)

        # 异步执行
        from test_manager.tasks import batch_ai_generate as _batch_task
        _batch_task.delay(record_ids)

        return Response({
            "record_ids": record_ids,
            "total": len(record_ids),
        })


class AIImportTestCasesViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        serializer = AIImportTestCasesRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        if data["user_id"] != request.user.id and not request.user.is_staff:
            return Response({"detail": "无权限导入其他用户草稿"}, status=status.HTTP_403_FORBIDDEN)

        group = get_object_or_404(AICaseDraftGroup, id=data["draft_group_id"])
        if group.created_by_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "无权限操作该草稿组"}, status=status.HTTP_403_FORBIDDEN)

        # 解析目标套件
        target_suite = None
        target_suite_id = data.get("target_suite_id")
        new_suite_name = (data.get("new_suite_name") or "").strip()

        if target_suite_id:
            target_suite = get_object_or_404(TestSuite, id=target_suite_id)
            if target_suite.created_by_id != request.user.id and not request.user.is_staff:
                return Response({"detail": "无权限操作该套件"}, status=status.HTTP_403_FORBIDDEN)

        with transaction.atomic():
            # 对草稿组加行锁，防止并发导入导致 status 更新竞态
            group = AICaseDraftGroup.objects.select_for_update().get(id=group.id)

            if new_suite_name and not target_suite:
                target_suite = TestSuite.objects.create(
                    name=new_suite_name,
                    project=group.project,
                    created_by=request.user,
                )

            drafts = AICaseDraft.objects.select_for_update().filter(
                draft_group=group,
                id__in=data["draft_ids"],
            )

            success_count = 0
            failure_count = 0
            results = []
            imported_case_ids = []

            for draft in drafts:
                if draft.import_status == AICaseDraft.IMPORT_IMPORTED:
                    failure_count += 1
                    results.append({"draft_id": draft.id, "success": False, "reason": "草稿已导入"})
                    continue

                form = TestCaseForm(data=draft.case_data)
                if not form.is_valid():
                    draft.import_status = AICaseDraft.IMPORT_FAILED
                    draft.validation_errors = form.errors.get_json_data()
                    draft.save(update_fields=["import_status", "validation_errors", "updated_at"])
                    failure_count += 1
                    results.append({"draft_id": draft.id, "success": False, "reason": "表单校验失败"})
                    continue

                test_case = form.save(commit=False)
                test_case.created_by = request.user
                test_case.save()

                draft.import_status = AICaseDraft.IMPORT_IMPORTED
                draft.imported_case = test_case
                draft.validation_errors = {}
                draft.save(update_fields=["import_status", "imported_case", "validation_errors", "updated_at"])
                success_count += 1
                imported_case_ids.append(test_case.id)
                results.append({"draft_id": draft.id, "success": True, "imported_case_id": test_case.id})

            # 将导入的用例关联到套件
            if target_suite and imported_case_ids:
                existing_count = TestSuiteCase.objects.filter(test_suite=target_suite).count()
                suite_cases = [
                    TestSuiteCase(test_suite=target_suite, test_case_id=cid, order=existing_count + i)
                    for i, cid in enumerate(imported_case_ids)
                ]
                TestSuiteCase.objects.bulk_create(suite_cases)

            total = group.drafts.count()
            imported = group.drafts.filter(import_status=AICaseDraft.IMPORT_IMPORTED).count()
            if imported == 0:
                group.status = AICaseDraftGroup.STATUS_PENDING
            elif imported < total:
                group.status = AICaseDraftGroup.STATUS_PARTIAL
            else:
                group.status = AICaseDraftGroup.STATUS_IMPORTED
            group.save(update_fields=["status", "updated_at"])

        resp_data = {
            "draft_group_id": group.id,
            "success_count": success_count,
            "failure_count": failure_count,
            "results": results,
            "group_status": group.status,
        }
        if target_suite:
            resp_data["suite_id"] = target_suite.id
            resp_data["suite_name"] = target_suite.name
        return Response(resp_data)


class AICaseDraftBoxViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @property
    def paginator(self):
        if not hasattr(self, '_paginator'):
            self._paginator = self.pagination_class()
        return self._paginator

    def paginate_queryset(self, queryset):
        return self.paginator.paginate_queryset(queryset, self.request, view=self)

    def get_paginated_response(self, data):
        return self.paginator.get_paginated_response(data)

    def list(self, request):
        groups = AICaseDraftGroup.objects.filter(created_by=request.user)
        # 支持按项目过滤
        project_id = request.query_params.get("project_id")
        if project_id:
            groups = groups.filter(project_id=project_id)
        groups = groups.select_related('project').prefetch_related('drafts').order_by("-created_at")
        page = self.paginate_queryset(groups)
        if page is not None:
            serializer = AICaseDraftGroupItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(AICaseDraftGroupItemSerializer(groups, many=True).data)

    @action(detail=False, methods=["get"], url_path="drafts")
    def drafts(self, request):
        group_id = request.query_params.get("draft_group_id")
        if not group_id:
            return Response({"detail": "draft_group_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        group = get_object_or_404(AICaseDraftGroup, id=group_id)
        if group.created_by_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "无权限查看该草稿组"}, status=status.HTTP_403_FORBIDDEN)
        drafts = group.drafts.order_by("id")
        page = self.paginate_queryset(drafts)
        if page is not None:
            serializer = AICaseDraftItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        return Response(AICaseDraftItemSerializer(drafts, many=True).data)

    @action(detail=False, methods=["get"], url_path="suites")
    def suites(self, request):
        """列出当前用户可用的测试套件"""
        project_id = request.query_params.get("project_id")
        suites = TestSuite.objects.filter(created_by=request.user)
        if project_id:
            suites = suites.filter(project_id=project_id)
        suites = suites.select_related("project").order_by("-updated_at")
        data = [{"id": s.id, "name": s.name, "project_id": s.project_id, "project_name": s.project.name} for s in suites]
        return Response(data)

    @action(detail=False, methods=["post"], url_path="delete-drafts")
    def delete_drafts(self, request):
        """删除指定草稿（已导入的不可删）"""
        draft_ids = request.data.get("draft_ids", [])
        if not draft_ids:
            return Response({"detail": "draft_ids不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        drafts = AICaseDraft.objects.filter(id__in=draft_ids, import_status__in=[
            AICaseDraft.IMPORT_PENDING, AICaseDraft.IMPORT_FAILED
        ])
        own_drafts = drafts.filter(draft_group__created_by=request.user)
        if request.user.is_staff:
            own_drafts = drafts

        deleted = own_drafts.count()
        own_drafts.delete()
        return Response({"deleted_count": deleted})

    @action(detail=False, methods=["post"], url_path="delete-group")
    def delete_group(self, request):
        """删除整个草稿组及其所有草稿。含已导入草稿的组不可直接删除。"""
        group_id = request.data.get("draft_group_id")
        if not group_id:
            return Response({"detail": "draft_group_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)

        group = get_object_or_404(AICaseDraftGroup, id=group_id)
        if group.created_by_id != request.user.id and not request.user.is_staff:
            return Response({"detail": "无权限删除该草稿组"}, status=status.HTTP_403_FORBIDDEN)

        imported_count = group.drafts.filter(import_status=AICaseDraft.IMPORT_IMPORTED).count()
        if imported_count > 0:
            return Response(
                {"detail": f"该草稿组有 {imported_count} 条草稿已导入为测试用例，请先单独删除未导入的草稿"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        group.delete()
        return Response({"deleted": True})


class RuleManagementViewSet(viewsets.ModelViewSet):
    """AI 测试用例生成规则管理。"""
    queryset = TestCaseGenerationRule.objects.all()
    serializer_class = TestCaseGenerationRuleSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = TestCaseGenerationRule.objects.all()
        category = self.request.query_params.get("category")
        priority = self.request.query_params.get("priority")
        is_enabled = self.request.query_params.get("is_enabled")
        keyword = self.request.query_params.get("keyword")

        if category:
            queryset = queryset.filter(category=category)
        if priority:
            queryset = queryset.filter(priority=priority)
        if is_enabled is not None:
            is_enabled_bool = is_enabled.lower() == "true"
            queryset = queryset.filter(is_enabled=is_enabled_bool)
        if keyword:
            queryset = queryset.filter(name__icontains=keyword) | \
                      queryset.filter(description__icontains=keyword)
        return queryset.order_by("category", "-priority", "-created_at")

    def get_serializer_context(self):
        return {"request": self.request}

    @action(detail=False, methods=["post"], url_path="import-json")
    def import_json(self, request):
        """从 JSON 批量导入规则。
        POST /api/rules/import-json/
        请求体：[{ "name": "...", "description": "...", "category": "param_validate", "priority": "high", "rule_content": "一行一条规则\n第二行", "is_enabled": true }, ...]
        返回：{ "created": 3, "updated": 1, "errors": [...] }
        """
        if not isinstance(request.data, list):
            return Response(
                {"detail": "请求体必须是JSON数组"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        created_count = 0
        updated_count = 0
        errors = []

        for index, item in enumerate(request.data):
            if not isinstance(item, dict):
                errors.append({"index": index, "error": "元素必须是对象"})
                continue
            rule_id = item.get("id")
            name = item.get("name")
            if not name:
                errors.append({"index": index, "error": "name 不能为空"})
                continue
            try:
                if rule_id:
                    rule = TestCaseGenerationRule.objects.get(id=rule_id, created_by=request.user)
                    serializer = TestCaseGenerationRuleSerializer(
                        rule, data=item, partial=True, context={"request": request}
                    )
                else:
                    serializer = TestCaseGenerationRuleSerializer(
                        data=item, context={"request": request}
                    )
                if serializer.is_valid():
                    serializer.save()
                    if rule_id:
                        updated_count += 1
                    else:
                        created_count += 1
                else:
                    errors.append({"index": index, "errors": serializer.errors})
            except TestCaseGenerationRule.DoesNotExist:
                errors.append({"index": index, "error": "规则不存在或无权限"})
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        return Response({
            "created": created_count,
            "updated": updated_count,
            "errors": errors,
        })

    @action(detail=False, methods=["get"], url_path="export-json")
    def export_json(self, request):
        """导出规则为 JSON 数组。
        GET /api/rules/export-json/?category=param_validate&priority=high&is_enabled=true
        """
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class PromptTemplateManagementViewSet(viewsets.ModelViewSet):
    """提示词模板管理。"""
    serializer_class = PromptTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = PromptTemplate.objects.filter(
            Q(created_by=self.request.user) | Q(created_by__isnull=True)
        )
        keyword = self.request.query_params.get("keyword")
        is_enabled = self.request.query_params.get("is_enabled")
        category = self.request.query_params.get("category")

        if keyword:
            queryset = queryset.filter(name__icontains=keyword) | \
                      queryset.filter(description__icontains=keyword)
        if is_enabled is not None:
            is_enabled_bool = is_enabled.lower() == "true"
            queryset = queryset.filter(is_enabled=is_enabled_bool)
        if category:
            queryset = queryset.filter(category=category)
        return queryset.order_by("-updated_at")

    def get_serializer_context(self):
        return {"request": self.request}

    def perform_create(self, serializer):
        # 如果设置为默认模板，先将其他模板设为非默认
        if serializer.validated_data.get("is_default", False):
            PromptTemplate.objects.filter(
                created_by=self.request.user,
                is_default=True
            ).update(is_default=False)
        serializer.save(created_by=self.request.user)

    def perform_update(self, serializer):
        # 如果设置为默认模板，先将其他模板设为非默认
        if serializer.validated_data.get("is_default", False):
            PromptTemplate.objects.filter(
                created_by=self.request.user,
                is_default=True
            ).exclude(id=self.get_object().id).update(is_default=False)
        serializer.save()

    @action(detail=False, methods=["post"], url_path="set-default")
    def set_default(self, request):
        """设置默认模板。"""
        template_id = request.data.get("template_id")
        if not template_id:
            return Response({"detail": "template_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        
        template = get_object_or_404(PromptTemplate, id=template_id, created_by=request.user)
        
        # 先将所有模板设为非默认
        PromptTemplate.objects.filter(
            created_by=request.user,
            is_default=True
        ).update(is_default=False)
        
        # 设置当前模板为默认
        template.is_default = True
        template.save()
        
        return Response({"detail": "设置成功", "template": PromptTemplateSerializer(template).data})

    @action(detail=False, methods=["get"], url_path="default")
    def get_default(self, request):
        """获取当前用户的默认模板。"""
        template = PromptTemplate.objects.filter(
            created_by=request.user,
            is_default=True,
            is_enabled=True
        ).first()
        
        if not template:
            # 如果没有默认模板，返回第一个启用的模板
            template = PromptTemplate.objects.filter(
                created_by=request.user,
                is_enabled=True
            ).order_by("-created_at").first()
        
        if not template:
            return Response({"detail": "没有可用的提示词模板"}, status=status.HTTP_404_NOT_FOUND)
        
        return Response(PromptTemplateSerializer(template).data)

    @action(detail=False, methods=["post"], url_path="import-json")
    def import_json(self, request):
        """从 JSON 批量导入提示词模板。"""
        if not isinstance(request.data, list):
            return Response(
                {"detail": "请求体必须是JSON数组"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        created_count = 0
        updated_count = 0
        errors = []

        for index, item in enumerate(request.data):
            if not isinstance(item, dict):
                errors.append({"index": index, "error": "元素必须是对象"})
                continue
            template_id = item.get("id")
            name = item.get("name")
            if not name:
                errors.append({"index": index, "error": "name 不能为空"})
                continue
            try:
                if template_id:
                    template = PromptTemplate.objects.get(id=template_id, created_by=request.user)
                    serializer = PromptTemplateSerializer(
                        template, data=item, partial=True, context={"request": request}
                    )
                else:
                    serializer = PromptTemplateSerializer(
                        data=item, context={"request": request}
                    )
                if serializer.is_valid():
                    serializer.save()
                    if template_id:
                        updated_count += 1
                    else:
                        created_count += 1
                else:
                    errors.append({"index": index, "errors": serializer.errors})
            except PromptTemplate.DoesNotExist:
                errors.append({"index": index, "error": "模板不存在或无权限"})
            except Exception as e:
                errors.append({"index": index, "error": str(e)})

        return Response({
            "created": created_count,
            "updated": updated_count,
            "errors": errors,
        })

    @action(detail=False, methods=["get"], url_path="export-json")
    def export_json(self, request):
        """导出提示词模板为 JSON 数组。"""
        queryset = self.filter_queryset(self.get_queryset())
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


class AIModelProviderViewSet(viewsets.ModelViewSet):
    """AI 大模型供应商管理。"""
    serializer_class = AIModelProviderSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = AIModelProvider.objects.all()
        keyword = self.request.query_params.get("keyword")
        provider_type = self.request.query_params.get("provider_type")
        is_enabled = self.request.query_params.get("is_enabled")
        if keyword:
            queryset = queryset.filter(name__icontains=keyword)
        if provider_type:
            queryset = queryset.filter(provider_type=provider_type)
        if is_enabled:
            queryset = queryset.filter(is_enabled=(is_enabled.lower() == "true"))
        return queryset.order_by("-is_enabled", "-is_default", "name")

    def perform_create(self, serializer):
        if serializer.validated_data.get("is_default", False):
            AIModelProvider.objects.filter(is_default=True).update(is_default=False)
        serializer.save()

    def perform_update(self, serializer):
        if serializer.validated_data.get("is_default", False):
            AIModelProvider.objects.filter(is_default=True).exclude(
                id=self.get_object().id
            ).update(is_default=False)
        serializer.save()

    @action(detail=False, methods=["post"], url_path="set-default")
    def set_default(self, request):
        """设置默认供应商"""
        provider_id = request.data.get("provider_id")
        if not provider_id:
            return Response({"detail": "provider_id不能为空"}, status=status.HTTP_400_BAD_REQUEST)
        provider = get_object_or_404(AIModelProvider, id=provider_id)
        AIModelProvider.objects.filter(is_default=True).update(is_default=False)
        provider.is_default = True
        provider.save()
        return Response({"detail": "设置成功", "provider": AIModelProviderSerializer(provider).data})

    @action(detail=True, methods=["post"], url_path="test")
    def test_connection(self, request, pk=None):
        """测试供应商连接"""
        provider = self.get_object()
        from test_manager.ai_adapters import get_adapter
        try:
            adapter = get_adapter(provider)
            interface_info = {
                "request_method": "GET",
                "request_url": "/health-check",
                "request_headers": {},
                "request_body_schema": {},
            }
            cases = adapter.call(interface_info, "这是一个连通性测试", "connectivity_check")
            return Response({
                "success": True,
                "message": f"连接成功，返回 {len(cases)} 条用例",
                "cases_preview": cases[:3] if cases else [],
            })
        except Exception as e:
            return Response({
                "success": False,
                "message": f"连接失败: {str(e)}",
            }, status=status.HTTP_400_BAD_REQUEST)


# === 分组 ViewSet（轻量版：list + create + update + delete） ===

class TestCaseGroupViewSet(viewsets.ModelViewSet):
    queryset = TestCaseGroup.objects.all()
    serializer_class = TestCaseGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TestCaseGroup.objects.all()
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.order_by("name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        """返回分组树（仅顶级节点，children 递归展开），支持按项目筛选"""
        project_id = request.query_params.get("project")
        root_groups = TestCaseGroup.objects.filter(parent=None)
        if project_id:
            root_groups = root_groups.filter(project_id=project_id)
        root_groups = root_groups.order_by("name")
        serializer = self.get_serializer(root_groups, many=True)
        return Response(serializer.data)


class TestSuiteGroupViewSet(viewsets.ModelViewSet):
    queryset = TestSuiteGroup.objects.all()
    serializer_class = TestSuiteGroupSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        qs = TestSuiteGroup.objects.all()
        project_id = self.request.query_params.get("project")
        if project_id:
            qs = qs.filter(project_id=project_id)
        return qs.order_by("name")

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=["get"], url_path="tree")
    def tree(self, request):
        """返回分组树（仅顶级节点，children 递归展开），支持按项目筛选"""
        project_id = request.query_params.get("project")
        root_groups = TestSuiteGroup.objects.filter(parent=None)
        if project_id:
            root_groups = root_groups.filter(project_id=project_id)
        root_groups = root_groups.order_by("name")
        serializer = self.get_serializer(root_groups, many=True)
        return Response(serializer.data)


class AIGenerationRecordViewSet(viewsets.ModelViewSet):
    queryset = AIGenerationRecord.objects.all()
    serializer_class = AIGenerationRecordSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    http_method_names = ["get", "delete", "post", "head", "options"]

    def get_queryset(self):
        qs = AIGenerationRecord.objects.all()
        provider_id = self.request.query_params.get("model_provider")
        if provider_id:
            qs = qs.filter(model_provider_id=provider_id)
        search = self.request.query_params.get("search", "").strip()
        if search:
            qs = qs.filter(request_prompt__icontains=search)
        start_date = self.request.query_params.get("start_date", "").strip()
        if start_date:
            qs = qs.filter(created_at__date__gte=start_date)
        end_date = self.request.query_params.get("end_date", "").strip()
        if end_date:
            qs = qs.filter(created_at__date__lte=end_date)
        return qs.order_by("-created_at")

    @action(detail=False, methods=["post"])
    def batch_delete(self, request):
        record_ids = request.data.get("ids", [])
        if not record_ids or not isinstance(record_ids, list):
            return Response({"detail": "请提供要删除的记录ID列表"}, status=400)
        qs = self.get_queryset().filter(id__in=record_ids)
        deleted_count, _ = qs.delete()
        return Response({"deleted_count": deleted_count})

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """重新生成：使用记录保存的参数再次调用AI，替换原草稿组中的测试用例"""
        record = self.get_object()
        if record.status == "generating":
            return Response({"detail": "该记录正在生成中，请等待完成"}, status=400)

        from test_manager.ai_adapters import get_adapter
        import time as _time

        provider = record.model_provider
        if not provider:
            return Response({"detail": "原记录未关联AI模型，无法重新生成"}, status=400)

        base_info = record.interface_info or {}
        if not base_info.get("request_url"):
            return Response({"detail": "记录中缺少接口信息，无法重新生成"}, status=400)

        case_type = record.case_type

        # 构建 interface_info（与 batch_ai_generate 相同的规范化逻辑）
        raw_params = base_info.get("request_params", {})
        interface_info = {
            "request_method": base_info.get("request_method", ""),
            "request_url": base_info.get("request_url", ""),
            "api_name": base_info.get("api_name", ""),
            "api_desc": base_info.get("api_desc", ""),
            "request_headers": _normalize_kv(base_info.get("request_headers", {})),
            "request_params": _normalize_kv(raw_params),
            "param_schema": _format_param_schema(raw_params),
            "request_body_format": base_info.get("request_body_format", ""),
            "request_body": base_info.get("request_body", {}),
            "response_schema": base_info.get("response_schema", {}),
            "error_codes": _normalize_list(base_info.get("error_codes", [])),
            "auth_config": _normalize_kv(base_info.get("auth_config", {})),
        }
        rules_text = base_info.get("generation_rules", "")

        # 重建提示词模板（优先使用快照原文，避免数据库查询变化）
        prompt_template_obj = None
        pt_text = base_info.get("prompt_template_text")
        if pt_text:
            class _PromptTemplateProxy:
                def to_rendered_prompt(self, ctx):
                    text = pt_text
                    for k, v in ctx.items():
                        text = text.replace("{" + k + "}", str(v))
                    return text
            prompt_template_obj = _PromptTemplateProxy()
        elif pt_id := base_info.get("prompt_template_id"):
            from test_manager.models.prompt_template import PromptTemplate as _PT
            prompt_template_obj = _PT.objects.filter(id=pt_id, is_enabled=True).first()

        # 调用 AI
        adapter = get_adapter(provider)
        _start = _time.monotonic()
        try:
            actual_prompt = adapter._render_prompt(
                interface_info, rules_text, case_type, prompt_template_obj
            )
            cases = adapter.call(interface_info, rules_text, case_type, prompt_template_obj)
        except Exception as exc:
            _elapsed_ms = int((_time.monotonic() - _start) * 1000)
            record.status = "failed"
            record.error_message = str(exc)[:2000]
            record.duration_ms = _elapsed_ms
            record.response_raw = (getattr(adapter, "last_raw_response", None) or "")[:10000]
            record.save(update_fields=["status", "error_message", "duration_ms", "response_raw"])
            return Response({"detail": str(exc)}, status=400)

        _elapsed_ms = int((_time.monotonic() - _start) * 1000)

        if not isinstance(cases, list) or len(cases) == 0:
            record.status = "failed"
            record.error_message = "AI未返回有效用例"
            record.duration_ms = _elapsed_ms
            record.save(update_fields=["status", "error_message", "duration_ms"])
            return Response({"detail": "AI未返回有效用例"}, status=400)

        # 查找草稿组，替换其中的草稿
        draft_group_id = base_info.get("draft_group_id")

        with transaction.atomic():
            draft_group = None
            if draft_group_id:
                draft_group = AICaseDraftGroup.objects.filter(id=draft_group_id).first()

            if draft_group:
                # 删除未导入的旧草稿
                deleted_count, _ = draft_group.drafts.filter(
                    import_status="pending"
                ).delete()
            else:
                # 草稿组已被删除，使用项目ID新建一个
                platform_project_id = base_info.get("platform_project_id")
                if not platform_project_id:
                    record.status = "failed"
                    record.error_message = "缺少项目ID，无法创建草稿组"
                    record.save(update_fields=["status", "error_message"])
                    return Response({"detail": "缺少项目ID"}, status=400)

                draft_group = AICaseDraftGroup.objects.create(
                    project_id=platform_project_id,
                    interface_id=base_info.get("interface_id"),
                    case_type=case_type,
                    base_info=interface_info,
                    created_by=record.created_by or request.user,
                )

            # 创建新草稿
            created_count = 0
            for index, item in enumerate(cases):
                ai_headers = _normalize_kv(item.get("request_headers") or {})
                ai_rules = _normalize_list(item.get("validation_rules"))
                ai_params = item.get("request_params") or {}
                req_method = item.get("request_method") or base_info.get("request_method", "")
                req_url = item.get("request_url") or base_info.get("request_url", "")
                if ai_params and req_method in ("GET", "DELETE"):
                    sep = "&" if "?" in req_url else "?"
                    req_url = f"{req_url}{sep}{urlencode(ai_params, doseq=True)}"
                case_data = {
                    "name": item.get("name") or f"AI生成用例{index + 1}",
                    "description": item.get("description") or "",
                    "project": draft_group.project_id,
                    "request_method": req_method,
                    "request_url": req_url,
                    "request_params": ai_params,
                    "request_headers_json": json.dumps(ai_headers, ensure_ascii=False),
                    "request_body_json": json.dumps(item.get("request_body") or {}, ensure_ascii=False),
                    "request_body_format": item.get("request_body_format") or base_info.get("request_body_format") or "json",
                    "validation_rules_json": json.dumps(ai_rules, ensure_ascii=False),
                    "expected_status_code": item.get("expected_status_code") or 200,
                }
                form = TestCaseForm(data=case_data)
                is_valid = form.is_valid()
                AICaseDraft.objects.create(
                    draft_group=draft_group,
                    case_data=case_data,
                    is_valid=is_valid,
                    validation_errors=form.errors.get_json_data() if not is_valid else {},
                )
                created_count += 1

            # 重置草稿组状态
            if draft_group.status != AICaseDraftGroup.STATUS_PENDING:
                draft_group.status = AICaseDraftGroup.STATUS_PENDING
                draft_group.save(update_fields=["status"])

        # 更新记录
        record.request_prompt = actual_prompt[:10000]
        record.response_raw = json.dumps(cases, ensure_ascii=False, indent=2)[:10000]
        record.case_count = created_count
        record.duration_ms = _elapsed_ms
        record.success = True
        record.status = "success"
        record.error_message = ""
        # 确保 draft_group_id 已记录
        info = record.interface_info or {}
        info["draft_group_id"] = draft_group.id
        record.interface_info = info
        record.save(update_fields=[
            "request_prompt", "response_raw", "case_count",
            "duration_ms", "success", "status", "error_message", "interface_info",
        ])

        return Response({
            "draft_group_id": draft_group.id,
            "case_count": created_count,
        })
