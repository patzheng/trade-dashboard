# Trade Dashboard

一个用于展示交易数据的可部署 Web 项目骨架。

## 技术栈

- Frontend: Next.js + TypeScript
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Cache/Queue: Redis
- Reverse Proxy: Nginx
- Deployment: Docker Compose

## 目录结构

- `frontend/`: 交易展示前端
- `backend/`: 数据 API
- `nginx/`: 反向代理配置
- `docker-compose.yml`: 本地和服务器部署编排

## 本地启动

1. 复制环境变量文件

```bash
cp .env.example .env
```

2. 启动服务

```bash
docker compose up --build
```

3. 打开

- `http://localhost`

## 服务器部署

1. 在美国服务器上安装 Docker 和 Docker Compose。
2. 把这个项目同步到服务器。
3. 配置 `.env`，修改数据库密码。
4. 执行：

```bash
docker compose up --build -d
```

5. 域名解析到服务器公网 IP 后，访问 80 端口即可。

## 一键更新

以后页面或功能更新后，在本地执行：

```bash
git add .
git commit -m "Update dashboard"
git push
```

然后在服务器项目目录里执行：

```bash
./scripts/deploy.sh
```

这个脚本会自动：

- `git pull --rebase`
- `docker compose build`
- `docker compose up -d --remove-orphans`

## GitHub Actions 自动部署

你也可以让 GitHub 在 `main` 分支有新提交时自动更新服务器。

这套仓库现在使用的是 `self-hosted` runner，也就是 Runner 装在你的服务器上，GitHub Actions 触发后直接在服务器本机执行 `./scripts/deploy.sh`。

### 服务器端要求

- 服务器已经完成 `git clone`
- `deploy.sh` 有执行权限
- `docker` 和 `docker compose` 已安装
- 服务器上已经注册了 GitHub self-hosted runner

### 安装 Runner

在仓库页面打开：

- `Settings`
- `Actions`
- `Runners`
- `New self-hosted runner`

按页面提示选择 `Linux` 和 `x64`，然后在服务器上以 `deploy` 用户运行 GitHub 给出的安装命令。

### 工作方式

- 代码推送到 `main`
- GitHub Actions 调度服务器上的 self-hosted runner
- Runner 在服务器本机执行 `./scripts/deploy.sh`

## 后续建议

- 加上 HTTPS 证书
- 接入真实交易所 API 或你的交易数据库
- 增加登录鉴权
- 增加导出、筛选、风控告警
