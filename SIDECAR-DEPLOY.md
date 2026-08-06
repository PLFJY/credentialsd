# Credential Portal Sidecar 部署指南

本文档描述如何在 Arch Linux 上部署 Firefox Hybrid QR Passkey 方案。运行时架构与桌面环境无关，可用于 GNOME、KDE Plasma、Hyprland、Sway 等具备用户 D-Bus 与 systemd user service 的图形会话。

## 架构

```text
Firefox WebExtension
→ Native Messaging host
→ io.github.PLFJY.CredentialPortal
→ Credential Portal sidecar frontend
→ credentialsd daemon/UI
→ Hybrid QR
→ 手机 Passkey
```

标准的 `org.freedesktop.portal.Desktop`、桌面环境原有的 Portal backend 以及 FileChooser、ScreenCast、Screenshot 等接口不受影响。

## 前置条件

- Arch Linux
- Firefox 140+ 原生包
- 用户 D-Bus 会话
- systemd user service
- Rust、Cargo、Meson 与 Ninja

推荐使用仓库提供的 all-in-one PKGBUILD，而不是分别手工安装两个项目。

## 安装 Linux 端

```sh
git clone https://github.com/PLFJY/credentialsd.git
cd credentialsd/packaging/credentialsd-firefox-sidecar-git
makepkg -si
```

该包安装：

- credentialsd daemon 与 UI
- Credential Portal sidecar frontend
- systemd user units
- D-Bus activation files
- Firefox Native Messaging executable
- Firefox Native Messaging manifest

该包**不会**安装 Firefox 扩展，也不会把 unsigned XPI 放进 `/usr`。

## Portal backend 选择

sidecar 使用内部 Desktop ID：

```text
credentials-sidecar
```

systemd drop-in 只覆盖 sidecar 进程：

```ini
[Service]
Environment=XDG_CURRENT_DESKTOP=credentials-sidecar
Environment=XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential
```

sidecar 使用独立配置：

```text
/usr/share/xdg-desktop-portal/credentials-sidecar-portals.conf
```

内容：

```ini
[preferred]
default=none
org.freedesktop.impl.portal.experimental.Credential=credentialsd
```

`credentialsd.portal` 中的：

```ini
UseIn=credentials-sidecar;
```

仅作为兼容性 fallback。用户通常不需要创建 `~/.config/xdg-desktop-portal/portals.conf`。

## 启动服务

```sh
systemctl --user daemon-reload
systemctl --user start credentials-portal-sidecar.service
systemctl --user start xyz.iinuwa.credentialsd.UiControl.service
```

credentialsd daemon 会在第一次请求时通过 D-Bus 自动激活。

## 安装 Firefox 扩展

正式版本使用 Mozilla AMO 的 unlisted signing，并通过 GitHub Releases 自行分发：

```text
https://github.com/PLFJY/credentialsd/releases/latest
```

安装步骤：

1. 下载 Release 中 Mozilla-signed XPI。
2. 打开 `about:addons`。
3. 点击齿轮菜单。
4. 选择 **Install Add-on From File…**。
5. 选择下载的 XPI。

当前永久 Extension ID：

```text
credentialsd-firefox-sidecar@plfjy.top
```

Native Messaging manifest 的 `allowed_extensions` 必须与该 ID 完全一致。

## 开发时临时加载

Meson 可以继续生成 unsigned XPI，但它只作为 build artifact 使用，不安装到 `/usr`，也不上传到正式 Release。

```sh
ninja -C build
```

然后打开：

```text
about:debugging#/runtime/this-firefox
```

选择 **Load Temporary Add-on…**，加载 build directory 中的 XPI 或准备好的 `manifest.json`。临时扩展会在 Firefox 重启后失效。

## 发布 Firefox 版本

维护者需要在 GitHub Environment `amo-signing` 中配置：

```text
AMO_JWT_ISSUER
AMO_JWT_SECRET
```

凭据来自 Mozilla Add-ons Developer Hub 的 API credentials。不要把真实值提交到仓库、文档、日志或 workflow artifact。

发布步骤：

1. 修改 `webext/add-on/manifest.firefox.json` 中的 `version`。
2. 合并到默认分支。
3. 打开 GitHub Actions。
4. 运行 **Release Firefox Extension**。
5. 设置 `publish=true`。
6. 如配置了 Environment reviewer，批准 `amo-signing` deployment。
7. 等待 AMO unlisted signing 与 GitHub Release 创建完成。

版本会生成：

```text
Tag: firefox-v<VERSION>
XPI: credentialsd-sidecar-firefox-<VERSION>.xpi
```

Release 应包含：

- Mozilla-signed XPI
- `updates.json`
- `SHA256SUMS`
- `release-metadata.json`

Release 必须是普通 Release，不能是 draft 或 prerelease。

## 自动更新

Firefox manifest 中的固定更新地址：

```text
https://github.com/PLFJY/credentialsd/releases/latest/download/updates.json
```

`updates.json` 再指向精确版本的 XPI：

```text
https://github.com/PLFJY/credentialsd/releases/download/firefox-v<VERSION>/credentialsd-sidecar-firefox-<VERSION>.xpi
```

只有 `updates.json` 使用 `releases/latest`；XPI 必须使用不可变的 versioned URL 和 SHA-256。

## 验证

检查服务：

```sh
systemctl --user status credentials-portal-sidecar.service
systemctl --user status xyz.iinuwa.credentialsd.UiControl.service
```

检查 sidecar Credential interface：

```sh
gdbus introspect --session --dest io.github.PLFJY.CredentialPortal --object-path /org/freedesktop/portal/desktop | grep Credential
```

检查标准 Portal 仍独立运行：

```sh
busctl --user status org.freedesktop.portal.Desktop
busctl --user status io.github.PLFJY.CredentialPortal
```

检查 Native Messaging manifest：

```sh
cat /usr/lib/mozilla/native-messaging-hosts/xyz.iinuwa.credentialsd_helper.json
```

其中应包含：

```json
"allowed_extensions": ["credentialsd-firefox-sidecar@plfjy.top"]
```

最后打开 `https://webauthn.io`，测试 Register、Hybrid QR 扫码和 Get/Login。

## 常见问题

### Credential interface 未注册

```sh
systemctl --user show credentials-portal-sidecar.service -p Environment
cat /usr/share/xdg-desktop-portal/credentials-sidecar-portals.conf
cat /usr/share/xdg-desktop-portal/portals/credentialsd.portal
```

确认 sidecar 环境中存在：

```text
XDG_CURRENT_DESKTOP=credentials-sidecar
XDG_DESKTOP_PORTAL_ENABLE_EXPERIMENTAL=credential
```

### Native Messaging 连接失败

确认浏览器扩展 ID 和 Native Messaging `allowed_extensions` 都是：

```text
credentialsd-firefox-sidecar@plfjy.top
```

### SecurityError 或 untrusted caller

```sh
journalctl --user -u xyz.iinuwa.credentialsd.Credentials.service --no-pager -n 50
```

确认 `/usr/lib/credentials-portal-sidecar` 位于 credentialsd 的 trusted caller list，且 shim 的 App ID 为 `firefox`。
