#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""远端扩展原始数据收集脚本（资产库筛选 + 增量收集）。

用途
----
把远端 raw 目录里「尚未采集的其它原始文件」收集到新的 *_app 目录，保持相对路径，
供你补传回数据集。

规则
----
1) 任务筛选：脚本顶部内置 TASK_NAME_ALLOWLIST（607 个「witty-ub 已入库且有故障」
   任务名：v7/ci_yxh_new 367 + 1022/yxh_new 240），任务目录名命中该白名单才收集，
   其余整目录跳过；**离线运行，不依赖 witty-ub**。清空白名单（[]）才回退到资产库。
2) 任务名关键字（可选，TASK_NAME_KEYWORDS）：非空时任务名还需命中其中之一（子串/glob）。
   任务名排除（TASK_NAME_EXCLUDE_KEYWORDS）：任务名命中任一排除关键字则整目录跳过，
   优先级高于白名单/关键字。默认排除 20 个「场景关键词未出现在 labels.json 中」的场景
   （共 45 个任务），即**只保留有 label、可被数据集打标评估的 562 个 case**。
3) 文件名过滤（FILE_EXCLUDE_NAMES / FILE_EXCLUDE_PATTERNS）：命中「精确文件名」或
   glob 模式的文件跳过不收集；其余文件一律收集。默认跳过访问/INFO 日志。
3b) 无条件排除（FILE_HARD_EXCLUDE_PATTERNS，默认 *ubse*.log*）：命中即跳过，
   任何情况下都不收集，**不受 4) 路径强制纳入豁免**。覆盖 ubse 各类日志及其
   轮转/压缩变体（master_ubse.log、coordinator_UBSE.log、master_ubse.log.1/.gz/.20261116）。
4) 路径强制纳入（PATH_FORCE_INCLUDE_KEYWORDS，默认 coordinator）：文件在**任务目录内**
   的相对路径（**不含任务名本身**）包含该关键字时，强制收集并豁免 3) 的黑名单，用于补收
   此前漏采的 coordinator 数据（豁免不了 3b) 的无条件排除）。只匹配任务名之后的路径段，
   以免任务名含 coordinator 的 case 被整目录误采。
5) 目录结构：源 ./X/<task>/<...>  →  目标 ./X_app/<task>/<...>（相对路径原样保留）。
6) 幂等：目标已存在同名文件则跳过；不删除、不覆盖既有内容。
7) 打包：每个任务收集完成后，把对应 ./X_app 打成 ./X_app.zip（含顶层目录名），
   便于整体传输；默认开启，`--no-zip` 可关闭，`--dry-run` 时不打包。

放置与运行
----------
把本脚本放到 ./ci_yxh_new 与 ./yxh_new「并列」的目录下，直接 `python collect_remote_extras.py`。
默认按脚本所在目录定位两个源目录；也可用命令行参数覆盖。

示例
----
  python collect_remote_extras.py                     # 全量跑
  python collect_remote_extras.py --dry-run           # 只打印，不落盘
  python collect_remote_extras.py --api-base http://10.0.0.5:9772
  python collect_remote_extras.py --tasks-file tasks.txt   # 离线：用本地任务清单代替资产库
  python collect_remote_extras.py --task-keyword '*worker_process_upgrade*'   # 只收名字含该关键字的任务
  python collect_remote_extras.py --exclude-name 'dmesg.txt' --exclude '*.metric'  # 追加不收集的文件
  python collect_remote_extras.py --no-zip            # 不打包 zip，只落目录
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import shutil
import urllib.error
import urllib.request

