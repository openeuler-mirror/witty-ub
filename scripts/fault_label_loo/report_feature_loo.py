#!/usr/bin/env python3
"""Report complete, validated default K4 and mined-feature source LOO results."""
import argparse
import csv
from datetime import datetime
import html
import math
from pathlib import Path
from zoneinfo import ZoneInfo

import loo_support as io

NAMES={'v5':'基线特征','v1_numeric':'第一版数值原型（有解析缺陷，仅对照）',
       'numeric_units':'新增数值特征（统一单位）','templates':'去身份消息模板','sequences':'相邻模式与组合',
       'numeric_context':'第二版行为统计合并','all_context_v2':'全特征'}

CLASSIFIER_ROWS=[
    ['基线特征＋分类器','原有错误码、故障模式、操作、结构化数值/范围、遥测和日志词语等观测',
     '包含','不包含本轮新增提取器的特征','v5'],
    ['新增数值特征（统一单位）＋分类器','仅新增数值统计：统一单位的耗时/大小、样本数、均值、极值、分布和分位桶，保留角色/组件/阶段上下文',
     '不包含','不包含基线特征，也不包含上下文词语、模板和事件组合','numeric_units'],
    ['全特征＋分类器','基线特征＋新增数值＋阶段/显式状态统计＋成功失败对比＋相对时间窗＋上下文词语、模板和事件组合',
     '包含','合并本轮全部新增特征','all_context_v2']]


def classifier_rows(plan):
    return [row[:4]+[plan['views'][row[4]]] for row in CLASSIFIER_ROWS]


def refresh_markdown(out,plan):
    """Keep the existing Markdown report and user edits; refresh names and definitions."""
    path=out/'report.md'
    if not path.exists():return
    content=path.read_text()
    replacements=[
        ('当前默认全部特征 K4','基线特征 K4'),('当前默认 K4','基线特征 K4'),
        ('默认 K4','基线特征 K4'),('默认K4','基线特征K4'),
        ('原 v5 观测的余弦 K4','基线特征余弦 K4'),('原 v5 观测','基线特征'),
        ('原 v5 的','基线特征中的'),('v5＋全部新上下文/行为统计','全特征'),
        ('v5＋角色/组件上下文','基线特征＋角色/组件上下文'),
        ('v5 与第二版数值表示','基线特征与新增数值特征（统一单位）'),
        ('v5 余弦路径','基线特征余弦路径'),('v5 分类器','基线特征分类器'),
        ('第二版统一单位数值','新增数值特征（统一单位）'),
        ('新版统一单位数值','新增数值特征（统一单位）'),
        ('第二版数值分类器','新增数值特征分类器'),('新版数值分类器','新增数值特征分类器'),
        ('全部新特征合并的余弦 K4','全特征余弦 K4'),
        ('全部特征合并','全特征'),('全部合并分类器','全特征分类器'),('全部合并','全特征')]
    for old,new in replacements:content=content.replace(old,new)
    headers=['方案','实际输入','是否包含基线特征','边界说明','Logistic C']
    md_table='\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+
        ['| '+' | '.join(map(str,row))+' |' for row in classifier_rows(plan)])
    section=f'''### 三组主要分类器的区别

三组均使用 Logistic 分类器，主要比较输入表征；每组每折都独立拟合词表、缩放和权重，每组各有 {plan['queries']} 套折内权重。

'''+md_table+'''

**新增数值特征方案只使用新增数值统计，没有在基线特征上叠加数值特征。全特征方案才将基线特征与本轮全部新增特征合并。**
前两组 C=1，全特征组 C=0.1；后者的正则化更强。因此三组并非仅输入不同，配置也有差异，不能把成绩差值全部归因于特征增减。

这里的“基线特征”特指本轮开始前已使用的 v5 观测；“基线特征 K4”为当前默认路径的 71.52%，与“旧底座 K4”的 69.20% 分开命名。
'''
    start='<!-- classifier-differences:start -->';end='<!-- classifier-differences:end -->'
    block=start+'\n\n'+section+'\n'+end
    if start in content:
        before,tail=content.split(start,1);_,after=tail.split(end,1);content=before+block+after
    else:
        anchor='## 2. 数据覆盖与计分口径'
        if anchor not in content:raise ValueError('Cannot find Markdown insertion point')
        content=content.replace(anchor,block+'\n\n'+anchor,1)
    path.write_text(content)


