import tempfile
import unittest
from pathlib import Path
from studio import read, write, sha, ROOT
from check_production_run import check, CHECKS


class RunEvidenceTests(unittest.TestCase):
    def test_pending_template_cannot_pass(self):
        self.assertEqual(check(Path(__file__).with_name('production-run.json'))['result'], 'incomplete')

    def test_assisted_and_missing_evidence_cannot_pass_independently(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);e=root/'evidence.txt';e.write_text('synthetic evidence only')
            r={'model':'synthetic-test','reasoning_effort':'max','source':{'path':e.name,'sha256':sha(e),'new_material':True},
               'usage':{'status':'unavailable','evidence':'unit test'},'paid_calls':0,'interventions':[],
               'checks':{k:{'status':'pass','evidence':e.name,'sha256':sha(e)} for k in CHECKS}}
            p=root/'run.json';write(p,r);self.assertEqual(check(p)['result'],'evidence_complete')
            r['interventions']=['another model fixed a scene'];write(p,r);self.assertEqual(check(p)['result'],'assisted_or_reused')
            e.write_text('changed');self.assertEqual(check(p)['result'],'incomplete')


if __name__=='__main__':unittest.main()
