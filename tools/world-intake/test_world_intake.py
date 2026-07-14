import importlib.util, tempfile, unittest
from pathlib import Path

ROOT=Path(__file__).parent
spec=importlib.util.spec_from_file_location("world_intake",ROOT/"world_intake.py")
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class Acceptance(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(); self.db=Path(self.tmp.name)/"intake.db"; self.w=m.Intake(self.db)
  self.raw=(ROOT/"first_wave_reactor_crew.txt").read_bytes(); self.src=self.w.ingest(self.raw,"Monad","2026-07-14T00:00:00Z","First Wave")
  self.ast=self.w.extract(self.src)
 def tearDown(self): self.w.close(); self.tmp.cleanup()
 def find(self,pred,subject=None): return next(x for x in self.ast if x["predicate"]==pred and (subject is None or x["subject"]==subject))
 def test_01_source_byte_exact(self):
  self.assertEqual(bytes(self.w.source(self.src)["content"]),self.raw)
  with self.assertRaises(m.sqlite3.IntegrityError): self.w.db.execute("update sources set author='rewritten' where id=?",(self.src,))
 def test_02_nine_recruits(self): self.assertEqual(len([x for x in self.ast if x["predicate"]=="propose_entity"]),9)
 def test_03_classes_separated(self): self.assertTrue({"identity","assignment","claim","permission","location","request","flavor"}<={x["class"] for x in self.ast})
 def test_04_alias_possible_not_created(self):
  e=self.w.add_entity("agent","Claude",["Recruit Claude","Commander Claude"]); a=self.find("alias_reference")
  outcome,candidates=self.w.resolve(a["id"]); self.assertEqual((outcome,candidates),("matched",[e])); self.assertEqual(self.w.db.execute("select count(*) from entities").fetchone()[0],1)
 def test_05_radiation_unverified(self): self.assertEqual(self.find("attach_capability","Ada")["value"]["verification"],"unverified")
 def test_06_scram_explicit(self): self.assertEqual(self.w.validate(self.find("request_permission","Vance")["id"])[0]["code"],"explicit_authority_required")
 def test_07_startup_is_request(self):
  a=self.find("authorization_request"); self.assertEqual(a["class"],"request"); self.assertEqual(a["value"]["status"],"pending"); self.assertFalse(any(x["class"]=="event" for x in self.ast))
 def test_08_exclusive_conflict(self): self.assertEqual(self.w.validate(self.find("assign_role","Cyra")["id"])[0]["code"],"duplicate_exclusive_assignment")
 def test_09_approved_uses_submit_path(self):
  a=self.find("assign_role","Ada"); adj=self.w.review(a["id"],"approve"); cid,payload=self.w.compile(adj); calls=[]
  ev=self.w.commit(cid,lambda p,k: calls.append((p,k)) or {"accepted":True,"event_id":"fc-1"})
  self.assertEqual(len(calls),1); self.assertEqual(calls[0][0]["type"],"apply-canon-change"); self.assertEqual(calls[0][0]["change"]["change"],"assign"); self.assertIsNotNone(ev)
 def test_10_full_provenance(self):
  a=self.find("assign_role","Ada"); adj=self.w.review(a["id"],"approve"); cid,_=self.w.compile(adj); self.w.commit(cid,lambda p,k:{"accepted":True,"event_id":"fc-2"})
  p=self.w.provenance(a["id"]); self.assertEqual(bytes(p["source"]["content"]),self.raw); self.assertTrue(p["adjudications"]); self.assertTrue(p["commands"][0]["canon_event"])
 def test_11_retry_idempotent(self):
  self.assertEqual(self.w.ingest(self.raw,"other"),self.src); self.w.extract(self.src); self.assertEqual(len(self.w.assertions(self.src)),40)
  a=self.find("assign_role","Ada"); adj=self.w.review(a["id"],"approve"); cid,_=self.w.compile(adj); count=[]; submit=lambda p,k: count.append(1) or {"accepted":True}
  self.w.commit(cid,submit); self.w.commit(cid,submit); self.assertEqual(len(count),1)
 def test_12_restart_and_correction(self):
  a=self.find("assign_role","Ada"); adj=self.w.review(a["id"],"approve"); cid,_=self.w.compile(adj); ev=self.w.commit(cid,lambda p,k:{"accepted":True,"event_id":"fc-3"}); cor=self.w.correct(ev["id"],"assignment_revoked","Captain correction")
  correction_command,payload=self.w.compile_correction(cor); self.assertEqual(payload["change"]["change"],"revoke-assignment"); self.assertEqual(self.w.db.execute("select command_id from corrections where id=?",(cor,)).fetchone()[0],correction_command)
  self.w.close(); self.w=m.Intake(self.db); self.assertIsNotNone(self.w.source(self.src)); self.assertIsNotNone(self.w.provenance(a["id"])); self.assertEqual(self.w.db.execute("select kind from corrections where id=?",(cor,)).fetchone()[0],"assignment_revoked")

if __name__=="__main__": unittest.main()
