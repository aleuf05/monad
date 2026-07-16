import importlib.util,tempfile,unittest
from pathlib import Path
P=Path(__file__).with_name('serve.py'); S=importlib.util.spec_from_file_location('ls',P); s=importlib.util.module_from_spec(S); S.loader.exec_module(s)
class T(unittest.TestCase):
 def test_rejects_extra_fields_without_spawning(self):
  with self.assertRaisesRegex(ValueError,'unsupported'): s.generate({'shape':'sphere','name':'safe','scheme':'evil'})
 def test_status_reports_manifest_models(self):
  old_manifest=s.MANIFEST; old_run=s.subprocess.run
  with tempfile.TemporaryDirectory() as directory:
   s.MANIFEST=Path(directory)/'manifest.json'; s.MANIFEST.write_text('{"models":[{"name":"one"}]}')
   class R: stdout='{"installed":false}'; returncode=0
   s.subprocess.run=lambda *a,**k:R()
   try: self.assertEqual(s.status()['models'][0]['name'],'one')
   finally: s.MANIFEST=old_manifest; s.subprocess.run=old_run
if __name__=='__main__': unittest.main()
