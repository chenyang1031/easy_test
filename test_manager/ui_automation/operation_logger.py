"""
操作审计日志辅助函数
"""
import logging

logger = logging.getLogger('test_manager.ui_automation')


def log_operation(request, action_type, instance, old_value=None, new_value=None):
    """
    记录操作审计日志

    Args:
        request: HTTP request 对象
        action_type: 操作类型 (create/update/delete/execute)
        instance: 模型实例
        old_value: 旧值 (dict, optional)
        new_value: 新值 (dict, optional)
    """
    from .models import UiOperationRecord

    try:
        model_name = instance.__class__.__name__
        project = None

        # 尝试获取 project
        if hasattr(instance, 'project'):
            project = instance.project
        elif hasattr(instance, 'page') and hasattr(instance.page, 'module'):
            project = instance.page.module.project
        elif hasattr(instance, 'module') and hasattr(instance.module, 'project'):
            project = instance.module.project
        elif hasattr(instance, 'test_case') and hasattr(instance.test_case, 'project'):
            project = instance.test_case.project

        target_name = str(instance) if instance else ''

        UiOperationRecord.objects.create(
            project=project,
            user=request.user if request.user.is_authenticated else None,
            action_type=action_type,
            target_model=model_name,
            target_id=instance.pk or 0,
            target_name=target_name[:200],
            old_value=old_value,
            new_value=new_value,
        )
    except Exception as e:
        # 审计日志记录失败不应影响主业务
        logger.warning(f"操作日志记录失败: {e}")
