"""场景执行报告相关权限：业务 Project 口径与 Environment.project 一致。"""


def user_can_access_scene_execution_report(user, execution) -> bool:
    """
    允许访问条件：staff；或 execution.environment.project.created_by 为当前用户。
    无环境时仅 staff 可通过（后续生成仍会因缺少项目失败）。
    """
    if getattr(user, "is_staff", False):
        return True
    env = execution.environment
    if env is None:
        return False
    project = env.project
    if project is None:
        return False
    return project.created_by_id == user.id
