const apiBase = new URLSearchParams(location.search).get("api") || "/world-intake-api";
const list = document.querySelector("#proposalList");
const template = document.querySelector("#proposalTemplate");
const statusFilter = document.querySelector("#statusFilter");
const feedback = document.querySelector("#feedback");
const reviewToken = document.querySelector("#reviewToken");
let demoMode = false;
reviewToken.value=sessionStorage.getItem("worldIntakeReviewToken")||"";
reviewToken.addEventListener("change",()=>sessionStorage.setItem("worldIntakeReviewToken",reviewToken.value));

const demo = [{
  id:"assertion.demo-vance-scram", subject:"Recruit Vance", assertion_class:"assignment",
  proposed_change:"Assign Recruit Vance to the reactor scram watch (assignment only; no authority grant).",
  source_excerpt:"Vance will take the scram position when the reactor crew comes aboard.", confidence:0.91,
  existing_canon:{ entity_id:"crew.vance", roles:[], permissions:[] },
  conflicts:["Scram is an exclusive watch assignment; verify no active holder."], requires_individual_approval:true,
  proposed_command:{ type:"assign-role", entity_id:"crew.vance", role:"reactor-scram-watch", source_assertion_id:"assertion.demo-vance-scram" },
  provenance:{ source_id:"source.first-wave-reactor-crew", author:"Captain", received_at:"2026-07-14T00:00:00Z", content_hash:"sha256:demo", assertion_id:"assertion.demo-vance-scram" }
}];

function esc(value) { return String(value ?? "").replaceAll("&","&amp;").replaceAll("<","&lt;").replaceAll(">","&gt;").replaceAll('"',"&quot;"); }
function show(message,error=false) { feedback.textContent=message;feedback.classList.toggle("error",error);feedback.hidden=false;setTimeout(()=>feedback.hidden=true,5000); }
function normalize(payload) { return Array.isArray(payload) ? payload : payload.proposals || payload.items || []; }

async function load() {
  list.innerHTML='<p class="empty">Loading proposals…</p>';
  try {
    const response=await fetch(`${apiBase}/proposals?status=${encodeURIComponent(statusFilter.value)}`,{cache:"no-store"});
    if(!response.ok) throw new Error(`HTTP ${response.status}`);
    demoMode=false;render(normalize(await response.json()));setLink("API linked",true);
  } catch(error) {
    demoMode=true;render(demo);setLink("Demo fixture",false);show(`Intake API unavailable (${error.message}); review actions remain local and non-canonical.`,true);
  }
}
function setLink(text,live) { document.querySelector("#linkStatus").textContent=text;document.querySelector(".status").classList.toggle("is-live",live); }

function render(proposals) {
  document.querySelector("#queueCount").textContent=`${proposals.length} pending`;
  list.replaceChildren();
  if(!proposals.length) { list.innerHTML='<p class="empty">No proposals in this queue.</p>';return; }
  proposals.forEach(item => {
    const id=item.id||item.assertion_id;const node=template.content.firstElementChild.cloneNode(true);node.dataset.id=id;
    node.querySelector(".proposal-id").textContent=id;node.querySelector(".subject").textContent=item.subject||"—";
    node.querySelector(".class-tag").textContent=item.assertion_class;node.querySelector(".change").textContent=typeof item.proposed_change==="string"?item.proposed_change:JSON.stringify(item.proposed_change);
    node.querySelector(".excerpt").textContent=item.source_excerpt||item.supporting_source_excerpt;node.querySelector(".confidence").textContent=`${Math.round((item.confidence||0)*100)}%`;
    node.querySelector(".risk").textContent=item.requires_individual_approval ? "Individual approval required" : "Standard review";
    node.querySelector(".canon").textContent=JSON.stringify(item.existing_canon ?? null,null,2);
    const conflicts=node.querySelector(".conflicts");const conflictList=item.conflicts||[];
    conflicts.innerHTML=conflictList.length?conflictList.map(x=>`<li>${esc(typeof x==="string"?x:(x.detail||x.code||JSON.stringify(x)))}</li>`).join(""):'<li class="no-conflict">No conflict detected</li>';
    const command=JSON.stringify(item.proposed_command??item.proposed_fleetcore_command??null,null,2);node.querySelector(".command").value=command;node.querySelector(".amended-command").value=JSON.stringify(item.proposed_change?.value??item.proposed_change??null,null,2);
    node.querySelector(".provenance").innerHTML=Object.entries(item.provenance||{}).map(([k,v])=>`<dt>${esc(k)}</dt><dd>${esc(v)}</dd>`).join("");
    node._proposal=item;list.append(node);
  });
}

list.addEventListener("click", async event => {
  const button=event.target.closest("button[data-action]");if(!button)return;
  const card=button.closest(".proposal");const action=button.dataset.action;const panel=card.querySelector(".edit-panel");
  if(action==="approve_with_edit" && panel.hidden) { panel.hidden=false;card.querySelector(".link-field").hidden=true;card.querySelector(".amended-command").focus();return; }
  if(action==="link_existing" && (panel.hidden || card.querySelector(".link-field").hidden)) { panel.hidden=false;card.querySelector(".link-field").hidden=false;card.querySelector(".entity-link").focus();return; }
  let amended_command=null;
  if(action==="approve_with_edit") { try { amended_command=JSON.parse(card.querySelector(".amended-command").value); } catch { show("Amended value must be valid JSON.",true);return; } }
  const body={ proposal_id:card.dataset.id, action, amended_command, linked_entity_id:action==="link_existing"?card.querySelector(".entity-link").value.trim()||null:null };
  if(demoMode) { show(`Demo decision recorded locally: ${action}. Canon was not changed.`);card.remove();return; }
  button.disabled=true;
  try { const response=await fetch(`${apiBase}/adjudications`,{method:"POST",headers:{"Content-Type":"application/json","Authorization":`Bearer ${reviewToken.value}`},body:JSON.stringify(body)});if(!response.ok)throw new Error(`HTTP ${response.status}`);show(`Decision recorded: ${action}. Any approved command still passes through FleetCore.`);await load(); }
  catch(error) { show(`Decision was not recorded: ${error.message}`,true);button.disabled=false; }
});
document.querySelector("#refreshButton").addEventListener("click",load);statusFilter.addEventListener("change",load);load();