# ────────────────────────── 默认配置（可在命令行覆盖） ──────────────────────────
DEFAULT_API_BASE = os.environ.get("WITTY_API_BASE", "http://127.0.0.1:9772")
API_SEARCH_PATH = "/diag_case_library/search"
# ─────────── ① 任务白名单（内置，离线可用）───────────
# 远端无 witty-ub：直接使用下面硬编码的任务名白名单作为「已入库且有故障」的任务集合。
# 口径 = log_file 中 anomalous_count>0 或 failure_count>0 的任务名（607 条：
#        v7/KB 7c8989fe 367 条 → ./ci_yxh_new；1022/KB 28be2351 240 条 → ./yxh_new）。
# 任务目录名与此清单精确匹配（并含前后缀容错）才收集；其余整目录跳过。
# 如需改用资产库动态筛选：把本清单清空（改为 []）即可，届时才读 FAULT_TYPES + API。
TASK_NAME_ALLOWLIST: list[str] = [
    "demo_chaos_001_20261019_21_10_38",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20260930_03_34_36",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261008_14_30_06",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261010_10_17_06",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261010_10_45_14",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261010_15_43_16",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261010_16_41_33",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261012_20_47_29",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261021_01_51_58",
    "lingqu_kvcache_dfx_1z3b_1port_fault_001_20261031_00_39_01",
    "lingqu_kvcache_dfx_1z3b_1port_fault_003_20260929_23_31_54",
    "lingqu_kvcache_dfx_1z3b_1port_fault_003_20261031_03_27_00",
    "lingqu_kvcache_dfx_1z3b_1port_fault_004_20261020_22_16_23",
    "lingqu_kvcache_dfx_1z3b_1port_fault_004_20261031_01_55_44",
    "lingqu_kvcache_dfx_1z3b_1port_fault_008_20260929_04_29_41",
    "lingqu_kvcache_dfx_1z3b_1port_fault_009_20261020_23_26_40",
    "lingqu_kvcache_dfx_1z3b_1port_fault_009_20261030_23_09_44",
    "lingqu_kvcache_dfx_1z3b_1port_fault_009_20261109_22_12_57",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_001_20260923_19_56_55",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_001_20261031_03_35_28",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_001_20261106_02_52_29",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_002_20260929_05_37_24",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_002_20261009_09_24_01",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_002_20261023_13_42_34",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_002_20261104_04_38_10",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_002_20261107_16_31_13",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_003_20261107_18_19_15",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_006_20260929_19_17_57",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_006_20261012_17_27_05",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_006_20261027_20_36_53",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_006_20261107_17_20_28",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_008_20261031_01_01_18",
    "lingqu_kvcache_dfx_1z3b_2ports_fault_008_20261109_22_03_16",
    "lingqu_kvcache_dfx_1z3b_2ports_scale_down_fault_005_20260928_21_51_49",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_001_20261105_22_03_39",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261009_09_36_39",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261010_17_33_20",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261012_17_01_48",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261013_12_17_57",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261013_16_44_36",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261013_22_30_54",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261023_13_55_12",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_002_20261023_22_29_05",
    "lingqu_kvcache_dfx_1z3b_3ports_fault_004_20261023_07_20_59",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261015_01_40_51",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261021_00_27_10",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261022_16_41_54",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261031_01_14_25",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261103_03_17_45",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261105_23_34_11",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_001_20261106_23_15_04",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20260928_22_28_58",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261009_12_44_00",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261010_17_16_56",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261010_20_00_39",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261014_00_10_41",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261023_21_12_48",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261105_06_22_28",
    "lingqu_kvcache_dfx_1z3b_4ports_fault_002_20261107_23_59_41",
    "lingqu_kvcache_dfx_client_pod_reboot_001_20261031_02_07_57",
    "lingqu_kvcache_dfx_client_pod_reboot_002_20261031_00_30_54",
    "lingqu_kvcache_dfx_client_pod_repeat_reboot_001_20261031_02_55_24",
    "lingqu_kvcache_dfx_client_process_get_hangup_001_20260929_07_47_42",
    "lingqu_kvcache_dfx_client_process_local_recall_exit_start_001_20261020_23_18_44",
    "lingqu_kvcache_dfx_client_process_local_recall_exit_start_001_20261030_23_02_01",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261011_09_35_44",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261013_13_09_56",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261013_19_38_25",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261013_20_11_02",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261013_23_27_14",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261021_06_51_48",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261024_22_16_35",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261108_09_16_39",
    "lingqu_kvcache_dfx_client_process_scale_down_worker_hang_up_001_20261110_00_17_01",
    "lingqu_kvcache_dfx_client_process_set_exit_001_20261014_16_45_27",
    "lingqu_kvcache_dfx_client_process_set_exit_001_20261031_03_52_30",
    "lingqu_kvcache_dfx_client_process_set_exit_002_20261031_00_55_09",
    "lingqu_kvcache_dfx_client_process_set_exit_cross_node_001_20261031_02_31_09",
    "lingqu_kvcache_dfx_client_process_set_exit_start_001_20260929_04_12_49",
    "lingqu_kvcache_dfx_client_process_set_exit_start_001_20261015_16_54_17",
    "lingqu_kvcache_dfx_client_process_set_exit_start_001_20261015_17_17_23",
    "lingqu_kvcache_dfx_client_process_set_exit_start_001_20261024_00_02_40",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261014_18_29_36",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261016_10_48_09",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261016_11_01_53",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261016_13_22_59",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261016_16_21_38",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261016_16_47_18",
    "lingqu_kvcache_dfx_client_process_tcp_down_001_20261019_10_33_03",
    "lingqu_kvcache_dfx_client_remote_coordinator_unavailable_001_20260924_07_25_09",
    "lingqu_kvcache_dfx_client_remote_coordinator_unavailable_001_20260924_07_30_06",
    "lingqu_kvcache_dfx_client_scale_down_tcp_bandwidth_limited_001_20261009_14_40_19",
    "lingqu_kvcache_dfx_client_scale_down_tcp_bandwidth_limited_001_20261024_20_52_05",
    "lingqu_kvcache_dfx_client_scale_down_tcp_delay_001_20260924_08_02_50",
    "lingqu_kvcache_dfx_client_scale_down_tcp_flapping_001_20260924_10_14_33",
    "lingqu_kvcache_dfx_client_scale_down_tcp_flapping_001_20261021_09_37_08",
    "lingqu_kvcache_dfx_client_scale_down_tcp_jitter_001_20260924_11_03_34",
    "lingqu_kvcache_dfx_client_scale_down_tcp_loss_001_20261108_15_55_04",
    "lingqu_kvcache_dfx_client_scale_down_tcp_loss_001_20261110_00_43_54",
    "lingqu_kvcache_dfx_client_scale_down_tcp_loss_002_20260924_08_07_20",
    "lingqu_kvcache_dfx_client_scale_down_tcp_loss_002_20261108_16_01_01",
    "lingqu_kvcache_dfx_client_scale_in_tcp_down_001_20260923_17_13_30",
    "lingqu_kvcache_dfx_client_scale_in_tcp_down_001_20261009_02_15_15",
    "lingqu_kvcache_dfx_client_scale_in_tcp_down_001_20261023_22_13_38",
    "lingqu_kvcache_dfx_client_scale_up_OS_storage_little_001_20260924_07_47_47",
    "lingqu_kvcache_dfx_client_scale_up_OS_storage_little_001_20261024_19_07_58",
    "lingqu_kvcache_dfx_client_scale_up_tcp_jitter_001_20260924_09_08_55",
    "lingqu_kvcache_dfx_client_scale_up_tcp_jitter_001_20260930_04_06_27",
    "lingqu_kvcache_dfx_client_scale_up_tcp_jitter_001_20261009_14_43_24",
    "lingqu_kvcache_dfx_client_scale_up_tcp_jitter_001_20261011_02_33_40",
    "lingqu_kvcache_dfx_client_scale_up_tcp_jitter_001_20261024_20_56_12",
    "lingqu_kvcache_dfx_client_scale_up_tcp_jitter_001_20261108_07_04_48",
    "lingqu_kvcache_dfx_client_scale_up_tcp_loss_001_20260924_09_29_10",
    "lingqu_kvcache_dfx_client_scale_up_tcp_loss_001_20260930_10_11_06",
    "lingqu_kvcache_dfx_client_scale_up_tcp_loss_002_20260924_06_50_35",
    "lingqu_kvcache_dfx_client_scale_up_tcp_loss_002_20261108_15_39_13",
    "lingqu_kvcache_dfx_client_scale_up_tcp_loss_002_20261110_00_34_11",
    "lingqu_kvcache_dfx_client_write_remote_after_ubm_fault_001_20260929_10_27_55",
    "lingqu_kvcache_dfx_client_write_remote_after_ubm_fault_001_20261107_23_29_22",
    "lingqu_kvcache_dfx_client_write_remote_after_ubse_fault_001_20260929_14_30_33",
    "lingqu_kvcache_dfx_client_write_remote_after_ubse_fault_001_20261023_01_05_00",
    "lingqu_kvcache_dfx_client_write_remote_worker_service_discovery_worker_reboot_001_20260924_05_33_39",
    "lingqu_kvcache_dfx_client_write_remote_worker_service_discovery_worker_reboot_001_20261011_07_07_13",
    "lingqu_kvcache_dfx_client_write_remote_worker_service_discovery_worker_reboot_001_20261024_16_28_56",
    "lingqu_kvcache_dfx_client_write_remote_worker_service_discovery_worker_reboot_001_20261108_04_54_15",
    "lingqu_kvcache_dfx_coordinator_cluster_exit_001_20260924_06_22_27",
    "lingqu_kvcache_dfx_coordinator_cluster_exit_001_20261024_17_10_27",
    "lingqu_kvcache_dfx_coordinator_cluster_exit_before_set_001_20260924_07_54_44",
    "lingqu_kvcache_dfx_coordinator_cluster_rolling_restart_001_20260924_06_15_25",
    "lingqu_kvcache_dfx_coordinator_cluster_rolling_restart_001_20261024_16_12_05",
    "lingqu_kvcache_dfx_coordinator_cluster_rolling_restart_before_set_001_20260924_04_53_30",
    "lingqu_kvcache_dfx_coordinator_cluster_tcp_network_delay_300_001_20260924_04_49_46",
    "lingqu_kvcache_dfx_coordinator_cluster_tcp_network_delay_300_001_20261108_10_54_53",
    "lingqu_kvcache_dfx_coordinator_main_fault_before_set_001_20260924_01_52_21",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261009_01_54_10",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261027_20_28_09",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261028_00_15_27",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261104_06_00_51",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261105_05_41_29",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261106_07_19_44",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261107_13_34_41",
    "lingqu_kvcache_dfx_coordinator_main_process_fault_scale_in_worker_001_20261107_14_14_33",
    "lingqu_kvcache_dfx_coordinator_main_process_repeat_restart_scale_in_worker_install_sdk_001_20261109_23_19_03",
    "lingqu_kvcache_dfx_coordinator_process_exit_001_20261015_16_39_16",
    "lingqu_kvcache_dfx_coordinator_process_exit_001_20261015_16_45_51",
    "lingqu_kvcache_dfx_coordinator_process_exit_001_20261016_09_44_22",
    "lingqu_kvcache_dfx_coordinator_process_exit_001_20261016_14_52_12",
    "lingqu_kvcache_dfx_coordinator_tcp_network_delay_install_sdk_001_20260929_07_54_20",
    "lingqu_kvcache_dfx_coordinator_tcp_network_loss_001_20260928_21_41_37",
    "lingqu_kvcache_dfx_key_non_spread_003_20261015_13_04_04",
    "lingqu_kvcache_dfx_key_non_spread_003_20261031_03_44_48",
    "lingqu_kvcache_dfx_key_non_spread_003_20261103_01_55_20",
    "lingqu_kvcache_dfx_key_non_spread_003_20261107_04_49_38",
    "lingqu_kvcache_dfx_local_ub_all_port_down_001_20260929_16_03_50",
    "lingqu_kvcache_dfx_local_ub_all_port_down_001_20261008_19_28_14",
    "lingqu_kvcache_dfx_local_ub_all_port_down_001_20261022_23_07_34",
    "lingqu_kvcache_dfx_local_ub_all_port_down_001_20261106_06_28_12",
    "lingqu_kvcache_dfx_local_ub_all_port_down_001_20261107_12_41_21",
    "lingqu_kvcache_dfx_local_ub_all_port_link_loss_001_20261015_17_37_13",
    "lingqu_kvcache_dfx_local_ub_all_port_link_loss_001_20261015_20_10_05",
    "lingqu_kvcache_dfx_local_ub_all_port_link_loss_001_20261016_02_06_46",
    "lingqu_kvcache_dfx_local_ub_single_socket_two_port_down_001_20261105_00_22_38",
    "lingqu_kvcache_dfx_local_ub_single_socket_two_port_lanedown_001_20260924_02_09_22",
    "lingqu_kvcache_dfx_local_ub_single_socket_two_port_link_loss_001_20260924_04_28_16",
    "lingqu_kvcache_dfx_local_ub_two_socket_single_port_lanedown_001_20260924_02_01_04",
    "lingqu_kvcache_dfx_metadata_affinity_recall_local_ub_port_down_001_20261107_13_09_30",
    "lingqu_kvcache_dfx_metadata_affinity_recall_worker_pod_reboot_001_20261030_23_54_13",
    "lingqu_kvcache_dfx_metadata_affinity_recall_worker_process_repeat_reboot_001_20261020_23_55_05",
    "lingqu_kvcache_dfx_metadata_affinity_recall_worker_process_repeat_reboot_001_20261030_23_38_10",
    "lingqu_kvcache_dfx_metadata_affinity_refine_sdk_pod_reboot_001_20261021_00_20_09",
    "lingqu_kvcache_dfx_metadata_affinity_refine_sdk_pod_reboot_001_20261031_00_02_38",
    "lingqu_kvcache_dfx_metadata_affinity_refine_tcp_delay_001_20260929_15_19_39",
    "lingqu_kvcache_dfx_metadata_affinity_refine_tcp_delay_001_20261009_02_20_11",
    "lingqu_kvcache_dfx_metadata_affinity_refine_tcp_delay_001_20261023_00_44_40",
    "lingqu_kvcache_dfx_metadata_affinity_refine_tcp_delay_001_20261024_02_21_12",
    "lingqu_kvcache_dfx_metadata_affinity_refine_tcp_delay_001_20261106_07_38_47",
    "lingqu_kvcache_dfx_metadata_affinity_refine_tcp_delay_001_20261107_11_44_10",
    "lingqu_kvcache_dfx_metadata_affinity_refine_ub_port_flashdown_001_20261024_01_14_18",
    "lingqu_kvcache_dfx_metadata_affinity_refine_worker_process_hangup_001_20261031_00_06_56",
    "lingqu_kvcache_dfx_metadata_affinity_write_sdk_process_exit_001_20261031_02_27_02",
    "lingqu_kvcache_dfx_metadata_affinity_write_ub_all_port_down_001_20260929_05_54_56",
    "lingqu_kvcache_dfx_metadata_affinity_write_ub_all_port_down_001_20261009_01_30_12",
    "lingqu_kvcache_dfx_metadata_affinity_write_ub_all_port_down_001_20261024_08_26_21",
    "lingqu_kvcache_dfx_metadata_affinity_write_ub_all_port_down_001_20261104_05_09_59",
    "lingqu_kvcache_dfx_metadata_affinity_write_ub_all_port_down_001_20261107_14_21_13",
    "lingqu_kvcache_dfx_ps_1_n_001_20261031_03_20_51",
    "lingqu_kvcache_dfx_ps_n_1_001_20261021_11_26_54",
    "lingqu_kvcache_dfx_ps_n_1_001_20261031_02_03_56",
    "lingqu_kvcache_dfx_ps_n_n_001_20260924_16_46_23",
    "lingqu_kvcache_dfx_ps_n_n_001_20261013_19_21_35",
    "lingqu_kvcache_dfx_ps_n_n_001_20261013_19_46_44",
    "lingqu_kvcache_dfx_ps_n_n_001_20261016_11_17_53",
    "lingqu_kvcache_dfx_ps_n_n_001_20261016_14_21_34",
    "lingqu_kvcache_dfx_ps_n_n_001_20261016_14_46_32",
    "lingqu_kvcache_dfx_ps_n_n_001_20261031_01_10_01",
    "lingqu_kvcache_dfx_ps_recall_1_75m_20261019_15_00_54",
    "lingqu_kvcache_dfx_ps_recall_1_75m_20261020_16_43_52",
    "lingqu_kvcache_dfx_ps_recall_1_75m_20261104_16_09_44",
    "lingqu_kvcache_dfx_ps_recall_4_Single_1_75M_inject_io_wait_write_20261102_15_39_21",
    "lingqu_kvcache_dfx_r_client_process_set_hangup_001_20261031_03_15_36",
    "lingqu_kvcache_dfx_r_client_update_001_20260929_07_20_04",
    "lingqu_kvcache_dfx_r_discovery_worker_process_hangup_001_20261008_20_23_35",
    "lingqu_kvcache_dfx_r_discovery_worker_process_hangup_001_20261010_18_34_48",
    "lingqu_kvcache_dfx_r_discovery_worker_process_hangup_001_20261023_08_45_42",
    "lingqu_kvcache_dfx_r_discovery_worker_process_hangup_001_20261024_04_59_06",
    "lingqu_kvcache_dfx_r_discovery_worker_process_hangup_001_20261104_06_46_16",
    "lingqu_kvcache_dfx_r_discovery_worker_process_hangup_001_20261107_06_41_07",
    "lingqu_kvcache_dfx_r_worker_process_net_fault_001_20260924_11_11_48",
    "lingqu_kvcache_dfx_r_worker_process_net_fault_001_20261021_07_02_44",
    "lingqu_kvcache_dfx_r_worker_process_net_fault_001_20261108_12_03_44",
    "lingqu_kvcache_dfx_r_worker_process_net_fault_003_20260924_12_53_24",
    "lingqu_kvcache_dfx_r_worker_process_net_fault_003_20261021_09_20_07",
    "lingqu_kvcache_dfx_r_worker_process_net_fault_003_20261108_13_50_57",
    "lingqu_kvcache_dfx_r_worker_process_set_UBM_001_20260929_09_23_42",
    "lingqu_kvcache_dfx_r_worker_process_set_UBM_001_20261008_23_17_05",
    "lingqu_kvcache_dfx_r_worker_process_set_UBM_001_20261023_02_32_33",
    "lingqu_kvcache_dfx_r_worker_process_set_UBM_001_20261105_00_30_22",
    "lingqu_kvcache_dfx_r_worker_process_set_UBM_001_20261107_14_48_52",
    "lingqu_kvcache_dfx_r_worker_process_set_UBSE_001_20260929_00_27_34",
    "lingqu_kvcache_dfx_r_worker_process_set_UBSE_001_20260929_18_54_08",
    "lingqu_kvcache_dfx_r_worker_process_set_UBSE_001_20260929_19_53_46",
    "lingqu_kvcache_dfx_r_worker_process_set_UBSE_001_20261022_23_39_32",
    "lingqu_kvcache_dfx_r_worker_process_set_exit_001_20260929_06_24_29",
    "lingqu_kvcache_dfx_r_worker_process_set_exit_001_20261009_01_37_04",
    "lingqu_kvcache_dfx_r_worker_process_set_exit_001_20261023_11_25_46",
    "lingqu_kvcache_dfx_r_worker_process_set_exit_001_20261024_08_16_53",
    "lingqu_kvcache_dfx_r_worker_process_set_exit_001_20261104_04_49_03",
    "lingqu_kvcache_dfx_r_worker_process_set_exit_001_20261107_14_05_02",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_001_20260923_20_56_31",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_001_20261009_20_12_13",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_001_20261012_14_34_31",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_001_20261020_23_46_05",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_001_20261030_23_29_09",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_002_20260924_11_16_31",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_002_20261021_07_11_11",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_002_20261108_12_11_54",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_003_20260924_12_58_06",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_003_20261021_09_29_02",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_003_20261108_13_59_55",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_004_20260924_12_48_44",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_004_20261021_09_11_48",
    "lingqu_kvcache_dfx_r_worker_process_set_hangup_004_20261108_13_42_22",
    "lingqu_kvcache_dfx_recall_1z3b_1port_fault_006_20261031_02_39_08",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_004_20260929_08_41_05",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_004_20261008_23_25_27",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_004_20261023_02_40_53",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_004_20261105_00_38_44",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_004_20261107_15_58_08",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_007_20260929_02_30_44",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_007_20261008_20_53_26",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_007_20261023_09_09_02",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_007_20261104_01_02_16",
    "lingqu_kvcache_dfx_recall_1z3b_2ports_fault_007_20261108_01_33_52",
    "lingqu_kvcache_dfx_remote_ub_all_port_down_001_20260929_05_22_54",
    "lingqu_kvcache_dfx_remote_ub_all_port_down_001_20261009_08_35_52",
    "lingqu_kvcache_dfx_remote_ub_all_port_down_001_20261023_13_01_54",
    "lingqu_kvcache_dfx_remote_ub_all_port_down_001_20261104_03_49_26",
    "lingqu_kvcache_dfx_remote_ub_all_port_down_001_20261107_16_41_49",
    "lingqu_kvcache_dfx_remote_ub_single_socket_two_port_down_001_20261009_10_31_43",
    "lingqu_kvcache_dfx_sdk_install_tcp_net_down_001_20261022_23_30_41",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_net_fault_001_20261011_09_47_49",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_net_fault_001_20261021_09_43_48",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_net_fault_001_20261108_11_15_57",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_net_fault_002_20260924_04_13_14",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_restart_001_20261024_18_35_58",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_restart_002_20261021_10_30_40",
    "lingqu_kvcache_dfx_sdk_process_scale_in_coordinator_restart_002_20261108_09_59_45",
    "lingqu_kvcache_dfx_spec_keys_n_1_001_20261010_10_28_30",
    "lingqu_kvcache_dfx_worker2_exit_scaleout_tcp_scalein_ub_lanedown_001_20260924_03_33_16",
    "lingqu_kvcache_dfx_worker2_exit_scaleout_tcp_scalein_ub_lanedown_001_20261011_05_08_31",
    "lingqu_kvcache_dfx_worker2_exit_scaleout_tcp_scalein_ub_lanedown_001_20261013_15_05_52",
    "lingqu_kvcache_dfx_worker2_exit_scaleout_tcp_scalein_ub_lanedown_001_20261024_11_44_18",
    "lingqu_kvcache_dfx_worker2_exit_scaleout_tcp_scalein_ub_lanedown_001_20261108_10_09_44",
    "lingqu_kvcache_dfx_worker_chain_migration_001_20260923_16_24_44",
    "lingqu_kvcache_dfx_worker_chain_migration_001_20260924_08_47_18",
    "lingqu_kvcache_dfx_worker_chain_migration_001_20261009_14_21_42",
    "lingqu_kvcache_dfx_worker_chain_migration_001_20261011_02_10_15",
    "lingqu_kvcache_dfx_worker_chain_migration_001_20261024_20_36_45",
    "lingqu_kvcache_dfx_worker_chain_migration_001_20261108_07_15_23",
    "lingqu_kvcache_dfx_worker_cluster_memory_balance_ratio_normal_scene_001_20261027_19_19_08",
    "lingqu_kvcache_dfx_worker_cluster_memory_balance_ratio_normal_scene_001_20261029_20_04_50",
    "lingqu_kvcache_dfx_worker_down_lane_scale_out_001_20260924_11_43_03",
    "lingqu_kvcache_dfx_worker_down_lane_scale_out_001_20261021_08_11_32",
    "lingqu_kvcache_dfx_worker_down_lane_scale_out_001_20261108_13_01_48",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20260924_12_07_31",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20260930_07_34_39",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20261009_18_00_18",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20261011_03_16_38",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20261021_07_39_48",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20261024_14_05_35",
    "lingqu_kvcache_dfx_worker_exit_scale_out_001_20261108_13_10_20",
    "lingqu_kvcache_dfx_worker_mixed_pod_fault_001_20260924_10_42_40",
    "lingqu_kvcache_dfx_worker_mixed_pod_fault_001_20261011_10_49_09",
    "lingqu_kvcache_dfx_worker_mixed_pod_fault_001_20261021_10_39_52",
    "lingqu_kvcache_dfx_worker_mixed_pod_fault_001_20261024_12_34_18",
    "lingqu_kvcache_dfx_worker_mixed_pod_fault_001_20261108_09_47_34",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20260924_08_18_54",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20260930_04_38_42",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261009_13_40_58",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261011_01_28_58",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261013_21_56_01",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261014_17_17_08",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261014_22_27_43",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261024_19_55_57",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261028_04_25_58",
    "lingqu_kvcache_dfx_worker_mixed_scale_tcp_ub_fault_001_20261108_06_43_04",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20260924_03_10_07",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20260930_04_11_14",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261013_20_02_03",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261013_20_25_30",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261013_21_12_34",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261014_12_00_23",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261014_14_11_20",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261014_22_46_10",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261024_12_46_08",
    "lingqu_kvcache_dfx_worker_multi_node_exit_scale_ub_fault_001_20261108_10_32_13",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20260924_05_01_43",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20260930_08_42_47",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261011_05_59_20",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261013_14_40_53",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261013_22_14_31",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261014_22_22_08",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261015_11_46_59",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261015_15_32_01",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261015_15_42_51",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261015_15_52_44",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261015_16_01_23",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261108_11_00_05",
    "lingqu_kvcache_dfx_worker_multi_scale_tcp_fault_001_20261109_23_38_28",
    "lingqu_kvcache_dfx_worker_multiple_scale_and_exit_001_20260924_02_45_03",
    "lingqu_kvcache_dfx_worker_multiple_scale_and_exit_001_20261011_07_47_27",
    "lingqu_kvcache_dfx_worker_multiple_scale_and_exit_001_20261024_22_36_48",
    "lingqu_kvcache_dfx_worker_multiple_scale_and_exit_001_20261108_05_24_41",
    "lingqu_kvcache_dfx_worker_pod_double_reboot_001_20260924_04_36_38",
    "lingqu_kvcache_dfx_worker_pod_double_reboot_001_20261011_04_56_20",
    "lingqu_kvcache_dfx_worker_pod_double_reboot_001_20261024_11_16_43",
    "lingqu_kvcache_dfx_worker_pod_double_reboot_001_20261108_09_35_03",
    "lingqu_kvcache_dfx_worker_pod_reboot_001_20261008_15_35_46",
    "lingqu_kvcache_dfx_worker_pod_reboot_001_20261012_12_10_58",
    "lingqu_kvcache_dfx_worker_pod_reboot_001_20261020_22_01_24",
    "lingqu_kvcache_dfx_worker_pod_reboot_001_20261031_01_42_26",
    "lingqu_kvcache_dfx_worker_pod_reboot_001_20261103_04_47_26",
    "lingqu_kvcache_dfx_worker_pod_reboot_l2_001_20261020_22_43_31",
    "lingqu_kvcache_dfx_worker_pod_reboot_l2_001_20261031_02_22_58",
    "lingqu_kvcache_dfx_worker_pod_repeat_reboot_001_20260928_21_45_42",
    "lingqu_kvcache_dfx_worker_pod_repeat_reboot_002_20261009_19_28_31",
    "lingqu_kvcache_dfx_worker_pod_repeat_reboot_002_20261031_02_48_45",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20260929_04_00_55",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20261009_03_59_07",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20261023_23_56_34",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20261027_21_27_51",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20261028_01_16_20",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20261030_11_15_15",
    "lingqu_kvcache_dfx_worker_process_bandwidth_limit_001_20261030_11_23_22",
    "lingqu_kvcache_dfx_worker_process_cross_node_net_card_loss_001_20260923_19_38_05",
    "lingqu_kvcache_dfx_worker_process_cross_node_net_card_loss_001_20261022_12_47_50",
    "lingqu_kvcache_dfx_worker_process_double_exit_001_20260930_06_13_48",
    "lingqu_kvcache_dfx_worker_process_double_exit_001_20261009_13_31_30",
    "lingqu_kvcache_dfx_worker_process_double_exit_001_20261011_01_19_28",
    "lingqu_kvcache_dfx_worker_process_double_exit_001_20261024_19_35_52",
    "lingqu_kvcache_dfx_worker_process_double_exit_001_20261108_07_30_45",
    "lingqu_kvcache_dfx_worker_process_exit_cross_node_get_001_20260924_12_02_52",
    "lingqu_kvcache_dfx_worker_process_exit_cross_node_get_001_20261021_08_28_04",
    "lingqu_kvcache_dfx_worker_process_exit_cross_node_get_001_20261108_13_31_00",
    "lingqu_kvcache_dfx_worker_process_exit_l2_001_20261008_17_02_44",
    "lingqu_kvcache_dfx_worker_process_exit_l2_001_20261031_03_58_04",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_001_20260924_11_25_21",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_001_20260930_07_51_10",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_001_20261011_03_08_04",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_001_20261021_07_30_52",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_001_20261024_13_57_00",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_001_20261108_12_47_14",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_same_time_001_20260924_11_21_12",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_same_time_001_20260930_07_43_25",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_same_time_001_20261011_03_38_50",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_same_time_001_20261021_08_03_27",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_same_time_001_20261024_14_30_50",
    "lingqu_kvcache_dfx_worker_process_exit_scale_in_mul_same_time_001_20261108_12_39_07",
    "lingqu_kvcache_dfx_worker_process_exit_single_node_001_20260929_09_08_17",
    "lingqu_kvcache_dfx_worker_process_exit_single_node_001_20261103_22_44_14",
    "lingqu_kvcache_dfx_worker_process_exit_single_node_001_20261107_19_49_45",
    "lingqu_kvcache_dfx_worker_process_get_exit_mul_001_20260924_13_02_43",
    "lingqu_kvcache_dfx_worker_process_get_exit_mul_001_20261011_04_43_57",
    "lingqu_kvcache_dfx_worker_process_get_exit_mul_001_20261024_16_03_13",
    "lingqu_kvcache_dfx_worker_process_get_exit_mul_001_20261028_03_31_11",
    "lingqu_kvcache_dfx_worker_process_get_exit_mul_001_20261108_14_08_14",
    "lingqu_kvcache_dfx_worker_process_local_get_coordinator_main_fail_001_20261011_09_29_45",
    "lingqu_kvcache_dfx_worker_process_local_get_coordinator_main_fail_001_20261021_06_45_57",
    "lingqu_kvcache_dfx_worker_process_local_get_coordinator_main_fail_001_20261024_22_10_19",
    "lingqu_kvcache_dfx_worker_process_local_get_os_cpu_overload_001_20261024_22_25_21",
    "lingqu_kvcache_dfx_worker_process_local_get_os_cpu_overload_001_20261108_11_43_55",
    "lingqu_kvcache_dfx_worker_process_local_get_os_cpu_overload_001_20261110_09_25_43",
    "lingqu_kvcache_dfx_worker_process_local_get_os_disk_iolatency_001_20260924_07_35_05",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20260923_23_32_14",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20260929_22_04_13",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261009_22_30_07",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261012_12_55_06",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261022_14_39_53",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261031_02_18_56",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261103_04_58_47",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261106_04_29_21",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_001_20261107_02_22_54",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20260923_23_14_23",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20260929_21_46_22",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261009_22_12_25",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261012_12_41_26",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261022_14_32_33",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261023_20_02_04",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261031_02_13_21",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261103_04_38_07",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261106_03_46_59",
    "lingqu_kvcache_dfx_worker_process_local_ub_link_down_002_20261107_01_40_30",
    "lingqu_kvcache_dfx_worker_process_net_card_loss_001_20260929_23_44_57",
    "lingqu_kvcache_dfx_worker_process_net_card_loss_001_20261012_14_01_43",
    "lingqu_kvcache_dfx_worker_process_net_card_loss_001_20261025_01_40_33",
    "lingqu_kvcache_dfx_worker_process_net_card_loss_001_20261103_06_40_25",
    "lingqu_kvcache_dfx_worker_process_net_card_loss_001_20261108_14_55_41",
    "lingqu_kvcache_dfx_worker_process_rebalance_normal_001_20261009_21_24_51",
    "lingqu_kvcache_dfx_worker_process_rebalance_normal_001_20261022_12_42_18",
    "lingqu_kvcache_dfx_worker_process_rebalance_normal_001_20261031_01_36_56",
    "lingqu_kvcache_dfx_worker_process_rebalance_resource_monitor_exit_001_20261010_16_25_29",
    "lingqu_kvcache_dfx_worker_process_rebalance_resource_monitor_exit_001_20261010_22_45_34",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20260928_21_03_04",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20260928_21_27_35",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261009_16_11_33",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261010_15_55_46",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261010_16_16_28",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261022_21_41_15",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261105_04_04_08",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261106_06_01_35",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261107_08_49_59",
    "lingqu_kvcache_dfx_worker_process_rebalance_source_exit_001_20261107_10_16_50",
    "lingqu_kvcache_dfx_worker_process_rebalance_target_exit_001_20261021_01_15_59",
    "lingqu_kvcache_dfx_worker_process_rebalance_target_exit_001_20261031_01_30_33",
    "lingqu_kvcache_dfx_worker_process_rebalance_target_hangup_001_20260928_21_35_03",
    "lingqu_kvcache_dfx_worker_process_remote_local_tcp_net_card_delay_001_20261009_02_09_10",
    "lingqu_kvcache_dfx_worker_process_remote_local_tcp_net_card_delay_001_20261023_00_34_30",
    "lingqu_kvcache_dfx_worker_process_remote_local_tcp_net_card_delay_001_20261104_22_49_29",
    "lingqu_kvcache_dfx_worker_process_remote_local_tcp_net_card_delay_001_20261107_11_59_08",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261015_15_39_20",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261015_17_33_19",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261015_20_03_24",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261016_02_00_40",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261016_11_09_33",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261016_14_06_18",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261016_14_12_22",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_link_loss_001_20261016_14_17_12",
    "lingqu_kvcache_dfx_worker_process_remote_local_ub_single_port_down_001_20261023_05_24_25",
    "lingqu_kvcache_dfx_worker_process_remote_recall_ub_port_all_down_001_20261023_08_59_07",
    "lingqu_kvcache_dfx_worker_process_remote_recall_ub_port_all_down_001_20261104_06_32_59",
    "lingqu_kvcache_dfx_worker_process_remote_recall_ub_port_all_down_001_20261107_05_56_05",
    "lingqu_kvcache_dfx_worker_process_remote_recall_ub_port_flashing_001_20261023_10_19_12",
    "lingqu_kvcache_dfx_worker_process_remote_remote_ub_single_port_down_001_20261023_04_26_05",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20260924_01_15_02",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20260929_22_17_01",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261008_14_37_18",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261009_21_12_03",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261012_12_04_28",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261021_01_09_27",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261022_10_41_44",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261031_01_26_16",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261103_06_23_42",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261106_05_28_36",
    "lingqu_kvcache_dfx_worker_process_remote_ub_link_down_001_20261107_00_07_56",
    "lingqu_kvcache_dfx_worker_process_remote_ub_nfe_001_20261031_03_07_28",
    "lingqu_kvcache_dfx_worker_process_repeat_exit_001_20260930_02_28_01",
    "lingqu_kvcache_dfx_worker_process_repeat_exit_001_20261012_13_55_57",
    "lingqu_kvcache_dfx_worker_process_repeat_exit_001_20261031_00_34_57",
    "lingqu_kvcache_dfx_worker_process_repeat_exit_001_20261103_02_44_46",
    "lingqu_kvcache_dfx_worker_process_repeat_exit_001_20261106_22_46_07",
    "lingqu_kvcache_dfx_worker_process_repeat_exit_002_20261031_03_11_31",
    "lingqu_kvcache_dfx_worker_process_scale_in_after_ubm_001_20261008_20_42_35",
    "lingqu_kvcache_dfx_worker_process_scale_in_after_ubm_001_20261024_04_48_16",
    "lingqu_kvcache_dfx_worker_process_scale_in_after_ubm_001_20261104_07_33_11",
    "lingqu_kvcache_dfx_worker_process_scale_in_after_ubm_001_20261105_01_31_50",
    "lingqu_kvcache_dfx_worker_process_scale_in_after_ubm_001_20261106_06_35_56",
    "lingqu_kvcache_dfx_worker_process_scale_in_after_ubm_001_20261107_06_01_44",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20260929_06_50_16",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261009_01_18_16",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261010_17_58_37",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261010_20_24_30",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261024_08_33_15",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261104_05_48_04",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261107_14_35_55",
    "lingqu_kvcache_dfx_worker_process_scale_in_before_ubm_001_20261109_23_23_40",
    "lingqu_kvcache_dfx_worker_process_scale_in_coordinator_restart_001_20260923_17_10_35",
    "lingqu_kvcache_dfx_worker_process_scale_in_coordinator_restart_001_20261108_11_50_15",
    "lingqu_kvcache_dfx_worker_process_scale_in_mul_001_20261021_09_03_35",
    "lingqu_kvcache_dfx_worker_process_scale_in_mul_001_20261024_15_38_08",
    "lingqu_kvcache_dfx_worker_process_scale_in_mul_001_20261028_05_13_46",
    "lingqu_kvcache_dfx_worker_process_scale_in_mul_same_time_001_20261021_08_39_10",
    "lingqu_kvcache_dfx_worker_process_scale_in_remote_ub_link_down_001_20261008_16_22_11",
    "lingqu_kvcache_dfx_worker_process_scale_in_remote_ub_link_down_001_20261031_03_03_32",
    "lingqu_kvcache_dfx_worker_process_scale_in_remote_ub_nfe_001_20261021_00_14_54",
    "lingqu_kvcache_dfx_worker_process_scale_in_remote_ub_nfe_001_20261030_23_58_32",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_bandwidth_limit_001_20260924_01_32_54",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_bandwidth_limit_001_20261011_08_56_16",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_bandwidth_limit_001_20261021_06_14_44",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_bandwidth_limit_001_20261024_21_34_53",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_bandwidth_limit_001_20261108_09_24_33",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_delay_001_20260924_02_28_39",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_delay_001_20261011_08_38_28",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_delay_001_20261021_05_56_58",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_delay_001_20261024_21_14_05",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_delay_001_20261108_08_32_50",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20260924_02_17_48",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261011_09_08_56",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261013_14_14_26",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261021_06_25_42",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261021_14_47_53",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261021_15_06_34",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261021_15_21_28",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261024_21_58_16",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_link_flapping_001_20261108_09_06_33",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_loss_001_20261025_01_55_32",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_loss_001_20261103_07_15_42",
    "lingqu_kvcache_dfx_worker_process_scale_in_tcp_loss_001_20261108_15_08_32",
    "lingqu_kvcache_dfx_worker_process_scale_in_ub_local_reduce_lane_001_20261013_12_50_38",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_net_fault_001_20261011_09_20_08",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_net_fault_001_20261021_06_36_52",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_net_fault_001_20261109_23_56_02",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20260924_09_21_23",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20260924_09_34_39",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20261021_10_22_40",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20261021_10_51_51",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20261024_21_45_59",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20261108_11_06_01",
    "lingqu_kvcache_dfx_worker_process_scale_out_coordinator_restart_001_20261109_23_44_40",
    "lingqu_kvcache_dfx_worker_process_scale_out_mul_001_20261021_08_46_30",
    "lingqu_kvcache_dfx_worker_process_scale_out_mul_same_time_001_20261021_08_55_09",
    "lingqu_kvcache_dfx_worker_process_set_exit_001_20261009_23_05_24",
    "lingqu_kvcache_dfx_worker_process_set_exit_001_20261030_23_50_14",
    "lingqu_kvcache_dfx_worker_process_set_exit_001_20261102_22_37_03",
    "lingqu_kvcache_dfx_worker_process_upgrade_OS_mem_little_001_20261109_17_11_11",
    "lingqu_kvcache_dfx_worker_process_upgrade_OS_mem_little_001_20261109_19_26_16",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_bandwidth_limit_001_20261109_15_40_23",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_bandwidth_limit_001_20261109_16_05_20",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_bandwidth_limit_001_20261109_16_32_48",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_bandwidth_limit_001_20261109_16_56_25",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_bandwidth_limit_001_20261109_19_39_48",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_delay_001_20261109_11_40_55",
    "lingqu_kvcache_dfx_worker_process_upgrade_tcp_jitter_001_20261109_14_58_34",
    "lingqu_kvcache_dfx_worker_process_upgrade_ub_local_double_port_down_001_20261023_12_51_24",
    "lingqu_kvcache_dfx_worker_process_upgrade_ub_local_double_port_down_001_20261024_05_54_07",
    "lingqu_kvcache_dfx_worker_process_upgrade_ub_local_double_port_down_001_20261104_07_55_01",
    "lingqu_kvcache_dfx_worker_process_upgrade_ub_local_double_port_down_001_20261107_23_00_07",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20260929_02_05_12",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261010_18_48_18",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261010_21_15_47",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261012_17_49_22",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261013_12_51_35",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261014_14_24_29",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261014_14_35_56",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261014_15_03_24",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261014_15_17_20",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261023_08_41_24",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261024_05_12_38",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261104_06_19_20",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261105_01_18_13",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261106_06_58_40",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261107_06_28_25",
    "lingqu_kvcache_dfx_worker_process_upgrade_ubm_001_20261109_23_10_03",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20260924_00_07_58",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20260930_01_55_44",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20261008_12_51_41",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20261009_18_46_20",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20261012_14_23_36",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20261021_02_54_15",
    "lingqu_kvcache_dfx_worker_process_write_net_card_loss_001_20261108_14_27_17",
    "lingqu_kvcache_dfx_worker_rebalance_etcd_fault_001_20260924_18_24_05",
    "lingqu_kvcache_dfx_worker_rebalance_etcd_fault_001_20261105_02_44_15",
    "lingqu_kvcache_dfx_worker_rebalance_multi_source_2_target_001_20260928_20_28_00",
    "lingqu_kvcache_dfx_worker_rebalance_tcp_flashdown_001_20260928_21_22_13",
    "lingqu_kvcache_dfx_worker_rebalance_ub_flashdown_001_20260928_20_36_40",
    "lingqu_kvcache_dfx_worker_reboot_single_node_001_20260928_22_51_34",
    "lingqu_kvcache_dfx_worker_reboot_single_node_001_20261009_12_58_19",
    "lingqu_kvcache_dfx_worker_reboot_single_node_001_20261023_06_00_23",
    "lingqu_kvcache_dfx_worker_reboot_single_node_001_20261106_06_43_59",
    "lingqu_kvcache_dfx_worker_reboot_single_node_001_20261107_06_55_14",
    "lingqu_kvcache_dfx_worker_reboot_single_node_001_20261109_22_45_19",
    "lingqu_kvcache_dfx_worker_remote_set_exit_002_20260928_20_42_02",
    "lingqu_kvcache_dfx_worker_remote_set_exit_003_20260928_21_14_49",
    "lingqu_kvcache_dfx_worker_scale_in_ub_flap_worker_exit_001_20260924_06_55_05",
    "lingqu_kvcache_dfx_worker_scale_in_ub_flap_worker_exit_001_20261024_17_52_00",
    "lingqu_kvcache_dfx_worker_scale_in_ub_flap_worker_exit_001_20261108_03_54_33",
    "lingqu_kvcache_dfx_worker_scale_up_tcp_flapping_001_20260924_09_13_44",
    "lingqu_kvcache_dfx_worker_sequential_double_exit_001_20260924_10_33_13",
    "lingqu_kvcache_dfx_worker_sequential_double_exit_001_20261011_10_11_57",
    "lingqu_kvcache_dfx_worker_sequential_double_exit_001_20261021_10_07_58",
    "lingqu_kvcache_dfx_worker_sequential_double_exit_001_20261024_12_05_59",
    "lingqu_kvcache_dfx_worker_sequential_double_exit_001_20261108_11_29_24",
    "lingqu_kvcache_dfx_worker_set_exit_002_20260929_07_28_35",
    "lingqu_kvcache_dfx_worker_tcp_interruption_cross_node_get_001_20260924_11_51_19",
    "lingqu_kvcache_dfx_worker_tcp_interruption_cross_node_get_001_20260930_07_15_55",
    "lingqu_kvcache_dfx_worker_tcp_interruption_cross_node_get_001_20261009_17_45_42",
    "lingqu_kvcache_dfx_worker_tcp_interruption_cross_node_get_001_20261021_07_19_59",
    "lingqu_kvcache_dfx_worker_tcp_interruption_cross_node_get_001_20261108_12_20_25",
    "lingqu_kvcache_dfx_worker_tcp_interruption_scale_out_001_20260924_11_29_30",
    "lingqu_kvcache_dfx_worker_tcp_interruption_scale_out_001_20261021_07_54_26",
    "lingqu_kvcache_dfx_worker_tcp_interruption_scale_out_001_20261108_13_19_22",
    "lingqu_kvcache_dfx_worker_ub_down_lane_cross_node_get_001_20260924_11_37_53",
    "lingqu_kvcache_dfx_worker_ub_down_lane_cross_node_get_001_20261021_08_20_05",
    "lingqu_kvcache_dfx_worker_ub_down_lane_cross_node_get_001_20261108_12_31_09",
    "lingqu_kvcache_dfx_worker_ub_port_flash_failure_001_20261107_17_44_10",
    "lingqu_kvcache_dfx_write_remote_tcp_flashdown_001_20261108_12_56_05",
    "lingqu_kvcache_dfx_write_remote_tcp_packet_loss_001_20261108_15_50_16",
    "lingqu_kvcache_dfx_write_remote_tcp_packet_loss_001_20261110_00_38_57",
]

