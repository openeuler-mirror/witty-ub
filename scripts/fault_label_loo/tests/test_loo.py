import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import eval_loo
import fixed_matching
import loo_support
import summarize_loo
import validate_loo
from test_fixed_policy import inputs


def dataset():
    profile,structured,raw,_=inputs()
    prepared={'reports':[],'cases':[]};observations={'reports':{}}
    for index in range(6):
        qid=f'source-{index}'
        identity=['shared-log'] if index<2 else [qid]
        label='Worker故障' if index%2 else '硬件故障'
        prepared['reports'].append({'source_id':qid,'identity':identity,'group':'train','scene':qid,
            'profile':copy.deepcopy(profile),'structured':copy.deepcopy(structured),'truth':[label]})
        prepared['cases'].append({'id':qid+'#fault-0','source_id':qid,'identity':identity,'label':label,
            'profile':copy.deepcopy(profile),'structured':copy.deepcopy(structured)})
        observations['reports'][qid]=copy.deepcopy(raw)
    return prepared,observations


class LooTests(unittest.TestCase):
    def test_full_loo_shares_agent_rules_and_excludes_aliases(self):
        prepared,raw=dataset()
        with tempfile.TemporaryDirectory() as tmp,contextlib.redirect_stdout(io.StringIO()):
            root=Path(tmp)
            (root/'prepared.json').write_text(json.dumps(prepared))
            (root/'raw.json').write_text(json.dumps(raw))
            run=root/'run'
            summary=eval_loo.evaluate(prepared,raw,run,
                {'prepared.json':root/'prepared.json','raw_observations.json':root/'raw.json'})
            self.assertFalse(summary['partial'])
            self.assertEqual(summary['classifier'],'none')
            records=loo_support.read(run/'predictions.json')
            self.assertEqual(records[0]['excluded_source_ids'],['source-0','source-1'])
            query=prepared['reports'][0]
            cases=[c for c in prepared['cases'] if c['source_id'] not in records[0]['excluded_source_ids']]
            expected=fixed_matching.match(query['profile'],cases,query['structured'],raw['reports'][query['source_id']])
            self.assertEqual(records[0]['decision'],expected['decision'])
            self.assertEqual(validate_loo.validate(run)['replayed_decisions'],6)
            exported=summarize_loo.summarize(run,root)
            self.assertEqual(exported['classifier'],'none')
            self.assertTrue((root/'report.html').is_file())
            records[0]['candidate_source_ids'].append('source-0')
            (run/'predictions.json').write_text(json.dumps(records))
            with self.assertRaises(AssertionError):
                validate_loo.validate(run)

    def test_query_answer_is_rejected_and_vote_is_fixed(self):
        profile,structured,raw,_=inputs()
        with self.assertRaises(ValueError):
            fixed_matching.match({**profile,'truth':'OS故障'},[],structured,raw)
        rows=[{'case_id':str(i),'first_level_label':label,'score_norm':score}
              for i,(label,score) in enumerate([('OS故障',.60),('Worker故障',.59),
                                                ('Worker故障',.58),('Worker故障',.57)])]
        decision=fixed_matching.decide(profile,structured,raw,rows)
        self.assertEqual(decision['label'],'Worker故障')
        self.assertEqual(decision['vote_method'],'topK_vote')


if __name__=='__main__':
    unittest.main()
