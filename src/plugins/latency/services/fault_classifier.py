"""Reconcile confirmed-case changes into versioned, atomic classifier bundles."""
from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import gzip
import hashlib
import importlib
import json
import logging
import os
from pathlib import Path
import shutil
import sys
import uuid

from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError

from latency.common.local_time import local_now
from latency.database.engine import PGManager
from latency.database.models import DiagCaseLibrary

logger=logging.getLogger(__name__)
LOCK_KEY=741793816
CHANGE_CHECK_SECONDS=1.0
MIN_TRAINING_REPORTS=20
MIN_REPORTS_PER_CLASS=5


def runtime():
    """Locate the bundled skill in source, host and RPM/container layouts."""
    roots=[Path(os.environ['WITTY_CASE_MATCHING_DIR'])] if os.environ.get('WITTY_CASE_MATCHING_DIR') else []
    deployed=Path(os.environ.get('WITTY_DIR') or '/var/witty-ub')
    roots += [Path(__file__).resolve().parents[4]/'witty_ub_diagnostician/skills/case-matching',
              deployed/'classifier-runtime',
              deployed/'witty_ub_diagnostician/.opencode/skills/case-matching']
    for root in roots:
        if (root/'scripts/default_matching.py').is_file():
            path=str(root/'scripts')
            if path not in sys.path:sys.path.insert(0,path)
            return importlib.import_module('default_matching')
    raise RuntimeError('找不到故障分类器 skill，请检查部署资源')


