"""Unit-aware and status/phase-conditioned observations; no labels at extraction."""
from collections import Counter,defaultdict
from datetime import datetime
import gzip
import hashlib
import math
from pathlib import Path
import re

from enhanced_matching import _actor
import mined_log_features as v1

VERSION='contextual-log-observations-v2'
NUMBER=re.compile(rb'\b([A-Za-z][A-Za-z_]{0,40})\s*[:=]\s*(-?\d+(?:\.\d+)?)\s*(ns|us|ms|s|KiB|MiB|GiB|KB|MB|GB|bytes)?(?=[\s,;|}\]]|$)',re.I)
PHASE=re.compile(rb'\[([A-Z][A-Z_]{2,60}(?:PHASE|TOTAL|SUMMARY))\]')
BOOLEAN=re.compile(rb'\b([A-Za-z][A-Za-z_]{0,40})\s*[:=]\s*(true|false)\b',re.I)
VIEWS=('v5','v1_numeric','numeric_units','conditioned','contrasts','temporal','numeric_context',
       'v5_numeric_context','v1_contextual','all_context_v2')


def parameters(message):
    result={}
    for key,value,unit in NUMBER.findall(message):
        key=key.decode();unit=unit.decode().lower()
        if v1.IDENTITY_NUMBER.search(key):continue
        if not unit and not v1.SAFE_NUMBER.search(key) and not re.search(r'query|publish|create|get_|set_|wait|prepare|process',key,re.I):continue
        value=float(value)
        if not math.isfinite(value) or value<0:continue
        if not unit:
            if key.lower().endswith('us'):unit='us'
            elif key.lower().endswith('ms'):unit='ms'
        if unit in ('ns','us','ms','s'):
            value*=dict(ns=.001,us=1.,ms=1000.,s=1000000.)[unit];unit='us'
        elif unit:
            value*=dict(kib=1024,mib=1048576,gib=1073741824,kb=1000,mb=1000000,gb=1000000000,bytes=1).get(unit,1);unit='bytes'
        result[key.lower()+'|'+(unit or 'value')]=value
    for key,value in BOOLEAN.findall(message):
        key=key.decode()
        if not v1.IDENTITY_NUMBER.search(key) and v1.SAFE_NUMBER.search(key):result[key.lower()+'|bool']=float(value.lower()==b'true')
    return result


