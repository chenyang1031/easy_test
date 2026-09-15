"""
场景静态校验器（健康检查）。

不发起任何网络请求，对场景配置做可静态检测的一致性检查，用于在保存/执行前
暴露"运行到该节点必然失败"的配置缺陷。检查项源自真实批量执行失败案例：

- undefined_variable：{{var}} 引用了未定义变量（不在场景变量/提取变量/
  节点输出/环境变量/内置变量/debugtalk 函数之中），运行时直接渲染失败
- url_placeholder：生效 URL 含未填充的 {placeholder} 字面量，会被原样发出
- cross_module_url：request_url 覆盖与所属资产的路径模块（前两段）不一致，
  通常是配错了接口链
- body_format_mismatch：接口资产要求 form-data，节点却按 JSON 提交请求体，
  表单字段会被服务端静默忽略
"""
import re
from urllib.parse import urlparse

from test_manager.api.scene_engine import VAR_PATTERN, get_debugtalk_functions
from test_manager.env_variables_compat import variables_for_runtime
from test_manager.models import Environment

# 引擎内置变量 + 变量池保留键，任何节点都可引用
BUILTIN_VARIABLE_NAMES = {"timestamp", "runId", "env", "scene"}


def _iter_template_exprs(value):
    """递归遍历配置结构，产出其中所有 {{expr}} 表达式文本。"""
    if isinstance(value, str):
        for match in VAR_PATTERN.finditer(value):
            yield match.group(1)
    elif isinstance(value, dict):
        for item in value.values():
            yield from _iter_template_exprs(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from _iter_template_exprs(item)


def _expr_root(expr):
    """取表达式根名：data.list[0] -> data；todayTime() -> todayTime。"""
    return re.split(r"[.\[(]", str(expr).strip(), maxsplit=1)[0].strip()


def _collect_defined_roots(scene, env_obj):
    """收集校验时视为"已定义"的变量根名。"""
    defined = set(BUILTIN_VARIABLE_NAMES)
    defined.update(str(k).strip() for k in get_debugtalk_functions().keys())
    defined.update(str(k).strip() for k in (scene.variables or {}).keys())

    for node in scene.nodes.filter(is_deleted=False):
        if node.node_key:
            defined.add(node.node_key.strip())
        defined.add(f"node_{node.id}")
        for raw in node.extract_rules or []:
            if isinstance(raw, dict) and raw.get("name"):
                defined.add(str(raw["name"]).strip())

    # 环境变量在执行时才注入：指定了环境只认该环境；未指定时取同项目全部环境的并集，
    # 宁可少报不可误报
    if env_obj is not None:
        env_queryset = Environment.objects.filter(id=env_obj.id)
    else:
        platform_project_id = getattr(scene.project, "platform_project_id", None)
        env_queryset = Environment.objects.filter(project_id=platform_project_id)
    for env in env_queryset:
        defined.update(str(k).strip() for k in variables_for_runtime(env.variables or {}))
    return defined


def _module_prefix(url_text):
    """取 URL 路径的前两段作为模块标识：/portal/badge/train/list -> portal/badge。"""
    path = urlparse(str(url_text or "")).path
    segments = [s for s in path.split("/") if s]
    return "/".join(segments[:2])


def _issue(node, check, severity, message):
    return {
        "check": check,
        "severity": severity,
        "node_id": node.id,
        "node_key": node.node_key,
        "node_name": node.name,
        "message": message,
    }


def _effective_url(node):
    # 与 scene_engine._run_node 的取值保持一致：request_url 覆盖优先，回退资产 URL
    return (node.request_url or "").strip() or (node.api_asset.url if node.api_asset else "")


def validate_scene(scene, environment_id=None):
    """
    执行三项静态检查，返回问题列表：
    [{check, severity, node_id, node_key, node_name, message}, ...]
    severity: error=运行时必然失败 / warning=疑似配置错误，需人工确认
    """
    env_obj = Environment.objects.filter(id=environment_id).first() if environment_id else None
    defined = _collect_defined_roots(scene, env_obj)
    issues = []

    for node in scene.nodes.select_related("api_asset").filter(is_deleted=False).order_by("sort", "id"):
        # --- 检查1：{{var}} 引用未定义变量/函数 ---
        checked_values = [
            node.request_url or "",
            node.custom_base_url or "",
            node.request_headers or {},
            node.request_params or {},
            node.request_body or {},
        ]
        for rule in node.assert_rules or []:
            if isinstance(rule, dict):
                checked_values.append(rule.get("expected"))
        seen_roots = set()
        for value in checked_values:
            for expr in _iter_template_exprs(value):
                root = _expr_root(expr)
                if not root or root in defined or root in seen_roots:
                    continue
                seen_roots.add(root)
                if "(" in expr:
                    issues.append(_issue(node, "undefined_variable", "error",
                                         f"引用的函数 {expr} 不在 debugtalk 函数中"))
                else:
                    issues.append(_issue(node, "undefined_variable", "error",
                                         f"引用了未定义的变量 {{{{{expr}}}}}：不在场景变量、提取变量、"
                                         f"节点输出或环境变量中，运行到该节点会直接失败"))

        # --- 检查2：生效 URL 含 {placeholder} 字面量 ---
        stripped_url = VAR_PATTERN.sub("", _effective_url(node))
        for placeholder in re.findall(r"(?<!\{)\{([^{}]+)\}(?!\})", stripped_url):
            issues.append(_issue(node, "url_placeholder", "error",
                                 f"生效 URL 含未填充的占位符 {{{placeholder}}}，请求会按字面量发出；"
                                 f"请为节点设置 request_url 覆盖并写成 {{{{变量}}}} 模板"))

        # --- 检查3：URL 覆盖指向其他模块 ---
        if (node.request_url or "").strip() and node.api_asset:
            asset_prefix = _module_prefix(node.api_asset.url)
            override_prefix = _module_prefix(node.request_url)
            if asset_prefix and override_prefix and asset_prefix != override_prefix:
                issues.append(_issue(node, "cross_module_url", "warning",
                                     f"URL 覆盖疑似配错链：资产「{node.api_asset.name}」属于 {asset_prefix}，"
                                     f"而覆盖指向 {override_prefix}，请确认是否为其他模块的接口"))

        # --- 检查4：接口资产要求 form-data，节点却按 JSON 提交请求体 ---
        if node.api_asset and node.request_body:
            asset_format = (getattr(node.api_asset, "request_body_format", "") or "").lower()
            node_format = (node.body_type or "json").lower()
            if asset_format == "form-data" and node_format == "json":
                issues.append(_issue(node, "body_format_mismatch", "warning",
                                     f"接口资产「{node.api_asset.name}」要求 form-data 提交，"
                                     f"而节点请求体格式为 json，表单字段会被服务端忽略"
                                     f"（典型报错\"xxx不能为空\"）；请将节点的请求体格式改为 form-data"))

    return issues
