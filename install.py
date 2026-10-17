"""Register the local journal host for the user's unpacked Chrome extension."""
import argparse,json,os,re,sys,winreg
from pathlib import Path
def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--extension-id',required=True)
    ap.add_argument('--data-dir',type=Path,default=Path(os.environ['LOCALAPPDATA'])/'DionSpeakerHelper')
    ap.add_argument('--sessions',type=Path,default=Path.home()/'DionRecordings')
    args=ap.parse_args()
    if not re.fullmatch('[a-p]{32}',args.extension_id):ap.error('Invalid Chrome extension ID')
    runtime=Path(__file__).resolve().parent/'runtime';runtime.mkdir(exist_ok=True)
    import shutil
    shutil.copy2(Path(__file__).with_name('native_host.py'),runtime/'native_host.py')
    origin='chrome-extension://'+args.extension_id+'/'
    cfg={'active':str(Path(os.environ['LOCALAPPDATA'])/'DionSecretary'/'active.json'),
         'sessions':str(args.sessions.resolve()),'journals':str(args.data_dir.resolve()/'journals'),'origin':origin}
    (runtime/'host-config.json').write_text(json.dumps(cfg,indent=2),'utf-8')
    launcher=runtime/'host.cmd'
    launcher.write_text('@echo off\n"'+sys.executable+'" -X utf8 -B "'+str(runtime/'native_host.py')+'" %*\n','utf-8')
    host=runtime/'native-host.json'
    host.write_text(json.dumps({'name':'local.dion_speaker_helper','description':'DION local name journal',
       'path':str(launcher),'type':'stdio','allowed_origins':[origin]},indent=2),'utf-8')
    with winreg.CreateKey(winreg.HKEY_CURRENT_USER,r'Software\Google\Chrome\NativeMessagingHosts\local.dion_speaker_helper') as reg:
        winreg.SetValueEx(reg,'',0,winreg.REG_SZ,str(host))
    print('Registered. Reload the extension. Journal directory:',cfg['journals'])
if __name__=='__main__':main()
