# Trade Dashboard

一个用于展示多市场交易数据的可部署 Web 项目骨架。

## 技术栈

- Frontend: Next.js + TypeScript
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Cache/Queue: Redis
- Reverse Proxy: Nginx
- Deployment: Docker Compose

当前首页按这几类市场统一展示：

- BTC / 数字货币
- A股
- 港股
- 美股
- 商品期货

首页里还会单独显示：

- 风险快照
- 市场暴露
- 最近成交
- 重点标的清单

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
6. 首页会自动聚合所有市场的总览、重点标的和最近成交。

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

## 后续建议

- 加上 HTTPS 证书
- 接入真实交易所 API 或你的交易数据库
- 增加登录鉴权
- 增加导出、筛选、风控告警
