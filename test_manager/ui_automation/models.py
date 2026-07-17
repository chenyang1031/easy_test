"""
UI自动化数据模型 - 融合 WHartTest + TestFusion
"""
from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator


# ============================================================
# 常量定义
# ============================================================

LOCATOR_TYPE_CHOICES = [
    ('css', 'CSS Selector'),
    ('xpath', 'XPath'),
    ('text', 'Text'),
    ('role', 'Role'),
    ('label', 'Label'),
    ('placeholder', 'Placeholder'),
    ('testid', 'TestID'),
    ('id', 'ID'),
    ('name', 'Name'),
]

ELEMENT_TYPE_CHOICES = [
    ('input', '输入框'),
    ('button', '按钮'),
    ('link', '链接'),
    ('dropdown', '下拉框'),
    ('checkbox', '复选框'),
    ('radio', '单选框'),
    ('text', '文本'),
    ('image', '图片'),
    ('container', '容器'),
    ('table', '表格'),
    ('form', '表单'),
    ('modal', '弹窗'),
]

VALIDATION_STATUS_CHOICES = [
    ('valid', '有效'),
    ('invalid', '无效'),
    ('unknown', '未知'),
    ('pending', '待验证'),
]

STEP_TYPE_CHOICES = [
    (0, '元素操作'),
    (1, '断言'),
    (2, 'SQL操作'),
    (3, '自定义变量'),
    (4, '条件逻辑'),
    (5, 'Python代码'),
]

EXECUTION_STATUS_CHOICES = [
    (0, '待执行'),
    (1, '执行中'),
    (2, '成功'),
    (3, '失败'),
    (4, '部分成功'),
]

TRIGGER_TYPE_CHOICES = [
    ('manual', '手动'),
    ('scheduled', '定时'),
    ('api', 'API触发'),
]

BROWSER_CHOICES = [
    ('chromium', 'Chromium'),
    ('firefox', 'Firefox'),
    ('webkit', 'WebKit'),
]

CASE_LEVEL_CHOICES = [
    ('P0', 'P0-核心'),
    ('P1', 'P1-重要'),
    ('P2', 'P2-一般'),
    ('P3', 'P3-低'),
]

DATA_TYPE_CHOICES = [
    (0, '字符串'),
    (1, '整数'),
    (2, '列表'),
    (3, '字典'),
]

SCRIPT_TYPE_CHOICES = [
    ('code', '代码'),
    ('low_code', '低代码'),
    ('no_code', '无代码'),
]

TASK_TYPE_CHOICES = [
    ('test_case', '测试用例'),
    ('test_suite', '测试套件'),
]

TRIGGER_SCHEDULE_CHOICES = [
    ('cron', 'Cron表达式'),
    ('interval', '固定间隔'),
    ('once', '单次执行'),
]

AI_STATUS_CHOICES = [
    ('pending', '待执行'),
    ('running', '执行中'),
    ('passed', '通过'),
    ('failed', '失败'),
    ('stopped', '已停止'),
]


# ============================================================
# 层级组织
# ============================================================

