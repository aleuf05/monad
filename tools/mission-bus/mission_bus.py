#!/usr/bin/env python3
"""Mission Bus: append-only record, read-only evidence, review, projection.

Generalized from the Kraken inquiry pilot (MISSIONBUS-01): Record now
carries its own mission_id/correlation_id instead of the module hardcoding
a single mission's constants, so a second mission can exist in the same
append-only store without a second copy of this file. Running with no
--mission-id/--objective/--correlation-id still behaves identically to the
original Kraken-only script -- KRAKEN_MID/KRAKEN_CID/KRAKEN_OBJECTIVE below
are exactly the values the hardcoded constants used to be.
"""
from __future__ import annotations
import argparse, hashlib, json, sqlite3, urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]; DEFAULT_DB=ROOT/'data/mission-record/mission-record.sqlite3'; OUT=ROOT/'web/data/mission-ops.json'; REGISTRY_OUT=ROOT/'web/data/mission-artifacts.json'
KRAKEN_MID='mission.kraken-inquiry-001'; KRAKEN_CID='run.kraken-inquiry-001'
KRAKEN_OBJECTIVE='What does the verified evidence justify about contact K-1?'
TERMINAL={'completed','rejected','cancelled','failed'}
def now(): return datetime.now(timezone.utc).isoformat()
def stable(prefix,obj): return prefix+'.'+hashlib.sha256(json.dumps(obj,sort_keys=True).encode()).hexdigest()[:16]
class Error(ValueError): pass
class Record:
 def __init__(self,path=DEFAULT_DB,mission_id=KRAKEN_MID,correlation_id=KRAKEN_CID):
  self.mission_id=mission_id; self.correlation_id=correlation_id
  path.parent.mkdir(parents=True,exist_ok=True); self.db=sqlite3.connect(path); self.db.row_factory=sqlite3.Row
  self.db.executescript("""PRAGMA journal_mode=WAL; CREATE TABLE IF NOT EXISTS mission_events(event_id TEXT PRIMARY KEY,mission_id TEXT NOT NULL,correlation_id TEXT NOT NULL,seq INTEGER NOT NULL,event_type TEXT NOT NULL,payload_json TEXT NOT NULL,recorded_at TEXT NOT NULL,UNIQUE(mission_id,seq)); CREATE TRIGGER IF NOT EXISTS no_event_update BEFORE UPDATE ON mission_events BEGIN SELECT RAISE(ABORT,'mission_events are immutable'); END; CREATE TRIGGER IF NOT EXISTS no_event_delete BEFORE DELETE ON mission_events BEGIN SELECT RAISE(ABORT,'mission_events are immutable'); END;""")
 def events(self): return [dict(r)|{'payload':json.loads(r['payload_json'])} for r in self.db.execute('SELECT * FROM mission_events WHERE mission_id=? ORDER BY seq',(self.mission_id,))]
 def status(self):
  ev=self.events(); return next((x['payload']['status'] for x in reversed(ev) if x['event_type'] in {'status_changed','mission_created'}),'absent')
 def append(self,event_type,payload,event_id=None):
  canonical=json.dumps(payload,sort_keys=True,separators=(',',':')); event_id=event_id or stable('missionevent',{'mission_id':self.mission_id,'type':event_type,'payload':payload})
  old=self.db.execute('SELECT payload_json,event_type FROM mission_events WHERE event_id=?',(event_id,)).fetchone()
  if old:
   if old['payload_json']!=canonical or old['event_type']!=event_type: raise Error('event ID reused with unequal content')
   return event_id
  current=self.status()
  if event_type=='mission_created' and current!='absent': raise Error('mission already exists')
  if event_type=='status_changed' and current in TERMINAL: raise Error('terminal mission cannot transition')
  seq=self.db.execute('SELECT COALESCE(MAX(seq),0)+1 FROM mission_events WHERE mission_id=?',(self.mission_id,)).fetchone()[0]
  self.db.execute('INSERT INTO mission_events VALUES(?,?,?,?,?,?,?)',(event_id,self.mission_id,self.correlation_id,seq,event_type,canonical,now())); self.db.commit(); return event_id

