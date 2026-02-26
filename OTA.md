# OTA 仓库发布说明（当前项目）

本仓库用于发布两类设备的 OTA 固件：
- Door Opener
- Door Lock

App 侧按设备读取各自目录下的 `manifest.json`，并下载对应 `.bin`。

## 1. 当前仓库结构

```text
Human_perception_OTA/
├── Door_Opener_OTA/
│   ├── manifest.json
│   └── firmware_Door_Opener_<version>.bin
├── Door_Lock_OTA/
│   ├── manifest.json
│   └── firmware_Door_Lock_<version>.bin
└── OTA.md
```

## 2. 版本与命名规范（按现状）

当前项目使用“设备名 + 语义版本”的版本字符串：
- Door Opener：`Door_Opener_X.Y.Z`
- Door Lock：`Door_Lock_X.Y.Z`

固件文件名规则：
- `firmware_<version>.bin`

示例：
- `version = Door_Opener_0.0.3`
- `file = firmware_Door_Opener_0.0.3.bin`

注意：
- `version` 与 `file` 中的版本部分必须完全一致。
- `manifest.json` 与对应 `.bin` 必须在同一目录。

## 3. manifest.json 格式（必须字段）

```json
{
  "version": "Door_Opener_0.0.3",
  "file": "firmware_Door_Opener_0.0.3.bin",
  "size": 67676,
  "sha256": "2a24faf24bda77d06fd96c9ae1157423b368b1ad906c597fffa00cb5a30f616b",
  "notes": "启用振动传感器"
}
```

字段说明：
- `version`：发布版本号（用于更新判断）
- `file`：固件文件名（相对当前设备目录）
- `size`：固件大小（字节）
- `sha256`：固件 SHA-256（64 位十六进制）
- `notes`：更新说明（用户可见）

## 4. 计算 size 与 SHA-256

Windows:
```bash
certutil -hashfile Door_Opener_OTA/firmware_Door_Opener_0.0.3.bin SHA256
```

macOS / Linux:
```bash
sha256sum Door_Opener_OTA/firmware_Door_Opener_0.0.3.bin
```

查看文件大小（字节）：
```bash
wc -c Door_Opener_OTA/firmware_Door_Opener_0.0.3.bin
```

Door Lock 同理，把路径替换为 `Door_Lock_OTA/...`。

## 5. 发布流程（每个设备独立执行）

1. 准备新固件并确定版本号（例如 `Door_Lock_0.1.1`）。
2. 将固件命名为 `firmware_<version>.bin` 并放入对应目录。
3. 计算新固件 `size` 与 `sha256`。
4. 更新该设备目录下的 `manifest.json`。
5. 确保 `manifest.json` 的 `file` 指向当前已提交的固件文件。
6. 将 `.bin` 与 `manifest.json` 在同一提交中提交并推送到 `main`。

## 6. App 端更新地址（Raw URL）

Door Opener:
`https://raw.githubusercontent.com/Doorothy-2025/Human_perception_OTA/main/Door_Opener_OTA/manifest.json`

Door Lock:
`https://raw.githubusercontent.com/Doorothy-2025/Human_perception_OTA/main/Door_Lock_OTA/manifest.json`

## 7. 大小限制（与当前 App 对齐）

- 当前 OTA 限制固件大小 `<= 0xE0020`（约 917,536 字节）。
- 超过该大小会被 App 拒绝。

## 8. 回滚策略（建议）

- 每个设备目录默认仅保留当前生效版本的 `.bin`（由自动化脚本发布时清理旧包）。
- 需要回滚时，通过 Git 历史恢复到旧提交，或重新发布旧固件并生成新 manifest。

## 9. 发布前检查清单

- 固件文件路径正确，文件可访问。
- `manifest.json` 的 `version` 与 `file` 一致。
- `size` 与 `sha256` 与实际文件一致。
- 提交中同时包含 `.bin` 与 `manifest.json`。

## 10. 自动化发布脚本（推荐）

仓库内提供脚本：
- `scripts/release_ota.py`

脚本功能：
- 通过设备参数选择发布对象（`--Op` 或 `--Lo`）。
- 读取现有 manifest 的版本号并自动补丁位 +1（例如 `0.0.3 -> 0.0.4`）。
- 将任意命名的 `.bin` 自动重命名为 `firmware_<version>.bin`。
- 发布前自动删除该设备目录下旧的 `.bin`，保持目录干净且唯一。
- 自动生成并覆盖 `manifest.json`（包含 `size`、`sha256`、`notes`）。
- 可选 `--push` 自动执行 `git add/commit/push`。

### 10.1 固件投放目录

不手动传 `--bin` 时，脚本会从以下目录取 `.bin`：
- Door Opener：`incoming/Door_Opener_OTA/`
- Door Lock：`incoming/Door_Lock_OTA/`

要求：
- 对应目录下一次只放一个 `.bin`。
- 如目录有多个 `.bin`，请删除多余文件或改用 `--bin` 指定路径。

### 10.2 使用示例

Door Opener（只生成文件，不推送）：
```bash
python3 scripts/release_ota.py --Op --notes "启用振动传感器"
```

Door Lock（生成文件并自动推送）：
```bash
python3 scripts/release_ota.py --Lo --notes "修复门锁偶发误触发" --push
```

手动指定任意 bin 路径：
```bash
python3 scripts/release_ota.py --Op --bin "/path/to/random_name.bin" --notes "xxx" --push
```

### 10.3 注意事项

- 自动推送依赖本机 Git 凭据已配置可用。
- 脚本会检查固件大小上限（`<= 0xE0020`）。
- 源 bin 不要直接放在 `Door_Opener_OTA/` 或 `Door_Lock_OTA/`，请放到 `incoming/` 或使用 `--bin` 指向其他路径。
