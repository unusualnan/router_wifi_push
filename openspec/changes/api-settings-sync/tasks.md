## 1. API 设置拉取

- [x] 1.1 实现 `fetch_api_settings(base_url)` 函数：GET `{base_url}/api/settings`，超时 5 秒，成功返回 `dict`，失败返回 `None`。验证：mock requests 测试成功/超时/非200 三种场景
- [x] 1.2 实现 `merge_settings(local_config, api_settings)` 函数：用 API 返回的 `download_threshold_mbps` 和 `poll_interval` 覆盖本地值，返回新 dict。验证：单元测试覆盖 API 有值/API 为 None 两种场景

## 2. 启动流程集成

- [x] 2.1 在 `main()` 中，`load_config()` 之后、`login()` 之前插入 API 拉取逻辑：有 `cloudflare_worker_url` 时调用 `fetch_api_settings` + `merge_settings`，无则跳过。验证：mock 模式下运行脚本，确认日志输出正确
- [x] 2.2 添加启动日志：API 拉取成功时打印覆盖的值，失败时打印 warning，未配置时打印跳过信息
- [x] 2.3 修改 `upload_records()` 中的 URL 拼接：从 `cloudflare_worker_url` 拼接 `/api/upload`（原 config 中存的是完整路径，现改为基础 URL）

## 3. 验证

- [ ] 3.1 mock 模式 + `cloudflare_worker_url` 配置：启动时确认尝试拉取 API 并回退到本地配置（API 不可达场景）
- [ ] 3.2 mock 模式 + `cloudflare_worker_url` 未配置：启动时确认跳过 API 拉取，直接使用本地配置