def envelope(r,status,objective=KRAKEN_OBJECTIVE): return {'schema_version':'monad.mission.v0.1','mission_id':r.mission_id,'correlation_id':r.correlation_id,'parent_mission_id':None,'kind':'inquiry','objective':objective,'requested_by':{'id':'lieutenant.cgl','authority':'human-command'},'status':status,'created_at':now(),'updated_at':now(),'input_refs':[],'constraints':['Unknown identity or approach alone does not establish hostility.'],'data':{}}
def create(r,objective=KRAKEN_OBJECTIVE): r.append('mission_created',envelope(r,'created',objective),stable('missionevent.created',{'mission_id':r.mission_id}))
def snapshot(url):
 with urllib.request.urlopen(url.rstrip('/')+'/snapshot',timeout=6) as x: return json.load(x)
def execute(r,url,objective=KRAKEN_OBJECTIVE):
 # Evidence gathering and hypothesis generation below remain Kraken/K-1-
 # specific (this pilot's stub cognition adapter, per KRAKEN-INQUIRY-
 # PILOT-1.0's scope) -- MISSIONBUS-01 generalizes which mission/
 # correlation ID this runs under, not what the stub adapter investigates.
 # A genuinely different inquiry needs its own cognition adapter; wiring
 # one in is exactly the kind of follow-up GLUE-03 already scoped
 # (Cognition Graph export, Mission Director import, etc.), not this task.
 if r.status()=='absent': create(r,objective)
 if r.status()=='created': r.append('status_changed',envelope(r,'running',objective),stable('missionevent.running',{'mission_id':r.mission_id}))
 if r.status()=='review-required': return
 s=snapshot(url); watches=[w for w in s.get('watch_events',[]) if 'K-1' in w.get('message','') or 'KRAKEN' in w.get('message','')]
 claim=watches[-1]['message'] if watches else 'K-1 is an unidentified contact under observation; no verified hostile act is present in the current snapshot.'
 ev={'schema_version':'monad.evidence.v0.1','evidence_id':stable('evidence.fleetcore.kraken-watch',{'mission_id':r.mission_id}),'source_system':'fleetcore','source_id':f"snapshot.tick.{s.get('tick')}",'locator':{'kind':'api','value':'/fleetcore-ws/snapshot#watch_events[K-1]'},'content_sha256':None,'observed_at':now(),'recorded_at':now(),'classification':'verified-state','claim':claim,'producer':'fleetcore-reader','supersedes_evidence_id':None}
 r.append('evidence_cited',ev,stable('missionevent.evidence',{'mission_id':r.mission_id}))
 hypotheses=[('unknown-non-hostile','Identity remains unknown; current evidence does not establish hostility.','No confirmed identity or intent.'),('surveillance-risk','The contact may be observing the formation.','Approach and observation are compatible with benign explanations.'),('potential-threat','The contact could become a threat if it closes aggressively or demonstrates hostile behavior.','No hostile behavior is currently verified.')]
 for i,(name,text,counter) in enumerate(hypotheses,1):
  a={'schema_version':'monad.artifact.v0.1','artifact_id':f'artifact.cognition.{r.mission_id}.hypothesis-{i}','mission_id':r.mission_id,'correlation_id':r.correlation_id,'component':'stub-cognition','artifact_type':'hypothesis','status':'candidate-ready','created_at':now(),'input_refs':[ev['evidence_id']],'evidence_refs':[ev['evidence_id']],'requires_review':False,'review_authority':'human-command','supersedes_artifact_id':None,'data':{'mode':'stub','name':name,'finding':text,'counterevidence':counter}}
  r.append('artifact_recorded',a,stable(f'missionevent.hypothesis-{i}',{'mission_id':r.mission_id}))
 verdict={'schema_version':'monad.artifact.v0.1','artifact_id':f'artifact.cognition.{r.mission_id}.verdict-01','mission_id':r.mission_id,'correlation_id':r.correlation_id,'component':'stub-cognition','artifact_type':'recommendation-candidate','status':'review-required','created_at':now(),'input_refs':[ev['evidence_id']],'evidence_refs':[ev['evidence_id']],'requires_review':True,'review_authority':'human-command','supersedes_artifact_id':None,'data':{'mode':'stub','recommendation':'Continue passive observation, maintain separation, and escalate only on new verified evidence.','unknowns':['identity','intent'],'fleetcore_mutation':False}}
 r.append('artifact_recorded',verdict,stable('missionevent.verdict',{'mission_id':r.mission_id})); r.append('status_changed',envelope(r,'review-required',objective),stable('missionevent.review-required',{'mission_id':r.mission_id}))
