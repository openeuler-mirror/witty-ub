#!/usr/bin/env python3
"""Export results for a validated, complete fixed-rule source LOO evaluation."""
import argparse
import csv
from datetime import datetime
import html
import json
import math
import os
from pathlib import Path
from zoneinfo import ZoneInfo


def summarize(run,out):
    read=lambda p:json.loads(p.read_text())
    summary,validation=read(run/'summary.json'),read(run/'validation.json')
    manifest,records=read(run/'manifest.json'),read(run/'predictions.json')
    assert validation['status']=='passed' and validation['classifier']==summary['classifier']=='none'
    assert not summary['partial'] and len(records)==summary['total_queries']==validation['queries']
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    result={**summary,'generated_at':now,'validation':validation,'dataset_audit':manifest['dataset_audit'],
        'run_directory':str(run),'independent_new_data_test':False,
        'feature_usage':{'scoring':['error codes','failure modes','latency buckets','operation',
            'pool label prior','log semantic IDF','BM25','actor','scope','raw telemetry',
            'sanitized message words/phrases','error process/host fractions','static software component names'],
            'extracted_but_not_scored':[]},
        'metric':'one predicted first-level label matches any external GT label'}
    out.mkdir(parents=True,exist_ok=True)
    (out/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    errors=[r for r in records if r['fixed'] not in r['truth']]
    with (out/'errors.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.DictWriter(stream,fieldnames=['query_id','group','truth','fixed','baseline'])
        writer.writeheader()
        for r in errors:
            writer.writerow({k:' / '.join(r[k]) if k=='truth' else r[k] for k in writer.fieldnames})
    def table(headers,rows):
        esc=lambda v:html.escape(str(v))
        return '<table><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr>'+''.join(
            '<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
    def metric_row(name,metrics):
        base,fixed=metrics['baseline'],metrics['fixed']
        return [name,fixed['n'],f"{base['hits']}/{base['n']}",f"{base['accuracy']:.2%}",
            f"{fixed['hits']}/{fixed['n']}",f"{fixed['accuracy']:.2%}",
            f"{(fixed['accuracy']-base['accuracy'])*100:+.2f} 个百分点",fixed['rescued'],fixed['harmed']]
    metrics=table(['数据集','报告数','底座命中','底座准确率','当前方案命中','当前准确率','差值','救回','误伤'],
        [metric_row('合并',summary['metrics'])]+[metric_row(g,m) for g,m in summary['by_group'].items()])
    fixed=summary['metrics']['fixed']
    per=table(['一级标签','GT 支持数','命中','预测数','精确率','召回率','F1'],[
        [label,p['support'],p['tp'],p['predicted'],f"{p['precision']:.2%}",f"{p['recall']:.2%}",f"{p['f1']:.4f}"]
        for label,p in fixed['per_label'].items()])
    labels=list(fixed['per_label'])
    confusion=table(['GT 标签集合 / 预测']+labels+['空预测'],[
        [truth]+[counts.get(label,0) for label in labels]+[counts.get('<unknown>',0)]
        for truth,counts in fixed['confusion'].items()])
    mistakes=table(['来源','分组','GT','当前预测','底座预测'],[
        [r['query_id'],r['group'],' / '.join(r['truth']),r['fixed'],r['baseline']] for r in errors])
    link=lambda p:html.escape(Path(os.path.relpath(p,out)).as_posix(),quote=True)
    audit=manifest['dataset_audit'] or {}
    total=sum(audit.get('report_counts',{}).values())
    excluded=sum(audit.get('excluded_counts',{}).values())
    target=math.ceil(.8*fixed['n']);gap=max(0,target-fixed['hits'])
    target_note=f'达到 80% 需至少 {target} 条命中，尚差 {gap} 条净命中。' if gap else '本批留一评估达到 80%。'
    content=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>固定特征评分与投票：全量 LOO</title>
<style>body{{font:15px/1.7 system-ui,sans-serif;color:#172033;max-width:1500px;margin:30px auto;padding:0 24px}}table{{border-collapse:collapse;width:100%;margin:18px 0;font-size:13px}}th,td{{border:1px solid #d7dee8;padding:7px;text-align:left;overflow-wrap:anywhere}}th{{background:#edf2f8}}.note{{background:#fff4d9;padding:16px}}h1{{font-size:26px}}</style>
<h1>固定特征评分与投票：全量 LOO</h1><p>{now}。当前方案命中 {fixed['hits']}/{fixed['n']}，准确率 <strong>{fixed['accuracy']:.2%}</strong>。{target_note}</p>
<p>本轮未加载或训练分类器。Agent、本地/HTTP 匹配和 LOO 共用 fixed_matching.match，使用相同观测提取、候选评分及 K4（margin=0.05）投票。
每条查询先排除自身、同日志和别名，再计算剩余历史候选的 IDF、标签先验等统计。留出查询的 GT 只用于最后计分；其他历史案例标签正常用于匹配与投票。</p>
<p>输入 reports/train 与 reports/v7 共 {total} 份报告，按已固化的五类故障范围纳入 {len(records)} 份，
排除 {excluded} 份仅含 Coordinator/UB 管控面故障的报告。每份报告预测一个一级标签，命中其任一外部 GT 即算正确；多标签支持数可能超过报告数。</p>
<p class="note">train/v7 是同一混合候选库中的分项统计。本批数据已用于多轮方案探索，结果是这批数据的留一评估，不是新采集数据的独立测试。
历史 77.00% 是“新增特征＋折内训练分类器”的来源分组结果，同折旧基线为 69.83%，每折候选库限于训练来源。
本轮是纯规则完整库留一，算法与候选池均不同，不能把 77.00% 当作本轮已实现的特征提取收益。
先前分类器的 92.83% 训练暴露回归结果已单独归档，不作为本次成绩或改进依据。</p>
<h2>实际参与决策的特征</h2><p>保留错误码 F1、模式/阶段桶、操作、候选池标签先验和日志语义 IDF；固定新增 BM25、角色、范围相似度各 0.05。
前两名分差大于 0.05 时取第一名，否则对前 4 个故障案例投票。IP、主机名、PID、绝对日期和报告答案不作为查询匹配键。</p>
<p>原始遥测、去身份词语/短语、错误进程/主机占比和静态组件名也通过观测家族相似度参与评分。
本轮没有宣称这些已提取字段带来命中率提升，也没有按本次成绩再调整权重或 K。</p>
<h2>合并与分组结果</h2>{metrics}<p>“底座”是去掉 BM25/角色/范围增量后的兼容评分及相同 K4 投票；“当前方案”增加这三个固定通道。</p>
<h2>各标签表现</h2>{per}<p>宏 F1：{fixed['macro_f1']:.4f}。</p><h2>混淆矩阵</h2>{confusion}
<h2>完整性核验</h2><p>状态 {validation['status']}，{validation['replayed_decisions']} 条预测全部重新计算核对；输入/源码快照哈希、来源排除、结果覆盖与指标检查通过。</p>
<p><a href="summary.json">完整汇总</a> · <a href="errors.csv">全部误判 CSV</a> ·
<a href="{link(run/'predictions.json')}">逐条预测与候选支持</a> · <a href="{link(run/'validation.json')}">完整性核验</a> ·
<a href="{link(run/'manifest.json')}">输入审计与源码清单</a></p><h2>全部误判（{len(errors)} 条）</h2>{mistakes}</html>'''
    (out/'report.html').write_text(content)
    print(out/'report.html')
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    summarize(args.run,args.out)


if __name__=='__main__':
    main()
