import asyncio
import copy
from contextlib import asynccontextmanager
import gzip
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from latency.services import fault_classifier as module
from latency.services.fault_classifier import FaultClassifierService as Service
from latency.routers.diag_case_library import router


def case(case_id='c1',label='Worker故障'):
    return {'id':case_id,'kb_id':'kb-'+case_id,'kb_name':case_id,'report_id':'r-'+case_id,
        'source_fault_id':'F01','source_sidecar_hash':'hash','first_level_label':label,'source_log_ids':[],'label_verified':True}


def sample(item):
    return {'source_id':item['report_id'],'identity':['kb_id:'+item['kb_id']],
        'labels':[item['first_level_label']],'vector':{'mined2:numeric_units:duration':2.},
        'cases':[{'id':item['id'],'source_id':item['report_id'],'label':item['first_level_label']}]}


@pytest.fixture
def training_env(tmp_path,monkeypatch):
    monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path));Service._error=None
    cases=[];builds=[];rt=module.runtime()
    async def current():return copy.deepcopy(cases)
    async def samples(items):return [sample(c) for c in items],[]
    def build(additions,managed,digest):
        version='model-'+str(len(builds));directory=tmp_path/'versions'/version;directory.mkdir(parents=True)
        rt.model_registry.atomic_json(directory/'manifest.json',{'dataset_fingerprint':digest})
        builds.append({'additions':additions,'managed':set(managed),'fingerprint':digest})
        return {'version':version,'directory':directory,'sample_count':474+len(additions)}
    monkeypatch.setattr(Service,'cases',current);monkeypatch.setattr(Service,'samples',samples)
    async def worker(*args):return await asyncio.to_thread(module.train_bundle,*args)
    monkeypatch.setattr(module,'build_in_process',worker)
    monkeypatch.setattr(module,'train_bundle',build)
    return SimpleNamespace(cases=cases,builds=builds,build=build,rt=rt,root=tmp_path)


@pytest.mark.asyncio
async def test_confirmed_add_and_delete_retrain_and_preserve_withdrawn_seed_identity(training_env):
    env=training_env
    await Service.reconcile();assert (await Service.status())['status']=='idle'
    env.cases.append(case());assert (await Service.status())['status']=='pending'
    await Service.reconcile();state=await Service.status()
    assert state['status']=='ready' and state['sample_count']==475
    env.cases.clear();assert (await Service.status())['status']=='pending'
    await Service.reconcile()
    assert len(env.builds)==2 and env.builds[1]['additions']==[]
    assert 'kb_id:kb-c1' in env.builds[1]['managed']
    assert (await Service.status())['model_version']=='model-1'
    await Service.reconcile();assert len(env.builds)==2


@pytest.mark.asyncio
async def test_changes_during_training_discard_stale_bundle_and_restart_immediately(training_env,monkeypatch):
    env=training_env;env.cases.append(case())
    def changing(*args):
        result=env.build(*args)
        if len(env.builds)==1:env.cases.append(case('c2'))
        return result
    monkeypatch.setattr(module,'train_bundle',changing)
    await Service.reconcile()
    assert (await Service.status())['status']=='ready'
    assert not (env.root/'versions/model-0').exists()
    assert len(env.builds)==2 and len(env.builds[-1]['additions'])==2


@pytest.mark.asyncio
async def test_running_work_is_cancelled_before_restarting_latest_snapshot(training_env,monkeypatch):
    env=training_env;env.cases.append(case());started=asyncio.Event();cancelled=asyncio.Event();calls=0
    async def worker(*args):
        nonlocal calls
        calls+=1
        if calls==1:
            started.set()
            try:await asyncio.Future()
            finally:cancelled.set()
        assert cancelled.is_set()
        return env.build(*args)
    monkeypatch.setattr(module,'build_in_process',worker)
    monkeypatch.setattr(module,'CHANGE_CHECK_SECONDS',.01)
    task=asyncio.create_task(Service.reconcile());await started.wait()
    env.cases.clear();env.cases.append(case('replacement'))
    await asyncio.wait_for(task,5)
    assert calls==2 and cancelled.is_set()
    assert env.builds[-1]['additions'][0]['source_id']=='r-replacement'
    assert (await Service.status())['status']=='ready'


@pytest.mark.asyncio
async def test_failed_training_keeps_old_active_model_and_can_retry(training_env,monkeypatch):
    env=training_env;env.cases.append(case());await Service.reconcile()
    active=(env.root/'active.json').read_bytes();env.cases.append(case('c2'))
    def fail(*args):raise ValueError('训练样本不完整')
    monkeypatch.setattr(module,'train_bundle',fail);await Service.reconcile()
    assert (await Service.status())['status']=='failed'
    assert (env.root/'active.json').read_bytes()==active
    await Service.retry();monkeypatch.setattr(module,'train_bundle',env.build)
    await Service.reconcile();assert (await Service.status())['status']=='ready'
    assert (env.root/'active.json').read_bytes()!=active


