# witty-ub RPM 包部署

## 概述

适用于 openEuler 原生部署场景，通过 systemd 管理服务。

> 推荐使用脚本部署 → [宿主机脚本部署](02-script-host.md) | [容器脚本部署](03-script-container.md)

---

## 前置条件

- openEuler 24.03 LTS SP3 / SP4
- PostgreSQL 已部署 → [05-database.md](05-database.md)

---

## 配置 RPM 仓库

### openEuler 24.03-LTS-SP3

```bash
sudo tee /etc/yum.repos.d/witty-ub.repo <<'EOF'
[witty-ub]
name=witty-ub
baseurl=http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP3/openeuler-2026-07-08-07-31-12/everything/$basearch/
enabled=1
gpgcheck=0
EOF
```

### openEuler 24.03-LTS-SP4

```bash
sudo tee /etc/yum.repos.d/witty-ub.repo <<'EOF'
[witty-ub]
name=witty-ub
baseurl=http://121.36.84.172/dailybuild/EBS-openEuler-24.03-LTS-SP4/openeuler-2026-07-08-07-31-12/everything/$basearch/
enabled=1
gpgcheck=0
EOF
```

> 注意：repo 源中的日期目录（如 `2026-07-08-07-31-12`）需替换为最新的每日构建目录。

---

## 安装

```bash
sudo yum install -y witty-ub
```

---

## 配置 OpenCode

```bash
# RPM 安装
npm i -g opencode-ai # 或按照 [opencode 官方文档](https://opencode.ai/zh/download) 安装

# 修改配置，参考 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)
vi ~/.config/opencode/opencode.jsonc

# 启动后台服务
bash ./src/plugins/latency/deploy/run_opencode.sh
```

---

## PG 连接配置

```bash
sudo vi /var/witty-ub/config/database.conf
```

```conf
PG_HOST=127.0.0.1
PG_PORT=15432
PG_DATABASE=witty-ub
PG_USER=witty-ub
PG_PASSWORD=witty-ub
```

---

## 服务管理

```bash
# 启动
sudo systemctl start witty-ub-web
sudo systemctl start witty-ub-latency

# 开机自启
sudo systemctl enable witty-ub-web
sudo systemctl enable witty-ub-latency

# 查看状态
sudo systemctl status witty-ub-web
sudo systemctl status witty-ub-latency

# 重启 / 停止
sudo systemctl restart witty-ub-web witty-ub-latency
sudo systemctl stop witty-ub-web witty-ub-latency
```

| 服务名 | 说明 | 默认端口 |
|--------|------|----------|
| `witty-ub-web` | Web UI（Nginx） | 8080 |
| `witty-ub-latency` | 后端 API（FastAPI） | 9772 |

---

## 验证

```bash
# 测试 API
curl http://localhost:8080/health_check

# 查看日志
journalctl -u witty-ub-web -f
journalctl -u witty-ub-latency -f
```

浏览器访问：`http://<服务器IP>:8080`

---

## 升级与卸载

```bash
# 升级
sudo yum update -y witty-ub
sudo systemctl restart witty-ub-web witty-ub-latency

# 卸载
sudo systemctl stop witty-ub-web witty-ub-latency
sudo systemctl disable witty-ub-web witty-ub-latency
sudo yum remove -y witty-ub
```

---

## 目录结构

```
/var/witty-ub/
├── data/          # 故障模式数据、KVCache
├── latency/       # 应用代码
├── log/           # 日志
├── config/        # 配置
└── web/           # Web 前端

/usr/bin/
├── witty-ub-log
├── witty-ub-topo
└── witty-ub-diag-tool
```

---

## 后续步骤

- 手动数据库部署 → [05-database.md](05-database.md)
- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