def transition(r,status,reason,objective=KRAKEN_OBJECTIVE):
 current=r.status(); allowed={('created','paused'),('running','paused'),('blocked','running'),('paused','running')}
 if not (status=='cancelled' and current not in TERMINAL) and (current,status) not in allowed: raise Error(f'cannot transition {current} to {status}')
 payload=envelope(r,status,objective); payload['data']={'reason':reason}; r.append('status_changed',payload,stable('missionevent.transition',{'mission_id':r.mission_id,'from':current,'to':status,'reason':reason}))
def review(r,action,reviewer,authority,reason,decision_id,amended=None,revision=1):
 if r.status()!='review-required': raise Error('mission is not review-required')
 if authority!='human-command': raise Error('human-command authority required')
 if action not in {'accept','reject','edit'}: raise Error('action must be accept, reject, or edit')
 verdicts=[x['payload'] for x in r.events() if x['event_type']=='artifact_recorded' and x['payload'].get('artifact_type')=='recommendation-candidate']; current_revision=len(verdicts)
 if revision!=current_revision: raise Error(f'stale review revision {revision}; current is {current_revision}')
 if action=='edit':
  if not amended: raise Error('edit requires amended recommendation')
  prior=verdicts[-1]; updated=json.loads(json.dumps(prior)); updated['artifact_id']=f'artifact.cognition.{r.mission_id}.verdict-{current_revision+1:02d}'; updated['supersedes_artifact_id']=prior['artifact_id']; updated['created_at']=now(); updated['data']['recommendation']=amended; updated['data']['revision']=current_revision+1
  r.append('artifact_recorded',updated,'missionevent.'+decision_id+'.edit'); return
 a={'schema_version':'monad.artifact.v0.1','artifact_id':f'artifact.review.{r.mission_id}.decision-01','mission_id':r.mission_id,'correlation_id':r.correlation_id,'component':'human-review','artifact_type':'review-decision','status':'accepted' if action=='accept' else 'rejected','created_at':now(),'input_refs':[verdicts[-1]['artifact_id']],'evidence_refs':[stable('evidence.fleetcore.kraken-watch',{'mission_id':r.mission_id})],'requires_review':False,'review_authority':'human-command','supersedes_artifact_id':None,'data':{'decision_id':decision_id,'action':action,'review_revision':revision,'decided_by':{'id':reviewer,'authority':authority},'reason':reason,'fleetcore_mutation':False}}
 r.append('artifact_recorded',a,'missionevent.'+decision_id); r.append('status_changed',envelope(r,'completed' if action=='accept' else 'rejected'),'missionevent.'+r.mission_id+'.'+('completed' if action=='accept' else 'rejected'))
def project(r,path=OUT,objective=KRAKEN_OBJECTIVE):
 ev=r.events(); arts=[x['payload'] for x in ev if x['event_type']=='artifact_recorded']; evidence=[x['payload'] for x in ev if x['event_type']=='evidence_cited']; decision=next((a for a in reversed(arts) if a['artifact_type']=='review-decision'),None)
 out={'schema_version':'monad.projection.v0.1','audience':'agent-ops','generated_at':now(),'source_record_cursor':ev[-1]['seq'] if ev else 0,'mission':{'mission_id':r.mission_id,'objective':objective,'status':r.status(),'fleetcore_mutation':False},'evidence':evidence,'findings':[a for a in arts if a['artifact_type']=='hypothesis'],'recommendation':next((a for a in arts if a['artifact_type']=='recommendation-candidate'),None),'decision':decision}
 path.parent.mkdir(parents=True,exist_ok=True); tmp=path.with_suffix('.tmp'); tmp.write_text(json.dumps(out,indent=2,sort_keys=True)); tmp.replace(path); return out