def upgrade(context,directory,expected_files=None):
    directory=Path(directory);expected={f['file']:f['sha256'] for f in expected_files or []}
    stats={};conditioned={};status_stats={};events=Counter();first_error=None
    def accumulate(store,key,value):
        if key not in store:store[key]=[0,0.,value,value,Counter()]
        row=store[key];row[0]+=1;row[1]+=value;row[2]=min(row[2],value);row[3]=max(row[3],value)
        row[4][min(40,int(math.log2(1+value)))]+=1
    for source in context['provenance']['files']:
        path=directory/source['file'];digest=hashlib.sha256();role=_actor(path)
        with (gzip.open if path.name.endswith('.gz') else open)(path,'rb') as stream:
            for row in stream:
                digest.update(row);parts=row.split(b'|',7)
                if len(parts)!=8 or parts[1].strip() not in (b'I',b'W',b'E'):continue
                level=parts[1].strip().decode();message=parts[7]
                if v1.ANNOTATION.search(message) or re.search(rb'fault[_ ]?inject',message,re.I):continue
                match=v1.COMPONENT.fullmatch(parts[2].strip());component=match[1].decode() if match else 'unknown'
                if re.search(r'(?:fault_inject|mock|test_case)',component,re.I):continue
                phase_match=PHASE.search(message);phase=phase_match[1].decode() if phase_match else 'general'
                status='unknown';match=v1.STATUS.search(message)
                if match:
                    word=match[1].decode('ascii','ignore').strip()
                    if v1.STATUS_WORD.fullmatch(word):status=word.upper().replace(' ','_')
                ret=v1.RETURN_CODE.search(message)
                if ret:status='code_'+str(int(ret[1]))
                status_class='ok' if status in ('OK','code_0') else 'error' if status!='unknown' else 'unknown'
                values=parameters(message)
                fields=message.split(b'|')
                if len(fields)>=4:
                    operation=fields[1].strip().decode('ascii','ignore')
                    if v1.OPERATION.fullmatch(operation):
                        try:
                            status='code_'+str(int(fields[0]));status_class='ok' if int(fields[0])==0 else 'error';phase=operation
                            values['access_elapsed|us']=max(0.,float(fields[2]));values['access_size|bytes']=max(0.,float(fields[3]))
                        except ValueError:pass
                tag=role+'|'+component+'|'+phase
                for key,value in values.items():
                    accumulate(stats,tag+'|'+key,value)
                    accumulate(conditioned,tag+'|'+status+'|'+key,value)
                    accumulate(status_stats,tag+'|'+key+'|'+status_class,value)
                total=values.get('totalus|us')
                if total and total>0:
                    for key,value in values.items():
                        if key.endswith('|us') and not key.startswith('totalus|') and value<=total:
                            accumulate(conditioned,tag+'|'+status+'|ratio:'+key,value/total)
                try:timestamp=datetime.fromisoformat(parts[0].strip().decode()).timestamp()
                except ValueError:continue
                if level in ('E','W'):first_error=min(first_error if first_error is not None else int(timestamp),int(timestamp))
                if values or level in ('E','W'):
                    events[(int(timestamp),tag+'|'+status+'|'+level)]+=1
        if expected and digest.hexdigest()!=expected[source['file']]:raise ValueError('Log changed: '+source['file'])
    def flatten(store):
        output={}
        for key,(n,total,minimum,maximum,hist) in store.items():
            output[key+'|mean']=math.log1p(total/n);output[key+'|max']=math.log1p(maximum)
            output[key+'|min']=math.log1p(minimum);output[key+'|sample_count']=math.log1p(n)
            for bucket,count in hist.items():output[key+f'|hist:{bucket}']=count/n
            for q in (.5,.9):
                cumulative=0
                for bucket in sorted(hist):
                    cumulative+=hist[bucket]
                    if cumulative>=q*n:output[key+f'|approx_quantile:{q}']=bucket;break
        return output
    contrasts={}
    for key in status_stats:
        if not key.endswith('|ok'):continue
        common=key[:-3];failed=status_stats.get(common+'|error')
        if failed:
            normal=status_stats[key];ratio=(failed[1]/failed[0]+1)/(normal[1]/normal[0]+1)
            contrasts[common+'|error_over_ok']=math.log1p(ratio)
            contrasts[common+'|error_fraction']=failed[0]/(normal[0]+failed[0])
    temporal=Counter()
    if first_error is not None:
        for (timestamp,tag),count in events.items():
            dt=timestamp-first_error
            bucket=sum(dt>=bound for bound in (-60,-10,-1,0,1,10,60))
            temporal[tag+f'|relative_window:{bucket}']+=count
    families={**context['families'],'numeric_units':flatten(stats),'conditioned':flatten(conditioned),
              'contrasts':contrasts,'temporal':v1._normalized(temporal)}
    return {'schema_version':VERSION,'families':families,'provenance':context['provenance']}


def scan(directory,expected_files=None):return upgrade(v1.scan(directory,expected_files),directory,expected_files)


def vector(view,base,context):
    if view not in VIEWS:raise ValueError('Unknown v2 representation')
    if view=='v5':return dict(base)
    if view=='v1_numeric':return {'mined:numeric:'+k:v for k,v in context['families']['numeric'].items()}
    if view=='v1_contextual':return v1.vector('v5_contextual',base,context)
    out=dict(base) if view in ('v5_numeric_context','all_context_v2') else {}
    groups=('numeric_units','conditioned','contrasts','temporal') if view in ('numeric_context','v5_numeric_context','all_context_v2') else (view,)
    if view=='all_context_v2':groups+=('all_context','templates','sequences')
    for group in groups:out.update({'mined2:'+group+':'+k:v for k,v in context['families'][group].items()})
    return out