@pytest.mark.asyncio
async def test_unacquired_database_lease_does_not_start_training(monkeypatch):
    @asynccontextmanager
    async def lease():yield False
    reconcile=AsyncMock();monkeypatch.setattr(Service,'lease',lease);monkeypatch.setattr(Service,'reconcile',reconcile)
    await Service.tick();reconcile.assert_not_awaited()


@pytest.mark.asyncio
async def test_pending_changes_are_visible_while_training(training_env):
    env=training_env
    Service._write({'status':'training','attempt_fingerprint':module.fingerprint([])})
    env.cases.append(case())
    state=await Service.status();assert state['pending_changes'] and state['status']=='training'
    assert '建议在训练完成后生成定界报告' in state['message']


def test_status_route_and_authenticated_manual_retry(monkeypatch):
    result={'status':'training','message':'故障分类器训练中','confirmed_case_count':3}
    monkeypatch.setattr(Service,'status',AsyncMock(return_value=result));retry=AsyncMock(return_value=result)
    monkeypatch.setattr(Service,'retry',retry)
    app=FastAPI();app.include_router(router);client=TestClient(app)
    assert client.get('/diag_case_library/classifier/status').json()['result']['status']=='training'
    response=client.post('/diag_case_library/classifier/retrain',json={'requested_by':'ops'})
    assert response.status_code==200;retry.assert_awaited_once()


def test_real_bundle_fit_can_export_binary_model_and_uses_only_numeric_input(tmp_path,monkeypatch):
    rt=module.runtime();monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    seed={'sources':[{'source_id':f'seed-{i}','identity':[f'kb_id:{i}'],
          'vector':{'mined2:numeric_units:x':float(i+1),'query:legacy:other':100.}} for i in range(20)],
          'cases':[{'id':str(i),'source_id':f'seed-{i}','label':'Worker故障' if i<10 else '硬件故障'} for i in range(20)]}
    monkeypatch.setattr(rt,'asset',lambda *args:seed)
    result=module.train_bundle([],set(),'snapshot')
    with gzip.open(result['directory']/'numeric_classifier.json.gz','rt') as stream:model=json.load(stream)
    assert model['feature_names']==['mined2:numeric_units:x']
    assert model['metadata']['dataset_fingerprint']=='snapshot'
    rt.validate_model(model)
    assert len(model['classes'])==2 and len(model['coefficients'])==1


