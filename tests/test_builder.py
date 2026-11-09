"""Real resolver/parser and regression safety checks; no claims of Bitwarden GUI tests."""
from __future__ import annotations
import importlib.util, pathlib, tempfile, unittest
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1]

def module(path):
    spec=importlib.util.spec_from_file_location(path.stem, path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
resolve=module(ROOT/'scripts'/'resolve.py')
validate=module(ROOT/'scripts'/'validate.py')
stage=module(ROOT/'scripts'/'stage.py')

class StableDiscovery(unittest.TestCase):
    def test_numeric_semver_not_lexicographic(self):
        with mock.patch.object(resolve,'request',return_value=[
          {'tag_name':'desktop-v2026.10.4','prerelease':False,'draft':False},
          {'tag_name':'desktop-v2026.10.11','prerelease':False,'draft':False},
          {'tag_name':'desktop-v2026.11.0-beta.1','prerelease':True,'draft':False},
          {'tag_name':'browser-v2026.99.9','prerelease':False,'draft':False},
        ]):
            self.assertEqual(resolve.choose_release('latest')['tag_name'],'desktop-v2026.10.11')
    def test_reject_beta_explicit(self):
        for v in ['2026.11.0-beta.1','main','v2026.10.4','']:
            with self.subTest(v=v):
                with self.assertRaises(ValueError): resolve.choose_release(v)
    def test_non_success_does_not_fall_back(self):
        from urllib.error import HTTPError
        with mock.patch.object(resolve,'request',side_effect=RuntimeError('HTTP 403')):
            with self.assertRaisesRegex(RuntimeError,'403'):resolve.choose_release('latest')

class PackageContract(unittest.TestCase):
    def test_source_uses_pin_and_narrow_enumeration(self):
        code=(ROOT/'launcher'/'BitwardenPortable'/'Program.cs').read_text(encoding='utf-8')
        self.assertIn('BITWARDEN_APPDATA_DIR',code)
        self.assertIn('PORTABLE_EXECUTABLE_DIR',code)
        self.assertIn('SOFTWARE\\BraveSoftware',code)
        self.assertIn('Registry.CurrentUser',code)
        self.assertNotIn('Registry.LocalMachine',code)
        self.assertNotIn('Directory.Delete(',code)
        self.assertNotIn('Process.Kill(',code)
    def test_no_wrong_mode_native_zip(self):
        workflow=(ROOT/'.github'/'workflows'/'build-portableapps.yml').read_text(encoding='utf-8')
        self.assertIn('0112c35580e83b37eb8757ebcb949274e1631a04',workflow)
        self.assertIn('cb64f86ac2d8c67506db5832de07f9ff58cbeaeb',workflow)
        self.assertIn('dry-run:',workflow)
        self.assertIn('if: steps.preflight.outputs.exists',workflow)
        self.assertNotIn('engine: official',workflow)
    def test_pe_arch_rejects_non_pe(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'fake.exe';p.write_bytes(b'MZ'+b'\0'*64)
            self.assertIsNone(stage.pe_arch(p))
    def test_empty_directory_zip_preserved(self):
        with tempfile.TemporaryDirectory() as td:
            p=pathlib.Path(td)/'BitwardenPortable'
            for s in ['Data/Profile','Data/TraceGuard','Data/Temp','Other/Source']:
                (p/s).mkdir(parents=True)
            # This test exercises archive construction only, not actual Bitwarden functionality.
            file=p/'README.txt';file.write_text('archive-fixture',encoding='utf-8')
            for rel in ['BitwardenPortable.exe','App/Bitwarden/Bitwarden.exe','App/AppInfo/appinfo.ini','Other/Source/BUILD-IDENTITY.json']:
                t=p/rel;t.parent.mkdir(parents=True,exist_ok=True);t.write_bytes(b'fixture-only')
            z=validate.produce_zip(p,pathlib.Path(td)/'dist','1.2.3','0'*40)
            import zipfile
            with zipfile.ZipFile(z) as f:
                self.assertIn('BitwardenPortable/Data/Profile/',f.namelist())
                self.assertIn('BitwardenPortable/Data/TraceGuard/',f.namelist())

if __name__=='__main__':unittest.main()
