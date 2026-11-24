#!/usr/bin/env python3
"""Export comparable tables, persisted assignments and Agent-ready artifacts."""
import argparse
import csv
from datetime import datetime
import html
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import skill_runtime
import all_feature_matching
import loo_support as io

NAMES={'base_k4':'基础评分＋K4','three_channel_k4':'基础＋BM25/角色/范围＋K4',
       'all_feature_k4':'全部特征＋K4','base_observations':'基础观测分类器',
       'all_observations':'全部观测分类器','all_observations_and_retrieval':'全部观测＋检索统计分类器'}


def summarize(root):
    validation=io.read(root/'validation.json');assert validation['status']=='passed'
    split,manifest=io.read(root/'split.json'),io.read(root/'manifest.json')
    loo,classification=io.read(root/'k4_loo/summary.json'),io.read(root/'classifier/summary.json')
    prepared,raw=io.read(root/'inputs/prepared.json'),io.read(root/'inputs/raw_observations.json')
    coverage=io.read(root/'feature_coverage.json')
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    report={'generated_at':now,'mixed_k4_loo':loo,'holdout':classification,
        'split':{'path':'split.json','seed':split['seed'],'train':len(split['train_indices']),
                 'validation':len(split['validation_indices']),'inner_folds':len(split['inner_folds'])},
        'validation':validation,'dataset_audit':manifest['dataset_audit'],
        'feature_version':manifest['feature_version'],'model_loo_performed':False,
        'deployment':'K4 is default; classifier requires explicit supplied train-only model',
        'independent_new_data_test':False,
        'note':'All schemas/feature design were explored on this dataset before. Holdout rows never fit weights or choose hyperparameters in this run.'}
    io.write(root/'summary.json',report)
    with (root/'split.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=['query_id','partition','group','stratum'])
        writer.writeheader();writer.writerows(split['assignments'])
    # Candidate bundles preserve measured historical sidecars for both inference paths.
    for name,sources in (('train',set(split['train_source_ids'])),('all',{q['source_id'] for q in prepared['reports']})):
        cases=[{key:c[key] for key in ('id','source_id','label','profile','structured')}|
               {'raw_observations':raw['reports'][c['source_id']]} for c in prepared['cases'] if c['source_id'] in sources]
        io.write(root/f'agent/cases_{name}.json',{'cases':cases,'partition':name})
    with (root/'comparison.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=['protocol','partition','variant','hits','n','accuracy','macro_f1'])
        writer.writeheader()
        for key,m in loo.items():writer.writerow({'protocol':'mixed_loo','partition':'all','variant':key,**{k:m[k] for k in ('hits','n','accuracy','macro_f1')}})
        for part,metrics in classification['metrics'].items():
            for key,m in metrics.items():writer.writerow({'protocol':'random_holdout','partition':part,'variant':key,**{k:m[k] for k in ('hits','n','accuracy','macro_f1')}})
    validation_records=io.read(root/'classifier/validation_predictions.json')
    mistakes=[]
    for r in validation_records:
        for key in classification['metrics']['validation']:
            if r[key] not in r['truth']:mistakes.append({'variant':key,'query_id':r['query_id'],'truth':r['truth'],'prediction':r[key]})
    io.write(root/'validation_errors.json',mistakes)
    def table(headers,rows):
        escape=lambda value:html.escape(str(value))
        return '<table><tr>'+''.join('<th>'+escape(v)+'</th>' for v in headers)+'</tr>'+''.join(
            '<tr>'+''.join('<td>'+escape(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
    def rows(metrics):
        return [[NAMES[key],f"{m['hits']}/{m['n']}",f"{m['accuracy']:.2%}",f"{m['macro_f1']:.4f}"] for key,m in metrics.items()]
    headers=['方案','命中/报告数','准确率','宏 F1']
    model_rows=[]
    for view,model in classification['models'].items():
        cfg=model['selected_config']
        model_rows.append([NAMES[view],cfg['id'],f"{model['inner_correct']}/{len(split['train_indices'])}",
                           f'classifier/models/{view}.json'])
    class_rows=[]
    for key,m in classification['metrics']['validation'].items():
        for label,p in m['per_label'].items():
            class_rows.append([NAMES[key],label,p['support'],p['tp'],p['predicted'],f"{p['f1']:.4f}"])
    cv=classification['metrics']['validation'];base=cv['three_channel_k4'];all_k4=cv['all_feature_k4']
    content=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>全部特征：K4 与分类器对照 v5</title>
<style>body{{font:15px/1.7 system-ui,sans-serif;color:#172033;max-width:1500px;margin:30px auto;padding:0 24px}}table{{border-collapse:collapse;width:100%;margin:18px 0;font-size:13px}}th,td{{border:1px solid #d7dee8;padding:7px;text-align:left;overflow-wrap:anywhere}}th{{background:#edf2f8}}.note{{background:#fff4d9;padding:16px}}h1{{font-size:26px}}</style>
<h1>全部特征：K4 与分类器对照 v5</h1><p>生成时间：{now}</p>
<p>train 与 v7 合并，纳入 474 份五类报告；另有 87 份仅含 Coordinator/UB 管控面故障的报告按原范围排除。
K4 只做合并数据的来源留一评估。分类器按来源分组、标签分层随机留出，固定 seed={split['seed']}，
训练 {len(split['train_indices'])} 份、验证 {len(split['validation_indices'])} 份；划分先于拟合并持久化。</p>
<p class="note">两张表的分母与候选库不同，不能直接用 K4 的 474 条 LOO 与分类器的 95 条验证成绩判胜负。
第二张表中的全部方法使用完全相同的验证报告与训练来源候选库，适合作直接比较。</p>
<h2>一、K4：混合数据全量 LOO</h2>{table(headers,rows(loo))}
<p>每条查询先排除自身、同日志和别名，再重算 IDF、先验及词语统计，权重和 K 固定；没有按本次成绩调 K4 参数。
没有另外拆分 train、v7 子实验，也没有运行分类器模型 LOO。</p>
<h2>二、相同验证集与候选库的对照</h2>{table(headers,rows(cv))}
<p>本次 K4 从三个增量通道扩展到全部特征后，验证命中 {base['hits']}→{all_k4['hits']}。
全部观测分类器命中 {cv['all_observations']['hits']}/{cv['all_observations']['n']}；
加入检索统计后命中 {cv['all_observations_and_retrieval']['hits']}/{cv['all_observations_and_retrieval']['n']}。
这些结果按原划分如实保留，没有因为成绩更换种子或使用验证集选参。</p>
<h2>三、训练集表现（不能当验证成绩）</h2>{table(headers,rows(classification['metrics']['train']))}
<p>K4 训练集行仍排除查询自身；分类器训练集行是已拟合样本上的表现，仅用于观察拟合与验证的差距。</p>
<h2>四、模型选择与隔离</h2>{table(['分类器输入','训练集内部所选配置','3 折内部命中','导出模型'],model_rows)}
<p>每种输入在训练集内部做 3 折分组验证，比较 logistic C=0.1/1/10 与 ExtraTrees depth=6/12；
用内部命中总数选配置，并列按预设顺序。候选库、IDF、先验、向量词表、缩放和模型权重均限于相应训练来源。
最终模型只用 379 份训练报告拟合，没有在评估后用 474 份重训。三个模型均作为显式对照导出，没有按验证成绩自动接管 Agent。</p>
<h2>五、所有特征如何接入</h2><p>两条路径共用 feature_vectors.build_observations。
错误码/模式/阶段/操作/语义与角色保留在底座及原三个通道；结构化分布、数值、相对时间、核对事实、机制、事件/错误族、
传输、交互/链、范围以及遥测、词语、短语、进程/主机影响和静态组件进入 16 个相似度家族。
K4 新家族总增量预算固定 0.30，各 0.01875；数值用共同已知项的距离及覆盖，词语/短语用候选库 IDF 余弦，其余用余弦。
缺失比较增量为零，显式数值零保留。分类器直接消费同一观测向量，第三种输入另加入分标签检索统计。</p>
{table(['新相似度家族','有观测的报告数（共474）'],list(coverage['blocks'].items()))}
<p>身份、绝对日期、报告答案、采集文件数不作为新增向量；场景名只用于数据管理。
facts 家族本批无已核对观测，因此没有填造事实。历史候选缺失原始观测时，该家族保持未知。
Agent 可用导出的 cases_train.json 或 cases_all.json 获得完整历史旁车；复现验证只能用 cases_train.json。</p>
<h2>六、各标签验证表现</h2>{table(['方案','标签','GT支持','命中','预测数','F1'],class_rows)}
<h2>七、核验与产物</h2><p>校验状态：{validation['status']}。K4 全量 {validation['mixed_loo_queries']} 条通过公共 Agent 入口重放；
训练内选参独立重拟合 {validation['inner_selection_refits']} 次；分类器可移植推理复核 {validation['classifier_portable_replays']} 次。
报告只预测一个一级标签，命中任一外部 GT 即算正确；多标签训练按每报告总权重 1 分摊。</p>
<p>本批数据曾用于特征和方案探索，所以本次随机留出不是从未研究过的新数据独立测试。验证集只有 95 份，SDK 与 OS 各 2 份，细分类别估计仍有限。
历史 77% 与 92.83% 属于不同方案和协议，不与本表混合。</p>
<ul><li><a href="summary.json">汇总 JSON</a> · <a href="comparison.csv">对照 CSV</a></li>
<li><a href="split.json">划分及内部折 JSON</a> · <a href="split.csv">逐报告划分 CSV</a></li>
<li><a href="k4_loo/predictions.json">全量 K4 预测</a> · <a href="classifier/validation_predictions.json">验证逐条预测</a> · <a href="validation_errors.json">验证误判</a></li>
<li><a href="validation.json">独立核验</a> · <a href="feature_coverage.json">特征清单与覆盖</a> · <a href="manifest.json">输入及源码哈希</a></li>
<li><a href="agent/cases_train.json">Agent 训练来源候选</a> · <a href="agent/cases_all.json">Agent 全部历史候选</a></li></ul></html>'''
    (root/'report.html').write_text(content)
    print(root/'report.html')
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,required=True)
    summarize(parser.parse_args().root)
