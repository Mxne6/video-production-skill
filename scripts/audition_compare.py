"""Generate one approved-scene voice audition, preserving production references."""
import argparse, copy, json
from types import SimpleNamespace
import studio

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('project'); parser.add_argument('--scene',required=True)
    parser.add_argument('--voice-id',required=True); parser.add_argument('--label',required=True)
    parser.add_argument('--prompt-key',action='store_true')
    parser.add_argument('--natural-pauses',action='store_true',help='Omit explicit pause tags for this audition only')
    args=parser.parse_args(); p=studio.Project(args.project)
    s=p.scenes(args.scene)[0]
    studio.need(p.state['scripts'].get(s['id'],{}).get('hash')==p.script_hash(s),'Approve script before audition')
    previous=copy.deepcopy(p.state['attempts'])
    s['voice']={**s.get('voice',{}),'voice_id':args.voice_id}
    if args.natural_pauses: s['pauses']=[]
    before=set((p.path/'.history').glob('tts-*'))
    error=None
    try:
        studio.tts(p,SimpleNamespace(scenes=args.scene,send=True,mode='audition',unit='ms',prompt_key=args.prompt_key))
    except Exception as exc:
        error=type(exc).__name__+': '+str(exc)
    finally:
        folders=set((p.path/'.history').glob('tts-*'))-before
        p.state['attempts']=previous
        p.save('audition_comparison_saved',scene=args.scene,voice_id=args.voice_id)
    studio.need(len(folders)==1, 'No unique saved request; inspect history before retry')
    folder=folders.pop(); audio=folder/'audio.mp3'
    report={'label':args.label,'voice_id':args.voice_id,'scene':args.scene,
            'natural_pauses':args.natural_pauses,
            'attempt':folder.relative_to(p.path).as_posix(),'mode':'audition',
            'audio_available':audio.exists(),'processing_error':error,
            'listening_approved':False,'production_references_unchanged':True}
    if audio.exists(): report['audio_sha256']=studio.sha(audio)
    studio.write(folder/'audition.json',report)
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