class UiModule(models.Model):
    """UI模块树（5级嵌套，来自WHartTest）"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_modules', verbose_name='项目'
    )
    name = models.CharField(max_length=100, verbose_name='模块名称')
    parent = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='父模块'
    )
    level = models.PositiveSmallIntegerField(
        default=1, validators=[MinValueValidator(1), MaxValueValidator(5)],
        verbose_name='层级'
    )
    order = models.IntegerField(default=0, verbose_name='排序')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_module'
        verbose_name = 'UI模块'
        verbose_name_plural = verbose_name
        ordering = ['order', 'name']

    def __str__(self):
        return self.name


class UiPage(models.Model):
    """页面管理"""
    module = models.ForeignKey(
        UiModule, on_delete=models.CASCADE,
        related_name='pages', verbose_name='模块'
    )
    name = models.CharField(max_length=200, verbose_name='页面名称')
    url = models.URLField(blank=True, default='', verbose_name='页面URL')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_page'
        verbose_name = 'UI页面'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class UiElement(models.Model):
    """UI元素（合并WHartTest的9定位策略 + TestFusion的12类型 + 验证状态）"""
    page = models.ForeignKey(
        UiPage, on_delete=models.CASCADE,
        related_name='elements', verbose_name='页面'
    )
    name = models.CharField(max_length=200, verbose_name='元素名称')
    element_type = models.CharField(
        max_length=20, choices=ELEMENT_TYPE_CHOICES,
        default='input', verbose_name='元素类型'
    )

    # 主定位器
    locator_type = models.CharField(
        max_length=20, choices=LOCATOR_TYPE_CHOICES, verbose_name='定位类型'
    )
    locator_value = models.CharField(max_length=500, verbose_name='定位值')
    locator_index = models.PositiveSmallIntegerField(
        default=0, verbose_name='定位索引'
    )

    # 备用定位器2
    locator_type_2 = models.CharField(
        max_length=20, choices=LOCATOR_TYPE_CHOICES,
        blank=True, default='', verbose_name='备用定位类型2'
    )
    locator_value_2 = models.CharField(
        max_length=500, blank=True, default='', verbose_name='备用定位值2'
    )
    locator_index_2 = models.PositiveSmallIntegerField(
        default=0, verbose_name='备用定位索引2'
    )

    # 备用定位器3
    locator_type_3 = models.CharField(
        max_length=20, choices=LOCATOR_TYPE_CHOICES,
        blank=True, default='', verbose_name='备用定位类型3'
    )
    locator_value_3 = models.CharField(
        max_length=500, blank=True, default='', verbose_name='备用定位值3'
    )
    locator_index_3 = models.PositiveSmallIntegerField(
        default=0, verbose_name='备用定位索引3'
    )

    # iframe支持（WHartTest）
    is_iframe = models.BooleanField(default=False, verbose_name='是否iframe内')
    iframe_locator = models.CharField(
        max_length=500, blank=True, default='', verbose_name='iframe定位器'
    )

    # 元素属性
    wait_time = models.PositiveSmallIntegerField(
        default=5, verbose_name='等待时间(秒)'
    )
    is_visible = models.BooleanField(default=True, verbose_name='是否可见')
    is_enabled = models.BooleanField(default=True, verbose_name='是否可用')
    force_action = models.BooleanField(
        default=False, verbose_name='强制操作（忽略可见性）'
    )
    is_unique = models.BooleanField(default=False, verbose_name='是否唯一')

    # 验证状态（TestFusion）
    validation_status = models.CharField(
        max_length=20, choices=VALIDATION_STATUS_CHOICES,
        default='unknown', verbose_name='验证状态'
    )
    validation_message = models.TextField(
        blank=True, default='', verbose_name='验证信息'
    )
    last_validated = models.DateTimeField(
        null=True, blank=True, verbose_name='最后验证时间'
    )
    usage_count = models.PositiveIntegerField(default=0, verbose_name='使用次数')

    # 层级
    parent_element = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='child_elements', verbose_name='父元素'
    )
    component = models.CharField(
        max_length=100, blank=True, default='', verbose_name='组件名'
    )
    page_name = models.CharField(
        max_length=100, blank=True, default='', verbose_name='页面标识'
    )
    description = models.TextField(blank=True, default='', verbose_name='描述')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_element'
        verbose_name = 'UI元素'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.element_type})"

    def get_all_locators(self):
        """返回所有有效定位器列表"""
        locators = [{'type': self.locator_type, 'value': self.locator_value, 'index': self.locator_index}]
        if self.locator_type_2 and self.locator_value_2:
            locators.append({'type': self.locator_type_2, 'value': self.locator_value_2, 'index': self.locator_index_2})
        if self.locator_type_3 and self.locator_value_3:
            locators.append({'type': self.locator_type_3, 'value': self.locator_value_3, 'index': self.locator_index_3})
        return locators

    def increment_usage_count(self):
        self.usage_count += 1
        self.save(update_fields=['usage_count'])


class UiElementGroup(models.Model):
    """元素分组（TestFusion）"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_element_groups', verbose_name='项目'
    )
    name = models.CharField(max_length=100, verbose_name='分组名称')
    parent_group = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True,
        related_name='children', verbose_name='父分组'
    )
    description = models.TextField(blank=True, default='', verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_element_group'
        verbose_name = 'UI元素分组'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


# ============================================================
# 操作步骤
# ============================================================

class UiPageSteps(models.Model):
    """可复用页面操作步骤（WHartTest）"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_page_steps', verbose_name='项目'
    )
    page = models.ForeignKey(
        UiPage, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='page_steps', verbose_name='页面'
    )
    module = models.ForeignKey(
        UiModule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='page_steps', verbose_name='模块'
    )
    name = models.CharField(max_length=200, verbose_name='步骤名称')
    status = models.CharField(
        max_length=20, default='pending',
        choices=[('pending', '待处理'), ('running', '执行中'), ('success', '成功'), ('failed', '失败')],
        verbose_name='状态'
    )
    flow_data = models.JSONField(
        null=True, blank=True, verbose_name='流程图数据'
    )
    description = models.TextField(blank=True, default='', verbose_name='描述')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_page_steps'
        verbose_name = 'UI页面步骤'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class UiPageStepsDetailed(models.Model):
    """步骤明细（6种操作类型，WHartTest）"""
    page_step = models.ForeignKey(
        UiPageSteps, on_delete=models.CASCADE,
        related_name='details', verbose_name='页面步骤'
    )
    step_type = models.SmallIntegerField(
        choices=STEP_TYPE_CHOICES, default=0, verbose_name='步骤类型'
    )
    element = models.ForeignKey(
        UiElement, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='step_details', verbose_name='元素'
    )
    step_sort = models.IntegerField(default=0, verbose_name='排序')
    ope_key = models.CharField(
        max_length=50, blank=True, default='', verbose_name='操作键'
    )
    ope_value = models.TextField(blank=True, default='', verbose_name='操作值')
    sql_execute = models.TextField(blank=True, default='', verbose_name='SQL语句')
    custom = models.JSONField(
        null=True, blank=True, verbose_name='自定义变量'
    )
    condition_value = models.JSONField(
        null=True, blank=True, verbose_name='条件值'
    )
    func = models.TextField(blank=True, default='', verbose_name='Python函数')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_page_steps_detailed'
        verbose_name = 'UI步骤明细'
        verbose_name_plural = verbose_name
        ordering = ['step_sort']

    def __str__(self):
        return f"{self.page_step.name} - 步骤{self.step_sort}"


# ============================================================
# 测试用例
# ============================================================

class UiTestCase(models.Model):
    """UI测试用例（合并两者）"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_test_cases', verbose_name='项目'
    )
    module = models.ForeignKey(
        UiModule, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='test_cases', verbose_name='模块'
    )
    name = models.CharField(max_length=200, verbose_name='用例名称')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    level = models.CharField(
        max_length=5, choices=CASE_LEVEL_CHOICES,
        default='P2', verbose_name='优先级'
    )
    status = models.CharField(
        max_length=20, default='pending',
        choices=[('pending', '待处理'), ('running', '执行中'), ('success', '成功'), ('failed', '失败')],
        verbose_name='状态'
    )

    # 前置条件
    front_sql = models.TextField(blank=True, default='', verbose_name='前置SQL')
    front_custom = models.JSONField(
        null=True, blank=True, verbose_name='前置自定义变量'
    )
    # 后置条件
    posterior_sql = models.TextField(blank=True, default='', verbose_name='后置SQL')

    # 参数化（数据驱动）
    parametrize = models.JSONField(
        null=True, blank=True, verbose_name='参数化数据'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_test_case'
        verbose_name = 'UI测试用例'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"[{self.level}] {self.name}"


class UiCaseStepsDetailed(models.Model):
    """用例步骤明细"""
    test_case = models.ForeignKey(
        UiTestCase, on_delete=models.CASCADE,
        related_name='case_steps', verbose_name='测试用例'
    )
    page_step = models.ForeignKey(
        UiPageSteps, on_delete=models.CASCADE,
        related_name='case_references', verbose_name='页面步骤'
    )
    case_sort = models.IntegerField(default=0, verbose_name='排序')
    case_data = models.JSONField(
        null=True, blank=True, verbose_name='用例级数据覆盖'
    )
    switch_step_open_url = models.BooleanField(
        default=False, verbose_name='步骤切换时打开URL'
    )
    error_retry = models.PositiveSmallIntegerField(
        default=0, verbose_name='失败重试次数'
    )
    status = models.CharField(
        max_length=20, default='pending',
        choices=[('pending', '待执行'), ('running', '执行中'), ('success', '成功'), ('failed', '失败')],
        verbose_name='状态'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_case_steps_detailed'
        verbose_name = 'UI用例步骤明细'
        verbose_name_plural = verbose_name
        ordering = ['case_sort']

    def __str__(self):
        return f"{self.test_case.name} - 步骤{self.case_sort}"


# ============================================================
# 脚本管理（TestFusion）
# ============================================================

class UiTestScript(models.Model):
    """测试脚本"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_scripts', verbose_name='项目'
    )
    name = models.CharField(max_length=200, verbose_name='脚本名称')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    script_type = models.CharField(
        max_length=20, choices=SCRIPT_TYPE_CHOICES,
        default='code', verbose_name='脚本类型'
    )
    content = models.TextField(blank=True, default='', verbose_name='脚本内容')
    language = models.CharField(
        max_length=20, default='python',
        choices=[('python', 'Python'), ('javascript', 'JavaScript')],
        verbose_name='语言'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_test_script'
        verbose_name = 'UI测试脚本'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class UiScriptStep(models.Model):
    """脚本步骤"""
    script = models.ForeignKey(
        UiTestScript, on_delete=models.CASCADE,
        related_name='steps', verbose_name='脚本'
    )
    step_order = models.IntegerField(default=0, verbose_name='步骤序号')
    action_type = models.CharField(max_length=50, verbose_name='动作类型')
    action_params = models.JSONField(
        null=True, blank=True, verbose_name='动作参数'
    )
    expected_result = models.TextField(
        blank=True, default='', verbose_name='预期结果'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_script_step'
        verbose_name = 'UI脚本步骤'
        verbose_name_plural = verbose_name
        ordering = ['step_order']

    def __str__(self):
        return f"{self.script.name} - 步骤{self.step_order}"


# ============================================================
# Page Object Model（TestFusion）
# ============================================================

class UiPageObject(models.Model):
    """页面对象"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_page_objects', verbose_name='项目'
    )
    name = models.CharField(max_length=200, verbose_name='页面对象名称')
    url = models.URLField(blank=True, default='', verbose_name='页面URL')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    generated_code_js = models.TextField(
        blank=True, default='', verbose_name='生成的JS代码'
    )
    generated_code_python = models.TextField(
        blank=True, default='', verbose_name='生成的Python代码'
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_page_object'
        verbose_name = 'UI页面对象'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return self.name


class UiPageObjectElement(models.Model):
    """页面对象元素绑定"""
    page_object = models.ForeignKey(
        UiPageObject, on_delete=models.CASCADE,
        related_name='po_elements', verbose_name='页面对象'
    )
    element = models.ForeignKey(
        UiElement, on_delete=models.CASCADE,
        related_name='po_references', verbose_name='元素'
    )
    method_name = models.CharField(
        max_length=100, verbose_name='方法名'
    )
    is_property = models.BooleanField(
        default=True, verbose_name='是否为属性'
    )

    class Meta:
        db_table = 'ui_page_object_element'
        verbose_name = 'UI页面对象元素'
        verbose_name_plural = verbose_name
        unique_together = [('page_object', 'element')]

    def __str__(self):
        return f"{self.page_object.name}.{self.method_name}"


# ============================================================
# 执行记录
# ============================================================

class UiBatchExecutionRecord(models.Model):
    """批量执行记录（WHartTest）"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_batch_records', verbose_name='项目'
    )
    name = models.CharField(max_length=200, verbose_name='批次名称')
    total_cases = models.PositiveIntegerField(default=0, verbose_name='总用例数')
    passed_cases = models.PositiveIntegerField(default=0, verbose_name='通过数')
    failed_cases = models.PositiveIntegerField(default=0, verbose_name='失败数')
    status = models.SmallIntegerField(
        choices=EXECUTION_STATUS_CHOICES, default=0, verbose_name='状态'
    )
    trigger_type = models.CharField(
        max_length=20, choices=TRIGGER_TYPE_CHOICES,
        default='manual', verbose_name='触发方式'
    )
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(default=0, verbose_name='耗时(秒)')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ui_batch_execution_record'
        verbose_name = 'UI批量执行记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} ({self.get_status_display()})"


class UiExecutionRecord(models.Model):
    """单条执行记录"""
    batch = models.ForeignKey(
        UiBatchExecutionRecord, on_delete=models.CASCADE,
        related_name='execution_records', verbose_name='批次'
    )
    test_case = models.ForeignKey(
        UiTestCase, on_delete=models.CASCADE,
        related_name='execution_records', verbose_name='测试用例'
    )
    executor = models.CharField(
        max_length=100, blank=True, default='', verbose_name='执行者'
    )
    status = models.SmallIntegerField(
        choices=EXECUTION_STATUS_CHOICES, default=0, verbose_name='状态'
    )
    trigger_type = models.CharField(
        max_length=20, choices=TRIGGER_TYPE_CHOICES,
        default='manual', verbose_name='触发方式'
    )
    step_results = models.JSONField(
        null=True, blank=True, verbose_name='步骤结果'
    )
    screenshots = models.JSONField(
        null=True, blank=True, verbose_name='截图列表'
    )
    video_path = models.CharField(
        max_length=500, blank=True, default='', verbose_name='视频路径'
    )
    trace_path = models.CharField(
        max_length=500, blank=True, default='', verbose_name='Trace路径'
    )
    trace_data = models.JSONField(
        null=True, blank=True, verbose_name='Trace数据'
    )
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(default=0, verbose_name='耗时(秒)')
    log = models.TextField(blank=True, default='', verbose_name='执行日志')
    error_message = models.TextField(blank=True, default='', verbose_name='错误信息')

    class Meta:
        db_table = 'ui_execution_record'
        verbose_name = 'UI执行记录'
        verbose_name_plural = verbose_name
        ordering = ['-start_time']

    def __str__(self):
        return f"{self.test_case.name} ({self.get_status_display()})"


# ============================================================
# 环境配置（WHartTest增强版）
# ============================================================

class UiEnvironmentConfig(models.Model):
    """执行环境配置"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_environments', verbose_name='项目'
    )
    name = models.CharField(max_length=100, verbose_name='环境名称')
    base_url = models.URLField(blank=True, default='', verbose_name='基础URL')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')

    # 浏览器配置
    browser = models.CharField(
        max_length=20, choices=BROWSER_CHOICES,
        default='chromium', verbose_name='浏览器'
    )
    headless = models.BooleanField(default=True, verbose_name='无头模式')
    viewport_width = models.PositiveIntegerField(default=1920, verbose_name='视口宽度')
    viewport_height = models.PositiveIntegerField(default=1080, verbose_name='视口高度')
    timeout = models.PositiveIntegerField(default=30, verbose_name='超时(秒)')

    # 数据库集成（WHartTest）
    db_status = models.BooleanField(default=False, verbose_name='启用数据库')
    db_type = models.CharField(
        max_length=20, default='mysql',
        choices=[('mysql', 'MySQL'), ('db2', 'DB2')],
        verbose_name='数据库类型'
    )
    mysql_config = models.JSONField(
        null=True, blank=True, verbose_name='MySQL配置'
    )
    db2_config = models.JSONField(
        null=True, blank=True, verbose_name='DB2配置'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_environment_config'
        verbose_name = 'UI环境配置'
        verbose_name_plural = verbose_name
        ordering = ['-is_default', 'name']

    def __str__(self):
        return f"{self.name} ({self.browser})"


# ============================================================
# 公共数据（WHartTest）
# ============================================================

class UiPublicData(models.Model):
    """共享变量"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_public_data', verbose_name='项目'
    )
    name = models.CharField(max_length=100, verbose_name='变量名称')
    data_type = models.SmallIntegerField(
        choices=DATA_TYPE_CHOICES, default=0, verbose_name='数据类型'
    )
    key = models.CharField(max_length=100, verbose_name='键名')
    value = models.TextField(blank=True, default='', verbose_name='值')
    is_enabled = models.BooleanField(default=True, verbose_name='是否启用')
    description = models.TextField(blank=True, default='', verbose_name='描述')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_public_data'
        verbose_name = 'UI公共数据'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return f"{self.key} = {self.value[:50]}"


# ============================================================
# 执行器管理
# ============================================================

class UiActuator(models.Model):
    """执行器注册"""
    name = models.CharField(max_length=100, verbose_name='执行器名称')
    host = models.CharField(max_length=200, verbose_name='主机地址')
    port = models.PositiveIntegerField(default=8080, verbose_name='端口')
    status = models.CharField(
        max_length=20, default='offline',
        choices=[('online', '在线'), ('offline', '离线')],
        verbose_name='状态'
    )
    browser_capabilities = models.JSONField(
        null=True, blank=True, verbose_name='浏览器能力'
    )
    last_heartbeat = models.DateTimeField(
        null=True, blank=True, verbose_name='最后心跳'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_actuator'
        verbose_name = 'UI执行器'
        verbose_name_plural = verbose_name
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.status})"


# ============================================================
# 定时任务（TestFusion增强版）
# ============================================================

class UiScheduledTask(models.Model):
    """UI定时任务"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_scheduled_tasks', verbose_name='项目'
    )
    name = models.CharField(max_length=200, verbose_name='任务名称')
    task_type = models.CharField(
        max_length=20, choices=TASK_TYPE_CHOICES,
        default='test_case', verbose_name='任务类型'
    )
    trigger_type = models.CharField(
        max_length=20, choices=TRIGGER_SCHEDULE_CHOICES,
        default='cron', verbose_name='触发类型'
    )
    cron_expression = models.CharField(
        max_length=100, blank=True, default='', verbose_name='Cron表达式'
    )
    interval_seconds = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='间隔秒数'
    )
    run_at = models.DateTimeField(null=True, blank=True, verbose_name='执行时间')

    test_cases = models.ManyToManyField(
        UiTestCase, blank=True, related_name='scheduled_tasks',
        verbose_name='测试用例'
    )
    environment = models.ForeignKey(
        UiEnvironmentConfig, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='scheduled_tasks', verbose_name='环境配置'
    )
    actuator = models.ForeignKey(
        UiActuator, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='scheduled_tasks', verbose_name='执行器'
    )
    engine = models.CharField(
        max_length=20, default='playwright', verbose_name='执行引擎'
    )
    browser = models.CharField(
        max_length=20, choices=BROWSER_CHOICES,
        default='chromium', verbose_name='浏览器'
    )
    headless = models.BooleanField(default=True, verbose_name='无头模式')

    # 通知配置
    notify_on_success = models.BooleanField(default=False, verbose_name='成功时通知')
    notify_on_failure = models.BooleanField(default=True, verbose_name='失败时通知')
    notify_email = models.JSONField(
        null=True, blank=True, verbose_name='邮件通知配置'
    )
    notify_webhook = models.JSONField(
        null=True, blank=True, verbose_name='Webhook通知配置'
    )

    # 统计
    total_runs = models.PositiveIntegerField(default=0, verbose_name='总执行次数')
    successful_runs = models.PositiveIntegerField(default=0, verbose_name='成功次数')
    failed_runs = models.PositiveIntegerField(default=0, verbose_name='失败次数')
    last_run_at = models.DateTimeField(null=True, blank=True, verbose_name='最后执行时间')
    next_run_at = models.DateTimeField(null=True, blank=True, verbose_name='下次执行时间')
    is_active = models.BooleanField(default=True, verbose_name='是否启用')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_scheduled_task'
        verbose_name = 'UI定时任务'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class UiNotificationLog(models.Model):
    """通知日志"""
    task = models.ForeignKey(
        UiScheduledTask, on_delete=models.CASCADE,
        related_name='notification_logs', verbose_name='任务'
    )
    trigger_type = models.CharField(
        max_length=20,
        choices=[('success', '成功'), ('failure', '失败'), ('error', '错误'), ('timeout', '超时')],
        verbose_name='触发类型'
    )
    channel = models.CharField(
        max_length=20,
        choices=[('email', '邮件'), ('webhook', 'Webhook')],
        verbose_name='通知渠道'
    )
    recipient = models.CharField(max_length=200, verbose_name='接收者')
    status = models.CharField(
        max_length=20,
        choices=[('sent', '已发送'), ('failed', '失败'), ('retry', '重试')],
        default='sent', verbose_name='状态'
    )
    retry_count = models.PositiveSmallIntegerField(default=0, verbose_name='重试次数')
    content = models.TextField(blank=True, default='', verbose_name='通知内容')
    error_message = models.TextField(blank=True, default='', verbose_name='错误信息')
    sent_at = models.DateTimeField(auto_now_add=True, verbose_name='发送时间')

    class Meta:
        db_table = 'ui_notification_log'
        verbose_name = 'UI通知日志'
        verbose_name_plural = verbose_name
        ordering = ['-sent_at']

    def __str__(self):
        return f"{self.task.name} - {self.trigger_type} - {self.channel}"