# 追加任务名关键字过滤（可选）：非空时，任务名还需命中其中之一（子串或 glob）才收集。
TASK_NAME_KEYWORDS: list[str] = [
    # "worker_process_upgrade",       # 子串包含
    # "lingqu_kvcache_dfx_worker_*",  # 也支持 glob 通配
]

# 任务名排除关键字：任务名（目录名）命中任一关键字（子串，大小写不敏感）即整目录跳过，
# 优先级高于上面的白名单/关键字。下面 20 个场景的「关键词未出现在 labels.json 中」，
# 即无法被数据集打标评估（共覆盖白名单 45 个任务）→ 只保留有 label 的 562 个 case。
# 留空（[]）则不排除、收录全部 607 个任务。
TASK_NAME_EXCLUDE_KEYWORDS: list[str] = [
    "demo_chaos_001",
    "key_non_spread_003",
    "local_ub_all_port_link_loss_001",
    "ps_1_n_001",
    "ps_n_1_001",
    "ps_n_n_001",
    "ps_recall_1_75m",
    "ps_recall_4_Single_1_75M_inject_io_wait_write",
    "r_worker_process_net_fault_001",
    "r_worker_process_net_fault_003",
    "spec_keys_n_1_001",
    "worker_cluster_memory_balance_ratio_normal_scene_001",
    "worker_process_scale_out_mul_001",
    "worker_process_scale_out_mul_same_time_001",
    "worker_process_upgrade_OS_mem_little_001",
    "worker_process_upgrade_tcp_bandwidth_limit_001",
    "worker_process_upgrade_tcp_delay_001",
    "worker_process_upgrade_tcp_jitter_001",
    "worker_rebalance_etcd_fault_001",
    "worker_rebalance_multi_source_2_target_001",
]

