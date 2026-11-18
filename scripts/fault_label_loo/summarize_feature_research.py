#!/usr/bin/env python3
"""Build an index for completed exploratory feature studies; no fitting/selection."""
import argparse
import hashlib
import html
import json
from pathlib import Path


def read(path):return json.loads(path.read_text())


def table(headers,rows):
    esc=lambda value:html.escape(str(value))
    return '<table><tr>'+''.join('<th>'+esc(x)+'</th>' for x in headers)+'</tr>'+''.join(
        '<tr>'+''.join('<td>'+esc(x)+'</td>' for x in row)+'</tr>' for row in rows)+'</table>'


def summarize(reference,root):
    first=read(root/'summary.json');second=read(root/'unit_conditioned_v2/summary.json')
    mapping=read(root/'mapping_comparison/summary.json')
    split=read(reference/'split.json');queries=read(reference/'inputs/prepared.json')['reports']
    first_train=read(root/'training_selection.json');second_train=read(root/'unit_conditioned_v2/training_selection.json')
    split_sha=hashlib.sha256((reference/'split.json').read_bytes()).hexdigest()
    collisions=read(root/'template_collisions.json')
    for folder in (root,root/'unit_conditioned_v2',root/'mapping_comparison'):
        assert (folder/'split.json').read_bytes()==(reference/'split.json').read_bytes()
        assert read(folder/'plan.json')['split_sha256']==split_sha
    assert read(root/'refit_validation.json')['status']=='passed'
    assert read(root/'unit_conditioned_v2/refit_validation.json')['status']=='passed'
    assert read(root/'mapping_comparison/validation.json')['status']=='passed'
    def row(name,view,summary,train):
        scores=summary['validation'][view]
        return [name,f"{train[view]['classifier']['metrics']['hits']}/379",
                f"{scores['classifier']['hits']}/95",f"{scores['classifier']['accuracy']:.2%}",
                f"{scores['classifier']['macro_f1']:.3f}",f"{scores['k4']['hits']}/95"]
    rows=[row('原 v5 表示，同网格重训','v5',first,first_train),
          row('第一轮训练所选：数值原型','numeric',first,first_train),
          row('第二版统一单位数值（消融）','numeric_units',second,second_train),
          row('消息顺序与常见组合（消融）','sequences',first,first_train),
          row('全部新上下文（消融）','contextual',first,first_train),
          row('v5＋全部新上下文（消融）','v5_contextual',first,first_train),
          row('第二版全部合并（消融）','all_context_v2',second,second_train)]
    counts=[]
    for label in ('OS故障','SDK故障','Worker故障','容器故障','硬件故障'):
        train_count=sum(label in queries[i]['truth'] for i in split['train_indices'])
        support=sum(label in queries[i]['truth'] for i in split['validation_indices'])
        counts.append([label,train_count,support]+[
            f"{model['per_label'][label]['tp']}/{support}" for model in (
                first['validation']['v5']['classifier'],first['validation']['numeric']['classifier'],
                second['validation']['numeric_units']['classifier'],first['validation']['templates']['k4'])])
    patterns=read(root/'pattern_evidence.json');pattern_rows=[]
    for label,needle in [('Worker故障','pure_query'),('硬件故障','worker_payload'),('容器故障','cooccur:'),('SDK故障','thread_pool')]:
        candidates=[item for item in patterns[label] if needle in item['feature'] and item['supporting_scenes']>=2]
        if candidates:
            x=candidates[0]
            pattern_rows.append([label,x['feature'],f"{x['label_hits']}/{x['feature_reports']}",x['supporting_scenes']])
    primary=mapping['primary_selected_on_training'];mapped=mapping['validation'][primary]
    document='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>日志特征挖掘研究汇总</title>
