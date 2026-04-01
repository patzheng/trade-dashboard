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

## 后续建议

- 加上 HTTPS 证书
- 接入真实交易所 API 或你的交易数据库
- 增加登录鉴权
- 增加导出、筛选、风控告警