# 资产库动态筛选用（仅当 TASK_NAME_ALLOWLIST 清空时才生效）
FAULT_TYPES = {"connectivity", "latency", "mixed"}

# ─────────── ③ 文件名过滤：显式黑名单 / 模式（不收集）───────────
# 命中任一「精确文件名」（FILE_EXCLUDE_NAMES）或「glob 模式」（FILE_EXCLUDE_PATTERNS）
# 的文件跳过；其余文件一律收集。（路径命中 ④ 的文件除外，见下）
FILE_EXCLUDE_NAMES: list[str] = [
    "test_case.log",   # 不收集
]
FILE_EXCLUDE_PATTERNS: list[str] = [
    "*access*.log",   # 已采集：访问日志
    "*.INFO*.log",    # 已采集：INFO 日志（含 xxx.INFO.log 与 xxx.INFO.<时间戳>.log）
]
# ─────────── ③b 无条件排除（优先级最高，不受 ④ 路径强制纳入豁免）───────────
# 文件名（小写）命中任一 glob 即跳过，任何情况下都不收集。
# 覆盖 ubse 各类日志：master_ubse.log / node_ubse.log / coordinator_UBSE.log，
# 以及轮转与压缩变体 master_ubse.log.1 / .gz / .20261116，和 master.ubse.log 等。
FILE_HARD_EXCLUDE_PATTERNS: list[str] = [
    "*ubse*.log*",
]