# ============================================================
# AI浏览器代理（TestFusion）
# ============================================================

class UiAICase(models.Model):
    """AI测试用例"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_ai_cases', verbose_name='项目'
    )
    name = models.CharField(max_length=200, verbose_name='用例名称')
    task_description = models.TextField(verbose_name='任务描述（自然语言）')
    tags = models.JSONField(null=True, blank=True, verbose_name='标签')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ui_ai_case'
        verbose_name = 'UI AI用例'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class UiAIExecutionRecord(models.Model):
    """AI执行记录"""
    ai_case = models.ForeignKey(
        UiAICase, on_delete=models.CASCADE,
        related_name='execution_records', verbose_name='AI用例'
    )
    status = models.CharField(
        max_length=20, choices=AI_STATUS_CHOICES,
        default='pending', verbose_name='状态'
    )
    planned_tasks = models.JSONField(
        null=True, blank=True, verbose_name='计划任务'
    )
    steps_completed = models.JSONField(
        null=True, blank=True, verbose_name='已完成步骤'
    )
    screenshots_sequence = models.JSONField(
        null=True, blank=True, verbose_name='截图序列'
    )
    gif_path = models.CharField(
        max_length=500, blank=True, default='', verbose_name='GIF路径'
    )
    logs = models.TextField(blank=True, default='', verbose_name='执行日志')
    token_cost = models.FloatField(default=0, verbose_name='Token消耗')
    start_time = models.DateTimeField(null=True, blank=True, verbose_name='开始时间')
    end_time = models.DateTimeField(null=True, blank=True, verbose_name='结束时间')
    duration = models.FloatField(default=0, verbose_name='耗时(秒)')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='创建者'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ui_ai_execution_record'
        verbose_name = 'UI AI执行记录'
        verbose_name_plural = verbose_name
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.ai_case.name} ({self.status})"


# ============================================================
# 操作审计（TestFusion）
# ============================================================

class UiOperationRecord(models.Model):
    """操作审计日志"""
    project = models.ForeignKey(
        'test_manager.Project', on_delete=models.CASCADE,
        related_name='ui_operation_records', verbose_name='项目'
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True,
        verbose_name='操作者'
    )
    action_type = models.CharField(
        max_length=20,
        choices=[('create', '创建'), ('update', '更新'), ('delete', '删除'), ('execute', '执行')],
        verbose_name='操作类型'
    )
    target_model = models.CharField(max_length=50, verbose_name='目标模型')
    target_id = models.PositiveIntegerField(verbose_name='目标ID')
    target_name = models.CharField(
        max_length=200, blank=True, default='', verbose_name='目标名称'
    )
    old_value = models.JSONField(null=True, blank=True, verbose_name='旧值')
    new_value = models.JSONField(null=True, blank=True, verbose_name='新值')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='操作时间')

    class Meta:
        db_table = 'ui_operation_record'
        verbose_name = 'UI操作记录'
        verbose_name_plural = verbose_name
        ordering = ['-timestamp']

    def __str__(self):
        return f"{self.user} {self.action_type} {self.target_model}#{self.target_id}"