def fingerprint(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def now():return local_now().isoformat(timespec='seconds')


def dataset_fingerprint(cases):
    rt=runtime()
    manifest_bytes = (rt.ASSETS/'manifest.json').read_bytes()
    manifest = json.loads(manifest_bytes)
    # Case retraining uses the reference bank as its seed. A bundled weight refresh is separate.
    reference_seed = manifest.get('reference_training_seed', {})
    bank_sha = manifest.get('files', {}).get('cosine_bank', {}).get('sha256')
    legacy_seed = reference_seed.get('legacy_manifest_sha256') if reference_seed.get('bank_sha256') == bank_sha else None
    seed = legacy_seed or hashlib.sha256(manifest_bytes).hexdigest()
    return fingerprint({'cases':cases,'features':rt.extraction.VERSION,
        'training_policy':[MIN_TRAINING_REPORTS,MIN_REPORTS_PER_CLASS],
        'seed_manifest':seed})


class FaultClassifierService:
    _error: str | None=None

    @staticmethod
    async def cases():
        fields=('id','report_id','source_fault_id','source_fault_hash','source_sidecar_hash',
                'source_label_hash','first_level_label','second_level_label','kb_id','kb_name','source_log_ids','verification_json')
        async with PGManager.session() as session:
            result=await session.execute(select(*(getattr(DiagCaseLibrary,k) for k in fields)).where(
                DiagCaseLibrary.status=='confirmed',DiagCaseLibrary.existed_status.is_(True)).order_by(DiagCaseLibrary.id))
            rows=[dict(row) for row in result.mappings().all()]
            for row in rows:row['label_verified']=bool((row.pop('verification_json') or {}).get('closed_loop'))
            return rows

    @staticmethod
    def _read():
        try:return runtime().model_registry.read_json(runtime().model_registry.model_root()/'training.json',{})
        except ValueError:return {'status':'failed','error':'训练状态文件损坏，将从已发布模型恢复'}

    @staticmethod
    def _write(state):
        runtime().model_registry.atomic_json(runtime().model_registry.model_root()/'training.json',state)

    @staticmethod
    async def status():
        current=await FaultClassifierService.cases();state=FaultClassifierService._read()
        digest=dataset_fingerprint(current);phase=state.get('status','idle')
        changed=digest!=state.get('trained_fingerprint') and bool(current or state.get('trained_fingerprint'))
        if FaultClassifierService._error:phase='failed'
        elif phase!='training' and changed and not (phase=='failed' and digest==state.get('attempt_fingerprint')):phase='pending'
        messages={'idle':'当前使用内置故障分类器，已确认案例变更后将自动训练。',
            'insufficient_data':'有效训练数据不足，已停用分类器，使用当前案例集的全特征余弦 K4；无可比案例时不自动选标签。',
            'pending':'故障分类器待训练，建议在训练完成后生成定界报告。',
            'training':'故障分类器训练中，建议在训练完成后生成定界报告。',
            'ready':'故障分类器训练完成，可以生成定界报告。',
            'failed':'故障分类器训练失败，当前继续使用上一版本，请稍后重试。'}
        return {'status':phase,'message':messages.get(phase,messages['idle']),
            'confirmed_case_count':len(current),'sample_count':state.get('sample_count'),
            'skipped_case_count':state.get('skipped_case_count',0),'model_version':state.get('model_version'),
            'started_at':state.get('started_at'),'completed_at':state.get('completed_at'),
            'pending_changes':phase=='training' and digest!=state.get('attempt_fingerprint'),
            'error':FaultClassifierService._error or state.get('error'),
            'training_reason':state.get('training_reason'),'class_counts':state.get('class_counts',{})}

    @staticmethod
    async def retry():
        state=FaultClassifierService._read()
        if state.get('status')!='training':
            state.update(status='pending',attempt_fingerprint=None,error=None)
            FaultClassifierService._error=None;FaultClassifierService._write(state)
        return await FaultClassifierService.status()

    @staticmethod
    @asynccontextmanager
    async def lease():
        async with PGManager.engine().connect() as conn:
            acquired=(await conn.execute(text('SELECT pg_try_advisory_lock(:key)'),{'key':LOCK_KEY})).scalar()
            try:yield bool(acquired)
            finally:
                if acquired:await conn.execute(text('SELECT pg_advisory_unlock(:key)'),{'key':LOCK_KEY})

    @staticmethod
    async def tick():
        if os.environ.get('WITTY_CLASSIFIER_AUTO_TRAIN','1').lower() in ('0','false','off'):return
        try:
            async with FaultClassifierService.lease() as acquired:
                if acquired:await FaultClassifierService.reconcile()
        except Exception as exc:
            FaultClassifierService._error=str(exc);logger.exception('故障分类器后台训练任务失败')

    @staticmethod
    async def reconcile():
        while await FaultClassifierService._reconcile_once():
            pass

    @staticmethod
    async def _reconcile_once():
        current=await FaultClassifierService.cases();digest=dataset_fingerprint(current);state=FaultClassifierService._read()
        FaultClassifierService._error=None
        if digest==state.get('trained_fingerprint') and state.get('status') in ('idle','ready','insufficient_data'):return
        registry=runtime().model_registry
        active=registry.active_directory()
        if active is not None:
            manifest=registry.read_json(active/'manifest.json',{})
            if manifest.get('dataset_fingerprint')==digest:
                state.update(status='insufficient_data' if manifest.get('classifier_disabled_reason') else 'ready',
                    trained_fingerprint=digest,model_version=active.name,
                    training_reason=manifest.get('classifier_disabled_reason'),class_counts=manifest.get('class_counts',{}),
                    sample_count=manifest.get('training_reports'),completed_at=state.get('completed_at') or now(),error=None,
                    managed_identities=manifest.get('managed_identities',state.get('managed_identities',[])),
                    skipped_case_count=manifest.get('skipped_case_count',state.get('skipped_case_count',0)))
                FaultClassifierService._error=None;FaultClassifierService._write(state);return
        if state.get('status')=='failed' and state.get('attempt_fingerprint')==digest:return
        if not state and not current:
            FaultClassifierService._write({'status':'idle','trained_fingerprint':digest,'managed_identities':[]});return
        identities=set(state.get('managed_identities',[]))
        for case in current:
            if not case.get('label_verified'):continue
            if case.get('kb_id'):identities.add('kb_id:'+str(case['kb_id']))
            if case.get('kb_name'):identities.add('name:'+str(case['kb_name']))
        state.update(status='training',attempt_fingerprint=digest,started_at=now(),error=None,
            confirmed_case_count=len(current),managed_identities=sorted(identities))
        FaultClassifierService._error=None;FaultClassifierService._write(state)
        candidate=None;published=False;work=None
        try:
            async def build():
                additions,skipped=await FaultClassifierService.samples(current)
                return await build_in_process(additions,identities,digest),skipped
            work=asyncio.create_task(build())
            while not work.done():
                await asyncio.wait({work},timeout=CHANGE_CHECK_SECONDS)
                if dataset_fingerprint(await FaultClassifierService.cases())!=digest:
                    await cancel_build(work)
                    state.update(status='pending',error=None)
                    FaultClassifierService._write(state)
                    return True
            candidate,skipped=await work
            if dataset_fingerprint(await FaultClassifierService.cases())!=digest:
                state.update(status='pending',error=None)
                shutil.rmtree(candidate['directory'],ignore_errors=True);candidate=None
                FaultClassifierService._write(state);return True
            else:
                rt=runtime();manifest_path=candidate['directory']/'manifest.json'
                manifest=rt.model_registry.read_json(manifest_path,{})
                manifest.update(skipped_case_count=len(skipped),confirmed_case_count=len(current))
                rt.model_registry.atomic_json(manifest_path,manifest)
                rt.model_registry.atomic_json(rt.model_registry.model_root()/'active.json',{'version':candidate['version']})
                published=True
                state.update(status='insufficient_data' if candidate.get('training_reason') else 'ready',
                    training_reason=candidate.get('training_reason'),class_counts=candidate.get('class_counts',{}),
                    trained_fingerprint=digest,completed_at=now(),
                    model_version=candidate['version'],sample_count=candidate['sample_count'],
                    skipped_case_count=len(skipped),skipped_cases=skipped,error=None)
            FaultClassifierService._write(state)
        except asyncio.CancelledError:
            if work and not published:await cancel_build(work)
            if candidate and not published:shutil.rmtree(candidate['directory'],ignore_errors=True)
            state.update(status='pending',error=None);FaultClassifierService._write(state)
            raise
        except Exception as exc:
            if work and not published:await cancel_build(work)
            state.update(status='failed',error=str(exc));FaultClassifierService._write(state)
            if candidate and not published:shutil.rmtree(candidate['directory'],ignore_errors=True)
            logger.exception('故障分类器训练失败，保留上一模型')

    @staticmethod
    async def samples(cases):
        from latency.services.report_review import ReportReviewService
        from latency.services.label_taxonomy import fault_case_labels
        from latency.database.managers.log_file import LogFilePGManager
        groups={};skipped=[];samples=[];rt=runtime()
        for case in cases:groups.setdefault(case.get('report_id') or 'independent:'+case['id'],[]).append(case)
        for report_id,items in groups.items():
            try:
                if report_id.startswith('independent:'):raise ValueError('无可追溯的源报告')
                if not all(c.get('label_verified') for c in items):raise ValueError('定界结论尚未完成检验')
                labels={c['first_level_label'] for c in items}
                if not labels or None in labels or not labels<=set(rt.feature_vectors.LABELS):raise ValueError('一级标签缺失或不在五类范围')
                hashes={c['source_sidecar_hash'] for c in items}
                if len(hashes)!=1 or None in hashes:raise ValueError('来源报告版本不一致')
                snapshot=await ReportReviewService.require_confirmed(report_id,next(iter(hashes)))
                payload=snapshot.payload
                faults={f['id']:f for f in payload.get('faults',[]) if f.get('id')}
                if faults and any(c['source_fault_id'] not in faults or
                    fault_case_labels(faults[c['source_fault_id']])[0]!=c['first_level_label'] for c in items):
                    raise ValueError('案例分类与已确认的故障快照不一致')
                required={f['id'] for f in payload.get('faults',[]) if fault_case_labels(f)[0] in rt.feature_vectors.LABELS}
                if not required<={c['source_fault_id'] for c in items}:raise ValueError('多故障报告尚未全部确认')
                key=fingerprint({'report':report_id,'hash':snapshot.sidecar_hash,'features':rt.extraction.VERSION})
                cache=rt.model_registry.model_root()/'samples'/(key+'.json.gz')
                if cache.exists():
                    with gzip.open(cache,'rt') as stream:sample=json.load(stream)
                else:
                    sample=await asyncio.to_thread(sidecar_sample,snapshot,rt)
                    if sample is None:
                        sample=await asyncio.to_thread(packaged_sample,payload,rt)
                    if sample is None:
                        log_ids=set(x for c in items for x in c.get('source_log_ids') or [])
                        basic=payload.get('basic_info') or {}
                        if basic.get('log_id'):log_ids.add(basic['log_id'])
                        paths=[]
                        for log_id in sorted(log_ids):
                            log=await LogFilePGManager.get_log_file_by_log_file_id(log_id)
                            if log:paths.append(Path(log.file_path))
                        if not paths and basic.get('kb_id'):
                            paths=[Path(p) for _,p in await LogFilePGManager.list_log_file_paths(basic['kb_id'])]
                        if len(paths)!=1 or not paths[0].is_dir():raise ValueError('缺少可读取的唯一原始日志目录或数值观测快照')
                        sample=await asyncio.to_thread(observe_sample,payload,paths[0],rt)
                    cache.parent.mkdir(parents=True,exist_ok=True)
                    with gzip.open(cache,'wt') as stream:json.dump(sample,stream,ensure_ascii=False)
                sample={**sample,'source_id':'report:'+report_id,'labels':sorted(labels),
                    'cases':[{'id':c['id'],'label':c['first_level_label'],'source_id':'report:'+report_id,
                              'identity':sample['identity'],'source_fault_id':c['source_fault_id']} for c in items]}
                matching=payload.get('label_matching') or {};prediction=matching.get('decision') or {}
                if prediction.get('method') in rt.CLASSIFIER_METHODS.values() and prediction.get('model_id'):
                    sample['prediction_before_training']={'model_id':prediction['model_id'],
                        'prediction':prediction.get('label'),'confirmed_labels':sorted(labels),
                        'hit':prediction.get('label') in labels,
                        'new_source':not bool(matching.get('excluded_source_ids'))}
                if not any(v for k,v in sample['vector'].items() if k.startswith('mined2:numeric_units:')):
                    raise ValueError('缺少可用的新增数值观测')
                samples.append(sample)
            except SQLAlchemyError:raise
            except Exception as exc:
                skipped.extend({'case_id':c['id'],'reason':str(exc)} for c in items)
        return samples,skipped


def observe_sample(payload,path,rt):
    profile,structured,raw,context=rt.observe(payload,path)
    return {'identity':rt.identities(payload),'vector':rt.extraction.vector('all_context_v2',
        rt.cosine_matching.observed_vector(profile,structured,raw),context),
        'log_content_sha256':rt.digest(sorted(f['sha256'] for f in context['provenance']['files']))}


def sidecar_sample(snapshot,rt):
    matching=(snapshot.payload or {}).get('label_matching') or {};hashes=matching.get('observation_hashes') or {}
    directory=snapshot.html.with_name(snapshot.html.stem+'.matching');prefix=matching.get('evidence_prefix','report')
    if prefix!='report':return None
    values={}
    for suffix in ('.json','.structured.json','.raw.json','.mined.json'):
        path=directory/(prefix+suffix)
        if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=hashes.get(suffix):return None
        values[suffix]=json.loads(path.read_text())
    context=values['.mined.json']
    if context.get('schema_version')!=rt.extraction.VERSION:return None
    return {'identity':rt.identities(snapshot.payload),'vector':rt.extraction.vector('all_context_v2',
        rt.cosine_matching.observed_vector(values['.json'],values['.structured.json'],values['.raw.json']),context),
        'log_content_sha256':rt.digest(sorted(f['sha256'] for f in context['provenance']['files']))}


def packaged_sample(payload,rt):
    """Only reuse real seed observations for the same source and unchanged evidence."""
    identities=set(rt.identities(payload))
    if not identities:return None
    expected=rt.digest(rt.fixed_matching.extract_report(payload)[:2])
    matches=[s for s in rt.asset('cosine_bank',rt.ASSETS)['sources'] if
             identities&set(s.get('identity',[])) and s.get('report_observation_fingerprint')==expected]
    if len(matches)!=1:return None
    source=matches[0]
    return {'identity':source['identity'],'vector':source['vector'],
            'log_content_sha256':source.get('log_content_sha256'),'observation_source':'packaged_verified_snapshot'}


def train_bundle(additions,managed_identities,dataset_fingerprint,version=None):
    import sklearn
    from sklearn.feature_extraction import DictVectorizer
    from sklearn.preprocessing import MaxAbsScaler
    from sklearn.linear_model import LogisticRegression
    from threadpoolctl import threadpool_limits
    rt=runtime();seed=rt.asset('cosine_bank',rt.ASSETS);sources=[];cases=[]
    labels={}
    for case in seed['cases']:labels.setdefault(case['source_id'],set()).add(case['label'])
    managed=set(managed_identities)
    for source in seed['sources']:
        if managed&set(source.get('identity',[])):continue
        sources.append({**source,'labels':sorted(labels[source['source_id']])})
    source_ids={s['source_id'] for s in sources}
    cases.extend(c for c in seed['cases'] if c['source_id'] in source_ids)
    for sample in additions:sources.append(sample);cases.extend(sample['cases'])
    # One training row per log source, with a label set; aliases do not multiply its weight.
    dedup={}
    for source in sources:
        key=source.get('log_content_sha256') or source['source_id']
        if key in dedup:dedup[key]['labels']=sorted(set(dedup[key]['labels'])|set(source['labels']))
        else:dedup[key]={**source}
    training_sources=list(dedup.values())
    canonical={s['source_id']:dedup[s.get('log_content_sha256') or s['source_id']]['source_id'] for s in sources}
    unique_cases=[];seen=set()
    for case in cases:
        source=canonical[case['source_id']]
        fault=case.get('source_fault_id') or case['id'].split('#')[-1]
        key=(source,fault,case['label'])
        if key not in seen:unique_cases.append({**case,'source_id':source});seen.add(key)
    sources=training_sources;cases=unique_cases
    counts={label:sum(label in s['labels'] for s in training_sources) for label in
            sorted({label for s in training_sources for label in s['labels']})}
    reasons=[]
    if len(training_sources)<MIN_TRAINING_REPORTS:reasons.append(f'独立来源 {len(training_sources)} 个，至少需要 {MIN_TRAINING_REPORTS} 个')
    if len(counts)<2:reasons.append('至少需要两类有效标签')
    rare={k:v for k,v in counts.items() if v<MIN_REPORTS_PER_CLASS}
    if rare:reasons.append(f'每个已出现类别至少需要 {MIN_REPORTS_PER_CLASS} 个独立来源，当前 '+str(rare))
    reason='；'.join(reasons) or None
    version=version or local_now().strftime('%Y%m%d%H%M%S')+'-'+uuid.uuid4().hex[:10]
    if reason:return publish_bundle(rt,None,sources,cases,managed,dataset_fingerprint,version,counts,reason)
    numeric=[{k:v for k,v in s['vector'].items() if k.startswith('mined2:numeric_units:')} for s in training_sources]
    with threadpool_limits(limits=1):
        dictionary=DictVectorizer();x=dictionary.fit_transform(numeric);scaler=MaxAbsScaler();x=scaler.fit_transform(x)
        indices=[];target=[];weight=[]
        for i,source in enumerate(training_sources):
            for label in source['labels']:indices.append(i);target.append(label);weight.append(1/len(source['labels']))
        classifier=LogisticRegression(C=1.,solver='lbfgs',max_iter=1200,tol=1e-4)
        classifier.fit(x[indices],target,sample_weight=weight)
    model={'schema_version':rt.portable_classifier.VERSION,'kind':'logistic','view':'numeric_units',
        'classes':classifier.classes_.tolist(),'feature_names':dictionary.get_feature_names_out().tolist(),
        'coefficients':(classifier.coef_/scaler.scale_).tolist(),'intercept':classifier.intercept_.tolist(),
        'metadata':{'feature_version':rt.extraction.VERSION,'model_id':version,'training_reports':len(training_sources),
            'training_source_ids':[s['source_id'] for s in training_sources],'config':{'C':1.,'class_weight':None},
            'dataset_fingerprint':dataset_fingerprint,'independent_test_score':None,'sklearn_version':sklearn.__version__,
            'prediction_before_training':[{'source_id':s['source_id'],**s['prediction_before_training']}
                for s in training_sources if s.get('prediction_before_training')]}}
    rt.validate_model(model)
    assert classifier.predict(x).tolist()==[rt.portable_classifier.predict(model,v)['label'] for v in numeric]
    return publish_bundle(rt,model,sources,cases,managed,dataset_fingerprint,version,counts)


def publish_bundle(rt,model,sources,cases,managed,dataset_fingerprint,version,counts,reason=None):
    directory=rt.model_registry.model_root()/'versions'/version;directory.mkdir(parents=True)
    bank={'schema_version':rt.cosine_matching.VERSION,'feature_version':rt.extraction.VERSION,'view':'all_context_v2',
          'sources':sources,'cases':cases}
    files={}
    for kind,value in ([('numeric_classifier',model)] if model is not None else [])+[('cosine_bank',bank)]:
        path=directory/(kind+'.json.gz')
        with gzip.open(path,'wt') as stream:json.dump(value,stream,ensure_ascii=False,allow_nan=False)
        files[kind]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    rt.model_registry.atomic_json(directory/'manifest.json',{'schema_version':'default-label-assets-v1','policy':rt.POLICY,
        'feature_version':rt.extraction.VERSION,'files':files,'training_reports':len(sources),'reference_cases':len(cases),
        'dataset_fingerprint':dataset_fingerprint,'independent_test_score':None,'model_version':version,
        'managed_identities':sorted(managed),'classifier_disabled_reason':reason,'class_counts':counts,'extractor_sha256':{
            name:hashlib.sha256((Path(rt.__file__).parent/name).read_bytes()).hexdigest() for name in
            ('mined_log_features.py','mined_log_features_v2.py','log_message_features.py')}})
    return {'directory':directory,'version':version,'sample_count':len(sources),'training_reason':reason,'class_counts':counts}


async def cancel_build(work):
    """Also clean up output if completion raced with cancellation."""
    work.cancel()
    try:
        result,_=await work
    except (asyncio.CancelledError,Exception):return
    shutil.rmtree(result['directory'],ignore_errors=True)


async def build_in_process(additions,managed,digest):
    """A fit runs outside the server so cancellation actually stops its CPU work."""
    rt=runtime();version=local_now().strftime('%Y%m%d%H%M%S')+'-'+uuid.uuid4().hex[:10]
    job=rt.model_registry.model_root()/'jobs'/version;job.mkdir(parents=True)
    candidate=rt.model_registry.model_root()/'versions'/version
    rt.model_registry.atomic_json(job/'input.json',{'additions':additions,'managed':sorted(managed),
        'digest':digest,'version':version})
    process=None;completed=False
    try:
        env=dict(os.environ)
        env['PYTHONPATH']=str(Path(__file__).resolve().parents[2])+os.pathsep+env.get('PYTHONPATH','')
        with (job/'worker.log').open('wb') as output:
            process=await asyncio.create_subprocess_exec(sys.executable,str(Path(__file__).resolve()),
                '--train',str(job),env=env,stdout=output,stderr=output)
            code=await process.wait()
        if code:raise RuntimeError('训练进程失败：'+(job/'worker.log').read_text(errors='replace')[-3000:])
        result=rt.model_registry.read_json(job/'result.json')
        result['directory']=Path(result['directory']);completed=True
        return result
    finally:
        if process and process.returncode is None:
            try:process.terminate()
            except ProcessLookupError:pass
            try:await asyncio.wait_for(process.wait(),timeout=5)
            except asyncio.TimeoutError:
                process.kill();await process.wait()
        if not completed:shutil.rmtree(candidate,ignore_errors=True)
        shutil.rmtree(job,ignore_errors=True)


if __name__=='__main__':
    if len(sys.argv)!=3 or sys.argv[1]!='--train':raise SystemExit('Use --train JOB_DIRECTORY')
    job=Path(sys.argv[2]);rt=runtime();request=rt.model_registry.read_json(job/'input.json')
    result=train_bundle(request['additions'],request['managed'],request['digest'],version=request['version'])
    result['directory']=str(result['directory']);rt.model_registry.atomic_json(job/'result.json',result)