# ─────────── ④ 路径强制纳入（命中即收集，豁免 ③ 黑名单）───────────
# 文件「相对路径」（小写）包含任一关键字即强制收集，用于补收此前漏采的组件数据。
PATH_FORCE_INCLUDE_KEYWORDS: list[str] = [
    "coordinator",   # coordinator 数据此前未被有效收集，强制纳入
]
# (源目录名, 目标目录名)，均相对于脚本所在目录
JOBS = [("ci_yxh_new", "ci_yxh_new_app"), ("yxh_new", "yxh_new_app")]
PAGE_CNT = 100  # 资产库分页大小


def _log(msg: str) -> None:
    print(msg, flush=True)


def fetch_fault_tasks(api_base: str) -> set[str]:
    """翻页拉全资产库，返回 fault_type ∈ FAULT_TYPES 的 kb_name 集合。"""
    tasks: set[str] = set()
    page = 1
    total = None
    while True:
        body = json.dumps({
            "signals": [], "kb_id": None, "scope": "all",
            "page_cnt": PAGE_CNT, "page_num": page,
        }).encode()
        req = urllib.request.Request(
            api_base.rstrip("/") + API_SEARCH_PATH, data=body,
            headers={"Content-Type": "application/json"}, method="POST")
        # 绕过 HTTP 代理（等价 curl --noproxy）
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=60) as resp:
                data = json.loads(resp.read().decode())
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            raise SystemExit(f"[错误] 访问资产库失败 {api_base}: {exc}\n"
                             f"       若资产库不可达，可改用 --tasks-file 提供任务清单。")
        result = data.get("result") or {}
        matches = result.get("matches") or []
        if total is None:
            total = result.get("total")
            _log(f"[资产库] total={total}")
        for m in matches:
            case = m.get("case") or {}
            if case.get("fault_type") in FAULT_TYPES and case.get("kb_name"):
                tasks.add(str(case["kb_name"]).strip())
        if not matches or (total is not None and page * PAGE_CNT >= total):
            break
        page += 1
    return tasks


