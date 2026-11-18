"""Label-blind contextual observations for supervised feature discovery.

Labels only select/weight these observations in offline training. This module
never accepts GT, report conclusions, source/scenario names or learned labels.
"""
from collections import Counter, defaultdict
import gzip
import hashlib
import itertools
import math
from pathlib import Path
import re

from enhanced_matching import _actor
import log_message_features

VERSION='contextual-log-observations-v1'
ANNOTATION=re.compile(rb'\b(?:scenario|test_case|case_name|fault_type|fault_injection|ground_truth|expected_label|root_cause)\s*[:=]',re.I)
COMPONENT=re.compile(rb'^([a-zA-Z][a-zA-Z0-9_]{0,80}\.(?:cpp|cc|c|h))(?::\d+)?$')
NUMBER=re.compile(rb'\b([a-zA-Z][a-zA-Z_]{0,40})\s*[:=]\s*(-?\d+(?:\.\d+)?)\b')
SAFE_NUMBER=re.compile(r'(?:us|ms|timeout|cost|duration|latency|size|length|bytes|count|wrs|ratio|percent|blocking|restart|retry|retries|batch|enable|valid|pending|total)',re.I)
IDENTITY_NUMBER=re.compile(r'(?:id$|_id$|address|addr|socket|fd$|port$|pid$|key|trace|timestamp)',re.I)
RETURN_CODE=re.compile(rb'\b(?:ret|return_code|status_code|error_code)\s*[:=]\s*(-?\d{1,6})\b',re.I)
STATUS=re.compile(rb'code:\s*\[([^\]]{1,80})\]')
STATUS_WORD=re.compile(r'^[A-Za-z][A-Za-z _-]{0,70}$')
OPERATION=re.compile(r'^DS_[A-Z_]{2,50}$')


def _normalized(values):
    norm=math.sqrt(math.fsum(math.log1p(v)**2 for v in values.values())) or 1.
    return {k:math.log1p(v)/norm for k,v in values.items()}


