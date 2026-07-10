# 回放导入：GoReplay 与 HAR

## 支持的文件

| 类型 | 扩展名 | 说明 |
|------|--------|------|
| GoReplay | `.gor`、`.gor.gz` | 与原有行为一致 |
| HAR | `.har` | Fiddler、Chrome 等导出的 HTTP Archive（JSON） |
| HAR（无扩展名） | 上传时 Content-Type 为 `application/json` | 服务端按 HAR 解析 |

不支持：SAZ、ZIP、原始 RAW 等非 HAR 格式。

## Fiddler 导出步骤（示例）

1. 在 Fiddler 中选中需要导入的会话（建议先过滤无关流量）。
2. **File → Export Sessions → HTTP Archive v1.2**，保存为 `.har`。
3. 在平台「回放导入」中上传该 `.har`，先 **解析预览**，再 **确认导入**。

## HTTPS

仅处理已解密的明文 HTTP 会话。`CONNECT` 隧道请求会被跳过。

## 编码

部分工具（含部分 Fiddler 导出）会在文件头写入 **UTF-8 BOM**；解析器已按 `utf-8-sig` 处理，无需手动去除。

## 限制

- 单次解析最多 **500** 条请求（与 `.gor` 一致），避免超大文件占用过多内存。
- 非 JSON 的响应体在导入确认时仍按原有规则处理（大段非 JSON 不落断言基线等）。

## 单元测试

```bash
python manage.py test test_manager.test_har_parser
```

示例 HAR 样例：`test_manager/fixtures/replay_sample.har`。
