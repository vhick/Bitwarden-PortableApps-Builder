"""Real resolver/parser and regression safety checks; no claims of Bitwarden GUI tests."""
from __future__ import annotations
import importlib.util, pathlib, tempfile, unittest, sys
from unittest import mock
ROOT=pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))

def module(path):
    spec=importlib.util.spec_from_file_location(path.stem, path)
    mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod);return mod
resolve=module(ROOT/'scripts'/'resolve.py')
validate=module(ROOT/'scripts'/'validate.py')
stage=module(ROOT/'scripts'/'stage.py')
oss=module(ROOT/'scripts'/'oss_contract.py')

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
        self.assertIn('OSS',workflow)
        self.assertIn('cb64f86ac2d8c67506db5832de07f9ff58cbeaeb',workflow)
        self.assertIn('dry-run:',workflow)
        self.assertIn('if: steps.preflight.outputs.exists',workflow)
        self.assertNotIn('engine: official',workflow)
    def test_shared_package_builder_running_exe_windows_relative_path(self):
        """Regression: v1.0.0 shared action rejects forward-slash running-exe paths."""
        import re
        action_pattern = re.compile(r"^(?!.*(?:^|[\\/])\.\.(?:[\\/]|$))[A-Za-z0-9_.+ -]+(?:\\[A-Za-z0-9_.+ -]+)*\.exe$")
        for file in ['build-portableapps.yml', 'installer-from-validated-zip.yml']:
            with self.subTest(workflow=file):
                workflow=(ROOT/'.github'/'workflows'/file).read_text(encoding='utf-8')
                match=re.search(r"(?m)^\s*running-exe:\s*(.+?)\s*$", workflow)
                self.assertIsNotNone(match, 'The shared action must receive a running-exe input')
                value=match.group(1).strip().strip("'\"")
                self.assertEqual(value, r'App\Bitwarden\Bitwarden.exe')
                self.assertIsNotNone(action_pattern.fullmatch(value), 'Shared v1.0.0 requires backslash separators')
                self.assertNotIn('running-exe: App/Bitwarden/Bitwarden.exe', workflow)

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


class OSSOnlyContract(unittest.TestCase):
    def identity(self,version):
        filename=oss.oss_filename(version)
        tag='desktop-v'+version
        return {'version':version,'asset_filename':filename,'upstream_release_tag':tag,
                'asset_url':f'https://github.com/bitwarden/clients/releases/download/{tag}/{filename}',
                'asset_sha256':'a'*64,
                'distribution_flavor':('upstream-oss-gplv3' if oss.parse_version(version)>=(2026,11,0)
                                       else 'upstream-noncommercial-OSS-asset')}

    def test_october_2026_legacy_oss(self):
        self.assertEqual(oss.oss_filename('2026.10.4'),'Bitwarden-Portable-2026.10.4.exe')
        oss.assert_oss_identity(self.identity('2026.10.4'))

    def test_november_2026_oss_prefix(self):
        self.assertEqual(oss.oss_filename('2026.11.0'),'oss-Bitwarden-Portable-2026.11.0.exe')
        oss.assert_oss_identity(self.identity('2026.11.0'))

    def test_numeric_cutoff_and_future_oss(self):
        self.assertEqual(oss.oss_filename('2026.10.99'),'Bitwarden-Portable-2026.10.99.exe')
        self.assertEqual(oss.oss_filename('2027.1.0'),'oss-Bitwarden-Portable-2027.1.0.exe')

    def test_commercial_variants_never_allowed(self):
        for version in ['2026.10.4','2026.11.0']:
            for prefix in ['commercial-','bit-']:
                with self.subTest(version=version,prefix=prefix):
                    j=self.identity(version)
                    j['asset_filename']=prefix+'Bitwarden-Portable-'+version+'.exe'
                    j['asset_url']=j['asset_url'].rsplit('/',1)[0]+'/'+j['asset_filename']
                    with self.assertRaisesRegex(RuntimeError,'OSS-only'):oss.assert_oss_identity(j)

    def test_unknown_legacy_and_missing_sha_denied(self):
        with self.assertRaisesRegex(ValueError,'older than'):oss.oss_filename('2026.8.0')
        j=self.identity('2026.11.0');j['asset_sha256']=''
        with self.assertRaisesRegex(RuntimeError,'SHA-256'):oss.assert_oss_identity(j)

    def test_non_official_url_and_wrong_flavor_denied(self):
        j=self.identity('2026.11.0')
        j['asset_url']='https://bitwarden.com/download';
        with self.assertRaisesRegex(RuntimeError,'URL'):oss.assert_oss_identity(j)
        j=self.identity('2026.11.0');j['distribution_flavor']='commercial'
        with self.assertRaisesRegex(RuntimeError,'flavor'):oss.assert_oss_identity(j)

    def test_source_resolver_enforces_contract(self):
        source=(ROOT/'scripts'/'resolve.py').read_text(encoding='utf-8')
        self.assertIn('exact=oss_filename(ver)',source)
        self.assertIn('assert_oss_identity(info)',source)
        self.assertIn('No commercial fallback',source)

    def test_reused_zip_must_pass_oss_guard(self):
        code=(ROOT/'scripts'/'packaging_only.py').read_text(encoding='utf-8')
        self.assertIn('assert_oss_identity(',code)

    def test_integrated_resolution_2026_11_oss_asset(self):
        import json
        ver='2026.11.0'
        filename=oss.oss_filename(ver)
        release={'tag_name':'desktop-v'+ver, 'id':98765, 'published_at':'2026-11-19T20:49:00Z',
                 'assets':[{'name':'bit-Bitwarden-Portable-'+ver+'.exe', 'digest':'sha256:'+'1'*64,
                            'browser_download_url':'https://github.com/bitwarden/clients/releases/download/desktop-v'+ver+'/bit-Bitwarden-Portable-'+ver+'.exe'},
                           {'name':filename,'digest':'sha256:'+'2'*64,'size':1234,
                            'browser_download_url':'https://github.com/bitwarden/clients/releases/download/desktop-v'+ver+'/'+filename}]}
        def request_fixture(url,binary=False):
            if '/commits/' in url: return {'sha':'3'*40}
            if binary: return b'locked-dependencies'
            raise RuntimeError('Unexpected request '+url)
        with tempfile.TemporaryDirectory() as d, mock.patch.object(resolve,'choose_release',return_value=release), mock.patch.object(resolve,'request',side_effect=request_fixture):
            output=pathlib.Path(d)/'identity.json'
            resolve.resolve('latest',output)
            j=json.loads(output.read_text())
            self.assertEqual(j['asset_filename'],filename)
            self.assertEqual(j['asset_sha256'],'2'*64)
            self.assertEqual(j['distribution_flavor'],'upstream-oss-gplv3')

    def test_integrated_resolver_refuses_commercial_only(self):
        ver='2026.11.0'
        release={'tag_name':'desktop-v'+ver,'assets':[{'name':'bit-Bitwarden-Portable-'+ver+'.exe'}]}
        with tempfile.TemporaryDirectory() as d, mock.patch.object(resolve,'choose_release',return_value=release):
            with self.assertRaisesRegex(RuntimeError,'No commercial fallback'):
                resolve.resolve('latest',pathlib.Path(d)/'identity.json')

    def test_existing_data_identity_preserved(self):
        stage_src=(ROOT/'scripts'/'stage.py').read_text(encoding='utf-8')
        self.assertIn('AppID=BitwardenDesktopCommunityPortable',stage_src)
        self.assertIn('Data/Profile',stage_src)
        self.assertIn('BitwardenPortable.exe',stage_src)

if __name__=='__main__':unittest.main()
