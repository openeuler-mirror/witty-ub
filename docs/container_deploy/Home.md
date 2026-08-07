<!-- Copyright (c) Huawei Technologies Co., Ltd. 2026. All rights reserved. -->
<!-- witty-ub is licensed under the Mulan PSL v2. -->

# Witty-UB 容器化部署指南

> 用于 Lingqu(UB) 架构 SuperPod 故障定位的工具容器化部署文档。

## 文档导航

| 章节 | 说明 |
|------|------|
| [1. 容器化部署说明](01-overview.md) | 概述、架构说明、镜像分层、环境要求、文件结构、RPM迁移 |
| [2. 镜像构建、上传与打包](02-build-and-package.md) | 构建步骤、多架构构建、上传镜像、打包分发 |
| [3. 镜像拉取、启动与使用](03-pull-and-run.md) | 拉取镜像、启动容器、配置说明、数据持久化、验证访问 |
| [4. 部署脚本使用指南](04-deploy-scripts.md) | deploy/docker/manage.sh 和 deploy/docker/deploy_witty.sh 的使用方法、参数说明、常见场景 |
| [5. 故障排查](05-troubleshooting.md) | 常见问题、容器调试、日志管理、生产环境建议 |

---

## 快速入口

- **快速开始**: 先阅读 [概述](01-overview.md) → [构建镜像](02-build-and-package.md) → [启动使用](03-pull-and-run.md)
- **快速部署**: 直接查看 [启动使用](03-pull-and-run.md)
- **常见问题**: 直接查看 [故障排查](05-troubleshooting.md)
- **镜像分发**: 参考 [上传与打包](02-build-and-package.md)

---

## 版本信息

- **适用版本**: witty-ub
- **基础镜像**: openeuler/openeuler:24.03-lts-sp4
- **外部端口**: 32412