REGISTRY_TYPES={
 'hypothesis':('generated-candidate','Cognition hypothesis'),
 'recommendation-candidate':('generated-candidate','Cognition recommendation'),
 'review-decision':('human-command','Human review decision'),
}
def build_registry(r,path=REGISTRY_OUT):
 """Build the public artifact index from recorded events, never directories."""
 events=r.events(); artifacts=[]; superseded={
  event['payload'].get('supersedes_artifact_id') for event in events
  if event['event_type']=='artifact_recorded'
 }
 for event in events:
  if event['event_type']!='artifact_recorded': continue
  artifact=event['payload']; artifact_type=artifact.get('artifact_type')
  if artifact_type not in REGISTRY_TYPES: raise Error(f'unknown registry artifact type: {artifact_type}')
  if artifact.get('visibility','public')!='public': continue
  if artifact.get('artifact_id') in superseded: continue
  classification,title=REGISTRY_TYPES[artifact_type]
  artifacts.append({
   'schema_version':'monad.registry.v0.1','artifact_id':artifact['artifact_id'],
   'mission_id':artifact['mission_id'],'artifact_type':artifact_type,
   'status':artifact['status'],'classification':classification,
   'title':artifact.get('title') or title,
   'locator':{'kind':'mission-record','value':event['event_id']},
   'content_sha256':None,'media_type':'application/json',
   'component':artifact['component'],'created_at':artifact['created_at'],
   'accepted_at':artifact['created_at'] if artifact['status']=='accepted' else None,
   'evidence_refs':artifact.get('evidence_refs',[]),
   'supersedes_artifact_id':artifact.get('supersedes_artifact_id'),
   'visibility':'public',
  })
 artifacts.sort(key=lambda item:item['artifact_id'])
 out={'schema_version':'monad.registry-index.v0.1','generated_at':events[-1]['recorded_at'] if events else None,'source_record_cursor':events[-1]['seq'] if events else 0,'artifacts':artifacts}
 path.parent.mkdir(parents=True,exist_ok=True); encoded=json.dumps(out,indent=2,sort_keys=True)+'\n'; tmp=path.with_suffix('.tmp'); tmp.write_text(encoded); tmp.replace(path); return out
def main():
 p=argparse.ArgumentParser(); p.add_argument('--db',type=Path,default=DEFAULT_DB)
 p.add_argument('--fleetcore-url',default='http://127.0.0.1:4771')
 p.add_argument('--mission-id',default=KRAKEN_MID); p.add_argument('--correlation-id',default=KRAKEN_CID); p.add_argument('--objective',default=KRAKEN_OBJECTIVE)
 sub=p.add_subparsers(dest='cmd',required=True)
 for x in ('create','execute','inspect','project','registry'): sub.add_parser(x)
 for x in ('pause','cancel','resume'):
  z=sub.add_parser(x); z.add_argument('--reason',required=True)
 q=sub.add_parser('review'); q.add_argument('action',choices=['accept','reject','edit']); q.add_argument('--reviewer',required=True); q.add_argument('--authority',required=True); q.add_argument('--reason',required=True); q.add_argument('--decision-id',default='decision.kraken.001'); q.add_argument('--amended'); q.add_argument('--revision',type=int,default=1)
 a=p.parse_args(); r=Record(a.db,a.mission_id,a.correlation_id)
 try:
  if a.cmd=='create': create(r,a.objective)
  elif a.cmd=='execute': execute(r,a.fleetcore_url,a.objective)
  elif a.cmd=='review': review(r,a.action,a.reviewer,a.authority,a.reason,a.decision_id,a.amended,a.revision)
  elif a.cmd=='pause': transition(r,'paused',a.reason,a.objective)
  elif a.cmd=='cancel': transition(r,'cancelled',a.reason,a.objective)
  elif a.cmd=='resume': transition(r,'running',a.reason,a.objective)
  if a.cmd=='project': result=project(r,OUT,a.objective)
  elif a.cmd=='registry': result=build_registry(r,REGISTRY_OUT)
  else: result={'status':r.status(),'events':r.events()}
 except Error as e: p.error(str(e))
 print(json.dumps(result,indent=2,default=str)); return 0
if __name__=='__main__': raise SystemExit(main())
