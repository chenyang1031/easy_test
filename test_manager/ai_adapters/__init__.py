"""AI 适配器工厂 — 根据供应商类型获取对应的适配器实例"""
from .base import OpenAICompatibleAdapter


ADAPTER_MAP = {
    "openai": OpenAICompatibleAdapter,
    "zhipu": OpenAICompatibleAdapter,
    "deepseek": OpenAICompatibleAdapter,
    # "custom" — 如需自定义格式，在此注册
}


def get_adapter(provider):
    """根据供应商配置获取适配器实例"""
    adapter_cls = ADAPTER_MAP.get(provider.provider_type, OpenAICompatibleAdapter)
    return adapter_cls(provider)
