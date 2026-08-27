## Purpose

封装与 MiWiFi 路由器的 HTTP API 交互，提供登录认证、token 管理和设备列表获取能力。

## ADDED Requirements

### Requirement: 自动检测加密方式

系统 SHALL 在登录前调用 `init_info` 接口获取 `newEncryptMode` 字段，并据此选择 SHA256（新固件）或 SHA1（老固件）进行密码哈希。

#### Scenario: 新固件使用 SHA256

- **WHEN** `init_info` 返回 `newEncryptMode` 为 `1`
- **THEN** 系统使用 `SHA256(nonce + SHA256(password + key))` 作为密码哈希

#### Scenario: 老固件使用 SHA1

- **WHEN** `init_info` 返回 `newEncryptMode` 为 `0` 或字段不存在
- **THEN** 系统使用 `SHA1(nonce + SHA1(password + key))` 作为密码哈希

#### Scenario: init_info 接口不可达

- **WHEN** `init_info` 请求失败或超时
- **THEN** 系统默认使用 SHA1 进行登录，登录失败后自动切换 SHA256 重试

### Requirement: 登录认证

系统 SHALL 使用 `username=admin`、加密后的密码、`logtype=2` 和生成的 nonce 调用登录接口，获取并缓存 token（stok）。

#### Scenario: 登录成功

- **WHEN** 登录接口返回 `code=0` 且包含 `token` 字段
- **THEN** 系统缓存 token 供后续请求使用

#### Scenario: 登录失败

- **WHEN** 登录接口返回非零 code 或 `invalid-auth` 错误
- **THEN** 系统记录错误日志并抛出异常

### Requirement: Token 过期自动重登

系统 SHALL 在 token 过期时自动重新登录获取新 token。

#### Scenario: Token 有效期内

- **WHEN** 距离上次登录不超过 10 分钟
- **THEN** 系统使用缓存的 token 发起请求

#### Scenario: Token 过期

- **WHEN** API 请求返回 token 无效或过期的错误
- **THEN** 系统重新调用登录接口获取新 token，并重试原请求

### Requirement: 获取设备列表

系统 SHALL 调用 `device_list` 接口获取当前连接设备列表，每个设备包含 MAC 地址、设备名称和统计数据（含下行速度）。

#### Scenario: 获取成功

- **WHEN** 调用 `device_list` 接口成功
- **THEN** 返回设备列表，每个设备的 `statistics.downspeed` 为当前下行速度（Bit/s）

#### Scenario: 目标设备不在线

- **WHEN** 设备列表中不包含目标 MAC 地址
- **THEN** 返回下行速度为 0