def test_runtime_loads_new_versions_and_pins_model_and_bank(tmp_path,monkeypatch):
    import hashlib
    rt=module.runtime();monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    classes=list(rt.feature_vectors.LABELS);key='mined2:numeric_units:signal'
    for version,winner in [('first','硬件故障'),('second','Worker故障')]:
        directory=tmp_path/'versions'/version;directory.mkdir(parents=True)
        model={'schema_version':'label-reranker-v1','kind':'logistic','view':'numeric_units','feature_names':[key],
            'classes':classes,'coefficients':[[0.] for _ in classes],
            'intercept':[10. if label==winner else 0. for label in classes],
            'metadata':{'model_id':version,'feature_version':rt.extraction.VERSION}}
        bank={'schema_version':rt.cosine_matching.VERSION,'sources':[],'cases':[]};files={}
        for kind,value in [('numeric_classifier',model),('cosine_bank',bank)]:
            path=directory/(kind+'.json.gz')
            with gzip.open(path,'wt') as stream:json.dump(value,stream)
            files[kind]={'path':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
        rt.model_registry.atomic_json(directory/'manifest.json',{'files':files})
    profile={'schema_version':'legacy-evidence-v1','status_codes':[],'failure_mode_ids':[],
        'latency_components':[],'operation':'GET','log_semantic_profile':{}}
    context=rt.unknown_context();context['families']['numeric_units']={'signal':1.}
    rt.model_registry.atomic_json(tmp_path/'active.json',{'version':'first'})
    original=rt.asset;seen=[]
    def swapping(kind,assets_dir=None):
        seen.append(Path(assets_dir).name)
        value=original(kind,assets_dir)
        if kind=='cosine_bank':rt.model_registry.atomic_json(tmp_path/'active.json',{'version':'second'})
        return value
    monkeypatch.setattr(rt,'asset',swapping)
    assert rt.match(profile,context=context)['decision']['label']=='硬件故障'
    assert seen==['first','first']
    assert rt.match(profile,context=context)['decision']['label']=='Worker故障'


@pytest.mark.parametrize('labels,reason',[
    ([], '独立来源 0 个'),
    (['Worker故障']*20,'至少需要两类'),
    (['Worker故障']*19+['硬件故障'],'每个已出现类别'),
    (['Worker故障']*5+['硬件故障']*5,'至少需要 20 个'),
])
def test_insufficient_corpus_exports_only_current_k4_not_old_classifier(tmp_path,monkeypatch,labels,reason):
    rt=module.runtime();monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    seed={'sources':[{'source_id':str(i),'identity':[],
          'vector':{'mined2:numeric_units:x':i+1}} for i in range(len(labels))],
          'cases':[{'id':str(i),'source_id':str(i),'label':label} for i,label in enumerate(labels)]}
    monkeypatch.setattr(rt,'asset',lambda *args:seed)
    result=module.train_bundle([],set(),'small')
    manifest=json.loads((result['directory']/'manifest.json').read_text())
    assert reason in manifest['classifier_disabled_reason']
    assert set(manifest['files'])=={'cosine_bank'}
    assert not (result['directory']/'numeric_classifier.json.gz').exists()
    with gzip.open(result['directory']/'cosine_bank.json.gz','rt') as stream:bank=json.load(stream)
    assert len(bank['sources'])==len(labels)


@pytest.mark.asyncio
async def test_deleting_all_managed_seed_sources_replaces_active_with_empty_k4(tmp_path,monkeypatch):
    rt=module.runtime();monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    seed=rt.asset('cosine_bank',rt.ASSETS)
    managed={i for s in seed['sources'] for i in s.get('identity',[])}
    result=module.train_bundle([],managed,'deleted')
    assert result['sample_count']==0 and result['training_reason']
    rt.model_registry.atomic_json(tmp_path/'active.json',{'version':result['version']})
    profile={'schema_version':'legacy-evidence-v1','status_codes':[],'failure_mode_ids':[],
        'latency_components':[],'operation':'GET','log_semantic_profile':{}}
    context=rt.unknown_context();context['families']['numeric_units']={'duration':1.}
    matching=rt.match(profile,context=context)
    assert matching['decision']['label'] is None
    assert matching['fallback_used'] and 'insufficient_training_data' in matching['decision']['fallback_reason']
    assert matching['candidates']==[]


@pytest.mark.asyncio
async def test_subprocess_cancellation_terminates_cpu_worker_and_cleans_output(tmp_path,monkeypatch):
    import sys
    monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    original=asyncio.create_subprocess_exec;started=asyncio.Event();children=[]
    async def slow_child(*args,**kwargs):
        child=await original(sys.executable,'-c','import time; time.sleep(60)',**kwargs)
        children.append(child);started.set();return child
    monkeypatch.setattr(asyncio,'create_subprocess_exec',slow_child)
    task=asyncio.create_task(module.build_in_process([],set(),'cancel'))
    await started.wait();task.cancel()
    with pytest.raises(asyncio.CancelledError):await task
    assert children[0].returncode is not None
    assert not list((tmp_path/'jobs').iterdir())


@pytest.mark.asyncio
async def test_real_subprocess_fits_portable_bundle_in_isolated_registry(tmp_path,monkeypatch):
    monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    result=await asyncio.wait_for(module.build_in_process([],set(),'process-test'),60)
    rt=module.runtime()
    manifest=rt.model_registry.read_json(result['directory']/'manifest.json')
    assert manifest['training_reports']>400 and manifest['dataset_fingerprint']=='process-test'
    assert 'numeric_classifier' in manifest['files']
    assert not (tmp_path/'active.json').exists()
    assert not list((tmp_path/'jobs').iterdir())


@pytest.mark.asyncio
async def test_missing_verification_is_skipped_before_reading_observation(tmp_path,monkeypatch):
    from latency.services.report_review import ReportReviewService
    monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    require=AsyncMock();monkeypatch.setattr(ReportReviewService,'require_confirmed',require)
    item=case();item['label_verified']=False
    samples,skipped=await Service.samples([item])
    assert samples==[] and len(skipped)==1 and '未完成检验' in skipped[0]['reason']
    require.assert_not_awaited()


@pytest.mark.asyncio
async def test_incomplete_multifault_report_cannot_be_used_as_global_training_row(tmp_path,monkeypatch):
    from latency.services.report_review import ReportReviewService
    monkeypatch.setenv('WITTY_CLASSIFIER_MODEL_DIR',str(tmp_path))
    payload={'faults':[{'id':'F01','conclusion':{'first_level_label':'Worker故障'}},
                       {'id':'F02','conclusion':{'first_level_label':'硬件故障'}}]}
    monkeypatch.setattr(ReportReviewService,'require_confirmed',AsyncMock(return_value=SimpleNamespace(payload=payload)))
    samples,skipped=await Service.samples([case()])
    assert samples==[] and len(skipped)==1 and '尚未全部确认' in skipped[0]['reason']


@pytest.mark.asyncio
async def test_insufficient_state_recovers_after_data_is_replenished(training_env,monkeypatch):
    env=training_env;env.cases.append(case())
    def small(*args):
        result=env.build(*args);result.update(training_reason='至少需要 20 个来源',class_counts={'Worker故障':1})
        return result
    monkeypatch.setattr(module,'train_bundle',small);await Service.reconcile()
    state=await Service.status();assert state['status']=='insufficient_data' and state['training_reason']
    await Service.reconcile();assert len(env.builds)==1
    env.cases.append(case('c2','硬件故障'))
    monkeypatch.setattr(module,'train_bundle',env.build);await Service.reconcile()
    assert (await Service.status())['status']=='ready'


@pytest.mark.asyncio
async def test_crash_after_publication_recovers_status_without_retraining(training_env):
    env=training_env;env.cases.append(case());await Service.reconcile()
    state=Service._read();state.update(status='training',trained_fingerprint=None);Service._write(state)
    await Service.reconcile()
    assert (await Service.status())['status']=='ready' and len(env.builds)==1
