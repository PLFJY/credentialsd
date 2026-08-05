# Credential Portal Sidecar 部署指南

本文档描述如何在 Arch Linux + Hyprland 上部署 Firefox Hybrid QR Passkey 方案。

## 架构

```
Firefox WebExtension → Native Messaging shim → io.github.PLFJY.CredentialPortal (sidecar)
→ Credential Portal frontend → credentialsd daemon/UI → Hybrid QR → 手机 Passkey
```

系统级 `org.freedesktop.portal.Desktop` 和 `xdg-desktop-portal-hyprland` 不受影响。

## 前置条件

- Arch Linux + Hyprland
- Firefox 140+ (原生包，非 Snap/Flatpak)
- Rust toolchain (stable)
- meson >= 1.5, ninja, pkg-config

## 依赖安装

```sh
sudo pacman -S --needed rust cargo meson ninja gtk4 dbus python-dbus-next \
  libwebauthn hidapi systemd libdex json-glib glib2 pipewire geoclue \
  gdk-pixbuf2 python-pytest python-dbusmock
```

## 构建与安装

### 1. xdg-desktop-portal (sidecar 前端)

```sh
cd xdg-desktop-portal
meson setup --prefix=/usr \
  -Dsidecar_install=true \
  -Dportal_bus_name=io.github.PLFJY.CredentialPortal \
  -Dportal_binary_name=credentials-portal-sidecar \
  -Dportal_systemd_unit_name=credentials-portal-sidecar.service \
  -Dportal_dbus_service_name=io.github.PLFJY.CredentialPortal.service \
  build
ninja -C build
sudo ninja -C build install
```

### 2. credentialsd (守护进程 + UI + 扩展)

```sh
cd credentialsd-sidecar
meson setup --prefix=/usr \
  -Dprofile=default \
  -Dfirefox_portal_bus_name=io.github.PLFJY.CredentialPortal \
  -Dcargo_locked=true \
  build
ninja -C build
sudo ninja -C build install
```

## 配置

### Portal 后端选择

credentialsd 安装时会安装 `credentialsd.portal`，其中包含 `UseIn=Hyprland;`，确保 xdg-desktop-portal 在 Hyprland 下选择 credentialsd 作为 Credential 接口的后端。

如果需要手动配置，创建 `~/.config/xdg-desktop-portal/portals.conf`:

```ini
[preferred]
default=hyprland;gtk
org.freedesktop.impl.portal.experimental.Credential=credentialsd
```

### App ID

shim 中的 `APP_ID` 已在构建时通过 meson 配置为 `firefox`（对应 `/usr/share/applications/firefox.desktop`）。

### Trusted Caller

credentialsd 守护进程验证调用者 PID 的可执行文件路径。`/usr/lib/credentials-portal-sidecar` 已在 `credentialsd/src/gateway/mod.rs` 的 trusted_caller_paths 中。

## 启动服务

```sh
systemctl --user daemon-reload
systemctl --user start credentials-portal-sidecar.service
systemctl --user start xyz.iinuwa.credentialsd.UiControl.service
```

credentialsd 守护进程 (`xyz.iinuwa.credentialsd.Credentials.service`) 会在首次请求时由 D-Bus 自动激活。

## 加载 Firefox 扩展

### 正式安装（用户）

正式安装使用 Mozilla AMO 未上架签名（unlisted）的 XPI，该 XPI 仅通过 GitHub Releases 分发：

1. 下载最新 Release 的签名 XPI：
   `https://github.com/PLFJY/credentialsd/releases/latest`
2. Firefox → `about:addons`
3. 齿轮菜单 → **Install Add-on From File…**
4. 选择下载的签名 XPI

`makepkg -si` 不会安装 Firefox 扩展，只安装 Linux 端的原生集成。

### 临时加载（仅开发用）

仅用于开发/测试。Meson 构建会在构建目录生成未签名的 XPI，可临时加载；该 XPI 不会安装到 `/usr`，Firefox 重启后失效。

1. 构建：`ninja -C build`
2. 定位未签名 XPI（典型路径）：`build/webext/add-on/credentialsd-firefox-helper.xpi`
3. Firefox → `about:debugging#/runtime/this-firefox`
4. 点击 "Load Temporary Add-on..."
5. 选择构建目录中的未签名 XPI

未签名 XPI 不得用于正式安装，也不会出现在 GitHub Release 中。

## 维护者设置

要发布 Firefox 扩展，维护者需要：

- Mozilla 开发者账号（https://addons.mozilla.org/developers/）
- AMO API 凭据（JWT Issuer + JWT Secret），从 AMO Developer Hub 申请
- GitHub Environment：`amo-signing`
  - Environment Secret：`AMO_JWT_ISSUER`
  - Environment Secret：`AMO_JWT_SECRET`
- 可选：为 `amo-signing` 环境配置 required reviewer

凭据值不得提交到仓库、写入工作流命令文本、打印到日志、发送到 artifacts，或暴露给 pull request。工作流仅通过步骤环境变量读取：

```yaml
env:
  AMO_JWT_ISSUER: ${{ secrets.AMO_JWT_ISSUER }}
  AMO_JWT_SECRET: ${{ secrets.AMO_JWT_SECRET }}
```

示例凭据值不得出现在仓库中。

## 发布 Firefox 版本