def scan(directory,expected_files=None):
    directory=Path(directory)
    files=sorted(p for p in directory.rglob('*') if p.is_file() and p.name.endswith(('.log','.log.gz')))
    expected={row['file']:row['sha256'] for row in expected_files or []}
    if expected and {str(p.relative_to(directory)) for p in files}!=set(expected):
        raise ValueError('Log file set changed')
    counts={key:Counter() for key in ('ew_context','all_context','templates','sequences','numeric')}
    numeric={};severity=defaultdict(Counter);markers=defaultdict(Counter)
    references=[];manifest=[];seen=set();rows=0;excluded=0
    def number(key,value):
        if not math.isfinite(value) or value<0:return
        if key not in numeric:numeric[key]=[0,0.,value,value]
        a=numeric[key];a[0]+=1;a[1]+=value;a[2]=min(a[2],value);a[3]=max(a[3],value)
    for path in files:
        role=_actor(path);previous={};digest=hashlib.sha256()
        with (gzip.open if path.name.endswith('.gz') else open)(path,'rb') as stream:
            for line,row in enumerate(stream,1):
                digest.update(row);parts=row.split(b'|',7)
                if len(parts)!=8 or parts[1].strip() not in (b'I',b'W',b'E'):continue
                level=parts[1].strip().decode();message=parts[7]
                if ANNOTATION.search(message) or re.search(rb'fault[_ ]?inject',message,re.I):
                    excluded+=1;continue
                for field in (parts[3].strip(),parts[5].strip(),parts[6].strip()):
                    if len(field)>=4 and not field.isdigit():message=message.replace(field,b' ')
                location=COMPONENT.fullmatch(parts[2].strip())
                component=location[1].decode() if location else 'unknown'
                if re.search(r'(?:fault_inject|mock|test_case)',component,re.I):continue
                identity=hashlib.sha256(row.rstrip(b'\r\n')).hexdigest()
                if identity in seen:continue
                seen.add(identity);rows+=1
                context=role+'|'+component+'|'+level
                words=log_message_features.tokens(message)
                # Tokens have identities, paths and absolute numbers removed by the shared sanitizer.
                if not words:continue
                counts['all_context'].update('ctxword:'+context+'|'+w for w in set(words))
                counts['all_context'].update('ctxphrase:'+context+'|'+a+'_'+b for a,b in set(zip(words,words[1:])))
                if level in ('E','W'):
                    counts['ew_context'].update('ctxword:'+context+'|'+w for w in set(words))
                    counts['ew_context'].update('ctxphrase:'+context+'|'+a+'_'+b for a,b in set(zip(words,words[1:])))
                signature=' '.join(words[:20]+(['...']+words[-8:] if len(words)>28 else words[20:]))
                template=context+'|'+signature
                counts['templates']['template:'+template]+=1
                severity[role+'|'+component][level]+=1
                marker=role+'|'+component+'|'+'_'.join(words[:5])
                markers[role][marker]+=1
                # Process/trace identity may group events locally but is never part of a feature key.
                process=parts[4].strip().split(b':',1)[0]
                before=previous.get(process)
                if before and before!=marker:counts['sequences']['transition:'+before+' => '+marker]+=1
                previous[process]=marker
                for code in RETURN_CODE.findall(message):
                    counts['numeric']['return:'+role+'|'+component+'|'+str(int(code))]+=1
                match=STATUS.search(message)
                if match:
                    status=match[1].decode('ascii','ignore').strip()
                    if STATUS_WORD.fullmatch(status):counts['numeric']['status:'+role+'|'+component+'|'+status.upper()]+=1
                measured={}
                for key,value in NUMBER.findall(message):
                    key=key.decode()
                    if IDENTITY_NUMBER.search(key) or not SAFE_NUMBER.search(key):continue
                    value=float(value)
                    if math.isfinite(value) and value>=0:
                        number('number:'+role+'|'+component+'|'+key,value);measured[key.lower()]=value
                total=measured.get('totalus')
                if total and total>0:
                    for key,value in measured.items():
                        if key.endswith('us') and key!='totalus' and 0<=value<=total:
                            number('ratio:'+role+'|'+component+'|'+key+'_over_total',value/total)
                # Access records carry observed status/operation/elapsed/size, not trace identifiers.
                fields=message.split(b'|')
                if len(fields)>=4:
                    operation=fields[1].strip().decode('ascii','ignore')
                    if OPERATION.fullmatch(operation):
                        try:
                            status=int(fields[0]);elapsed=float(fields[2]);size=float(fields[3])
                            counts['numeric'][f'access:{role}|{operation}|code:{status}']+=1
                            number(f'access_latency:{role}|{operation}|code:{status}',elapsed)
                            number(f'access_size:{role}|{operation}|code:{status}',size)
                        except ValueError:pass
                if len(references)<80 and counts['templates']['template:'+template]==1:
                    references.append({'template':template,'file':str(path.relative_to(directory)),
                                       'line':line,'row_sha256':identity})
        relative=str(path.relative_to(directory));checksum=digest.hexdigest()
        if expected and checksum!=expected[relative]:raise ValueError('Log content changed: '+relative)
        manifest.append({'file':relative,'sha256':checksum})
    for role,observed in markers.items():
        top=sorted(observed,key=lambda key:(-observed[key],key))[:12]
        for a,b in itertools.combinations(sorted(top),2):counts['sequences']['cooccur:'+a+' & '+b]=1
    result={family:_normalized(dict(sorted(values.items(),key=lambda kv:(-kv[1],kv[0]))[:4096]))
            for family,values in counts.items()}
    for key,(count,total,minimum,maximum) in numeric.items():
        result['numeric'][key+'|mean']=math.log1p(total/count)
        result['numeric'][key+'|min']=math.log1p(minimum)
        result['numeric'][key+'|max']=math.log1p(maximum)
        for stat,value in (('mean',total/count),('max',maximum)):
            bucket=min(10,int(value*10)) if key.startswith('ratio:') else min(30,int(math.log1p(value)))
            result['numeric'][f'bin:{key}|{stat}|{bucket}']=1.
    for context,levels in severity.items():
        total=sum(levels.values())
        for level in ('I','W','E'):result['numeric']['severity_fraction:'+context+'|'+level]=levels[level]/total
    return {'schema_version':VERSION,'families':result,'provenance':{'source':'log_message_columns',
        'rows':rows,'excluded_test_annotations':excluded,'files':manifest,'references':references}}


VIEWS=('v5','ew_context','all_context','templates','numeric','sequences','contextual','v5_contextual')


def vector(view,base,context):
    if view not in VIEWS:raise ValueError('Unknown mining representation')
    values=dict(base) if view in ('v5','v5_contextual') else {}
    families=('all_context','templates','numeric','sequences') if view in ('contextual','v5_contextual') else (view,)
    if view=='v5':return values
    for family in families:
        values.update({'mined:'+family+':'+key:value for key,value in context['families'][family].items()})
    return values
