"""AI 大模型适配器 — 基类和 OpenAI 兼容适配器"""
import json
import re
import requests
from abc import ABC, abstractmethod


class BaseAdapter(ABC):
    """AI 模型适配器基类"""

    # 内置默认 prompt（文档提取 API 使用）
    DEFAULT_DOCUMENT_EXTRACT_PROMPT = """你是一个专业的 API 接口文档解析专家。请从以下文档内容中提取所有 API 接口定义。

请严格按照以下 JSON 数组格式输出，每个元素包含以下字段：
- name: 接口名称
- method: 请求方法（GET/POST/PUT/DELETE/PATCH）
- url: 请求 URL 路径
- interface_desc: 接口描述
- request_headers: 请求头（JSON 对象）
- request_params: 请求参数（数组，每个元素包含 key/type/required/desc）
- request_body_format: 请求体格式（json/form-data）
- request_body: 请求体结构（JSON 对象）
- response_schema: 响应结构（JSON 对象）
- error_code: 错误码列表（数组）
- auth_config: 鉴权配置（JSON 对象）

注意事项：
1. 如果文档中没有明确说明某个字段，请使用 null 或空值
2. URL 请提取完整路径，如 /api/v1/users
3. method 必须是大写
4. 只输出 JSON 数组，不要包含 markdown 代码块标记或其他文字说明

文档内容：
{document_content}"""

    def __init__(self, provider):
        self.provider = provider  # AIModelProvider instance
        self.last_raw_response = None  # 最近一次 AI 调用的原始响应内容

    @abstractmethod
    def build_request(self, interface_info: dict, rules_text: str, case_type: str) -> dict:
        """构建 API 请求参数
        Returns: dict with keys: url, headers, json_body
        """
        pass

    @abstractmethod
    def parse_response(self, response_data: dict) -> list:
        """从 API 响应中提取测试用例列表
        Returns: list of case dicts
        """
        pass

    def call(self, interface_info: dict, rules_text: str, case_type: str, prompt_template=None) -> list:
        """完整的调用流程：构建请求 → 发送 → 解析"""
        req = self.build_request(interface_info, rules_text, case_type, prompt_template)
        # NVIDIA NIM 等平台可能需要绕过系统代理
        resp = requests.request(
            method="POST",
            url=req["url"],
            headers=req["headers"],
            json=req["json_body"],
            timeout=self.provider.timeout,
            proxies={"http": None, "https": None},
        )
        if resp.status_code >= 400:
            body = resp.text[:500]
            raise ValueError(
                f"AI 服务调用失败 [HTTP {resp.status_code}]: {body}"
            )
        self.last_raw_response = resp.text
        body = resp.json()
        return self.parse_response(body)

    def _render_prompt(self, interface_info: dict, rules_text: str, case_type: str, prompt_template=None) -> str:
        """渲染提示词模板，优先使用传入的 PromptTemplate，否则使用 provider 自带的模板"""
        method = interface_info.get("request_method", "")
        url = interface_info.get("request_url", "")
        headers = json.dumps(interface_info.get("request_headers", {}), ensure_ascii=False, indent=2)
        body_schema = json.dumps(interface_info.get("request_body", {}), ensure_ascii=False, indent=2)
        casetype_desc = self._describe_case_type(case_type)

        # P0-1 修复：新增接口详细信息变量
        api_name = interface_info.get("api_name", "")
        api_desc = interface_info.get("api_desc", "")
        request_params = json.dumps(interface_info.get("request_params", {}), ensure_ascii=False, indent=2)
        param_schema = interface_info.get("param_schema", "")
        body_format = interface_info.get("request_body_format", "")
        request_body = json.dumps(interface_info.get("request_body", {}), ensure_ascii=False, indent=2)
        response_schema = json.dumps(interface_info.get("response_schema", {}), ensure_ascii=False, indent=2)
        error_codes = json.dumps(interface_info.get("error_codes", []), ensure_ascii=False)
        auth_config = json.dumps(interface_info.get("auth_config", {}), ensure_ascii=False, indent=2)

        format_context = dict(
            method=method,
            url=url,
            headers=headers,
            body_schema=body_schema,
            rules_text=rules_text or "（无规则）",
            case_type=case_type,
            casetype_desc=casetype_desc,
            api_name=api_name,
            api_desc=api_desc,
            params=request_params,
            param_schema=param_schema,
            body_format=body_format,
            request_body=request_body,
            response_schema=response_schema,
            error_codes=error_codes,
            auth_config=auth_config,
        )

        # 如果传入了 PromptTemplate 对象，使用其 to_rendered_prompt 方法
        if prompt_template is not None:
            return prompt_template.to_rendered_prompt(format_context)

        return self.provider.prompt_template.format(**format_context)

    @staticmethod
    def _describe_case_type(case_type: str) -> str:
        """将 case_type 映射为中文描述"""
        mapping = {
            "api": "接口测试",
            "connectivity_check": "连通性校验",
            "param_validate": "参数校验",
            "biz_logic": "业务逻辑",
            "error_handle": "异常处理",
            "boundary": "边界值",
            "security": "安全",
            "performance": "性能",
        }
        return mapping.get(case_type, case_type)

    @staticmethod
    def _extract_json(text: str):
        """从 LLM 返回文本中提取 JSON 数组"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except (json.JSONDecodeError, TypeError):
            pass
        # 尝试从 markdown 代码块中提取
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            try:
                return json.loads(match.group(1))
            except (json.JSONDecodeError, TypeError):
                pass
        # 逐段尝试匹配 JSON 数组：找到所有 [...] 候选，从最长的开始尝试
        candidates = []
        bracket_depth = 0
        candidate_start = -1
        for i, ch in enumerate(text):
            if ch == '[':
                if bracket_depth == 0:
                    candidate_start = i
                bracket_depth += 1
            elif ch == ']':
                bracket_depth -= 1
                if bracket_depth == 0 and candidate_start != -1:
                    candidates.append((candidate_start, i + 1))
                    candidate_start = -1
        # 按长度降序尝试（更长的通常包含更多内容，可能是完整数组）
        for start, end in sorted(candidates, key=lambda se: se[1] - se[0], reverse=True):
            try:
                parsed = json.loads(text[start:end])
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                continue
        return None

    def _smart_parse(self, response_data: dict, fallback_path: str) -> list:
        """智能解析：先按 response_cases_path 取值，如果不是 JSON 则提取 JSON"""
        val = self._get_nested(response_data, fallback_path)
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            parsed = self._extract_json(val)
            if isinstance(parsed, list):
                return parsed
            # 可能是单个对象
            if isinstance(parsed, dict):
                return [parsed]
        # 尝试从整个 response_data 中找 list
        if isinstance(response_data, list):
            return response_data
        return []

    def _call_llm(self, prompt: str) -> str:
        """发送 prompt 到 LLM 并返回原始响应文本。
        供 extract_apis_from_document 等文档场景使用。

        Args:
            prompt: 完整的用户提示词

        Returns:
            str: LLM 返回的原始文本

        Raises:
            ValueError: 调用失败
        """
        headers = {"Content-Type": "application/json"}
        if self.provider.api_key:
            headers["Authorization"] = f"Bearer {self.provider.api_key}"

        payload = {
            "model": self.provider.model_name,
            "temperature": self.provider.temperature,
            "max_tokens": self.provider.max_tokens,
            "messages": [
                {"role": "system", "content": self.provider.system_prompt or "你是一个专业的API文档解析助手。"},
                {"role": "user", "content": prompt},
            ],
        }

        resp = requests.request(
            method="POST",
            url=self.provider.endpoint,
            headers=headers,
            json=payload,
            timeout=self.provider.timeout,
            proxies={"http": None, "https": None},
        )
        if resp.status_code >= 400:
            body = resp.text[:500]
            raise ValueError(f"AI 服务调用失败 [HTTP {resp.status_code}]: {body}")

        self.last_raw_response = resp.text
        body = resp.json()
        # OpenAI 兼容格式：choices[0].message.content
        content = self._get_nested(body, "choices.0.message.content")
        if content is None:
            raise ValueError("AI 响应格式异常：无法从 choices[0].message.content 提取内容")
        return content

    def extract_apis_from_document(self, md_content: str, prompt_template=None) -> dict:
        """从 Markdown 文档中提取 API 定义。

        Args:
            md_content: Markdown 格式的文档内容
            prompt_template: 可选的 PromptTemplate 实例，使用其 to_rendered_prompt 渲染

        Returns:
            dict: {"success": bool, "apis": list, "error": str|None,
                   "duration_ms": int, "prompt_full_text": str, "response_raw": str}
        """
        context = {"document_content": md_content}
        import time as _time
        _start = _time.monotonic()
        error = None
        apis = []
        actual_prompt = ""
        raw = ""

        try:
            if prompt_template is not None:
                actual_prompt = prompt_template.to_rendered_prompt(context)
            else:
                actual_prompt = self.DEFAULT_DOCUMENT_EXTRACT_PROMPT.format(**context)

            raw = self._call_llm(actual_prompt)
            parsed = self._extract_json(raw)
            if isinstance(parsed, list):
                apis = parsed
            elif parsed is not None:
                # 单个对象 → 包裹为列表
                apis = [parsed]
            else:
                error = "AI 返回内容未能解析为有效的 API 列表"
        except Exception as e:
            error = str(e)

        _elapsed_ms = int((_time.monotonic() - _start) * 1000)
        self.last_raw_response = raw or ""

        return {
            "success": error is None,
            "apis": apis,
            "error": error,
            "duration_ms": _elapsed_ms,
            "prompt_full_text": actual_prompt,
            "response_raw": self.last_raw_response,
        }

    @staticmethod
    def _get_nested(data: dict, path: str):
        """按点号路径从嵌套字典中取值"""
        current = data
        for seg in path.split("."):
            if seg.isdigit():
                seg = int(seg)
            if isinstance(current, dict):
                current = current.get(seg)
            elif isinstance(current, list) and isinstance(seg, int) and seg < len(current):
                current = current[seg]
            else:
                return None
        return current


class OpenAICompatibleAdapter(BaseAdapter):
    """OpenAI 兼容接口适配器（适用于智谱、DeepSeek 等）"""

    def build_request(self, interface_info: dict, rules_text: str, case_type: str, prompt_template=None) -> dict:
        user_prompt = self._render_prompt(interface_info, rules_text, case_type, prompt_template)
        headers = {"Content-Type": "application/json"}
        if self.provider.api_key:
            headers["Authorization"] = f"Bearer {self.provider.api_key}"
        return {
            "url": self.provider.endpoint,
            "headers": headers,
            "json_body": {
                "model": self.provider.model_name,
                "temperature": self.provider.temperature,
                "max_tokens": self.provider.max_tokens,
                "messages": [
                    {"role": "system", "content": self.provider.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        }

    def parse_response(self, response_data: dict) -> list:
        """解析 OpenAI 兼容响应，支持 reasoning_content 兜底（GLM-4-Air 等推理模型）"""
        cases = self._smart_parse(response_data, self.provider.response_cases_path)
        if cases:
            return cases
        # 兜底：如果 content 为空，尝试从 reasoning_content 提取
        msg = response_data.get("choices", [{}])[0].get("message", {})
        reasoning = msg.get("reasoning_content", "")
        if reasoning:
            return self._smart_parse({"content": reasoning}, "content")
        return []
