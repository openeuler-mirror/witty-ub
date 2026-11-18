# 故障分类器的部署目录

三种部署方式均由后端监听已确认案例变更并重训，Agent 读取发布后的模型。
训练策略、数据门槛及退化条件见[默认标签方案](../witty_ub_diagnostician/skills/case-matching/references/DEFAULT_LABEL_POLICY.md)。

| 资源 | 源码部署 | RPM 部署 | Docker 部署 |
| --- | --- | --- | --- |
| 初始模型、参考库与提取代码 | 源码 `witty_ub_diagnostician/skills/case-matching/` | 后端包 `/var/witty-ub/classifier-runtime/` | 后端镜像 `/var/witty-ub/classifier-runtime/`，前端随 Agent skill 打包 |
| 重训模型、参考库与状态 | `/var/witty-ub/fault_classifier/` | `/var/witty-ub/fault_classifier/` | 同一路径，挂载 `witty-ub-classifier-models` 持久卷 |
| 训练依赖 | 后端 venv 的 requirements | 后端 venv 的 requirements | backend/all 基础镜像及应用镜像安装 sklearn |

部署后权重的具体位置：

```text
/var/witty-ub/
  classifier-runtime/                  # RPM/容器后端的包内资源，可随升级替换
    scripts/
    assets/default_label_policy/
      numeric_classifier.json.gz       # 初始 474 来源部署模型
      cosine_bank.json.gz
      manifest.json
  fault_classifier/                    # 运行数据，普通升级保留
    active.json                        # 当前发布版本
    training.json                      # 训练状态及已接管来源记录
    versions/<version>/
      numeric_classifier.json.gz       # 重训权重；数据不足的版本不含此文件
      cosine_bank.json.gz
      manifest.json
    samples/                           # 经过验证的来源观测缓存
    jobs/                              # 训练中的临时文件
```

后端和 Agent 都导出 `WITTY_CLASSIFIER_MODEL_DIR`，默认 `${WITTY_DIR}/fault_classifier`；
`WITTY_DIR` 默认为 `/var/witty-ub`，与源码仓库所在目录无关。
修改报告目录 `WITTY_REPORT_DIR` 不会改变部署启动器明确指定的模型目录。
`WITTY_CASE_MATCHING_DIR` 用于指定后端提取代码及初始资源目录，通常无需修改。

源码部署在启动时创建运行目录并赋予部署用户写权限；nohup 与 systemd 使用相同路径。
Agent 的报告根目录也与后端统一为 `/var/witty-ub/reports`，可以同时为两端设置 `WITTY_REPORT_DIR` 覆盖。
源码目录下既有报告仍留在原处；本次部署代码不会自动移动历史文件。

## RPM 打包与升级

`witty-ub-backend` 必须独立携带 `classifier-runtime`，无需安装 `witty-ub-web` 才能训练。
打包仓的 `%install` 调用本仓的安装助手：

```spec
bash ./deploy/rpm/install_classifier_runtime.sh \
    ./witty_ub_diagnostician/skills/case-matching \
    %{buildroot}/var/witty-ub/classifier-runtime
install -d -m 0750 %{buildroot}/var/witty-ub/fault_classifier
```

对应后端包 `%files` 包含 `classifier-runtime/scripts/`、`classifier-runtime/assets/`，
以及空的 `fault_classifier` 目录；`active.json`、`training.json`、`versions/` 等运行时内容不打进 RPM。
安装助手会验证初始模型、参考库和提取代码的哈希，不依赖 sklearn 或前端服务。
打包仓 `witty-ub.spec` 须与上述规则配套更新。
构建新包时须使用包含本次源码改动的新源码归档；本仓 `build.sh --rpm` 从已发布仓库安装 RPM，不会代为构建新 RPM。

后端 systemd 单元和 RPM manager 都读取可选的 `/etc/witty-ub/classifier.env`。
普通升级保留运行数据；后端显式执行 manager 的 `clean` 会同时清理训练权重、状态和缓存，使其与清空后的案例库一致。
初始资源仍由 RPM 管理。部署管理器会检查分类器资源；旧包缺少资源时会提示升级并停止部署或启动。

## 分离部署

同机 Docker 的 all/backend/frontend 角色使用同名持久卷，启动脚本和 Compose 均已配置。
手工 `docker run` 时需给后端和前端同时加：

```bash
-v witty-ub-classifier-models:/var/witty-ub/fault_classifier
```

**跨机器时，相同目录名或 Docker 卷名并不代表共享存储。** 后端与 Agent 必须挂载同一份模型目录，
可使用共享文件系统并保证后端可写、Agent 可读，服务 UID/权限一致。
源码两端使用相同的 `WITTY_CLASSIFIER_MODEL_DIR=/mnt/witty-classifier`；
RPM 两端在 `/etc/witty-ub/classifier.env` 配置：

```bash
WITTY_CLASSIFIER_MODEL_DIR=/mnt/witty-classifier
```

之后重启后端及 Agent。跨机 Docker 可把同一个共享目录绑定到双方的 `/var/witty-ub/fault_classifier`，
或为同名卷配置共享存储驱动。没有共享目录时，另一台机器上的 Agent 无法读取后端新训练的权重。

## 验证

`GET /diag_case_library/classifier/status` 查看状态和版本；案例库顶部显示同一状态。
训练完成后检查 `active.json` 指向的版本目录；生成报告的 `label_matching.decision.model_id`
应与该版本一致。数据不足时该版本仅有当前 K4 参考库，报告记录 `insufficient_training_data`。