1. 更新 `webext/add-on/manifest.firefox.json` 中的 `version`
2. 本地校验：
   ```sh
   python3 scripts/prepare-firefox-extension.py /tmp/credentialsd-ext-prep
   python3 tests/test_release_manifest_invariants.py
   python3 tests/test_release_id_consistency.py
   python3 tests/test_prepare_extension.py /tmp/credentialsd-ext-prep
   python3 tests/test_update_manifest_generator.py
   python3 tests/test_packaging_policy.py
   python3 tests/test_workflow_security.py
   python3 tests/test_release_no_secrets.py
   python3 tests/test_release_retired_ids.py
   python3 tests/test_signed_xpi_structure.py
   ```
3. 将改动合并到默认分支
4. 打开 GitHub Actions
5. 选择 **Release Firefox Extension** workflow
6. 设置 `publish=true` 触发发布
7. 审批 `amo-signing` Environment 部署（如配置了 required reviewer）
8. 等待 AMO 签名完成
9. 校验 GitHub Release：tag `firefox-v<VERSION>`，包含 4 个资产：
   - `credentialsd-sidecar-firefox-<VERSION>.xpi`（Mozilla 签名的新 XPI）
   - `updates.json`
   - `SHA256SUMS`
   - `release-metadata.json`
10. 下载签名 XPI 安装到 Firefox，在 https://webauthn.io 测试 create/get

工作流不会在 push、pull request 或任意 tag 上自动发布。每次发布都使用新版本号，不得复用已存在的 AMO 版本或 Git tag。

## 自动更新

Firefox 通过扩展 manifest 中声明的 `update_url` 周期性拉取更新清单：

```
https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json
```

`updates.json` 中的 `update_link` 使用精确版本化的 Release 资产 URL：

```
https://github.com/PLFJY/credentialsd/releases/download/firefox-v<VERSION>/credentialsd-sidecar-firefox-<VERSION>.xpi
```

只有 `updates.json` 这个 URL 是 `releases/latest` 形式；XPI 本身始终指向精确版本。

Firefox 更新 Release 必须是普通 Release：

- 不是 draft
- 不是 prerelease

否则 Firefox 不会从 `updates.json` 拉取到该版本。

## 用户安装

1. Clone `PLFJY/credentialsd`
2. 进入 `packaging/credentialsd-firefox-sidecar-git`
3. 运行 `makepkg -si`
4. 重启/启动 user services
5. 从最新 GitHub Release 下载 Mozilla 签名的 XPI
6. 打开 `about:addons`
7. 选择 **Install Add-on From File…**
8. 选择下载的签名 XPI
9. 在 https://webauthn.io 测试 create/get

`makepkg -si` 不会安装 Firefox 扩展，只安装 Linux 端的原生集成。

## 开发者临时加载

未签名构建产物仅用于开发：

- 仅开发使用
- 通过 `about:debugging` 临时加载
- Firefox 重启后失效
- 不会安装到 `/usr`

临时加载说明不得与正式用户安装说明混用。

## 验证

```sh
# 检查 sidecar 是否运行
systemctl --user status credentials-portal-sidecar.service

# 检查 Credential 接口是否注册
gdbus introspect --session --dest io.github.PLFJY.CredentialPortal \
  --object-path /org/freedesktop/portal/desktop 2>&1 | grep credential

# 检查 credentialsd-ui 是否运行
systemctl --user status xyz.iinuwa.credentialsd.UiControl.service

# 测试 Passkey
# 打开 https://webauthn.io → Register → 扫码完成
```

## 网站覆盖范围

扩展 manifest 的 content_scripts 匹配 `https://*/*`，支持所有 HTTPS 网站。origin 验证由 credentialsd 守护进程执行，不依赖扩展的 matches。

## 修改的源文件

| 文件 | 改动 |
|------|------|
| `credentialsd/src/gateway/mod.rs` | 添加 `/usr/lib/credentials-portal-sidecar` 到 trusted_caller_paths |
| `webext/app/meson.build` | APP_ID 从 `org.mozilla.firefox` 改为 `firefox` |
| `webext/add-on/manifest.firefox.json` | matches 从特定网站改为 `https://*/*` |
| `portal/credentialsd.portal` | 添加 `UseIn=Hyprland;` |
| `meson.options` | 新增 `firefox_portal_bus_name` 选项 |
| `xdg-desktop-portal` meson 选项 | 新增 sidecar 安装支持 |

## 上游同步

1. 拉取上游更改
2. 冲突概率低 — 所有改动都是新增 option/路径，不修改既有逻辑
3. 同步后重新构建安装即可

## 清理

```sh
# 清理构建目录
rm -rf credentialsd-sidecar/build xdg-desktop-portal/build

# 清理临时文件
rm -f /tmp/credential_manager_shim.log
rm -rf /tmp/credentialsd-ext
```

## 排障

### Credential 接口未注册

检查 `credentialsd.portal` 是否包含 `UseIn=Hyprland;`：

```sh
cat /usr/share/xdg-desktop-portal/portals/credentialsd.portal
```

### SecurityError: no description

检查 credentialsd 日志：

```sh
journalctl --user -u xyz.iinuwa.credentialsd.Credentials.service --no-pager -n 10
```

如果显示 "untrusted caller"，确认 `/usr/lib/credentials-portal-sidecar` 在 trusted_caller_paths 中。

如果显示 "claimed_app_id 为空"，确认 shim 中的 APP_ID 是 `firefox`（不是 `org.mozilla.firefox`）。

### Native Messaging 连接失败

确认 manifest 存在且扩展 ID 匹配：

```sh
cat /usr/lib/mozilla/native-messaging-hosts/xyz.iinuwa.credentialsd_helper.json
```

确认 `allowed_extensions` 包含 `credentialsd-sidecar@plfjy.top`。