def read_tasks_file(path: str) -> set[str]:
    """离线清单：每行一个任务名（忽略空行与 # 注释）。"""
    tasks = set()
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            s = line.strip()
            if s and not s.startswith("#"):
                tasks.add(s)
    return tasks


def is_collected(filename: str) -> bool:
    """该文件是否命中「不收集」黑名单（精确名）或模式（glob）。"""
    low = filename.lower()
    if low in {n.lower() for n in FILE_EXCLUDE_NAMES}:
        return True
    return any(fnmatch.fnmatch(low, p.lower()) for p in FILE_EXCLUDE_PATTERNS)


def is_hard_excluded(filename: str) -> bool:
    """无条件排除（glob，大小写不敏感）：命中即跳过，不受 ④ 路径强制纳入影响。"""
    if not FILE_HARD_EXCLUDE_PATTERNS:
        return False
    low = filename.lower()
    return any(fnmatch.fnmatch(low, p.lower()) for p in FILE_HARD_EXCLUDE_PATTERNS)


def path_force_include(rel_in_task: str) -> bool:
    """「任务目录内的相对路径」命中 PATH_FORCE_INCLUDE_KEYWORDS（如 coordinator）→
    强制收集，豁免黑名单。注意：不含任务名本身，避免任务名含 coordinator 时整目录被豁免。"""
    if not PATH_FORCE_INCLUDE_KEYWORDS:
        return False
    low = rel_in_task.lower()
    return any(k.lower() in low for k in PATH_FORCE_INCLUDE_KEYWORDS)


