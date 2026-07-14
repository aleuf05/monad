#!/usr/bin/env python3
"""Living World Intake: proposals around, never writes to, canonical state."""
from __future__ import annotations
import argparse, hashlib, hmac, json, os, re, sqlite3, urllib.request, uuid
from pathlib import Path
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

CLASSES = {"identity", "assignment", "capability", "permission", "location", "relationship", "event", "request", "claim", "flavor"}
DECISIONS = {"approve", "amend", "reject", "defer", "flavor_only", "unverified", "link"}
HIGH_RISK = {"permission", "command_authority", "reactor_state", "vessel_movement", "injury", "death", "safety_status"}

SCHEMA = """
PRAGMA foreign_keys=ON;
CREATE TABLE IF NOT EXISTS sources(id TEXT PRIMARY KEY, content BLOB NOT NULL, content_hash TEXT UNIQUE NOT NULL, author TEXT NOT NULL, source_ts TEXT NOT NULL, mission_context TEXT, attachments_json TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS assertions(id TEXT PRIMARY KEY, source_id TEXT NOT NULL REFERENCES sources(id), ordinal INTEGER NOT NULL, class TEXT NOT NULL, subject TEXT, predicate TEXT NOT NULL, value_json TEXT NOT NULL, excerpt TEXT NOT NULL, confidence REAL NOT NULL, status TEXT NOT NULL DEFAULT 'pending', UNIQUE(source_id,ordinal));
CREATE TABLE IF NOT EXISTS entities(id TEXT PRIMARY KEY, kind TEXT NOT NULL, canonical_name TEXT NOT NULL, aliases_json TEXT NOT NULL DEFAULT '[]', state_json TEXT NOT NULL DEFAULT '{}');
CREATE TABLE IF NOT EXISTS resolutions(assertion_id TEXT PRIMARY KEY REFERENCES assertions(id), entity_id TEXT REFERENCES entities(id), outcome TEXT NOT NULL, candidates_json TEXT NOT NULL, note TEXT);
CREATE TABLE IF NOT EXISTS conflicts(id TEXT PRIMARY KEY, assertion_id TEXT NOT NULL REFERENCES assertions(id), code TEXT NOT NULL, material INTEGER NOT NULL, detail TEXT NOT NULL, UNIQUE(assertion_id,code,detail));
CREATE TABLE IF NOT EXISTS adjudications(id TEXT PRIMARY KEY, assertion_id TEXT NOT NULL REFERENCES assertions(id), decision TEXT NOT NULL, adjudicator TEXT NOT NULL, edit_json TEXT, decided_at TEXT NOT NULL, UNIQUE(assertion_id,decision,adjudicator,edit_json));
CREATE TABLE IF NOT EXISTS commands(id TEXT PRIMARY KEY, assertion_id TEXT NOT NULL REFERENCES assertions(id), adjudication_id TEXT NOT NULL REFERENCES adjudications(id), idempotency_key TEXT UNIQUE NOT NULL, payload_json TEXT NOT NULL, status TEXT NOT NULL, response_json TEXT, submitted_at TEXT);
CREATE TABLE IF NOT EXISTS canon_events(id TEXT PRIMARY KEY, command_id TEXT UNIQUE NOT NULL REFERENCES commands(id), external_event_id TEXT, event_json TEXT NOT NULL, occurred_at TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS corrections(id TEXT PRIMARY KEY, target_event_id TEXT NOT NULL REFERENCES canon_events(id), kind TEXT NOT NULL, reason TEXT NOT NULL, command_id TEXT REFERENCES commands(id), created_at TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS idx_assertions_source ON assertions(source_id); CREATE INDEX IF NOT EXISTS idx_adj_assertion ON adjudications(assertion_id);
CREATE TRIGGER IF NOT EXISTS sources_immutable_update BEFORE UPDATE ON sources BEGIN SELECT RAISE(ABORT,'sources are immutable'); END;
CREATE TRIGGER IF NOT EXISTS sources_immutable_delete BEFORE DELETE ON sources BEGIN SELECT RAISE(ABORT,'sources are immutable'); END;
PRAGMA user_version=1;
"""

