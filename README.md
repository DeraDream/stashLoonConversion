# StashAndLoon

一个适合部署在 Linux VPS 或 macOS 本地的轻量站点，用来做两件事：

1. 上传现有的 Stash YAML，生成可访问链接，并在线转换成 Loon 配置。
2. 提交节点链接，例如 `vless://...#节点名`，服务端把节点追加到固定模板中，生成 Stash YAML 和 Loon 配置文件。

## 当前能力

- 前端网页：填写节点、上传 YAML、展示结果和导入链接
- 后端 API：零依赖 Python `http.server`
- 文件分享：生成 `/files/<token>/stash.yaml` 和 `/files/<token>/loon.conf`
- 配置列表：保存历史上传和生成记录，支持重复查看和导入
- Stash 导入链接：`stash://install-config?...`
- Loon 导入链接：`loon://import?sub=...`
- 当前优先支持：`vless://`

## 页面结构

- `/`：主页，只显示配置列表和操作按钮
- `/convert`：子页面，用来上传 YAML 或提交节点生成配置

## Linux 命令安装

项目已经带了命令安装器与菜单脚本，适合后续放到 GitHub 后做一键安装。

- 初次安装入口：`install.sh`
- 全局短命令：`stashloon`
- 菜单能力：安装、更新、卸载、重启、查看状态
- 防重复安装：如果服务器已经安装，再次执行安装命令会直接进入菜单，而不是重复安装

当前脚本面向 Linux VPS，安装后会：

- 把程序部署到 `/opt/stashloon/app`
- 把环境配置放到 `/etc/stashloon/stashloon.env`
- 创建 `systemd` 服务 `/etc/systemd/system/stashloon.service`
- 创建全局命令 `/usr/local/bin/stashloon`

### 本地仓库安装

```bash
sudo bash install.sh
```

### 后续 GitHub 一键安装预留

等你把项目传到 GitHub 后，可以用同一套脚本走远程安装。脚本已经支持 `REPO_URL` 环境变量，例如：

```bash
curl -fsSL https://your-domain.example/install.sh | sudo REPO_URL=https://github.com/you/repo.git bash
```

你把 GitHub 地址给我后，我可以把这条最终命令和远程引导脚本一起收口好。

## macOS 本地部署

你的系统是 macOS，本项目现在已经支持本地启动并开放端口给浏览器访问。

### 方式 1：直接启动

```bash
cd /Users/dfw/Downloads/stashAndLoon
python3 server.py
```

启动后本机浏览器访问：

```bash
http://127.0.0.1:8080
```

### 方式 2：推荐，用启动脚本自动生成局域网访问地址

```bash
cd /Users/dfw/Downloads/stashAndLoon
chmod +x start-macos.sh
./start-macos.sh
```

脚本会自动探测你 Mac 的局域网 IP，并把 `PUBLIC_BASE_URL` 设成：

```bash
http://你的局域网IP:8080
```

这样生成出来的 Stash/Loon 导入链接，在同一局域网里的手机上也能直接使用。

脚本也会强制让服务监听在：

```bash
0.0.0.0:8080
```

避免因为终端里残留的 `HOST=127.0.0.1` 导致只能本机访问。

## 环境变量

可以复制一份环境变量模板：

```bash
cp .env.example .env
```

默认配置如下：

```bash
HOST=0.0.0.0
PORT=8080
PUBLIC_BASE_URL=http://127.0.0.1:8080
```

如果你希望手机或其他电脑访问，请把 `.env` 里的 `PUBLIC_BASE_URL` 改成你 Mac 的局域网 IP，例如：

```bash
PUBLIC_BASE_URL=http://192.168.1.25:8080
```

然后重新启动：

```bash
python3 server.py
```

## 开放端口给浏览器访问

### 本机访问

浏览器打开：

```bash
http://127.0.0.1:8080
```

### 局域网访问

先查本机 IP：

```bash
ipconfig getifaddr en0
```

如果你用的是 USB 网卡或其他网络接口，也可能是：

```bash
ipconfig getifaddr en1
```

得到 IP 后，局域网其他设备浏览器访问：

```bash
http://你的IP:8080
```

### macOS 防火墙

如果浏览器打不开，通常是 macOS 防火墙拦截了 Python。

你可以在：

`系统设置 -> 网络 -> 防火墙`

里允许 `Python` 接收入站连接。

也可以先临时关闭防火墙测试。

## Linux / VPS 部署

## API

### `POST /api/generate`

提交节点文本，每行一个节点。

```json
{
  "profile_name": "我的配置",
  "node_text": "vless://uuid@example.com:443?security=tls&type=ws&host=example.com&path=%2F#香港01"
}
```

### `POST /api/convert-upload`

上传现有 YAML 内容并转换。

```json
{
  "filename": "stash.yaml",
  "content": "..."
}
```

### `GET /api/records`

获取已保存的配置记录列表，前端会用它渲染历史记录和操作按钮。

### `systemd` 服务

创建 `/etc/systemd/system/stash-and-loon.service`：

```ini
[Unit]
Description=Stash And Loon Converter
After=network.target

[Service]
Type=simple
WorkingDirectory=/opt/stashAndLoon
Environment=PUBLIC_BASE_URL=https://your-domain.com
ExecStart=/usr/bin/python3 /opt/stashAndLoon/server.py
Restart=always
RestartSec=3
User=root

[Install]
WantedBy=multi-user.target
```

然后执行：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now stash-and-loon
sudo systemctl status stash-and-loon
```

### Nginx 反代

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 后续可扩展

- 增加更多协议解析：`trojan://`、`ss://`、`vmess://`
- 接入你自己的固定模板字段
- 持久化记录用户提交的节点和生成历史
- 增加鉴权和后台管理