def task_matches(folder: str, fault_tasks: set[str]) -> bool:
    """任务目录名与资产库 kb_name 的匹配（先精确，再前后缀容错）。"""
    f = folder.strip().rstrip("/")
    if f in fault_tasks:
        return True
    for t in fault_tasks:
        if t and (f.startswith(t) or t.startswith(f)):
            return True
    return False


def task_name_excluded(folder: str) -> bool:
    """任务名命中 TASK_NAME_EXCLUDE_KEYWORDS（子串，大小写不敏感）→ 排除。"""
    if not TASK_NAME_EXCLUDE_KEYWORDS:
        return False
    f = folder.strip().rstrip("/").lower()
    return any(k.lower() in f for k in TASK_NAME_EXCLUDE_KEYWORDS)


def task_name_allowed(folder: str) -> bool:
    """任务名是否通过 ②（白名单/关键字）；命中排除清单则直接否决。两清单都空 = 全部通过。"""
    f = folder.strip().rstrip("/")
    if task_name_excluded(f):
        return False
    if not TASK_NAME_ALLOWLIST and not TASK_NAME_KEYWORDS:
        return True
    if f in TASK_NAME_ALLOWLIST:
        return True
    lf = f.lower()
    for kw in TASK_NAME_KEYWORDS:
        k = kw.lower()
        if k in lf or fnmatch.fnmatch(lf, k):
            return True
    return False


