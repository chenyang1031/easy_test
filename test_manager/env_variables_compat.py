# -*- coding: utf-8 -*-
"""
环境 variables（JSON 字典）字段的运行时兼容。

编辑页可在字典中写入 __var_descriptions__（变量名 → 说明文案），仅供表单回显；
执行场景、接口测试、变量预览等逻辑必须通过 variables_for_runtime() 剔除该键，
避免进入变量池或污染 {{env.xxx}} 替换。
"""
from __future__ import annotations

import copy
from typing import Any, Dict

# 与前端 environment_form 中使用的键名保持一致
ENV_VAR_DESCRIPTIONS_KEY = "__var_descriptions__"


def variables_for_runtime(variables: Any) -> Dict[str, Any]:
    """
    返回用于变量替换、前置脚本、变量路径预览的环境变量副本。
    旧数据不含元数据键时，行为与原先 deepcopy(env.variables) 一致。
    """
    if not variables:
        return {}
    if not isinstance(variables, dict):
        return {}
    out = copy.deepcopy(variables)
    out.pop(ENV_VAR_DESCRIPTIONS_KEY, None)
    return out
