  # OTA 仓库构建说明

  本说明用于创建 GitHub 公共仓库作为 OTA 固件分发源，配合 App 在启动时检查更新并下载固件。

  ## 1. 仓库结构


  <your-repo>/
  ota/
  manifest.json
  firmware_1.2.4.bin


  - `ota/manifest.json`：发布清单（App 只读取这一个入口）。
  - `firmware_<version>.bin`：固件文件，命名与版本号一致。

  ## 2. 版本与文件命名规范

  - 版本格式：`X.Y.Z`（X/Y/Z 为非负整数），长度 ≤ 15
  - 文件名：`firmware_<version>.bin`
  - 示例：版本 `1.2.4` → 文件名 `firmware_1.2.4.bin`

  > 注意：版本与文件名必须一致，否则 App 会判定无有效更新。

  ## 3. manifest.json 格式（必须字段）

  ```json
  {
    "version": "1.2.4",
    "file": "firmware_1.2.4.bin",
    "size": 524288,
    "sha256": "填入64位hex的SHA-256",
    "notes": "简要更新说明"
  }

  字段说明：

  - version：固件版本号（用于判断是否有新版本）
  - file：固件文件名（相对 ota/ 的路径）
  - size：固件文件大小（字节）
  - sha256：固件文件 SHA‑256（64 位 hex）
  - notes：更新说明，用户可见

  ## 4. 计算 size 与 SHA‑256

  Windows

  certutil -hashfile firmware_1.2.4.bin SHA256

  macOS / Linux

  sha256sum firmware_1.2.4.bin

  查看文件大小（字节）

  wc -c firmware_1.2.4.bin

  ## 5. 发布流程（建议顺序）

  1. 准备好固件文件并确认版本号
  2. 按规范重命名固件（例：firmware_1.2.4.bin）
  3. 计算 size 和 sha256
  4. 更新 ota/manifest.json
  5. 将 firmware_1.2.4.bin 与 manifest.json 一起提交（同一提交，避免指向不存在的文件）
  6. 推送到 main 分支

  ## 6. App 端更新地址（Raw URL）

  https://raw.githubusercontent.com/<org>/<repo>/main/ota/manifest.json

  示例（你的仓库）：

  https://raw.githubusercontent.com/Doorothy-2025/Human_perception_OTA/main/ota/manifest.json

  ## 7. 大小限制（与当前 App 对齐）

  - 当前 App OTA 限制固件大小 ≤ 0xE0020（约 917,536 字节）
  - 超过该大小会被 App 拒绝

  如果你的 App 限制不同，请调整此上限说明。

  ## 8. 回滚策略（建议）

  - 保留旧版本固件（不要删除旧文件）
  - 需要回滚时，只需把 manifest.json 指回旧版本

  ## 9. 常见问题

  Q: 可以只上传固定命名的 bin 而不写 manifest 吗？
  A: 不建议。App 无法知道是否有更新，也无法做完整性校验。manifest 是“检查更新 + 校验”的必要入口。

  Q: 是否必须做 SHA‑256？
  A: 如果 App 实现了校验，就必须提供；否则校验会失败并拒绝更新。

  stat -c '%n %s' ota/firmware_0.0.7.bin && sha256sum ota/firmware_0.0.7.bin