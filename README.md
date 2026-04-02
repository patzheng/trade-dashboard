# Trade Dashboard

一个用于展示 BTC 链上、技术面和市场情绪数据的可部署 Web 项目骨架。

## 技术栈

- Frontend: Next.js + TypeScript
- Backend: FastAPI + SQLAlchemy
- Database: PostgreSQL
- Cache/Queue: Redis
- Reverse Proxy: Nginx
- Deployment: Docker Compose

当前首页是 BTC 专页，展示：

- 真实 BTC 价格主图和均线
- 链上指标
- 技术指标
- 情绪和流动性
- 关键支撑/阻力位
- 数据源更新时间和来源

页面分成三段：

- 链上
- 资金流
- 结构

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
6. 首页会直接展示 BTC 的实时价格主图、链上指标和技术面。
7. 实时数据来自 CoinGecko、Blockchain.com、mempool.space 和 Alternative.me，后端带有缓存和失败回退。

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
