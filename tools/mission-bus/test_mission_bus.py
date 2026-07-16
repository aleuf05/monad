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
 def test_pause_resume_cancel(self):
  m.create(self.r); m.transition(self.r,'paused','hold'); m.transition(self.r,'running','continue'); m.transition(self.r,'cancelled','stop'); self.assertEqual(self.r.status(),'cancelled')
 def test_edit_revision_and_stale_review(self):
  old=m.snapshot; m.snapshot=lambda u:{'tick':42,'watch_events':[]}
  try: m.execute(self.r,'x')
  finally: m.snapshot=old
  m.review(self.r,'edit','lieutenant.cgl','human-command','sharpen','edit1','Maintain separation.',1)
  with self.assertRaisesRegex(m.Error,'stale'): m.review(self.r,'accept','lieutenant.cgl','human-command','old','d2',revision=1)
if __name__=='__main__': unittest.main()
