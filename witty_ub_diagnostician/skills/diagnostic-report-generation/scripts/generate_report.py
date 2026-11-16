#!/usr/bin/env python3
"""Agent report workflow: fixed label policy, then the shared HTML renderer."""
import argparse
import copy
import hashlib
import json
from pathlib import Path
import sys

CASE_SCRIPTS = Path(__file__).resolve().parents[2]/'case-matching/scripts'
sys.path.insert(0, str(CASE_SCRIPTS))
import fixed_matching
import match_cases
import default_matching


def _label_legacy_report(payload, cases=None, log_dir=None, work_dir=None, api_base=None,classifier_model=None):
    """Use the same extraction, ranking and decision entry points as LOO."""
    result = copy.deepcopy(payload)
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    faults = result.get('faults')
    targets = list(enumerate(faults)) if isinstance(faults, list) and faults else [(None, result)]
    pairs = {(row['first_level_label'], row['second_level_label']) for row in json.loads(
        (Path(__file__).resolve().parents[1]/'references/log_label.json').read_text())}
    for index, target in targets:
        query, structured, raw = fixed_matching.extract_report(payload, log_dir, None if index is None else [index])
        stem = 'report' if index is None else f'fault-{index}'
        for suffix, value in [('.json', query), ('.structured.json', structured), ('.raw.json', raw)]:
            (work_dir/(stem+suffix)).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n')
        if cases is not None:
            if classifier_model is not None:
                from classifier_matching import match as classify
                matched=classify(query,cases,structured,raw,classifier_model)
            else:matched = fixed_matching.match(query, cases, structured, raw)
        else:
            argv = [str(work_dir/(stem+'.json')), '--json', str(work_dir/(stem+'.matches.json'))]
            if api_base:
                argv += ['--api-base', api_base]
            code = match_cases.main(argv)
            if code:
                raise ValueError(f'固定标签匹配失败，exit={code}')
            matched = json.loads((work_dir/(stem+'.matches.json')).read_text())
            if classifier_model is not None:
                from classifier_matching import features
                import feature_vectors,portable_classifier
                model=json.loads(Path(classifier_model).read_text()) if isinstance(classifier_model,(str,Path)) else classifier_model
                if model.get('metadata',{}).get('feature_version')!=feature_vectors.VERSION:
                    raise ValueError('Classifier feature version mismatch')
                if matched['decision']['method'] not in ('empty','user_usage_rule'):
                    decision=portable_classifier.predict(model,features(query,structured,raw,matched['candidates'],model['view']))
                    decision.update(method='explicit_classifier',model_id=model['metadata']['model_id'],policy='all-feature-classifier-v1')
                    matched.update(decision=decision,policy='all-feature-classifier-v1')
        decision = matched['decision']
        conclusion = target.setdefault('conclusion', {})
        first = decision['label']
        second = conclusion.get('second_level_label') if conclusion.get('first_level_label')==first else None
        if decision.get('method')=='user_usage_rule':
            second = decision.get('second_level_label')
        if (first, second) not in pairs:
            second = None
        conclusion['first_level_label'] = first
        conclusion['second_level_label'] = second
        conclusion['fault_domain'] = f'{first}/{second}' if first and second else None
        target['label_matching'] = {'policy': matched['policy'], 'decision': decision,
            'retrieval_decision': matched.get('retrieval_decision'), 'evidence_prefix': stem,
            'scope': 'fault' if index is not None else 'report',
            'observation_hashes': {suffix: hashlib.sha256((work_dir/(stem+suffix)).read_bytes()).hexdigest()
                                   for suffix in ('.json', '.structured.json', '.raw.json')},
            'log_files': raw.get('provenance', {}).get('files', [])}
    return result


