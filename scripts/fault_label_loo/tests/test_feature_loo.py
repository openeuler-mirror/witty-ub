from collections import Counter
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import eval_feature_loo as loo
import loo_support as io
import validate_feature_loo as validation


class FoldLocalTests(unittest.TestCase):
    def test_query_only_vocabulary_and_largest_value_are_excluded(self):
        try:
            from sklearn.feature_extraction import DictVectorizer
        except ImportError:
            self.skipTest('offline LOO dependencies are not installed')
        queries=[{'source_id':str(i),'identity':[str(i)],'truth':['硬件故障' if i%2 else 'Worker故障'],
                  'group':'train'} for i in range(6)]
        cases=[{'id':q['source_id']+'#fault-0','source_id':q['source_id'],'identity':q['identity'],'label':q['truth'][0]} for q in queries]
        features=[{'shared':1000.,'query_only':500.}]+[{'shared':float(i),'train_only':1.} for i in range(1,6)]
        folds=[{'fold':0,'query_id':'0','train_indices':[1,2,3,4,5],'excluded_source_ids':['0']}]
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            loo.init_state({'reports':queries,'cases':cases},[],[],folds,root)
            loo.STATE.update(view='v5',features=features)
            record,audit=loo.one_fold(0)
            model=loo.read_gzip(root/audit['model_path'])
            self.assertNotIn('query_only',model['feature_names'])
            self.assertEqual(model['metadata']['training_source_ids'],['1','2','3','4','5'])
            self.assertEqual(audit['scaling_sha256'],io.digest([5.,1.]))
            # Replay with independently built expected maxima and the validator's K4 implementation.
            dictionary=DictVectorizer();matrix=dictionary.fit_transform(features)
            validation.STATE.clear();validation.STATE.update(out=root,queries=queries,cases=cases,folds=folds,
                groups=[str(i) for i in range(6)],refit_indices={0},view='v5',features=features,
                matrix=matrix,names=dictionary.get_feature_names_out().tolist(),column=dictionary.vocabulary_,
                df=Counter(k for row in features for k in row),
                maxima={'query_only':[(500.,'0')],'shared':[(1000.,'0'),(5.,'5')],
                        'train_only':[(1.,'1'),(1.,'2')]},records=[record],audits=[audit])
            self.assertEqual(validation.one(0),0.)


if __name__=='__main__':unittest.main()
