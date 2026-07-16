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
 def test_second_mission_independent_of_kraken(self):
  # MISSIONBUS-01: a genuinely different mission, sharing the same DB
  # file as the default-constructed Kraken Record, must run its full
  # lifecycle to completion without touching or depending on Kraken's
  # events, and without any event_id collision across the two missions.
  db_path=Path(self.d.name)/'x.db'
  kraken=m.Record(db_path)
  other=m.Record(db_path,mission_id='mission.second-inquiry-001',correlation_id='run.second-inquiry-001')
  old=m.snapshot; m.snapshot=lambda u:{'tick':7,'watch_events':[]}
  try:
   m.execute(other,'x',objective='A second, independent inquiry.')
   m.execute(other,'x',objective='A second, independent inquiry.')
  finally: m.snapshot=old
  self.assertEqual(other.status(),'review-required')
  self.assertEqual(kraken.status(),'absent')  # untouched by the other mission
  m.review(other,'accept','lieutenant.cgl','human-command','proportionate','d-other')
  self.assertEqual(other.status(),'completed')
  out=m.project(other,Path(self.d.name)/'p-other.json',objective='A second, independent inquiry.')
  self.assertEqual(out['mission']['mission_id'],'mission.second-inquiry-001')
  self.assertEqual(len(out['findings']),3)
  # Kraken's own lifecycle still works untouched, same DB file.
  m.create(kraken); self.assertEqual(kraken.status(),'created')
  ids=[e['event_id'] for e in kraken.events()]+[e['event_id'] for e in other.events()]
  self.assertEqual(len(ids),len(set(ids)))  # no cross-mission event_id collision
 def test_registry_is_deterministic_and_excludes_superseded_revision(self):
  old=m.snapshot; m.snapshot=lambda u:{'tick':42,'watch_events':[]}
  try: m.execute(self.r,'x')
  finally: m.snapshot=old
  m.review(self.r,'edit','lieutenant.cgl','human-command','sharpen','edit-registry','Maintain separation.',1)
  path=Path(self.d.name)/'registry.json'
  first=m.build_registry(self.r,path); encoded=path.read_bytes()
  second=m.build_registry(self.r,path)
  self.assertEqual(first,second); self.assertEqual(encoded,path.read_bytes())
  ids={item['artifact_id'] for item in first['artifacts']}
  self.assertNotIn(f'artifact.cognition.{self.r.mission_id}.verdict-01',ids)
  self.assertIn(f'artifact.cognition.{self.r.mission_id}.verdict-02',ids)
if __name__=='__main__': unittest.main()
