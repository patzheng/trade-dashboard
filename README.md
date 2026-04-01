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

### 需要配置的 Secrets

- `DEPLOY_SSH_KEY`: GitHub Actions 用来登录服务器的私钥内容

### 需要配置的 Variables

- `DEPLOY_HOST`: 服务器 IP 或域名
- `DEPLOY_USER`: 服务器上的部署用户，例如 `deploy`
- `DEPLOY_PATH`: 仓库在服务器上的绝对路径，例如 `/home/deploy/trade-dashboard`
- `DEPLOY_PORT`: SSH 端口，默认 `22`

### 生成部署密钥

在本地机器生成一对专门给 GitHub Actions 用的 SSH key：

```bash
ssh-keygen -t ed25519 -C "github-actions-deploy" -f ./github-actions-deploy -N ""
```

把生成出来的公钥 `github-actions-deploy.pub` 追加到服务器上的：

```bash
/home/deploy/.ssh/authorized_keys
```

然后把私钥文件 `github-actions-deploy` 的内容复制到 GitHub 仓库的 `DEPLOY_SSH_KEY` Secret。

### 工作方式

- 代码推送到 `main`
- GitHub Actions 通过 SSH 登录服务器
- 在服务器上执行 `./scripts/deploy.sh`

### 服务器端要求

- 服务器已经完成 `git clone`
- `deploy.sh` 有执行权限
- `docker` 和 `docker compose` 已安装
- `deploy` 用户可以正常拉取仓库并启动容器

## 后续建议

- 加上 HTTPS 证书
- 接入真实交易所 API 或你的交易数据库
- 增加登录鉴权
- 增加导出、筛选、风控告警
