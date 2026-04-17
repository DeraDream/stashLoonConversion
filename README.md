# StashLoon Conversion

GitHub 仓库地址：

[https://github.com/DeraDream/stashLoonConversion](https://github.com/DeraDream/stashLoonConversion)

这是一个用于 `Stash` 和 `Loon` 的配置转换服务，支持：

- 上传现有 `Stash YAML`
- 在线转换为 `Loon conf`
- 提交节点链接生成配置
- 保存历史配置列表
- 下载配置文件
- 生成配置链接
- 在手机浏览器中直接唤起 `Stash` 和 `Loon` 导入

当前优先支持：

- `vless://`

## 页面结构

- `/`：主页，只显示配置列表和操作按钮
- `/convert`：子页面，用来上传 YAML 或提交节点生成配置

## 功能说明

- 首页展示所有已保存的配置记录
- 每条记录支持下载 `stash.yaml` 和 `loon.conf`
- 每条记录支持复制配置链接
- 每条记录支持直接导入 `Stash`
- 每条记录支持直接导入 `Loon`
- 上传或生成的新配置会自动写入列表

## Linux VPS 安装

推荐直接使用一键安装命令，不需要手动下载、上传或解压项目。

### 一键安装命令

```bash
curl -fsSL https://raw.githubusercontent.com/DeraDream/stashLoonConversion/main/bootstrap-install.sh | sudo bash
```

如果你怀疑命中了旧缓存，可以用这个等价写法强制拉取最新脚本：

```bash
curl -fsSL "https://raw.githubusercontent.com/DeraDream/stashLoonConversion/main/bootstrap-install.sh?t=$(date +%s)" | sudo bash
```

这条命令会自动：

- 从 GitHub 拉取最新代码
- 自动安装缺失的 `git` 和 `python3`
- 自动检查并补齐 `systemctl/systemd`
- 检测服务是否已安装
- 未安装时执行安装
- 已安装时直接打开菜单，不会重复安装

### 手动执行仓库安装

如果你确实需要手动从源码安装，也可以：

```bash
git clone https://github.com/DeraDream/stashLoonConversion.git
cd stashLoonConversion
sudo bash install.sh
```

安装器会自动完成这些事情：

- 安装程序到 `/opt/stashloon/app`
- 写入环境配置到 `/etc/stashloon/stashloon.env`
- 创建 `systemd` 服务 `stashloon.service`
- 创建全局命令 `stashloon`
- 先随机生成一个端口，并允许你交互式改成自定义端口
- 启动服务并设置开机自启
- 安装完成后打印完整面板地址

### 3. 安装完成后使用菜单

安装完成后会自动进入菜单。

后续你也可以随时输入下面的命令再次调出菜单：

```bash
sudo stashloon
```

菜单包含这些操作：

- 安装
- 更新
- 重启
- 卸载
- 状态

菜单顶部会显示当前面板地址，方便你随时查看访问入口。

### 4. 防重复安装逻辑

如果服务器已经安装过本服务，再次执行：

```bash
curl -fsSL https://raw.githubusercontent.com/DeraDream/stashLoonConversion/main/bootstrap-install.sh | sudo bash
```

不会重复安装，而是直接打开菜单。

## 更新项目

如果你已经安装过服务，后续更新建议这样做：

### 方式 1：通过菜单更新

```bash
sudo stashloon
```

然后选择：

```bash
2. 更新
```

更新时会强制从下面这个仓库重新拉取最新代码，而不是复用服务器上的旧副本：

```bash
https://github.com/DeraDream/stashLoonConversion.git
```

### 方式 2：重新执行安装命令

也可以重新执行一键安装命令：

```bash
curl -fsSL https://raw.githubusercontent.com/DeraDream/stashLoonConversion/main/bootstrap-install.sh | sudo bash
```

如果系统已经安装，会直接进入菜单，不会重复覆盖安装流程。

## 卸载项目

```bash
sudo stashloon
```

然后选择：

```bash
4. 卸载
```

卸载时会：

- 停止并移除 `systemd` 服务
- 删除 `/opt/stashloon`
- 删除 `/usr/local/bin/stashloon`

默认会保留：

- `/etc/stashloon/stashloon.env`

这样你以后重装时还能继续使用原配置。

## 服务配置文件

安装后主要文件位置：

- 程序目录：`/opt/stashloon/app`
- 环境配置：`/etc/stashloon/stashloon.env`
- 服务文件：`/etc/systemd/system/stashloon.service`
- 全局命令：`/usr/local/bin/stashloon`

环境配置还会保存更新源地址：

- `REPO_URL=https://github.com/DeraDream/stashLoonConversion.git`

## 修改访问地址

安装完成后，编辑环境文件：

```bash
sudo nano /etc/stashloon/stashloon.env
```

例如：

```bash
HOST=0.0.0.0
PORT=8080
PUBLIC_BASE_URL=http://your-server-ip:8080
SUBSCRIPTION_USERINFO=
```

修改后重启服务：

```bash
sudo stashloon
```

然后选择：

```bash
3. 重启
```

## 浏览器访问

假设你配置的是：

```bash
PORT=8080
PUBLIC_BASE_URL=http://your-server-ip:8080
```

那么访问地址就是：

- 首页列表：`http://your-server-ip:8080/`
- 转换页面：`http://your-server-ip:8080/convert`

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

## 数据存储方式

当前版本没有使用数据库，而是文件存储：

- 配置文件保存在 `data/generated/<token>/`
- 记录索引保存在 `data/index.json`

Linux VPS 安装后，这些数据位于：

- `/opt/stashloon/app/data/`

## 后续可扩展

- 增加更多协议解析：`trojan://`、`ss://`、`vmess://`
- 接入固定模板字段
- 增加后台管理
- 切换到 SQLite 或 MySQL
