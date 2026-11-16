#!/usr/bin/env python3
"""Explain supervised log-pattern discovery without changing the v5 defaults."""
import argparse
from collections import Counter,defaultdict
import csv
from datetime import datetime
import gzip
import hashlib
import html
import json
from pathlib import Path
from zoneinfo import ZoneInfo

import skill_runtime
import feature_vectors
import mined_log_features as extraction
import mine_label_features as mining
import loo_support as io
import portable_classifier

NAMES={'v5':'v5 观测（本轮同网格重训）','ew_context':'E/W 角色＋组件词语','all_context':'I/W/E 角色＋组件词语',
       'templates':'去身份消息模板','numeric':'状态/耗时/比例/数值桶','sequences':'模式顺序与组合',
       'contextual':'全部新上下文合并','v5_contextual':'v5＋全部新上下文',
       'v1_numeric':'第一版数值原型','numeric_units':'统一单位与数值分布',
       'conditioned':'阶段×显式状态分布','contrasts':'显式成功/失败数值对比','temporal':'相对报错时间窗',
       'numeric_context':'四类行为统计合并','v5_numeric_context':'v5＋四类行为统计',
       'v1_contextual':'第一版合并上下文','all_context_v2':'词语/模板/组合＋行为统计＋v5'}


def report(reference,root,revision=1):
    if revision==2:
        import mined_log_features_v2 as extraction
        import mine_label_features_v2 as mining
    else:
        import mined_log_features as extraction
        import mine_label_features as mining
    summary=io.read(root/'summary.json');selection=io.read(root/'training_selection.json')
    split=io.read(root/'split.json');prepared=io.read(reference/'inputs/prepared.json');raw=io.read(reference/'inputs/raw_observations.json')
    plan=io.read(root/'plan.json');queries=prepared['reports'];train=split['train_indices'];valid=split['validation_indices']
    assert hashlib.sha256((reference/'split.json').read_bytes()).hexdigest()==summary['split_sha256']
    assert (reference/'split.json').read_bytes()==(root/'split.json').read_bytes()
    assert hashlib.sha256(Path(plan['dataset_audit']['truth_source']).read_bytes()).hexdigest()==plan['gt_sha256']
    original=getattr(extraction,'v1',extraction)
    for source in {Path(mining.__file__),Path(extraction.__file__),Path(original.__file__),Path(original.log_message_features.__file__)}:
        assert (root/'source_snapshot'/source.name).read_bytes()==source.read_bytes()
    contexts={}
    for i,q in enumerate(queries):
        with gzip.open(root/'context_cache'/f'{i:04d}.json.gz','rt') as stream:context=json.load(stream)
        assert context['schema_version']==extraction.VERSION
        expected={f['file']:f['sha256'] for f in q['structured']['log']['provenance']['files']}
        actual={f['file']:f['sha256'] for f in context['provenance']['files']}
        assert actual==expected
        contexts[q['source_id']]=context
    base=[feature_vectors.build_observations(q['profile'],q['structured'],raw['reports'][q['source_id']]) for q in queries]
    checks=0;associations=io.read(root/'label_associations.json');models={}
    for view in extraction.VIEWS:
        model=io.read(root/f'models/{view}.json');models[view]=model
        assert model['metadata']['training_source_ids']==split['train_source_ids']
        assert model['metadata']['split_sha256']==summary['split_sha256']
        candidates=selection[view]['all_configs']
        best=max(candidates,key=lambda row:(row['metrics']['accuracy'],row['metrics']['macro_f1']))
        assert best==selection[view]['classifier']
        assert model['metadata']['config']==best['config']
        predictions=io.read(root/f'predictions/{view}_classifier.json')
        assert [r['query_id'] for r in predictions]==split['validation_source_ids']
        train_keys={key for i in train for key in extraction.vector(view,base[i],contexts[queries[i]['source_id']])}
        assert set(model['feature_names'])<=train_keys
        for i,r in zip(valid,predictions):
            values=extraction.vector(view,base[i],contexts[queries[i]['source_id']])
            assert portable_classifier.predict(model,values)['label']==r['prediction']
            assert r['truth']==queries[i]['truth'];checks+=1
        assert io.metrics(predictions,'prediction')==summary['validation'][view]['classifier']
        rows=io.read(root/f'predictions/{view}_k4.json')
        assert [r['query_id'] for r in rows]==split['validation_source_ids']
        assert io.metrics(rows,'prediction')==summary['validation'][view]['k4']
    primary=max(selection,key=lambda v:(selection[v]['classifier']['metrics']['accuracy'],selection[v]['classifier']['metrics']['macro_f1']))
    assert primary==summary['primary_selected_on_training']
    # Detect observational ambiguity in binary template sets, using training rows only.
    collisions=defaultdict(list)
    for i in train:
        signature=tuple(sorted(contexts[queries[i]['source_id']]['families']['templates']))
        collisions[signature].append(i)
    groups=[];forced=0
    for signature,indices in collisions.items():
        counts=Counter(label for i in indices for label in queries[i]['truth'])
        missed=len(indices)-max(counts.values())
        if missed:
            forced+=missed;groups.append({'reports':[queries[i]['source_id'] for i in indices],
                'labels':dict(counts),'unavoidable_errors_with_binary_template_only':missed})
    io.write(root/'template_collisions.json',{'training_reports':len(train),'conflicting_groups':groups,'forced_training_errors':forced})
    evidence={}
    maps=[extraction.vector('all_context_v2' if revision==2 else 'v5_contextual',base[i],contexts[q['source_id']]) for i,q in enumerate(queries)]
    for label,items in associations.items():
        evidence[label]=[]
        for item in items[:12]:
            sources=[{'query_id':queries[i]['source_id'],'scene':queries[i]['scene']}
                     for i in train if label in queries[i]['truth'] and maps[i].get(item['feature'],0)>0]
            evidence[label].append({**item,'example_training_sources':sources[:5]})
    io.write(root/'pattern_evidence.json',evidence)
    primary_model=models[primary]
    maxima={key:0. for key in primary_model['feature_names']}
    for i in train:
        values=extraction.vector(primary,base[i],contexts[queries[i]['source_id']])
        for key in maxima:maxima[key]=max(maxima[key],values.get(key,0.))
    effects={label:sorted([{'feature':key,'coefficient':coefficient,
                            'train_range_effect':coefficient*maxima[key]}
                           for key,coefficient in zip(primary_model['feature_names'],weights) if coefficient>0],
                          key=lambda row:-row['train_range_effect'])[:30]
             for label,weights in zip(primary_model['classes'],primary_model['coefficients'])}
    io.write(root/'primary_feature_effects.json',effects)
    validation={'status':'passed','classifier_portable_replays':checks,'raw_log_manifests':len(queries),
        'frozen_split':True,'training_only_vocabularies':True,'primary_chosen_from_training':primary,
        'note':'Checks outputs, identities, metadata, input provenance and vocabulary boundaries; original fitting is frozen in source snapshots.'}
    io.write(root/'validation.json',validation)
    with (root/'comparison.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        fields=['view','classifier_cv_hits','classifier_cv_n','classifier_validation_hits','k4_validation_hits','validation_n','primary']
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for view in extraction.VIEWS:
            writer.writerow({'view':view,'classifier_cv_hits':selection[view]['classifier']['metrics']['hits'],
                'classifier_cv_n':len(train),'classifier_validation_hits':summary['validation'][view]['classifier']['hits'],
                'k4_validation_hits':summary['validation'][view]['k4']['hits'],'validation_n':len(valid),'primary':view==primary})
    def table(headers,rows):
        esc=lambda x:html.escape(str(x))
        return '<table><tr>'+''.join('<th>'+esc(h)+'</th>' for h in headers)+'</tr>'+''.join(
            '<tr>'+''.join('<td>'+esc(v)+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
    rows=[]
    for view in extraction.VIEWS:
        cv=selection[view]['classifier'];m=summary['validation'][view]
        rows.append([NAMES[view],cv['config']['id'],f"{cv['metrics']['hits']}/{len(train)}",f"{cv['metrics']['accuracy']:.2%}",
            f"{m['classifier']['hits']}/{len(valid)}",f"{m['classifier']['accuracy']:.2%}",f"{m['classifier']['macro_f1']:.4f}",
            f"{m['k4']['hits']}/{len(valid)}",f"{m['k4']['accuracy']:.2%}",selection[view]['k4']['supervised']])
    patterns=''
    for label,items in evidence.items():
        stable=[x for x in items if x['supporting_scenes']>=2]
        selected=(stable or items)[:8]
        patterns+='<h3>'+html.escape(label)+'</h3>'+table(['特征','该类命中/出现报告数','该类训练报告数','训练条件比例','相对提升','支持场景数'],[
            [x['feature'],f"{x['label_hits']}/{x['feature_reports']}",x['label_reports'],f"{x['precision_in_train']:.2%}",f"{x['lift']:.2f}",x['supporting_scenes']] for x in selected])
    now=datetime.now(ZoneInfo('Asia/Shanghai')).isoformat(timespec='seconds')
    primary_result=summary['validation'][primary]['classifier']
    refitted=summary['validation']['v5']['classifier']
    original=io.read(reference/'classifier/summary.json')['metrics']['validation']['all_observations']
    class_rows=[]
    for label,counts in primary_result['per_label'].items():
        baseline=refitted['per_label'][label]
        class_rows.append([label,counts['support'],baseline['tp'],counts['tp'],
                           f"{counts['recall']:.2%}",f"{counts['f1']:.4f}"])
    document=f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>真实标签监督的日志特征挖掘</title>
<style>body{{font:15px/1.7 system-ui,sans-serif;color:#172033;max-width:1550px;margin:30px auto;padding:0 24px}}table{{border-collapse:collapse;width:100%;margin:18px 0;font-size:13px}}th,td{{border:1px solid #d7dee8;padding:7px;text-align:left;overflow-wrap:anywhere}}th{{background:#edf2f8}}.note{{background:#fff4d9;padding:16px}}</style>
<h1>用真实标签挖掘日志表征</h1><p>{now}</p>
<p>GT：/home/witty-ub-logs/gt_labels.json；原样复用 v5 的 379 训练/95 验证及内部 3 折。
寻找日志模式与标签的预测关联，不要求日志表面必须直接陈述根因。标签只用于训练部分的选择/加权/分类器，不写入查询特征。</p>
<p class="note">{len(extraction.VIEWS)} 种表示与参数选择在查看本轮验证输出之前确定。主方案由训练内部成绩选择为 {NAMES[primary]}，
固定验证命中 {primary_result['hits']}/{len(valid)}＝{primary_result['accuracy']:.2%}。
其他行是预先列出的消融对照，不根据验证成绩重新挑主方案。
v5 验证成绩此前已看过，本轮属于开发性研究，不能称为新的独立外部测试。</p>
<h2>方法与实际结果</h2>{table(['表示','训练内配置','3折命中','3折准确率','验证命中','验证准确率','验证宏F1','K4验证命中','K4验证准确率','K4监督选择'],rows)}
<p>“v5 观测”行在本轮同一 Logistic/选择/类别权重网格内重训，验证为 {refitted['hits']}/{len(valid)}＝{refitted['accuracy']:.2%}；
原 v5 报告的全部观测分类器是 {original['hits']}/{len(valid)}＝{original['accuracy']:.2%}，参数选择规则不同。
因此新增表征的同口径主比较是 {refitted['accuracy']:.2%}→{primary_result['accuracy']:.2%}，不能把参数选择带来的变化全归给新特征。</p>
<h2>主方案的类别短板</h2>{table(['标签','验证支持','同网格 v5 命中','主方案命中','主方案召回','主方案 F1'],class_rows)}
<p>主方案宏 F1 为 {primary_result['macro_f1']:.4f}，同网格 v5 为 {refitted['macro_f1']:.4f}。
总体准确率和类别覆盖必须分别判断；不能把硬件与 Worker 的收益说成各类故障均有改善。</p>
<p>第一版数值原型不能完整解析紧接单位的小数，例如 11.519ms 会截成 11；第二版已修正。
两版还存在逐行去重语义和统计方式差异，因此其差值不是“只修正单位”的单变量实验。
旧原型保留用于可追溯对照，不作为生产提取器替换的依据。</p>
<p>分类器比较 C=0.1/1、自然/平衡类别权重、是否 chi-square 选择 500 维。每折词表、缩放、选择和权重仅来自本折训练来源。
{'第二版另比较训练支持不少于 3 份报告后选择最多 1000 维，并改进单位、小数、阶段与显式状态的条件统计。第一版保留作原型对照。' if revision==2 else ''}
K4 行以对应新表示的余弦相似度取代原评分，然后保留前四票/0.05 分差规则；可选监督选择/加权也仅在训练折拟合。
它不是简单往 v5 的规则分数上加一个通道，不能把差异完全归因为原评分权重。</p>
<h2>新增提取内容</h2><ul><li>角色＋静态组件＋日志等级的词语与短语；对比只取 E/W 与加入 INFO。</li>
<li>去身份消息模板，移除日期、主机、集群、地址、PID、trace、对象键、随机数字和行号，排除测试/注入/GT 注释。</li>
<li>观测到的状态/返回码、访问操作和耗时/大小分布，同一消息里的阶段等待占比，以及固定数值分桶。</li>
<li>同进程相邻模式、常见模式组合及组件的 I/W/E 比例。身份只作本地分组，不成为特征。</li></ul>
<h2>训练数据挖出的“模式—标签”关联</h2><p>下表为训练关联，不是物理根因证明。优先展示跨至少两个场景的模式；没有时展示单场景线索。
条件比例再高，低支持或单场景模式也不升级为通用规则。完整支持来源在 pattern_evidence.json。</p>{patterns}
<h2>表征歧义与核验</h2><p>训练部分中，以模板集合完全相同分组发现 {len(groups)} 组标签冲突，
仅用二值模板时至少会有 {forced} 条训练误判。此项只衡量该种表示的信息边界，不代表全部日志不可区分。</p>
<p>核验状态 {validation['status']}：{checks} 次可移植分类器推理、474 份日志哈希清单、冻结划分及训练词表边界已核对。
当前默认 Agent 与 v5 模型未被覆盖；新提取器和模型先作为研究候选保留。</p>
<ul><li><a href="summary.json">完整结果</a> · <a href="comparison.csv">对照 CSV</a> · <a href="training_selection.json">训练内全部选择</a></li>
<li><a href="pattern_evidence.json">模式与支持案例</a> · <a href="label_associations.json">完整关联清单</a> · <a href="template_collisions.json">模板歧义</a></li>
<li><a href="primary_feature_effects.json">训练所选主模型的数值特征贡献（统计解释）</a> · <a href="refit_validation.json">独立重拟合核验</a></li>
<li><a href="split.json">原划分</a> · <a href="plan.json">冻结计划与 GT 哈希</a> · <a href="validation.json">核验</a></li></ul></html>'''
    (root/'report.html').write_text(document)
    print(root/'report.html')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',type=Path,required=True);parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--revision',type=int,choices=(1,2),default=1)
    args=parser.parse_args();report(args.reference,args.root,args.revision)
