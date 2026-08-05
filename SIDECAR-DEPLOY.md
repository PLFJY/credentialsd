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

### 临时加载（开发用）

1. Firefox → `about:debugging#/runtime/this-firefox`
2. 点击 "Load Temporary Add-on..."
3. 选择 `/usr/share/credentialsd/credentialsd-firefox-helper.xpi`

### 签名安装（正式用）

需要 Firefox 开发者账号和 `web-ext` 工具：

```sh
npm install --global web-ext

web-ext sign \
  --source-dir /path/to/extension-source \
  --api-key YOUR_API_KEY \
  --api-secret YOUR_API_SECRET \
  --channel unlisted
```

签名后的 XPI 可以通过 Firefox 正式安装流程安装，重启后保留。

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

确认 `allowed_extensions` 包含 `credentialsd-helper@iinuwa.xyz`。
