import importlib.util,tempfile,unittest
from pathlib import Path
P=Path(__file__).with_name('mission_bus.py'); S=importlib.util.spec_from_file_location('mb',P); m=importlib.util.module_from_spec(S); S.loader.exec_module(m)
class T(unittest.TestCase):
 def setUp(self): self.d=tempfile.TemporaryDirectory(); self.r=m.Record(Path(self.d.name)/'x.db')
 def tearDown(self): self.d.cleanup()
 def test_immutable_and_review_gate(self):
  m.create(self.r); self.assertEqual(self.r.status(),'created');
  with self.assertRaises(Exception): self.r.db.execute('DELETE FROM mission_events')
 def test_flow_with_fixture(self):
  old=m.snapshot; m.snapshot=lambda u:{'tick':42,'watch_events':[{'message':'Contact K-1 (KRAKEN) unidentified; weapons cold.'}]}
  try: m.execute(self.r,'x')
  finally: m.snapshot=old
  self.assertEqual(self.r.status(),'review-required'); m.execute(self.r,'x'); self.assertEqual(len(self.r.events()),8)
  with self.assertRaises(m.Error): m.review(self.r,'accept','x','operator','no','d')
  m.review(self.r,'accept','lieutenant.cgl','human-command','proportionate','d'); self.assertEqual(self.r.status(),'completed')
  out=m.project(self.r,Path(self.d.name)/'p.json'); self.assertFalse(out['mission']['fleetcore_mutation']); self.assertEqual(len(out['findings']),3)
if __name__=='__main__': unittest.main()
