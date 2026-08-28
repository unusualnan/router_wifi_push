## 1. 配置与数据结构

- [x] 1.1 在 config.yaml 中新增 upload_enabled、cloudflare_worker_url、upload_interval、batch_size 配置项，并在 load_config 中读取
- [x] 1.2 实现 `upload_records(records, url)` 函数：POST JSON 到 Worker，成功返回 True，失败返回 False

## 2. 缓存与上传逻辑

- [x] 2.1 在主循环中实现 records 缓存：每次轮询成功后追加 `{ts, download, upload: 0}` 到列表
- [x] 2.2 实现双触发上传：records 数量 >= batch_size 或距上次上传超过 upload_interval 时调用 upload_records
- [x] 2.3 实现上传成功后清空 records，上传失败时保留 records

## 3. 集成与验证

- [x] 3.1 将上传逻辑集成到主循环，与告警逻辑并行执行
- [x] 3.2 添加上传相关日志：上传成功/失败记录数、下次重试提示
- [x] 3.3 mock 模式下测试：设置 mock_mode + upload_enabled=true，验证缓存和上传逻辑
