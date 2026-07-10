-- 测试场景编排模块建表 SQL（MySQL 8+）
-- 与 Django ORM 模型保持一致，不改动现有 API 资产表结构

CREATE TABLE IF NOT EXISTS `test_scene` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `name` varchar(150) NOT NULL COMMENT '场景名称',
  `description` longtext NOT NULL COMMENT '场景描述',
  `variables` json NOT NULL COMMENT '场景变量池',
  `runtime_config` json NOT NULL COMMENT '运行配置',
  `is_active` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用',
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  `updated_at` datetime(6) NOT NULL COMMENT '更新时间',
  `created_by_id` int NOT NULL COMMENT '创建人',
  `project_id` bigint NOT NULL COMMENT '所属API项目',
  PRIMARY KEY (`id`),
  KEY `test_scene_proj_active_idx` (`project_id`, `is_active`),
  KEY `test_scene_proj_update_idx` (`project_id`, `updated_at`),
  KEY `test_scene_created_by_id_idx` (`created_by_id`),
  CONSTRAINT `test_scene_created_by_id_fk` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`) ON DELETE CASCADE,
  CONSTRAINT `test_scene_project_id_fk` FOREIGN KEY (`project_id`) REFERENCES `test_manager_apiproject` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测试场景主表';


CREATE TABLE IF NOT EXISTS `test_scene_node` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `node_key` varchar(80) NOT NULL COMMENT '节点标识',
  `name` varchar(150) NOT NULL COMMENT '节点名称',
  `description` longtext NOT NULL COMMENT '节点描述',
  `request_headers` json NOT NULL COMMENT '请求头覆盖',
  `request_params` json NOT NULL COMMENT '请求参数覆盖',
  `request_body` json NOT NULL COMMENT '请求体覆盖',
  `assert_rules` json NOT NULL COMMENT '断言规则',
  `extract_rules` json NOT NULL COMMENT '提取规则',
  `expected_status_code` int unsigned NOT NULL DEFAULT '200' COMMENT '预期状态码',
  `timeout` int unsigned DEFAULT NULL COMMENT '超时时间(秒)',
  `on_failed` varchar(20) NOT NULL DEFAULT 'stop' COMMENT '失败策略',
  `sort` int NOT NULL DEFAULT '0' COMMENT '排序',
  `is_enabled` tinyint(1) NOT NULL DEFAULT '1' COMMENT '是否启用',
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  `updated_at` datetime(6) NOT NULL COMMENT '更新时间',
  `api_asset_id` bigint DEFAULT NULL COMMENT '关联API资产',
  `scene_id` bigint NOT NULL COMMENT '所属场景',
  PRIMARY KEY (`id`),
  UNIQUE KEY `test_scene_node_scene_node_key_uniq` (`scene_id`, `node_key`),
  KEY `test_scene_node_sort_idx` (`scene_id`, `sort`),
  KEY `test_scene_node_enable_idx` (`scene_id`, `is_enabled`),
  KEY `test_scene_node_api_asset_id_idx` (`api_asset_id`),
  CONSTRAINT `test_scene_node_api_asset_id_fk` FOREIGN KEY (`api_asset_id`) REFERENCES `test_manager_apiasset` (`id`) ON DELETE SET NULL,
  CONSTRAINT `test_scene_node_scene_id_fk` FOREIGN KEY (`scene_id`) REFERENCES `test_scene` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测试场景节点表';


CREATE TABLE IF NOT EXISTS `test_scene_execution` (
  `id` bigint NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `run_mode` varchar(20) NOT NULL DEFAULT 'all' COMMENT '执行模式(all/single)',
  `status` varchar(20) NOT NULL DEFAULT 'running' COMMENT '执行状态',
  `total_nodes` int unsigned NOT NULL DEFAULT '0' COMMENT '总节点数',
  `passed_nodes` int unsigned NOT NULL DEFAULT '0' COMMENT '成功节点数',
  `failed_nodes` int unsigned NOT NULL DEFAULT '0' COMMENT '失败节点数',
  `skipped_nodes` int unsigned NOT NULL DEFAULT '0' COMMENT '跳过节点数',
  `duration_ms` int unsigned NOT NULL DEFAULT '0' COMMENT '执行耗时毫秒',
  `summary` json NOT NULL COMMENT '执行汇总',
  `node_results` json NOT NULL COMMENT '节点执行结果',
  `error_message` longtext NOT NULL COMMENT '错误信息',
  `started_at` datetime(6) NOT NULL COMMENT '开始时间',
  `finished_at` datetime(6) DEFAULT NULL COMMENT '结束时间',
  `created_at` datetime(6) NOT NULL COMMENT '创建时间',
  `updated_at` datetime(6) NOT NULL COMMENT '更新时间',
  `created_by_id` int DEFAULT NULL COMMENT '执行人',
  `scene_id` bigint NOT NULL COMMENT '场景',
  `target_node_id` bigint DEFAULT NULL COMMENT '目标节点',
  PRIMARY KEY (`id`),
  KEY `test_scene_exec_scene_idx` (`scene_id`, `created_at`),
  KEY `test_scene_exec_status_idx` (`status`, `created_at`),
  KEY `test_scene_exec_created_by_id_idx` (`created_by_id`),
  KEY `test_scene_exec_target_node_id_idx` (`target_node_id`),
  CONSTRAINT `test_scene_exec_created_by_id_fk` FOREIGN KEY (`created_by_id`) REFERENCES `auth_user` (`id`) ON DELETE SET NULL,
  CONSTRAINT `test_scene_exec_scene_id_fk` FOREIGN KEY (`scene_id`) REFERENCES `test_scene` (`id`) ON DELETE CASCADE,
  CONSTRAINT `test_scene_exec_target_node_id_fk` FOREIGN KEY (`target_node_id`) REFERENCES `test_scene_node` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='测试场景执行记录表';
