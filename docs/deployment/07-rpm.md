# witty-ub RPM 包部署

## 概述

适用于 openEuler 原生部署场景，通过 systemd 管理服务。`yum install witty-ub` 安装后，使用 `witty-ub manager` 完成 PG 初始化、服务启停、数据清理、日志查看等运维操作。

---

## 前置条件

- openEuler 24.03 LTS SP3 / SP4
- root 或 sudo 权限

> PostgreSQL 不需要预装，`witty-ub manager install` 会自动初始化。

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

## 安装与初始化

```bash
sudo yum install -y witty-ub
sudo witty-ub manager install    # 初始化 PostgreSQL + 启动服务
```

完成后访问 `http://<服务器IP>:8080`。

---

## 配置 OpenCode（可选）

```bash
npm i -g opencode-ai   # 或参考 [opencode 官方文档](https://opencode.ai/zh/download)
vi ~/.config/opencode/opencode.jsonc
bash /var/witty-ub/latency/deploy/run_opencode.sh   # 启动后台服务
```

参考 [配置参考手册 · OpenCode 配置](../usage/03-configuration-reference.md#opencode-配置)。

---

## PG 连接配置

PG 凭据位于 `/etc/witty-ub/pg.conf`，默认值：`host=127.0.0.1 port=15432 db/user/pass=witty-ub`。

如需修改（如指向外部 PG），编辑后重新执行 `sudo witty-ub manager install` 即可同步生效。

---

## 服务管理

```bash
sudo witty-ub manager             # 交互式菜单
sudo witty-ub manager start       # 启动
sudo witty-ub manager stop        # 停止
sudo witty-ub manager restart     # 重启
sudo witty-ub manager status      # 查看状态
sudo witty-ub manager logs        # 查看日志
sudo witty-ub manager psql        # 进入 psql
```

| 服务 | 说明 | 端口 |
|------|------|------|
| `witty-ub-web` | Web UI（Nginx） | 8080 |
| `witty-ub-latency` | 后端 API（FastAPI） | 9772 |
| `postgresql-15` | 数据库 | 15432 |

---

## 验证

```bash
curl http://localhost:9772/health_check
curl -I http://localhost:8080
sudo witty-ub manager status
```

浏览器访问 `http://<服务器IP>:8080`。

---

## 升级 / 卸载 / 清理

```bash
sudo yum update -y witty-ub && sudo witty-ub manager restart   # 升级
sudo witty-ub manager clean                                    # 清空数据（PG 表 + /var 数据）
sudo witty-ub manager uninstall                                # 停服务 + 禁用 units
sudo yum remove -y witty-ub witty-ub-manager                   # 彻底卸载 RPM
```

---

## 故障排查

| 问题 | 排查 |
|------|------|
| 后端 9772 起不来 | `sudo witty-ub manager logs`；最常见 PG 未就绪/密码不匹配 → `sudo witty-ub manager install` |
| 前端 8080 起不来 | `ss -tlnp \| grep 8080` 查端口占用 |
| psql 连不上 | `systemctl status postgresql-15`；`cat /etc/witty-ub/pg.conf` |
| 重置一切 | `sudo witty-ub manager clean` → `sudo witty-ub manager install` |

---

## 后续步骤

- 数据库手动部署 → [05-database.md](05-database.md)
- 宿主机脚本部署 → [02-script-host.md](02-script-host.md)
- 容器脚本部署 → [03-script-container.md](03-script-container.md)
