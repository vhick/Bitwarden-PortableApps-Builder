#!/usr/bin/env python3
"""Download exactly the official GitHub release asset and verify SHA-256."""
import argparse, hashlib, json, pathlib, urllib.request

def download(identity:pathlib.Path,outdir:pathlib.Path):
    info=json.loads(identity.read_text(encoding='utf-8'))
    filename=info['asset_filename']
    expected=f'https://github.com/bitwarden/clients/releases/download/{info["upstream_release_tag"]}/{filename}'
    if info['asset_url']!=expected: raise ValueError('Untrusted asset URL')
    if len(info['asset_sha256'])!=64: raise ValueError('Missing SHA256')
    outdir.mkdir(parents=True,exist_ok=True)
    dest=outdir/filename
    if dest.is_file() and hashlib.sha256(dest.read_bytes()).hexdigest()==info['asset_sha256']:
        print('Official download already verified:',dest);return dest
    tmp=dest.with_suffix('.partial'); sha=hashlib.sha256(); size=0
    req=urllib.request.Request(info['asset_url'],headers={'User-Agent':'Bitwarden-PortableApps-Builder-b1r1','Accept':'application/octet-stream'})
    try:
        with urllib.request.urlopen(req,timeout=150) as response, tmp.open('wb') as f:
            for chunk in iter(lambda:response.read(4*1024*1024),b''):
                sha.update(chunk);f.write(chunk);size+=len(chunk)
        if sha.hexdigest()!=info['asset_sha256']: raise RuntimeError('SHA256 mismatch: rejecting download')
        if info.get('asset_size') and info['asset_size']!=size: raise RuntimeError('Size mismatch: rejecting download')
        if tmp.open('rb').read(2)!=b'MZ': raise RuntimeError('Official asset not an EXE')
        tmp.replace(dest)
    finally:
        if tmp.exists(): tmp.unlink()
    print('Verified official asset',dest,'bytes=',size,'sha256=',sha.hexdigest())
    return dest

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--identity',required=True);p.add_argument('--outdir',required=True)
    a=p.parse_args();download(pathlib.Path(a.identity),pathlib.Path(a.outdir))
