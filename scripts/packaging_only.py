#!/usr/bin/env python3
"""Extract a previously verified Bitwarden builder ZIP without upstream recompilation."""
import argparse,hashlib,json,pathlib,re,stat,zipfile
from validate import validate

def main(zip_path:pathlib.Path,sha256:str,destination:pathlib.Path):
    if not re.fullmatch('[0-9a-fA-F]{64}',sha256): raise RuntimeError('Provide exact source ZIP SHA-256 from original release')
    with zip_path.open('rb') as f:
        actual=hashlib.file_digest(f,'sha256').hexdigest()
    if actual!=sha256.lower(): raise RuntimeError('Previous release ZIP checksum differs, aborting packaging-only')
    with zipfile.ZipFile(zip_path) as z:
        for entry in z.infolist():
            p=pathlib.PurePosixPath(entry.filename)
            if p.is_absolute() or '..' in p.parts or not p.parts or p.parts[0]!='BitwardenPortable':
                raise RuntimeError('Untrusted ZIP member: '+entry.filename)
            # Refuse symlinks / other unsafe Unix permissions in imported archive.
            mode=(entry.external_attr>>16)&0xffff
            if stat.S_IFMT(mode)==stat.S_IFLNK: raise RuntimeError('Symlink in release ZIP: '+entry.filename)
        z.extractall(destination)
    root=destination/'BitwardenPortable'
    info=root/'Other'/'Source'/'BUILD-IDENTITY.json'
    validate(root,info)
    print('PACKAGING-ONLY SOURCE VALIDATED:',actual,'source release:',json.loads(info.read_text(encoding='utf-8'))['upstream_release_tag'])

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--zip',required=True);p.add_argument('--sha256',required=True);p.add_argument('--destination',required=True)
    a=p.parse_args();main(pathlib.Path(a.zip),a.sha256,pathlib.Path(a.destination))