def now(): return datetime.now(timezone.utc).isoformat()
def sid(prefix, text): return prefix + "_" + hashlib.sha256(text.encode()).hexdigest()[:24]
def slug(text): return re.sub(r"[^a-z0-9]+", ".", (text or "unknown").casefold()).strip(".")

class Intake:
    def __init__(self, db):
        self.db_path = str(db); self.db = sqlite3.connect(self.db_path); self.db.row_factory=sqlite3.Row
        self.db.executescript(SCHEMA); self.db.commit()
    def close(self): self.db.close()
    def ingest(self, content: bytes, author="unknown", source_ts=None, mission_context="", attachments=()):
        h=hashlib.sha256(content).hexdigest(); ident="src_"+h[:24]
        self.db.execute("INSERT OR IGNORE INTO sources VALUES(?,?,?,?,?,?,?,?)",(ident,sqlite3.Binary(content),h,author,source_ts or now(),mission_context,json.dumps(list(attachments),sort_keys=True),now())); self.db.commit(); return ident
    def source(self, source_id):
        r=self.db.execute("SELECT * FROM sources WHERE id=?",(source_id,)).fetchone(); return dict(r) if r else None
    def _add(self, source, ordinal, cls, subject, pred, value, excerpt, confidence=.95):
        ident=sid("ast",f"{source}:{ordinal}"); self.db.execute("INSERT OR IGNORE INTO assertions(id,source_id,ordinal,class,subject,predicate,value_json,excerpt,confidence) VALUES(?,?,?,?,?,?,?,?,?)",(ident,source,ordinal,cls,subject,pred,json.dumps(value,sort_keys=True),excerpt,confidence)); return ident
    def extract(self, source_id):
        raw=bytes(self.source(source_id)["content"]).decode("utf-8"); n=0
        for line in raw.splitlines():
            m=re.match(r"Recruit ([A-Za-z][\w-]*): assign role ([^;]+); station ([^;]+); claims (.+)\.$",line)
            if m:
                name,role,station,claim=m.groups()
                for cls,pred,val,conf in (("identity","propose_entity",{"kind":"crew","name":name},.99),("assignment","assign_role",role,.98),("location","assign_station",station,.98),("claim","attach_capability",{"capability":claim,"verification":"unverified"},.75)):
                    self._add(source_id,n,cls,name,pred,val,line,conf); n+=1
                continue
            if "Commander Claude reports" in line:
                self._add(source_id,n,"identity","Chief Claude","alias_reference",{"alias":"Commander Claude","possible_canonical":"Claude"},line,.7); n+=1
            if line.startswith("Request Captain authorization"):
                self._add(source_id,n,"request","reactor","authorization_request",{"action":"reactor_start","status":"pending"},line,.99); n+=1
                self._add(source_id,n,"permission","Vance","request_permission",{"permission":"scram_authority","status":"pending"},line,.99); n+=1
            if "bright sparks" in line:
                self._add(source_id,n,"flavor",None,"narrative_flavor",line,line,.99); n+=1
        self.db.commit(); return self.assertions(source_id)
    def assertions(self, source_id=None):
        q="SELECT * FROM assertions"; args=()
        if source_id: q+=" WHERE source_id=?"; args=(source_id,)
        q+=" ORDER BY source_id,ordinal"; return [{**dict(r),"value":json.loads(r["value_json"])} for r in self.db.execute(q,args)]
    def queue(self, source_id=None):
        """Inspectable review cards; compilation is a preview, never execution."""
        cards=[]
        for a in self.assertions(source_id):
            entity=self.db.execute("SELECT * FROM entities WHERE lower(canonical_name)=lower(?)",(a["subject"] or "",)).fetchone()
            source=self.source(a["source_id"])
            cards.append({"assertion_id":a["id"],"subject":a["subject"],"proposed_change":{"operation":a["predicate"],"value":a["value"]},"assertion_class":a["class"],"supporting_source_excerpt":a["excerpt"],"confidence":a["confidence"],"existing_canonical_state":json.loads(entity["state_json"]) if entity else None,"conflicts":self.validate(a["id"]),"requires_individual_approval":a["class"] in {"permission","event"} or a["predicate"] in {"authorization_request","grant_permission"},"proposed_fleetcore_command":{"type":"apply-canon-change","command_id":"assigned-after-adjudication","change":a["predicate"]},"provenance":{"source_id":a["source_id"],"source_hash":source["content_hash"],"author":source["author"],"source_timestamp":source["source_ts"],"assertion_id":a["id"]}})
        return cards
    def add_entity(self, kind,name,aliases=(),state=None):
        ident=sid("ent",kind+":"+name.casefold()); self.db.execute("INSERT OR REPLACE INTO entities VALUES(?,?,?,?,?)",(ident,kind,name,json.dumps(list(aliases)),json.dumps(state or {}))); self.db.commit(); return ident
    def resolve(self, assertion_id):
        a=self.db.execute("SELECT * FROM assertions WHERE id=?",(assertion_id,)).fetchone(); term=(a["subject"] or "").casefold().removeprefix("recruit ").removeprefix("commander ").removeprefix("chief ")
        candidates=[]
        for e in self.db.execute("SELECT * FROM entities"):
            names=[e["canonical_name"],*json.loads(e["aliases_json"])]
            if any(term and (term==x.casefold() or term in x.casefold().split()) for x in names): candidates.append(e["id"])
        outcome="matched" if len(candidates)==1 else "ambiguous" if len(candidates)>1 else "new_candidate"
        ent=candidates[0] if len(candidates)==1 else None
        self.db.execute("INSERT OR REPLACE INTO resolutions VALUES(?,?,?,?,?)",(assertion_id,ent,outcome,json.dumps(candidates),"no silent merge or creation")); self.db.commit(); return outcome,candidates
    def validate(self, assertion_id):
        a=self.db.execute("SELECT * FROM assertions WHERE id=?",(assertion_id,)).fetchone(); conflicts=[]
        val=json.loads(a["value_json"])
        if a["predicate"]=="assign_role" and val in {"Reactor Operator","Scram Officer","Watch Officer"}:
            peers=self.db.execute("SELECT subject FROM assertions WHERE predicate=? AND value_json=? AND id<>?",("assign_role",a["value_json"],assertion_id)).fetchall()
            if peers: conflicts.append(("duplicate_exclusive_assignment",1,f"{val} also proposed for {', '.join(x[0] for x in peers)}"))
        if a["predicate"]=="assign_station" and not str(val).startswith("Deck 7"):
            conflicts.append(("nonexistent_station",1,f"station is not in known Deck 7 intake scope: {val}"))
        if a["predicate"]=="assign_station":
            peers=self.db.execute("SELECT value_json FROM assertions WHERE subject=? AND predicate='assign_station' AND id<>?",(a["subject"],assertion_id)).fetchall()
            if any(peer[0] != a["value_json"] for peer in peers): conflicts.append(("conflicting_locations",1,"subject has different proposed station locations"))
        if a["predicate"]=="assign_role":
            entity=self.db.execute("SELECT state_json FROM entities WHERE lower(canonical_name)=lower(?)",(a["subject"],)).fetchone()
            state=json.loads(entity[0]) if entity else {}
            if val in state.get("incompatible_roles",[]): conflicts.append(("incompatible_roles",1,f"{val} conflicts with current canonical role"))
            if state.get("available") is False and any(word in str(val).casefold() for word in ("watch","officer","operator")): conflicts.append(("unavailable_personnel",1,"unavailable personnel cannot be assigned to watch"))
        if a["predicate"]=="propose_entity":
            existing=self.db.execute("SELECT kind FROM entities WHERE lower(canonical_name)=lower(?)",(val.get("name",""),)).fetchone()
            if existing and existing[0] != val.get("kind"): conflicts.append(("contradictory_identity",1,"existing entity has a different kind or chassis classification"))
        if a["class"]=="permission": conflicts.append(("explicit_authority_required",1,"permissions are never inferred and require individual Captain approval"))
        if a["class"]=="permission":
            peers=self.db.execute("SELECT subject FROM assertions WHERE class='permission' AND value_json=? AND id<>?",(a["value_json"],assertion_id)).fetchall()
            if peers: conflicts.append(("conflicting_command_authority",1,"the same authority is proposed for multiple subjects"))
        if isinstance(val,dict) and val.get("status") == "superseded": conflicts.append(("superseded_order",1,"proposal references an order already marked superseded"))
        if a["class"]=="event":
            peers=self.db.execute("SELECT id FROM assertions WHERE class='event' AND predicate=? AND value_json=? AND id<>?",(a["predicate"],a["value_json"],assertion_id)).fetchall()
            if peers: conflicts.append(("duplicate_event",1,"equivalent event already exists in this intake"))
            if isinstance(val,dict) and val.get("ended_at") and val.get("started_at") and val["ended_at"] < val["started_at"]: conflicts.append(("impossible_chronology",1,"event end precedes event start"))
        for code,mat,detail in conflicts:
            self.db.execute("INSERT OR IGNORE INTO conflicts VALUES(?,?,?,?,?)",(sid("con",assertion_id+code+detail),assertion_id,code,mat,detail))
        self.db.commit(); return [dict(x) for x in self.db.execute("SELECT * FROM conflicts WHERE assertion_id=?",(assertion_id,))]
    def review(self, assertion_id, decision, adjudicator="Captain", edit=None):
        if decision not in DECISIONS: raise ValueError("invalid adjudication")
        a=self.db.execute("SELECT * FROM assertions WHERE id=?",(assertion_id,)).fetchone()
        if not a: raise KeyError(assertion_id)
        edit_s=json.dumps(edit,sort_keys=True) if edit is not None else None; ident=sid("adj",assertion_id+decision+adjudicator+(edit_s or ""))
        self.db.execute("INSERT OR IGNORE INTO adjudications VALUES(?,?,?,?,?,?)",(ident,assertion_id,decision,adjudicator,edit_s,now())); self.db.execute("UPDATE assertions SET status=? WHERE id=?",(decision,assertion_id)); self.db.commit(); return ident
    def compile(self, adjudication_id):
        row=self.db.execute("SELECT d.*,a.class,a.subject,a.predicate,a.value_json,a.source_id,s.content_hash FROM adjudications d JOIN assertions a ON a.id=d.assertion_id JOIN sources s ON s.id=a.source_id WHERE d.id=?",(adjudication_id,)).fetchone()
        if row["decision"] not in {"approve","amend","unverified","link"}: raise ValueError("decision is not compilable")
        if row["class"] == "flavor": raise ValueError("flavor is non-operational")
        value=json.loads(row["edit_json"] or row["value_json"]); subject_id="crew."+slug(row["subject"])
        pred=row["predicate"]
        if pred == "propose_entity":
            subject_id=value["kind"]+"."+slug(value["name"])
            change={"change":"create-entity","entity":{"id":subject_id,"kind":value["kind"],"name":value["name"],"aliases":[],"onboarding_status":"proposed","merged_into":None}}
        elif pred == "alias_reference":
            if row["decision"] != "link" or not value.get("entity_id"): raise ValueError("ambiguous aliases require an explicit link decision and existing entity id")
            change={"change":"add-alias","entity_id":value["entity_id"],"alias":json.loads(row["value_json"])["alias"]}
        elif pred in {"assign_role","assign_station"}:
            assignment_type="role" if pred == "assign_role" else "station"
            change={"change":"assign","assignment":{"id":sid("assignment",row["assertion_id"]),"subject_id":subject_id,"assignment_type":assignment_type,"value":value,"active":True}}
        elif pred == "attach_capability":
            change={"change":"attach-capability","claim":{"id":sid("claim",row["assertion_id"]),"subject_id":subject_id,"capability":value["capability"],"verified":False,"active":True}}
        elif pred in {"authorization_request","request_permission"}:
            request=value.get("action") or value.get("permission")
            if pred == "authorization_request" and value.get("action") == "reactor_start": subject_id="vessel.monad"
            change={"change":"record-authorization","authorization":{"id":sid("authorization",row["assertion_id"]),"subject_id":subject_id,"request":request,"status":"pending"}}
        elif pred == "add_alias": change={"change":"add-alias","entity_id":subject_id,"alias":value}
        elif pred == "set_onboarding_status": change={"change":"set-onboarding-status","entity_id":subject_id,"status":value}
        elif pred == "create_relationship": change={"change":"create-relationship","relationship":{"id":sid("relationship",row["assertion_id"]),"subject_id":subject_id,"relationship":value["relationship"],"object_id":value["object_id"],"active":True}}
        elif pred in {"record_approval","record_denial"}: change={"change":"record-authorization","authorization":{"id":sid("authorization",row["assertion_id"]),"subject_id":subject_id,"request":value["request"],"status":"approved" if pred == "record_approval" else "denied"}}
        elif pred == "grant_permission": change={"change":"grant-permission","permission":{"id":sid("permission",row["assertion_id"]),"subject_id":subject_id,"permission":value["permission"],"approved_by":row["adjudicator"],"active":True}}
        else:
            raise ValueError(f"unsupported canon operation: {pred}")
        key=hashlib.sha256((adjudication_id+json.dumps(change,sort_keys=True)).encode()).hexdigest(); ident="cmd_"+key[:24]
        payload={"type":"apply-canon-change","command_id":ident,"change":change,"provenance":{"source_id":row["source_id"],"source_hash":row["content_hash"],"assertion_id":row["assertion_id"],"adjudication_id":adjudication_id,"adjudicator":row["adjudicator"],"adjudicated_at":row["decided_at"]}}
        self.db.execute("INSERT OR IGNORE INTO commands(id,assertion_id,adjudication_id,idempotency_key,payload_json,status) VALUES(?,?,?,?,?,'compiled')",(ident,row["assertion_id"],adjudication_id,key,json.dumps(payload,sort_keys=True))); self.db.commit(); return ident,payload
    def commit(self, command_id, submit):
        c=self.db.execute("SELECT * FROM commands WHERE id=?",(command_id,)).fetchone()
        prior=self.db.execute("SELECT * FROM canon_events WHERE command_id=?",(command_id,)).fetchone()
        if prior: return dict(prior)
        payload=json.loads(c["payload_json"]); response=submit(payload,c["idempotency_key"])
        if not response.get("accepted"): self.db.execute("UPDATE commands SET status='rejected',response_json=?,submitted_at=? WHERE id=?",(json.dumps(response),now(),command_id)); self.db.commit(); return None
        eid=sid("evt",command_id); event={"command":payload,"fleetcore":response}; ts=now()
        with self.db:
            self.db.execute("UPDATE commands SET status='accepted',response_json=?,submitted_at=? WHERE id=?",(json.dumps(response),ts,command_id))
            self.db.execute("INSERT OR IGNORE INTO canon_events VALUES(?,?,?,?,?)",(eid,command_id,response.get("event_id"),json.dumps(event,sort_keys=True),ts))
        return dict(self.db.execute("SELECT * FROM canon_events WHERE id=?",(eid,)).fetchone())
    def provenance(self, assertion_id):
        a=self.db.execute("SELECT * FROM assertions WHERE id=?",(assertion_id,)).fetchone()
        if not a:return None
        src=self.source(a["source_id"]); adjs=[dict(x) for x in self.db.execute("SELECT * FROM adjudications WHERE assertion_id=?",(assertion_id,))]
        cmds=[]
        for x in self.db.execute("SELECT * FROM commands WHERE assertion_id=?",(assertion_id,)):
            d=dict(x); ev=self.db.execute("SELECT * FROM canon_events WHERE command_id=?",(x["id"],)).fetchone(); d["canon_event"]=dict(ev) if ev else None; cmds.append(d)
        return {"source":src,"assertion":dict(a),"adjudications":adjs,"commands":cmds}
    def correct(self,event_id,kind,reason):
        allowed={"assignment_revoked","permission_removed","entity_merged","location_corrected","claim_downgraded","prior_event_superseded"}
        if kind not in allowed: raise ValueError("correction must be a compensating event")
        ident=sid("cor",event_id+kind+reason); self.db.execute("INSERT OR IGNORE INTO corrections(id,target_event_id,kind,reason,created_at) VALUES(?,?,?,?,?)",(ident,event_id,kind,reason,now())); self.db.commit(); return ident
    def compile_correction(self, correction_id, adjudicator="Captain"):
        row=self.db.execute("SELECT r.*,e.event_json,c.assertion_id,c.adjudication_id,c.id original_command_id,a.source_id,s.content_hash FROM corrections r JOIN canon_events e ON e.id=r.target_event_id JOIN commands c ON c.id=e.command_id JOIN assertions a ON a.id=c.assertion_id JOIN sources s ON s.id=a.source_id WHERE r.id=?",(correction_id,)).fetchone()
        if not row: raise KeyError(correction_id)
        original=json.loads(row["event_json"])["command"]; change=original["change"]; kind=row["kind"]
        if kind == "assignment_revoked": compensating={"change":"revoke-assignment","assignment_id":change["assignment"]["id"]}
        elif kind == "permission_removed": compensating={"change":"remove-permission","permission_id":change["permission"]["id"]}
        elif kind == "entity_merged": raise ValueError("entity merge correction requires an explicit target entity edit")
        elif kind == "location_corrected": raise ValueError("location correction requires an explicit corrected location edit")
        elif kind == "claim_downgraded": compensating={"change":"downgrade-claim","claim_id":change["claim"]["id"]}
        elif kind == "prior_event_superseded": compensating={"change":"supersede-event","event_id":row["target_event_id"]}
        else: raise ValueError("unsupported correction")
        ident=sid("cmd",correction_id+json.dumps(compensating,sort_keys=True)); payload={"type":"apply-canon-change","command_id":ident,"change":compensating,"provenance":{"source_id":row["source_id"],"source_hash":row["content_hash"],"assertion_id":row["assertion_id"],"adjudication_id":correction_id,"adjudicator":adjudicator,"adjudicated_at":now()}}
        key=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
        self.db.execute("INSERT OR IGNORE INTO commands(id,assertion_id,adjudication_id,idempotency_key,payload_json,status) VALUES(?,?,?,?,?,'compiled')",(ident,row["assertion_id"],row["adjudication_id"],key,json.dumps(payload,sort_keys=True))); self.db.execute("UPDATE corrections SET command_id=? WHERE id=?",(ident,correction_id)); self.db.commit(); return ident,payload

