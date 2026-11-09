#!/usr/bin/env python3
"""Check the shared builder's real output file, checksum, and NSIS archive contents."""
import argparse,hashlib,pathlib,re,struct,subprocess
from stage import find_7z

def validate(path:pathlib.Path,digest:str,rootname='BitwardenPortable'):
    if not path.exists() or not path.name.lower().endswith('.paf.exe'): raise RuntimeError('Missing shared installer .paf.exe output')
    if not re.fullmatch('[0-9a-fA-F]{64}',digest): raise RuntimeError('Bad action-provided installer digest')
    with path.open('rb') as f:
        if f.read(2)!=b'MZ': raise RuntimeError('Installer not a Windows executable')
        f.seek(0x3c);offset=struct.unpack('<I',f.read(4))[0];f.seek(offset)
        if f.read(4)!=b'PE\x00\x00': raise RuntimeError('Installer lacks PE signature')
    with path.open('rb') as handle:
        actual=hashlib.file_digest(handle,'sha256').hexdigest()
    if actual.lower()!=digest.lower(): raise RuntimeError('Shared builder SHA256 output does not match installer')
    result=subprocess.run([find_7z(),'l',str(path)],capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=180)
    if result.returncode!=0: raise RuntimeError('Cannot independently list NSIS embedded archive: '+result.stdout[-1000:])
    output=result.stdout.lower()
    if rootname.lower() not in path.name.lower() or 'bitwarden.exe' not in output or 'appinfo.ini' not in output:
        raise RuntimeError('NSIS does not list expected embedded Bitwarden binary and metadata')
    print('STATIC-VALIDATED installer provenance via shared action; PE, SHA256, 7-Zip listing:',actual)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--sha256',required=True)
    a=p.parse_args();validate(pathlib.Path(a.file),a.sha256)
