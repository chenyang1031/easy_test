"""
文档格式转换工具 — 将 .docx 转换为 Markdown，支持统一入口。

依赖：
    mammoth>=1.6.0
    python-docx>=1.1.0
"""
import os
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def convert_docx_to_md(file_path: str) -> str:
    """使用 mammoth 将 .docx 文件转换为 Markdown 文本。

    Args:
        file_path: .docx 文件的绝对路径

    Returns:
        str: 转换后的 Markdown 文本

    Raises:
        FileNotFoundError: 文件不存在
        ValueError: 转换失败（依赖缺失或格式错误）
    """
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    try:
        import mammoth
    except ImportError:
        raise ValueError(
            "缺少 mammoth 依赖，请执行: pip install mammoth"
        )

    try:
        with open(file_path, "rb") as f:
            result = mammoth.convert_to_markdown(f)
            if result.value:
                return result.value.strip()
            if result.messages:
                logger.warning("mammoth 转换告警: %s", result.messages)
            return ""
    except Exception as e:
        raise ValueError(f"docx 转 markdown 失败: {e}")


def convert_to_md(file_path: str, file_type: str) -> str:
    """统一入口：根据文件类型选择转换方式。

    Args:
        file_path: 文件绝对路径
        file_type: "docx" 或 "md"

    Returns:
        str: Markdown 文本内容
    """
    file_type = file_type.lower()
    if file_type == "docx":
        return convert_docx_to_md(file_path)
    elif file_type == "md":
        if not os.path.isfile(file_path):
            raise FileNotFoundError(f"文件不存在: {file_path}")
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    else:
        raise ValueError(f"不支持的文件类型: {file_type}，仅支持 docx / md")


def save_converted_md(md_content: str, record_id: int) -> str:
    """将 Markdown 内容写入 media 目录，返回相对路径。

    Args:
        md_content: Markdown 文本内容
        record_id: DocumentGenRecord 的 ID（用于文件名）

    Returns:
        str: 相对路径（相对于 MEDIA_ROOT），如 "document_gen/converted/{record_id}.md"

    Raises:
        OSError: 写入失败
    """
    relative_dir = "document_gen/converted"
    absolute_dir = os.path.join(settings.MEDIA_ROOT, relative_dir)
    os.makedirs(absolute_dir, exist_ok=True)

    filename = f"{record_id}.md"
    absolute_path = os.path.join(absolute_dir, filename)

    with open(absolute_path, "w", encoding="utf-8") as f:
        f.write(md_content)

    relative_path = f"{relative_dir}/{filename}"
    logger.info("Markdown 已保存: %s", relative_path)
    return relative_path