def table(headers,rows):
    esc=lambda value:html.escape(str(value))
    return '<table><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr>'+''.join(
        '<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'


def report(out):
    summary=io.read(out/'summary.json');validation=io.read(out/'validation.json');plan=io.read(out/'plan.json')
    default=io.read(out/'default_k4/summary.json');default_validation=io.read(out/'default_k4/validation.json')
    default_predictions=io.read(out/'default_k4/predictions.json')
    assert not summary['partial'] and validation['status']==default_validation['status']=='passed'
    assert len(default_predictions)==summary['n']==validation['n']==default_validation['queries']
    baseline_by_source={r['query_id']:r['fixed'] for r in default_predictions}
    metrics={};predictions={};rows=[]
    for key,title in (('baseline','旧底座 K4'),('fixed','基线特征 K4')):
        name='default_'+key;records=[{**r,'prediction':r[key],'baseline':r['fixed']} for r in default_predictions]
        metrics[name]=io.metrics(records,'prediction');predictions[name]=records
        rows.append([title,'固定规则',metrics[name]['hits'],f"{metrics[name]['accuracy']:.2%}",
                     f"{metrics[name]['macro_f1']:.4f}",metrics[name]['rescued'],metrics[name]['harmed']])
    for view in summary['results']:
        records=io.read(out/f'predictions/{view}.json')
        for key in ('classifier','k4'):
            name=view+'__'+key
            rows_for_key=[{**r,'prediction':r[key],'baseline':baseline_by_source[r['query_id']]} for r in records]
            metrics[name]=io.metrics(rows_for_key,'prediction');predictions[name]=rows_for_key;m=metrics[name]
            method=f"折内 Logistic C={plan['views'][view]}" if key=='classifier' else '新表示余弦 K4'
            rows.append([NAMES[view],method,m['hits'],f"{m['accuracy']:.2%}",f"{m['macro_f1']:.4f}",m['rescued'],m['harmed']])
    with (out/'comparison.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['表示','方法','命中','准确率','宏F1','相对基线特征K4救回','相对基线特征K4误伤']);writer.writerows(rows)
    with (out/'errors.csv').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.writer(stream);writer.writerow(['method','query_id','group','truth','prediction','default_k4'])
        for name,records in predictions.items():
            for r in records:
                if r['prediction'] not in r['truth']:
                    writer.writerow([name,r['query_id'],r['group'],' / '.join(r['truth']),r['prediction'],r['baseline']])
    by_group={group:{name:io.metrics([r for r in records if r['group']==group],'prediction')
                     for name,records in predictions.items()} for group in sorted({r['group'] for r in default_predictions})}
    io.write(out/'comparison_summary.json',{'n':summary['n'],'metrics':metrics,'by_group':by_group,
        'dataset_audit':plan['dataset_audit'],'independent_new_data_test':False,'validation':validation,
        'default_validation':default_validation,'note':'All configurations frozen before this run; no model selected from LOO outcomes.'})
    unit=metrics['numeric_units__classifier'];default_metric=metrics['default_fixed'];n=summary['n']
    target=math.ceil(.8*n);gap=target-unit['hits']
    target_note=f'达到 80% 需要至少 {target} 条命中，尚差 {gap} 条净命中。' if gap>0 else '本批 LOO 数值模型准确率达到 80%。'
    audit=plan['dataset_audit'];total=sum(audit['report_counts'].values());excluded=sum(audit['excluded_counts'].values())
    per_rows=[]
    for label in io.LABELS:
        per_rows.append([label,unit['per_label'][label]['support']]+[
            f"{m['per_label'][label]['tp']}/{m['per_label'][label]['support']}" for m in (
                default_metric,metrics['v5__classifier'],unit,metrics['sequences__classifier'],metrics['all_context_v2__classifier'])])
    group_rows=[]
    for group,results in by_group.items():
        group_rows.append([group,results['default_fixed']['n']]+[
            f"{results[name]['hits']} / {results[name]['n']} = {results[name]['accuracy']:.2%}"
            for name in ('default_fixed','v5__classifier','numeric_units__classifier','all_context_v2__classifier')])
    total_models=sum(v['folds'] for v in validation['views'].values())
    total_refits=sum(v['independent_refits'] for v in validation['views'].values())
    max_difference=max(v['max_parameter_difference'] for v in validation['views'].values())
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    content=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>v6：全量来源 LOO</title>
<style>body{{font:15px/1.75 system-ui,sans-serif;max-width:1500px;margin:30px auto;padding:0 24px;color:#172033}}table{{border-collapse:collapse;width:100%;margin:18px 0;font-size:13px}}td,th{{border:1px solid #ccd6e2;padding:8px;text-align:left;overflow-wrap:anywhere}}th{{background:#edf2f8}}.note{{background:#fff4d9;padding:16px}}</style>
<h1>v6：全量来源 LOO</h1><p>{now}</p>
<p><strong>分类器列评估的是固定特征与训练流程：每折重新训练，共 {n} 套不同权重。
它不是某一套使用全部 {n} 份数据训练出的冻结权重的测试成绩。全量冻结模型需另用未参与训练的新数据验证。</strong></p>
<p>基线特征 K4：<strong>{default_metric['hits']}/{n}＝{default_metric['accuracy']:.2%}</strong>。
新增数值特征（统一单位）＋分类器：<strong>{unit['hits']}/{n}＝{unit['accuracy']:.2%}</strong>。{target_note}</p>
<h2>三组主要分类器的区别</h2>
<p>三组均为 Logistic 分类器，各自逐折拟合词表、缩放和权重，每组各有 {n} 套折内权重。</p>
{table(['方案','实际输入','是否包含基线特征','边界说明','Logistic C'],classifier_rows(plan))}
<p>新增数值特征方案仅使用新增数值统计，不包含基线特征或上下文词语/模板/事件组合；全特征方案才将基线与全部新增特征合并。
前两组 C=1，全特征组 C=0.1，后者正则化更强，因而这并非严格的单变量特征消融。
“基线特征”指本轮开始前已使用的 v5 观测；基线特征 K4（71.52%）与旧底座 K4（69.20%）分别列示。</p>
<h2>覆盖与协议</h2><p>扫描 reports/train＋reports/v7 全部 {total} 份报告，沿用五类范围评估 {n} 份，
另 {excluded} 份仅含 Coordinator／UB 管控面故障，明确排除并保留于 coverage.json。
真实标签来自 /home/witty-ub-logs/gt_labels.json。预测一个一级标签，命中该报告任一 GT 即算正确。</p>
<p>每折排除当前报告及同源/别名/完整日志相同来源。当前为 {plan['source_groups']} 个来源组、{n} 个留出查询；
每个分类器均重新拟合其余来源，词表、缩放和权重都不含留出来源。没有加载全量预训练权重，也没有在最后用全量重训覆盖模型。
这是混合库来源留一，同场景的其他来源可以进入训练；不等价于把整个场景留出的跨场景测试。
C 等配置沿用前一轮开发中已确定的值，在本轮 plan.json 中先固定；不按本轮成绩调参或挑选主模型，因此这是固定配置 LOO，而不是嵌套选参 LOO。
各表示的 C 不完全相同，比较体现整条管线，不能把差值全部归因为单一特征变化。</p>
<p>新表示 K4 使用本折词表和 MaxAbs 缩放后的余弦相似度，保留 K＝4、margin＝0.05，候选只能来自本折训练来源。
候选故障共享其来源报告的聚合观测，与上一轮特征研究一致。它替换了相似度定义，不能理解为只在原默认 K4 分数上增加一个通道。
基线特征 K4 则调用 Agent 共用的 fixed_matching.match，不训练分类器。</p>
<p class="note">这批数据已用于开发特征及配置，本轮虽逐折排除查询再拟合，仍不是全新独立数据测试。
与上一轮 379/95 留出对照不同，本轮每次使用其余约 473 份报告，训练数据更多、测试查询也不同；不能把 74.74%→本轮结果全部归因于代码再次改善。
第一版数值原型的带单位小数解析存在缺陷，仅保留作对照。默认 Agent 策略未替换。</p>
<h2>全部对照</h2>{table(['表示','方法','命中 / '+str(n),'准确率','宏F1','相对基线特征K4救回','相对基线特征K4误伤'],rows)}
<p>“救回/误伤”均以基线特征 K4 为共同参照。未根据此表选择新默认模型，也没有四舍五入把低于 80% 的成绩称为已达到 80%。</p>
<h2>各类别命中</h2>{table(['标签','GT支持','基线特征K4','基线特征分类器','新增数值特征分类器','顺序组合分类器','全特征分类器'],per_rows)}
<p>新增数值特征分类器宏 F1 为 {unit['macro_f1']:.4f}，基线特征 K4 为 {default_metric['macro_f1']:.4f}。
总体准确率与少数类召回需一起查看。多标签报告可同时计入多个标签支持，支持数之和可能超过报告数。</p>
<h2>来源分项（同一混合库，非两个独立测试）</h2>{table(['来源','报告数','基线特征K4','基线特征分类器','新增数值特征分类器','全特征分类器'],group_rows)}
<h2>完整性核验</h2><p>状态 passed：基线特征 K4 的 {n} 条决策全部重新计算；{total_models} 个折内分类器的训练来源、词表、缩放及可移植推理逐一核对，
对应 {total_models} 条新表示 K4 由独立实现重放。按事先规定的首/中/末及各标签首例，另独立重拟合 {total_refits} 个模型，
参数最大差值 {max_difference}。原始日志内容重新哈希验证，GT、报告、缓存、源码及每折模型均保留哈希。</p>
<ul><li><a href="comparison_summary.json">完整指标</a> · <a href="comparison.csv">对照 CSV</a> · <a href="errors.csv">全部误判</a></li>
<li><a href="plan.json">固定实验计划与源码/缓存哈希</a> · <a href="folds.json">持久化逐折划分</a> · <a href="coverage.json">全部输入及排除清单</a></li>
<li><a href="validation.json">分类器及新 K4 核验</a> · <a href="default_k4/validation.json">基线特征 K4 核验</a> · <a href="raw_log_validation.json">原始日志校验</a></li>
<li><a href="tests.log">28 项测试记录</a> · <a href="postprocessing_manifest.json">核验与报告脚本快照</a></li>
<li><a href="predictions/numeric_units.json">新增数值特征逐条结果</a> · <a href="default_k4/predictions.json">基线特征 K4 逐条结果</a></li></ul></html>'''
    (out/'report.html').write_text(content)
    refresh_markdown(out,plan)
    print(out/'report.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    report(parser.parse_args().out)