def _write_evidence(directory,stem,profile,structured,raw,context):
    values={'.json':profile,'.structured.json':structured,'.raw.json':raw,'.mined.json':context}
    for suffix,value in values.items():
        (directory/(stem+suffix)).write_text(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')
    return {suffix:hashlib.sha256((directory/(stem+suffix)).read_bytes()).hexdigest() for suffix in values}


def _matching_record(matched,scope,stem,hashes,raw):
    return {'policy':matched['policy'],'decision':matched['decision'],'retrieval_decision':matched.get('retrieval_decision'),
            'feature_usage':matched.get('feature_usage'),'fallback_used':matched.get('fallback_used',False),
            'disagreement':matched.get('disagreement',False),
            'scope':scope,'evidence_prefix':stem,'observation_hashes':hashes,
            'excluded_source_ids':matched.get('excluded_source_ids',[]),
            'log_files':raw.get('provenance',{}).get('files',[])}


def _apply_label(target,matched,pairs):
    decision=matched['decision'];conclusion=target.setdefault('conclusion',{});first=decision['label']
    second=conclusion.get('second_level_label') if conclusion.get('first_level_label')==first else None
    if decision.get('method')=='user_usage_rule':second=decision.get('second_level_label')
    if (first,second) not in pairs:second=None
    conclusion.update(first_level_label=first,second_level_label=second,
                      fault_domain=f'{first}/{second}' if first and second else None)


def label_report(payload,cases=None,log_dir=None,work_dir=None,api_base=None,classifier_model=None):
    """Default report-level numeric inference plus observable cosine fallback/reference."""
    model=classifier_model
    if isinstance(model,(str,Path)):model=default_matching.load_file(str(model))
    if model is not None and model.get('view')!='numeric_units':
        return _label_legacy_report(payload,cases,log_dir,work_dir,api_base,model)
    result=copy.deepcopy(payload);directory=Path(work_dir);directory.mkdir(parents=True,exist_ok=True)
    profile,structured,raw,context=default_matching.observe(payload,log_dir)
    hashes=_write_evidence(directory,'report',profile,structured,raw,context)
    if cases is None and api_base:
        argv=[str(directory/'report.json'),'--api-base',api_base,'--json',str(directory/'report.matches.json')]
        code=match_cases.main(argv)
        if code:raise ValueError(f'案例库检索失败，exit={code}')
        cases=json.loads((directory/'report.matches.json').read_text())['case_envelopes']
    matched=default_matching.match(profile,cases,structured,raw,context,model=model,
                                    query_identities=default_matching.identities(payload))
    (directory/'report.matches.json').write_text(json.dumps(matched,ensure_ascii=False,indent=2)+'\n')
    result['label_matching']=_matching_record(matched,'report','report',hashes,raw)
    faults=result.get('faults');targets=list(enumerate(faults)) if isinstance(faults,list) and faults else [(None,result)]
    pairs={(row['first_level_label'],row['second_level_label']) for row in json.loads(
        (Path(__file__).resolve().parents[1]/'references/log_label.json').read_text())}
    if len(targets)==1:
        index,target=targets[0];_apply_label(target,matched,pairs)
        target['label_matching']=_matching_record(matched,'report','report',hashes,raw)
    else:
        for index,target in targets:
            query,observed,_=fixed_matching.extract_report(payload,None,[index])
            query['log_semantic_profile']=profile['log_semantic_profile'];observed['log']=structured['log']
            stem=f'fault-{index}';fault_hashes=_write_evidence(directory,stem,query,observed,raw,context)
            fault_match=default_matching.match(query,cases,observed,raw,context,allow_classifier=False,
                fallback_reason='multiple_faults_require_fault_scoped_evidence',
                query_identities=default_matching.identities(payload))
            _apply_label(target,fault_match,pairs)
            target['label_matching']=_matching_record(fault_match,'fault_profile_with_shared_report_logs',stem,fault_hashes,raw)
            (directory/(stem+'.matches.json')).write_text(json.dumps(fault_match,ensure_ascii=False,indent=2)+'\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', type=Path, help='Agent 准备的观测和诊断报告 JSON')
    parser.add_argument('out', type=Path, nargs='?', help='输出 HTML；默认沿用报告 skill 的持久化目录')
    parser.add_argument('--cases', type=Path, help='已准备案例信封；不提供时检索已确认案例库')
    parser.add_argument('--log-dir', type=Path, help='本次现场原始日志；缺失时明确记录未知观测')
    parser.add_argument('--api-base', help='HTTP 案例库地址')
    parser.add_argument('--classifier-model',type=Path,help='覆盖内置冻结模型；默认新增数值特征分类器，退化为全特征余弦 K4')
    parser.add_argument('--allow-incomplete', action='store_true')
    parser.add_argument('--labels-only', action='store_true', help='只生成已应用固定标签的 JSON，不渲染 HTML')
    args = parser.parse_args(argv)
    payload = json.loads(args.data.read_text())
    bundle = json.loads(args.cases.read_text()) if args.cases else None
    cases = bundle.get('cases') if isinstance(bundle, dict) else bundle
    import render_report
    from types import SimpleNamespace
    output = args.out
    if output is None:
        output = (args.data.with_name(args.data.stem+'.labelled.json') if args.labels_only else
                  render_report.output_path(SimpleNamespace(out=None, kb_id=None, no_sidecar=False), payload))
    if args.labels_only and output.resolve()==args.data.resolve():
        parser.error('标签输出不能覆盖输入原稿')
    work = output.with_name(output.stem+'.matching')
    try:
        labelled = label_report(payload, cases, args.log_dir, work, args.api_base,args.classifier_model)
    except ValueError as error:
        parser.error(str(error))
    labelled_path = work/'labelled_report.json'
    labelled_path.write_text(json.dumps(labelled, ensure_ascii=False, indent=2)+'\n')
    if args.labels_only:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(labelled_path.read_text())
        print(output)
        return 0
    render_args = [str(labelled_path), str(output)]
    if args.allow_incomplete:
        render_args.append('--allow-incomplete')
    return render_report.main(render_args)


if __name__=='__main__':
    raise SystemExit(main())