def collect(src_root: str, dst_root: str, fault_tasks: set[str],
            dry_run: bool) -> dict:
    """遍历一个源目录，收集未采集文件。返回统计。"""
    stat = {"tasks_total": 0, "tasks_skipped_nofault": 0, "tasks_skipped_byname": 0,
            "tasks_processed": 0, "files_copied": 0, "files_skipped_collected": 0,
            "files_skipped_hard": 0,
            "files_skipped_exists": 0, "files_forced_include": 0, "copied": []}
    if not os.path.isdir(src_root):
        _log(f"[跳过] 源目录不存在: {src_root}")
        return stat

    for entry in sorted(os.listdir(src_root)):
        task_dir = os.path.join(src_root, entry)
        if not os.path.isdir(task_dir) or entry.startswith("."):
            continue
        stat["tasks_total"] += 1
        if not task_matches(entry, fault_tasks):
            stat["tasks_skipped_nofault"] += 1
            continue
        if not task_name_allowed(entry):
            stat["tasks_skipped_byname"] += 1
            continue
        stat["tasks_processed"] += 1
        for dirpath, dirnames, filenames in os.walk(task_dir):
            dirnames[:] = [d for d in dirnames if not d.startswith(".")]
            for fn in sorted(filenames):
                if fn.startswith("."):
                    continue
                src_file = os.path.join(dirpath, fn)
                rel = os.path.relpath(src_file, src_root)
                rel_in_task = os.path.relpath(src_file, task_dir)
                if is_hard_excluded(fn):          # ③b 无条件排除（含 ubse 及其变体）
                    stat["files_skipped_hard"] += 1
                    continue
                if is_collected(fn) and not path_force_include(rel_in_task):
                    stat["files_skipped_collected"] += 1
                    continue
                if is_collected(fn):
                    stat["files_forced_include"] += 1
                dst_file = os.path.join(dst_root, rel)
                if os.path.exists(dst_file):
                    stat["files_skipped_exists"] += 1
                    continue
                if dry_run:
                    stat["files_copied"] += 1
                    stat["copied"].append(rel)
                    continue
                os.makedirs(os.path.dirname(dst_file), exist_ok=True)
                shutil.copy2(src_file, dst_file)
                stat["files_copied"] += 1
                stat["copied"].append(rel)

    # 落一份清单，便于核对补传内容
    if not dry_run and stat["copied"]:
        os.makedirs(dst_root, exist_ok=True)
        manifest = os.path.join(dst_root, "_manifest.json")
        with open(manifest, "w", encoding="utf-8") as fh:
            json.dump({"src_root": src_root, "dst_root": dst_root,
                       "files": stat["copied"]}, fh, ensure_ascii=False, indent=1)
    return stat


def main() -> None:
    ap = argparse.ArgumentParser(description="远端扩展原始数据收集（资产库筛选+增量）")
    ap.add_argument("--api-base", default=DEFAULT_API_BASE, help="witty-ub 资产库地址")
    ap.add_argument("--tasks-file", default=None,
                    help="离线任务清单（每行一个任务名）；提供后不访问资产库")
    ap.add_argument("--base-dir", default=os.path.dirname(os.path.abspath(__file__)),
                    help="源/目标目录的父目录（默认=脚本所在目录）")
    ap.add_argument("--exclude", action="append", default=[],
                    help="追加「不收集」文件名 glob 模式，可多次指定，如 --exclude '*.monitor.log'")
    ap.add_argument("--exclude-name", action="append", default=[],
                    help="追加「不收集」精确文件名，可多次指定，如 --exclude-name 'dmesg.txt'")
    ap.add_argument("--task-allow", action="append", default=[],
                    help="追加任务名白名单（精确），可多次指定")
    ap.add_argument("--task-keyword", action="append", default=[],
                    help="追加任务名关键字（子串或 glob），可多次指定")
    ap.add_argument("--task-exclude", action="append", default=[],
                    help="追加任务名排除关键字（子串），可多次指定；命中则跳过整目录")
    ap.add_argument("--no-zip", action="store_true",
                    help="收集后不打包 zip（默认会打成 <X_app>.zip）")
    ap.add_argument("--dry-run", action="store_true", help="只统计不落盘")
    args = ap.parse_args()

    global FILE_EXCLUDE_PATTERNS, FILE_EXCLUDE_NAMES
    global TASK_NAME_ALLOWLIST, TASK_NAME_KEYWORDS, TASK_NAME_EXCLUDE_KEYWORDS
    FILE_EXCLUDE_PATTERNS = FILE_EXCLUDE_PATTERNS + list(args.exclude)
    FILE_EXCLUDE_NAMES = FILE_EXCLUDE_NAMES + list(args.exclude_name)
    TASK_NAME_ALLOWLIST = TASK_NAME_ALLOWLIST + list(args.task_allow)
    TASK_NAME_KEYWORDS = TASK_NAME_KEYWORDS + list(args.task_keyword)
    TASK_NAME_EXCLUDE_KEYWORDS = TASK_NAME_EXCLUDE_KEYWORDS + list(args.task_exclude)

    if args.tasks_file:
        fault_tasks = read_tasks_file(args.tasks_file)
        _log(f"[任务源] 清单文件 {args.tasks_file} → {len(fault_tasks)} 个任务")
    elif TASK_NAME_ALLOWLIST:
        fault_tasks = {t.strip() for t in TASK_NAME_ALLOWLIST if t.strip()}
        _log(f"[任务源] 脚本内置白名单 TASK_NAME_ALLOWLIST → {len(fault_tasks)} 个任务（离线，不访问资产库）")
    else:
        fault_tasks = fetch_fault_tasks(args.api_base)
        _log(f"[任务源] 资产库 {args.api_base}（fault_type∈{sorted(FAULT_TYPES)}）→ {len(fault_tasks)} 个任务")
    if not fault_tasks:
        raise SystemExit("[错误] 任务集合为空，请检查白名单/清单/资产库。")

    _log(f"[配置] 任务名关键字={TASK_NAME_KEYWORDS or '—'}")
    _log(f"[配置] 任务名排除关键字={TASK_NAME_EXCLUDE_KEYWORDS or '—'}")
    _log(f"[配置] 不收集文件名={FILE_EXCLUDE_NAMES or '—'} 模式={FILE_EXCLUDE_PATTERNS}")
    _log(f"[配置] 路径强制纳入={PATH_FORCE_INCLUDE_KEYWORDS or '—'}")
    grand = {"files_copied": 0, "tasks_processed": 0}
    for src_name, dst_name in JOBS:
        src_root = os.path.join(args.base_dir, src_name)
        dst_root = os.path.join(args.base_dir, dst_name)
        _log(f"\n===== {src_name} → {dst_name} =====")
        st = collect(src_root, dst_root, fault_tasks, args.dry_run)
        _log(f"  任务：总 {st['tasks_total']}，跳过(不在白名单) {st['tasks_skipped_nofault']}，"
             f"跳过(被排除/任务名不匹配) {st['tasks_skipped_byname']}，处理 {st['tasks_processed']}")
        _log(f"  文件：收集 {st['files_copied']}（其中路径强制纳入 {st['files_forced_include']}），"
             f"跳过(已采集) {st['files_skipped_collected']}，"
             f"跳过(ubse/无条件排除) {st['files_skipped_hard']}，"
             f"跳过(目标已存在) {st['files_skipped_exists']}"
             + ("   [dry-run 未落盘]" if args.dry_run else ""))
        grand["files_copied"] += st["files_copied"]
        grand["tasks_processed"] += st["tasks_processed"]
        if not args.dry_run and not args.no_zip and os.path.isdir(dst_root):
            zip_path = shutil.make_archive(dst_root, "zip", args.base_dir, dst_name)
            _log(f"  打包：{zip_path}（{os.path.getsize(zip_path) / 1048576:.1f} MB）")
    _log(f"\n[完成] 共处理 {grand['tasks_processed']} 个任务，"
         f"收集 {grand['files_copied']} 个文件。"
         + ("（dry-run，未写入磁盘）" if args.dry_run else ""))


if __name__ == "__main__":
    main()