def serve(intake, host="127.0.0.1", port=4773):
    review_token=os.getenv("WORLD_INTAKE_REVIEW_TOKEN")
    if not review_token: raise RuntimeError("WORLD_INTAKE_REVIEW_TOKEN is required for adjudication service")
    decision_map={"approve":"approve","approve_with_edit":"amend","reject":"reject","defer":"defer","flavor_only":"flavor_only","mark_unverified":"unverified","link_existing":"link"}
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, payload, status=200):
            body=json.dumps(payload,default=lambda value: bytes(value).decode()).encode()
            self.send_response(status); self.send_header("Content-Type","application/json"); self.send_header("Content-Length",str(len(body))); self.send_header("Access-Control-Allow-Origin","*"); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            parsed=urlparse(self.path)
            if parsed.path == "/proposals":
                status=parse_qs(parsed.query).get("status",["pending"])[0]; status="defer" if status == "deferred" else status
                cards=intake.queue()
                if status != "all": cards=[card for card in cards if next(a for a in intake.assertions() if a["id"]==card["assertion_id"])["status"] == status]
                self.send_json({"proposals":cards}); return
            self.send_json({"error":"not found"},404)
        def do_POST(self):
            if urlparse(self.path).path != "/adjudications": self.send_json({"error":"not found"},404); return
            presented=self.headers.get("Authorization","").removeprefix("Bearer ")
            if not hmac.compare_digest(presented,review_token): self.send_json({"error":"Captain review authentication required"},401); return
            try:
                length=int(self.headers.get("Content-Length","0")); body=json.loads(self.rfile.read(length) or b"{}")
                action=decision_map[body["action"]]; assertion_id=body.get("proposal_id") or body["assertion_id"]
                edit=body.get("amended_command") if action == "amend" else ({"entity_id":body.get("linked_entity_id")} if action == "link" else None)
                adjudication_id=intake.review(assertion_id,action,edit=edit)
                response={"adjudication_id":adjudication_id,"decision":action,"canon_mutated":False}
                if action in {"approve","amend","unverified","link"}:
                    command_id,command=intake.compile(adjudication_id); response.update({"command_id":command_id,"command":command,"status":"awaiting-fleetcore-submission"})
                self.send_json(response,201)
            except (KeyError,ValueError,json.JSONDecodeError) as error: self.send_json({"error":str(error)},422)
        def do_OPTIONS(self):
            self.send_response(204); self.send_header("Access-Control-Allow-Origin","*"); self.send_header("Access-Control-Allow-Headers","Content-Type"); self.send_header("Access-Control-Allow-Methods","GET,POST,OPTIONS"); self.end_headers()
        def log_message(self, format, *args): pass
    server=HTTPServer((host,port),Handler)
    print(f"world-intake review API listening on http://{host}:{port}")
    try: server.serve_forever()
    finally: server.server_close()