<style>body{font:15px/1.75 system-ui,sans-serif;max-width:1400px;margin:30px auto;padding:0 24px;color:#172033}table{border-collapse:collapse;width:100%;margin:18px 0;font-size:13px}td,th{border:1px solid #ccd6e2;padding:8px;text-align:left;overflow-wrap:anywhere}th{background:#edf2f8}.note{background:#fff4d9;padding:16px}</style>
<h1>真实标签监督的日志特征挖掘</h1>
<p>使用 train＋v7 中 474 份五类标签报告，GT 为 /home/witty-ub-logs/gt_labels.json。
冻结复用 v5 的 379 训练、95 验证和训练内部 3 折，未抽换验证集，未做全量重训。
寻找下游日志模式与真实标签的经验映射，不要求日志直接陈述根因。</p>
<p class="note">实际完成两轮特征提取对照和一轮映射方法对照，未达到 80%。
两轮 Logistic 训练所选主方案均为第一版数值原型，验证 69/95＝72.63%；
新版统一单位数值及消息顺序分别观察到 71/95＝74.74%，属于消融观察，未据此改选主方案。
本批验证数据已用于多轮开发，以上不能称为新的独立测试成绩。当前默认 Agent 和 v5 模型未覆盖。</p>
<h2>同一划分的结果</h2>'''+table(['表示','训练3折','分类器验证','准确率','宏F1','新表示余弦K4验证'],rows)+'''
<p>原 v5 报告全部观测分类器为 62/95＝65.26%；本轮同网格重训的同表示为 65/95＝68.42%。
新增特征的主要同口径对照是 68.42%→72.63%，不能把参数选择变化全算作特征收益。
K4 列由新表示余弦相似度取代原评分，K＝4、margin＝0.05；是否监督选择度量见各轮报告。
这是固定训练库的留出查询，不是本轮新增的全量 LOO；不能与旧版 474 条 LOO 百分比混排。</p>
<h2>究竟改进了什么</h2><ol>
<li>从无上下文错误词语扩展为角色×静态组件×等级的词语、短语和消息模板，纳入 INFO 中的成功慢调用。</li>
<li>抽取实际返回码、操作、耗时、大小、同消息阶段占比和分布；第二版保留小数并统一时间/大小单位。</li>
<li>加入同进程相邻模式、角色内常见模式组合，及阶段×显式状态统计、成功失败对比和相对 W/E 时间窗。</li>
<li>通过训练标签学习选择与权重：正则强度、类别平衡、chi2 筛选、监督相似度；词表/缩放/选择均在训练折拟合。</li></ol>
<p>第一版数值原型存在已确认的解析限制：11.519ms 会截为 11。第二版修正；两版还有去重和统计方式差异。
旧原型保留用于对照，不建议直接作为生产提取器。全部特征合并未胜过更简洁的表示；不能由“更多维度”推出“更好诊断”。</p>
<h2>真实标签提供了哪些映射线索</h2>'''+table(['关联标签','观测模式','该标签命中/模式出现报告数（仅训练）','支持场景数'],pattern_rows)+'''
<p>这些是训练关联，不是根因规则。比如 query/payload 可能同时反映工作负载和采集差异。
SDK 的示例仅 2/3，容器仅跨两个场景，不足以写成通用判据；完整支持案例可追溯到 pattern_evidence.json。
OS 没有找到高支持、稳定区分的线索。二值模板集合相同却标签不同的训练冲突组有 12 组，该表示至少会错 25 条；
这只说明二值模板丢失信息，不说明全部日志都不可区分。</p>
<h2>各类识别仍有哪些短板</h2>'''+table(['标签','训练标签支持','验证支持','v5重训命中','数值原型命中','新版数值命中','模板K4命中（消融）'],counts)+'''
<p>总体收益集中于 Worker 与硬件。主方案宏 F1 从同网格 v5 的 0.404 降至 0.301，
OS、SDK、容器均未命中；新版数值虽改善 SDK，OS 和容器仍为零。不能据总体准确率称各类别全面改善。</p>
<h2>换权重或非线性映射能否解决</h2>
<p>额外固定比较 4 种表示×6 个线性/核 SVC 与 ExtraTrees 配置，训练内 3 折选择。
本轮训练所选主方案为新版数值＋ExtraTrees（叶最小样本 2），验证 '''+f"{mapped['hits']}/95＝{mapped['accuracy']:.2%}"+'''。
本轮没有超过 Logistic 新数值的 74.74%。这里统一使用训练支持至少 3 份报告、chi2 前 1000 维，
与 Logistic 的差异也包含筛选；不能据此笼统断言非线性无效。类别平衡和监督筛选在前两轮也未成为训练所选配置。
现有证据不足以靠随意调大某类或某家族权重达到 80%。</p>
<h2>后续优先级</h2><ol>
<li>以第二版正确的单位解析为基础，在相同操作、载荷大小和配置条件下比较阶段占比/分位数，降低工作负载差异的干扰。</li>
<li>把粗略“同角色共现”细化成有限时间窗、同调用的事件组合；对未知阶段、缺失状态显式记录缺失，避免与零耗时混淆。</li>
<li>优先补 SDK、OS、容器的可区分观测与样本；现有训练支持只有 10、8、27，单靠多数类准确率难评估改进。</li>
<li>评估时同时看宏 F1、各类召回、相同/新场景；后续规则应检查跨场景一致性。当前 95 份继续作为开发集，最终结论需要后续未参与方案设计的数据。</li></ol>
<p>二值模板集合完全相同的训练报告中，有 '''+str(len(collisions['conflicting_groups']))+''' 组真实标签冲突，
仅靠该种模板集合至少会产生 '''+str(collisions['forced_training_errors'])+''' 条训练误判。
这只表明模板存在信息损失，不能推出原始日志没有任何进一步可用信号。</p>
<h2>产物与核验</h2><p>27 项测试通过；两轮共重拟合 18 个分类器、18 个 K4 度量及 6 个主方案训练折，
逐条重放 3420 条留出预测，模型系数最大差值为 0；映射对照另重拟合并重放 4 个模型。
候选 skill 入口通过不加载第三方包的实际日志推理，复现新版与原型数值验证预测。来源、日志、GT、源码、划分哈希均保留。</p>
<ul><li><a href="report.html">第一轮：8 种表示</a> · <a href="unit_conditioned_v2/report.html">第二轮：10 种表示</a>
 · <a href="mapping_comparison/readme.md">映射方法对照</a></li>
<li><a href="pattern_evidence.json">训练模式与支持案例</a> · <a href="unit_conditioned_v2/primary_feature_effects.json">主模型特征贡献</a></li>
<li><a href="refit_validation.json">第一轮重拟合</a> · <a href="unit_conditioned_v2/refit_validation.json">第二轮重拟合</a>
 · <a href="mapping_comparison/validation.json">映射对照核验</a></li>
<li><a href="implementation_validation.json">代码、默认流程及文件核验</a> · <a href="tests_final.log">测试记录</a></li></ul></html>'''
    (root/'research_report.html').write_text(document)
    print(root/'research_report.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args();summarize(args.reference,args.root)
