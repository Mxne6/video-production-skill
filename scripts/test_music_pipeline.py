import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
import studio
import music_pipeline as music
from mix_background import RATE, encode_wav, decode, mix


class MusicPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        studio.init(self.tmp.name)
        self.p = studio.Project(self.tmp.name)
        t = np.arange(RATE * 2)/RATE
        self.voice = np.repeat((.12*np.sin(2*np.pi*400*t))[:, None], 2, axis=1)
        encode_wav(self.p.path/'voice.wav', self.voice)
        encode_wav(self.p.path/'music.wav', np.repeat((.1*np.sin(2*np.pi*700*t))[:, None], 2, axis=1))
        studio.write(self.p.path/'license.json', {k:'test only' for k in ('title','artist','source_url','license','attribution')})
        self.p.data['test_mode'] = True
        self.p.data['music'] = {'source':'music.wav','license':'license.json','gap_db':6,'offset_db':5}
        self.bundle = {'audio':'voice.wav','audio_hash':studio.sha(self.p.path/'voice.wav'),'duration':2}

    def test_cache_approval_and_invalidation(self):
        r = music.prepare(self.p, self.bundle)
        with patch.object(music, 'compose_audio', return_value=self.bundle):
            music.approve(self.p, SimpleNamespace(evidence='synthetic test, not human approval', review_hash=r['identity']))
        self.assertTrue(music.approved(self.p, r))
        with patch('mix_background.mix', side_effect=AssertionError('must reuse')):
            self.assertEqual(music.prepare(self.p, self.bundle)['identity'], r['identity'])
        self.p.data['scenes'][0]['caption_phrases']=['changed visual-only input']
        self.assertEqual(music.spec(self.p, self.bundle)['identity'], r['identity'])
        self.p.data['music']['offset_db']=4
        changed=music.prepare(self.p,self.bundle)
        self.assertFalse(music.approved(self.p, changed))
        self.p.file(changed['dir']+'/soundtrack.wav').write_bytes(b'damaged')
        with self.assertRaises(ValueError): music.prepare(self.p,self.bundle)

    def test_slider_matches_export_once(self):
        r=music.prepare(self.p,self.bundle)
        base=decode(self.p.file(r['dir']+'/base-bed.wav'))
        voice=decode(self.p.path/'voice.wav')
        for offset in (-18,0,5,8):
            desired=10**(offset/20)
            scale=min(1,(.98-r['voice_peak'])/max(r['base_peak']*desired,1e-9))
            live=voice+base*desired*scale
            source=decode(self.p.path/'music.wav',2,'highpass=f=110,lowpass=f=7000')
            expected,_,_=mix(voice,source,6,offset)
            np.testing.assert_allclose(live,expected,atol=1e-6)

    def test_invalid_config_and_short_source(self):
        self.p.data['music']['offset_db']=float('nan')
        with self.assertRaises(ValueError):music.spec(self.p,self.bundle)
        self.p.data['music']['offset_db']=0
        self.p.data['music']['source']='../escape.wav'
        with self.assertRaises(ValueError):music.spec(self.p,self.bundle)
        self.p.data['music']['enabled']=False
        self.assertIsNone(music.prepare(self.p,self.bundle))

    def test_candidate_selection_and_audition_do_not_change_selection(self):
        t=np.arange(RATE*2)/RATE
        encode_wav(self.p.path/'music-alt.wav',np.repeat((.1*np.sin(2*np.pi*900*t))[:,None],2,axis=1))
        self.p.data['music']['candidates']=[
            {'id':'calm','source':'music.wav','license':'license.json'},
            {'id':'bright','source':'music-alt.wav','license':'license.json'},
        ]
        self.p.data['music']['selected']='calm'
        self.assertEqual(music.music_candidates(self.p)['selected'],'calm')
        first=music.prepare(self.p,self.bundle)['identity']
        result=music.music_select(self.p,'bright','test selection')
        self.assertEqual(result['selected'],'bright')
        second=music.prepare(self.p,self.bundle)['identity']
        self.assertNotEqual(first,second)
        before=dict(self.p.data['music'])
        out='review/audition'
        rows=music.audition(self.p,self.bundle,out)
        self.assertEqual([row['id'] for row in rows['candidates']],['calm','bright'])
        self.assertEqual(self.p.data['music'],before)
        for row in rows['candidates']:
            self.assertTrue(self.p.file(row['file']).is_file())

    def test_short_music_can_loop_to_narration_length(self):
        import numpy as np
        short=np.repeat((.1*np.sin(2*np.pi*700*np.arange(RATE//4)/RATE))[:,None],2,axis=1)
        encode_wav(self.p.path/'short.wav',short)
        self.p.data['music']={'source':'short.wav','license':'license.json','gap_db':6,'offset_db':0,'loop':True}
        decoded=music.decode_music(self.p.path/'short.wav',2,True)
        self.assertGreaterEqual(len(decoded),RATE*2)
        record=music.prepare(self.p,self.bundle)
        self.assertTrue(record['loop'])

    def test_music_can_be_randomly_or_explicitly_selected(self):
        t=np.arange(RATE*2)/RATE
        encode_wav(self.p.path/'music-alt.wav',np.repeat((.1*np.sin(2*np.pi*900*t))[:,None],2,axis=1))
        self.p.data['music']['candidates']=[
            {'id':'one','source':'music.wav','license':'license.json'},
            {'id':'two','source':'music-alt.wav','license':'license.json'},
        ]
        explicit=music.music_select(self.p,'two','user chose two')
        self.assertEqual(explicit['method'],'explicit')
        chosen=set()
        for seed in range(20):
            result=music.music_select(self.p,None,'random test',seed=seed)
            self.assertEqual(result['method'],'random')
            self.assertEqual(result['seed'],seed)
            chosen.add(result['selected'])
        self.assertEqual(chosen,{'one','two'})


if __name__=='__main__':unittest.main()