def main():
    p=argparse.ArgumentParser(); p.add_argument("--db",default="world-intake.sqlite3"); sub=p.add_subparsers(dest="cmd",required=True)
    x=sub.add_parser("ingest"); x.add_argument("file"); x.add_argument("--author",default="unknown"); x.add_argument("--mission-context",default="")
    x=sub.add_parser("extract"); x.add_argument("source_id")
    x=sub.add_parser("queue"); x.add_argument("--source-id")
    x=sub.add_parser("review"); x.add_argument("assertion_id"); x.add_argument("decision",choices=sorted(DECISIONS)); x.add_argument("--adjudicator",default="Captain")
    x=sub.add_parser("provenance"); x.add_argument("assertion_id")
    x=sub.add_parser("serve"); x.add_argument("--host",default="127.0.0.1"); x.add_argument("--port",type=int,default=4773)
    a=p.parse_args(); w=Intake(a.db)
    if a.cmd=="ingest": print(w.ingest(Path(a.file).read_bytes(),a.author,mission_context=a.mission_context))
    elif a.cmd=="extract": print(json.dumps(w.extract(a.source_id),indent=2,default=str))
    elif a.cmd=="queue": print(json.dumps(w.queue(a.source_id),indent=2,default=str))
    elif a.cmd=="review": print(w.review(a.assertion_id,a.decision,a.adjudicator))
    elif a.cmd=="provenance": print(json.dumps(w.provenance(a.assertion_id),indent=2,default=lambda x: bytes(x).decode()))
    elif a.cmd=="serve": serve(w,a.host,a.port)
if __name__=="__main__": main()
