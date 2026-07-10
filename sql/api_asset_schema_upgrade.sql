-- API资产管理结构升级（MySQL）
-- 说明：
-- 1) 参数交互字段：required / param_type / sort / param_status
-- 2) 详情补充字段：interface_desc / error_code

ALTER TABLE `test_manager_apiasset`
    ADD COLUMN `required` tinyint(1) NOT NULL DEFAULT 0 COMMENT '参数必填',
    ADD COLUMN `param_type` varchar(30) NOT NULL DEFAULT 'string' COMMENT '参数类型',
    ADD COLUMN `sort` int NOT NULL DEFAULT 0 COMMENT '参数排序',
    ADD COLUMN `param_status` varchar(20) NOT NULL DEFAULT 'enabled' COMMENT '参数启用状态';

ALTER TABLE `test_manager_apiasset`
    ADD COLUMN `interface_desc` text NULL COMMENT '接口描述',
    ADD COLUMN `error_code` json NULL COMMENT '错误码';
