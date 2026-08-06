const $=id=>document.getElementById(id),controls=["a","b","c"],TAU=Math.PI*2;
const regions=["radial","bilateral","segmented","colonial","annular","arborescent"],colors=["#55ded1","#8cb9ff","#efae4b","#b59cff","#ef7184","#8dd878"];
const clamp=(n,a=0,b=1)=>Math.max(a,Math.min(b,n)),fract=n=>n-Math.floor(n);
let learnedAtlas=null,activeSpace=null;
function nav(){return controls.map(id=>+$(id).value/1000)}
function navigate(){
 let coordinate=nav(),strategy=$("strategy").value;
 if(strategy!=="umap"||!activeSpace)return{v:coordinate,coordinate,strategy:"authored",specimen:null};
 let nearby=activeSpace.specimens.map(specimen=>({specimen,d2:specimen.chart.reduce((sum,n,i)=>sum+(n-coordinate[i])**2,0)})).sort((a,b)=>a.d2-b.d2).slice(0,12);
 let bandwidth=Math.max(nearby[nearby.length-1].d2*.45,.00008),weights=nearby.map(item=>Math.exp(-item.d2/bandwidth)),total=weights.reduce((a,b)=>a+b,0);weights=weights.map(w=>w/total);
 let blend=key=>nearby[0].specimen[key].map((_,i)=>nearby.reduce((sum,item,j)=>sum+item.specimen[key][i]*weights[j],0));
 let descriptor=blend("descriptor"),v=blend("v"),scores=descriptor.slice(11,17),ranked=scores.map((score,i)=>({i,score})).sort((a,b)=>b.score-a.score);
 let phenotype={f:{centers:Math.max(1,Math.round(descriptor[0])),symmetry:Math.max(3,Math.round(descriptor[1])),depth:Math.max(1,Math.round(descriptor[2])),branch:descriptor[3],fusion:descriptor[4],segments:Math.max(3,Math.round(descriptor[5])),curl:descriptor[6],spread:descriptor[7],membrane:descriptor[8],breakage:descriptor[9]},r:{primary:ranked[0],secondary:ranked[1],boundary:clamp(descriptor[10])}};
 return{v,coordinate,strategy:"umap",specimen:nearby[0].specimen,distance:Math.sqrt(nearby[0].d2),phenotype,anchors:nearby.map((item,i)=>({id:item.specimen.atlasId,weight:weights[i]}))};
}
function fields([a,b,c]){return{centers:1+Math.floor(fract(a*7+b*11+c*13)*5),symmetry:3+Math.floor(fract(a*17+b*5+c*3)*9),depth:1+Math.floor(fract(a*5+b*19+c*7)*4),branch:fract(a*13+b*23+c*29),fusion:fract(a*31+b*7+c*17),segments:3+Math.floor(fract(a*37+b*13+c*5)*10),curl:(fract(a*11+b*41+c*19)-.5)*1.8,spread:.45+fract(a*3+b*17+c*43)*.55,membrane:fract(a*47+b*2+c*23),breakage:fract(a*29+b*31+c*7)}}
function classify(v){let ranked=regions.map((_,i)=>({i,score:.5+.5*Math.sin(TAU*(v[0]*(i+2)+v[1]*(i*3+1)+v[2]*(i*5+2)))})).sort((a,b)=>b.score-a.score);return{primary:ranked[0],secondary:ranked[1],boundary:clamp(1-(ranked[0].score-ranked[1].score)*6)}}
function graph(v,phenotype=null){
 let f=phenotype?.f||fields(v),r=phenotype?.r||classify(v),type=r.primary.i,nodes=[],edges=[],add=(x,y,role="joint",radius=7)=>{nodes.push({id:nodes.length,x,y,role,radius});return nodes.length-1},link=(a,b,level=0,membrane=false)=>edges.push({a,b,level,membrane}),root=add(0,0,"core",38);
 if(type===0)for(let arm=0;arm<f.symmetry;arm++){let prev=root,ang=arm*TAU/f.symmetry+f.breakage*.18;for(let d=1;d<=f.depth+2;d++){ang+=f.curl*.13;let id=add(Math.cos(ang)*d*58*f.spread,Math.sin(ang)*d*58*f.spread,d===f.depth+2?"organ":"joint",d===f.depth+2?11:7);link(prev,id,d);if(d>1&&f.branch>.35){let side=add(nodes[id].x+Math.cos(ang+1.1)*(30+25*f.branch),nodes[id].y+Math.sin(ang+1.1)*(30+25*f.branch),"tip",5);link(id,side,d+1)}prev=id}}
 if(type===1){nodes[root].x=-f.segments*24;let prev=root;for(let i=1;i<=f.segments;i++){let id=add((i-f.segments/2)*48,Math.sin(i*1.2+v[0]*TAU)*22,"segment",12);link(prev,id);prev=id;for(let side of[-1,1]){let hip=add(nodes[id].x+side*24,nodes[id].y+side*20),foot=add(nodes[id].x+side*(55+f.spread*50),nodes[id].y+side*(55+f.branch*70),"organ",9);link(id,hip,1);link(hip,foot,2)}}}
 if(type===2){nodes[root].x=-260;let prev=root;for(let i=1;i<=f.segments;i++){let id=add(-260+i*520/f.segments,Math.sin(i*.9+v[2]*8)*50,"segment",18);link(prev,id,0,f.membrane>.65);if(i%2){let fin=add(nodes[id].x,nodes[id].y+(i%4===1?1:-1)*(50+f.spread*60),"organ",8);link(id,fin,1)}prev=id}}
 if(type===3){let centers=[root];for(let i=1;i<f.centers+4;i++){let ang=i*2.399+v[1]*TAU,rad=55+i*38*f.spread,id=add(Math.cos(ang)*rad,Math.sin(ang)*rad,"core",20);link(centers[Math.floor((i-1)*f.fusion)%centers.length],id,0,f.membrane>.55);centers.push(id)}for(let i=2;i<centers.length;i++)if(f.fusion>.45)link(centers[i],centers[Math.floor(i*.4)],1)}
 if(type===4){let count=f.symmetry+f.centers*2,ring=[];for(let i=0;i<count;i++)ring.push(add(Math.cos(i*TAU/count)*220*f.spread,Math.sin(i*TAU/count)*150*f.spread,"segment",11));ring.forEach((id,i)=>{link(id,ring[(i+1)%count],0,true);if(i%2===0)link(root,id,1,f.membrane>.35)})}
 if(type===5){nodes[root].y=260;let frontier=[root];for(let d=1;d<=f.depth+2;d++){let next=[];for(let parent of frontier){let count=2+(f.branch>.55?1:0);for(let k=0;k<count;k++){let ang=-Math.PI/2+(k-(count-1)/2)*(.55+f.spread*.5)+(fract(v[0]*31+v[1]*17+d*k*.37)-.5)*f.breakage*.3,id=add(nodes[parent].x+Math.cos(ang)*(65+d*8),nodes[parent].y+Math.sin(ang)*(65+d*8),d===f.depth+2?"organ":"joint",d===f.depth+2?9:7);link(parent,id,d,f.membrane>.72);next.push(id)}}frontier=next}}
 return{schema:"monad.beastscapeSpecimen.v0.1",v,f,r,type,region:regions[type],nodes,edges,id:`beast-${v.map(n=>Math.round(n*999)).join("-")}`};
}
const project=(n,w,h)=>[w/2+n.x,h/2+n.y];
function renderGraph(canvas,g,flesh){let x=canvas.getContext("2d"),w=canvas.width,h=canvas.height,bg=x.createRadialGradient(w/2,h/2,10,w/2,h/2,w*.65),color=colors[g.type];bg.addColorStop(0,flesh?"#183b3e":"#0b2024");bg.addColorStop(1,"#020609");x.fillStyle=bg;x.fillRect(0,0,w,h);if(flesh)for(let e of g.edges.filter(e=>e.membrane)){let a=project(g.nodes[e.a],w,h),b=project(g.nodes[e.b],w,h);x.strokeStyle=color+"35";x.lineWidth=35;x.beginPath();x.moveTo(...a);x.lineTo(...b);x.stroke()}for(let e of g.edges){let a=project(g.nodes[e.a],w,h),b=project(g.nodes[e.b],w,h);x.strokeStyle=flesh?color:(e.level?"#719f9b":"#55ded1");x.lineWidth=flesh?Math.max(5,24-e.level*3):Math.max(2,7-e.level);x.lineCap="round";x.shadowBlur=flesh?12:0;x.shadowColor=color;x.beginPath();x.moveTo(...a);x.lineTo(...b);x.stroke()}x.shadowBlur=0;for(let n of g.nodes){let p=project(n,w,h),rad=flesh?n.radius*1.25:Math.max(4,n.radius*.45);x.fillStyle=n.role==="organ"?"#efae4b":n.role==="core"?(flesh?"#235f5d":"#102c2d"):color;x.strokeStyle=flesh?"#9ce0d3":"#efae4b";x.lineWidth=2;x.beginPath();x.arc(...p,rad,0,TAU);x.fill();x.stroke();if(flesh&&n.role==="organ"){x.fillStyle="#071014";x.beginPath();x.arc(p[0]+2,p[1],rad*.45,0,TAU);x.fill()}}}
function renderFoundry(){if(!activeSpace)return;let e=activeSpace.evidence;$("spaceHypothesis").textContent=activeSpace.hypothesis;$("spaceOperations").textContent=activeSpace.operations.join(" → ");$("spaceSpecimens").textContent=e.specimens;$("spaceTopologies").textContent=`${e.topologies}/6`;$("spaceTransitions").textContent=`${Math.round(e.transitionDensity*100)}%`;$("spaceValidity").textContent=e.validity}
function render(){let selection=navigate(),v=selection.v,g=graph(v,selection.phenotype);g.navigationCoordinate=selection.coordinate;g.navigationStrategy=selection.strategy;g.beastscapeId=activeSpace?.id||"authored";if(selection.specimen){g.atlasId=selection.specimen.atlasId;g.id=`${activeSpace.id}-${selection.coordinate.map(n=>Math.round(n*1000)).join("-")}`;g.chartDistance=selection.distance;g.anchors=selection.anchors}controls.forEach((id,i)=>$(id+"Out").textContent=Math.round(selection.coordinate[i]*1000));renderGraph($("skeleton"),g,false);renderGraph($("organism"),g,true);$("region").textContent=regions[g.type];$("transition").textContent=g.r.boundary>.28?`boundary with ${regions[g.r.secondary.i]} · ${Math.round(g.r.boundary*100)}%`:"stable local region";$("coordinate").textContent=selection.coordinate.map(n=>n.toFixed(3)).join(" · ");$("specimen").textContent=`SPECIMEN ${g.id}`;$("reading").textContent=selection.specimen?`${activeSpace.name} · ${g.nodes.length} nodes · ${g.edges.length} relations · 12-sounding continuous decoder`:`${g.nodes.length} nodes · ${g.edges.length} relations · authored projection`;history.replaceState(null,"",`?space=${activeSpace?.id||""}&strategy=${selection.strategy}&a=${Math.round(selection.coordinate[0]*1000)}&b=${Math.round(selection.coordinate[1]*1000)}&c=${Math.round(selection.coordinate[2]*1000)}`);window.currentGraph=g}
function evidence(kind,g=window.currentGraph){let data=JSON.parse(localStorage.getItem("beastscapeEvidence")||"[]");data.push({kind,coordinate:g.navigationCoordinate||g.v,region:regions[g.type],specimen:g.id,beastscape:g.beastscapeId,strategy:g.navigationStrategy,at:new Date().toISOString()});localStorage.setItem("beastscapeEvidence",JSON.stringify(data.slice(-200)))}
controls.forEach(id=>$(id).addEventListener("input",render));$("strategy").addEventListener("change",render);$("space").addEventListener("change",()=>{activeSpace=learnedAtlas.spaces.find(space=>space.id===$("space").value);renderFoundry();render();evidence("beastscape-selected")});$("drift").onclick=()=>{controls.forEach(id=>$(id).value=clamp(+$(id).value+Math.round((Math.random()-.5)*36),0,1000));render()};$("landmark").onclick=()=>{let g=window.currentGraph,v=[...(g.navigationCoordinate||g.v)],strategy=g.navigationStrategy,space=g.beastscapeId;evidence("landmark",g);let button=document.createElement("button");button.className="mark";button.innerHTML=`${regions[g.type]}<small>${g.id}</small>`;button.onclick=()=>{if(learnedAtlas){$("space").value=space;activeSpace=learnedAtlas.spaces.find(item=>item.id===space)||activeSpace;renderFoundry()}$("strategy").value=strategy;controls.forEach((id,i)=>$(id).value=Math.round(v[i]*1000));render();evidence("revisit")};let box=$("landmarks");if(box.querySelector(".dim"))box.innerHTML="";box.append(button)};
let q=new URLSearchParams(location.search);controls.forEach(id=>{if(q.has(id))$(id).value=q.get(id)});if(q.has("strategy"))$("strategy").value=q.get("strategy");render();
fetch("umap-atlas.v1.json?v=3").then(response=>{if(!response.ok)throw new Error(`HTTP ${response.status}`);return response.json()}).then(atlas=>{if(atlas.schema!=="monad.beastscapeFoundry.v0.1"||!atlas.spaces?.[0]?.specimens?.[0]?.descriptor)throw new Error("wrong Foundry schema");learnedAtlas=atlas;$("space").innerHTML=atlas.spaces.map(space=>`<option value="${space.id}">${space.name}</option>`).join("");let requested=q.get("space");activeSpace=atlas.spaces.find(space=>space.id===requested)||atlas.spaces.find(space=>space.id===atlas.defaultSpace)||atlas.spaces[0];$("space").value=activeSpace.id;renderFoundry();$("mapStatus").textContent=`Independent ${atlas.method} chart ready · 12-anchor local decoder`;$("strategy").value=q.get("strategy")||"umap";render()}).catch(error=>{$("mapStatus").textContent=`Foundry unavailable · authored navigation retained (${error.message})`;$("strategy").value="authored";render()});

function download(name,blob){let a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)}
$("exportSpecimen").onclick=()=>download(`${window.currentGraph.id}.json`,new Blob([JSON.stringify(window.currentGraph,null,2)],{type:"application/json"}));
$("exportImage").onclick=()=>$("organism").toBlob(blob=>download(`${window.currentGraph.id}.png`,blob));

// --- Beastscape Lab, Phase 1 -----------------------------------------
// Instrumented mode over the SAME engine/state above (navigate/graph/
// activeSpace/window.currentGraph). Every experiment lives in its own
// localStorage bucket and is never written into umap-atlas.v1.json or
// any other canonical file -- "canonical" here already means "static,
// generated offline, read-only from the browser," so branching just
// means "a separate bucket of Lab annotations," not real copy-on-write
// data infrastructure. See docs/architecture/beastspec-design-v0.1.md
// for the fuller design this Phase 1 slice is deliberately smaller than.
const LAB_SCHEMA="monad.beastscapeLab.v0.1",LAB_KEY="beastscapeLab.v1";
function loadLab(){try{let data=JSON.parse(localStorage.getItem(LAB_KEY)||"");if(data.schema!==LAB_SCHEMA)throw 0;return data}catch{return{schema:LAB_SCHEMA,experiments:[],active_experiment_id:null}}}
function saveLab(){localStorage.setItem(LAB_KEY,JSON.stringify(lab))}
let lab=loadLab();
function currentExperiment(){return lab.experiments.find(e=>e.id===lab.active_experiment_id)||null}
function activeBeast(){let exp=currentExperiment();return exp&&exp.active_beast_key?exp.beasts[exp.active_beast_key]:null}
function createExperiment(name){
 let exp={id:`exp_${Date.now().toString(36)}${Math.floor(Math.random()*1e4).toString(36)}`,name:(name||"").trim()||`Experiment ${lab.experiments.length+1}`,status:"draft",created_at:new Date().toISOString(),updated_at:new Date().toISOString(),beasts:{},active_beast_key:null};
 lab.experiments.push(exp);lab.active_experiment_id=exp.id;saveLab();renderLabExperiments();renderLab();return exp;
}
// Reuses the same chart-distance math navigate() already computes for the
// continuous decoder, just exposed as a visible list instead of only
// feeding an internal blend.
function neighborsOf(space,specimen,k=6){
 if(!space||!specimen)return[];
 return space.specimens.filter(s=>s.atlasId!==specimen.atlasId)
  .map(s=>({specimen:s,distance:Math.sqrt(s.chart.reduce((sum,n,i)=>sum+(n-specimen.chart[i])**2,0))}))
  .sort((a,b)=>a.distance-b.distance).slice(0,k)
  .map(item=>({...item,reason:item.specimen.region===specimen.region?`same region · ${specimen.region}`:`bridges ${specimen.region} → ${item.specimen.region}`}));
}
function findSpecimen(spaceId,atlasId){return learnedAtlas?.spaces.find(s=>s.id===spaceId)?.specimens.find(s=>s.atlasId===atlasId)||null}
function beastKeyFor(selection){return selection.specimen?`${activeSpace.id}:${selection.specimen.atlasId}`:`authored:${selection.coordinate.map(n=>n.toFixed(3)).join(",")}`}
function inspectInLab(){
 let exp=currentExperiment();if(!exp)return;
 let selection=navigate(),g=window.currentGraph,key=beastKeyFor(selection),beast=exp.beasts[key];
 if(!beast)beast={beast_id:key,identity:{name:"",summary:""},notes:"",ratings:{coherence:3,distinctiveness:3,desire_to_continue:3},provenance:{source:"human"},created_at:new Date().toISOString()};
 beast.generated={space:activeSpace?.id||null,space_name:activeSpace?.name||"authored (no Foundry space)",atlasId:selection.specimen?.atlasId||null,region:g.region,strategy:selection.strategy,coordinate:selection.coordinate.map(n=>+n.toFixed(4)),nodes:g.nodes.length,edges:g.edges.length};
 beast.updated_at=new Date().toISOString();
 exp.beasts[key]=beast;exp.active_beast_key=key;exp.updated_at=new Date().toISOString();
 saveLab();renderLab();evidence("lab-inspect");
}
function persistActiveBeast(){let exp=currentExperiment();if(!exp||!exp.active_beast_key)return;exp.updated_at=new Date().toISOString();exp.beasts[exp.active_beast_key].updated_at=exp.updated_at;saveLab()}
function renderLabExperiments(){
 let select=$("labExperimentSelect");
 select.innerHTML=`<option value="">— none —</option>`+lab.experiments.map(e=>`<option value="${e.id}">${e.name} · ${e.status}</option>`).join("");
 select.value=lab.active_experiment_id||"";
}
function renderLab(){
 let exp=currentExperiment(),beast=activeBeast();
 $("labEmpty").hidden=!!exp;
 $("labBeast").hidden=!beast;
 if(!exp||!beast)return;
 let gen=beast.generated;
 $("labGenerated").innerHTML=`<div><dt>Region</dt><dd>${gen.region}</dd></div><div><dt>Passage</dt><dd>${gen.strategy}</dd></div><div><dt>Foundry space</dt><dd>${gen.space_name}</dd></div><div><dt>Atlas id</dt><dd>${gen.atlasId||"—"}</dd></div><div><dt>Coordinate</dt><dd>${gen.coordinate.join(" · ")}</dd></div><div><dt>Structure</dt><dd>${gen.nodes} nodes · ${gen.edges} relations</dd></div>`;
 $("labName").value=beast.identity.name;$("labNotes").value=beast.notes;
 $("labRateCoherence").value=beast.ratings.coherence;$("labRateCoherenceOut").textContent=beast.ratings.coherence;
 $("labRateDistinct").value=beast.ratings.distinctiveness;$("labRateDistinctOut").textContent=beast.ratings.distinctiveness;
 $("labRateContinue").value=beast.ratings.desire_to_continue;$("labRateContinueOut").textContent=beast.ratings.desire_to_continue;
 let list=$("labNeighbors");
 if(gen.strategy!=="umap"||!gen.atlasId){
  $("labNeighborNote").textContent="(needs Continuous UMAP Passage)";list.innerHTML="";
 }else{
  $("labNeighborNote").textContent="";
  let space=learnedAtlas.spaces.find(s=>s.id===gen.space),specimen=findSpecimen(gen.space,gen.atlasId);
  let neighbors=neighborsOf(space,specimen,6);
  list.innerHTML=neighbors.map(n=>`<li><b>${n.specimen.atlasId}</b> · score ${(1-Math.min(1,n.distance)).toFixed(2)} · distance ${n.distance.toFixed(3)}<span>${n.reason}</span></li>`).join("")||"<li>No other specimens in this space.</li>";
 }
 $("labStatus").textContent=`${exp.name} · ${exp.status} · ${Object.keys(exp.beasts).length} beast(s) recorded`;
}
$("labToggle").onclick=()=>{let panel=$("lab"),hidden=!panel.hidden;panel.hidden=hidden;$("labToggle").classList.toggle("active",!hidden)};
$("labNewExperiment").onclick=()=>{createExperiment($("labNewExperimentName").value);$("labNewExperimentName").value=""};
$("labExperimentSelect").addEventListener("change",()=>{lab.active_experiment_id=$("labExperimentSelect").value||null;saveLab();renderLab()});
$("labInspect").onclick=inspectInLab;
$("labName").addEventListener("input",()=>{let b=activeBeast();if(!b)return;b.identity.name=$("labName").value;b.provenance.source="human";persistActiveBeast()});
$("labNotes").addEventListener("input",()=>{let b=activeBeast();if(!b)return;b.notes=$("labNotes").value;b.provenance.source="human";persistActiveBeast()});
for(let[id,key]of[["labRateCoherence","coherence"],["labRateDistinct","distinctiveness"],["labRateContinue","desire_to_continue"]])
 $(id).addEventListener("input",()=>{let b=activeBeast();if(!b)return;b.ratings[key]=+$(id).value;$(id+"Out").textContent=$(id).value;persistActiveBeast()});
$("labDiscard").onclick=()=>{let exp=currentExperiment();if(!exp)return;if(!confirm(`Discard experiment "${exp.name}"? This only removes Lab annotations, never the canonical atlas.`))return;lab.experiments=lab.experiments.filter(e=>e.id!==exp.id);lab.active_experiment_id=lab.experiments[0]?.id||null;saveLab();renderLabExperiments();renderLab()};
$("labPromote").onclick=()=>{let exp=currentExperiment();if(!exp)return;exp.status="promoted";exp.updated_at=new Date().toISOString();saveLab();renderLabExperiments();renderLab();evidence("lab-promote")};
renderLabExperiments();renderLab();
const workbench="/captain-workbench-api";let enhancedUrl="";
const activityFacts=[];let activityKeys=new Set(),currentJobId="",lastObservedAt=0,lastPollAt=0;
function addActivity(stage,message,at=new Date().toISOString(),source="browser"){
 let key=`${stage}|${at}|${message}`;if(activityKeys.has(key))return;activityKeys.add(key);activityFacts.push({stage,message,at,source});lastObservedAt=new Date(at).getTime()||Date.now();
 let log=$("activityLog");log.innerHTML="";activityFacts.slice(-4).forEach((fact,index,list)=>{let item=document.createElement("li");if(index===list.length-1)item.className="current";let time=new Date(fact.at);item.innerHTML=`<b>${Number.isNaN(time.getTime())?"observed":time.toLocaleTimeString([], {hour:"2-digit",minute:"2-digit",second:"2-digit"})}</b><span></span>`;item.querySelector("span").textContent=fact.message;log.append(item)});
}
function setActivity(state,message,{at=new Date().toISOString(),terminal=false,failed=false,stage="browser_observation",source="browser"}={}){
 let panel=$("captainActivity");panel.hidden=false;panel.classList.toggle("terminal",terminal);panel.classList.toggle("failed",failed);$("activityState").textContent=state;$("activityTime").textContent=`last observed ${new Date(at).toLocaleTimeString()}`;$("enhanceStatus").textContent=message;addActivity(stage,message,at,source);
}
function resetActivity(){activityFacts.length=0;activityKeys=new Set();currentJobId="";lastObservedAt=lastPollAt=Date.now();$("activityLog").innerHTML="";$("captainActivity").className="captainActivity";$("captainActivity").hidden=false;$("activityJob").textContent="—"}
function observeJob(job){currentJobId=job.id;$("activityJob").textContent=job.id;$("activityEngine").textContent=job.engine==="codex"?"GPT Live Captain":"Gemini";$("activityVisibility").textContent=job.engine==="codex"?"local orchestration · remote generation":"remote request/response only";for(let fact of job.observations||[])addActivity(fact.stage,fact.message,fact.observed_at,fact.source);let cancelled=job.status==="cancelled",terminal=job.status==="succeeded"||cancelled,failed=job.status==="failed";setActivity(cancelled?"Local run cancelled":failed?"Failed":job.status==="succeeded"?"Artifact reported ready":job.status==="queued"?"Queued locally":"Remote generation · telemetry dark",job.note||`Job state: ${job.status}`,{at:job.updated_at,terminal,failed,stage:`job_${job.status}`,source:"job_receipt"});$("cancelRun").hidden=terminal||failed}
setInterval(()=>{if($("captainActivity").hidden)return;let seconds=stamp=>stamp?Math.max(0,Math.floor((Date.now()-stamp)/1000)):null,age=seconds(lastObservedAt),poll=seconds(lastPollAt);$("activityAge").textContent=age===null?"—":`${age}s`;$("pollAge").textContent=poll===null?"—":poll<5?`live · ${poll}s`:`stale · ${poll}s`},1000);
async function jsonResponse(response){let text=await response.text();if(!text)throw new Error("Captain pipeline is offline.");try{return JSON.parse(text)}catch{throw new Error(`Captain pipeline returned an unreadable response (${response.status}).`)}}
async function pollJob(id,specimenId){for(let attempt=0;attempt<90;attempt++){await new Promise(resolve=>setTimeout(resolve,2000));let response=await fetch(`${workbench}/jobs/${id}`),body=await jsonResponse(response);lastPollAt=Date.now();if(!response.ok)throw new Error(body.error||"Could not read Captain job.");let job=body.job;observeJob(job);if(job.status==="cancelled")return;if(job.status==="failed")throw new Error(job.note);if(job.status==="succeeded"){setActivity("Retrieving artifact","Workbench reports an artifact; requesting its bytes.",{stage:"artifact_fetch_started"});let imageResponse=await fetch(`${workbench}/jobs/${id}/image`);if(!imageResponse.ok)throw new Error("Enhanced image could not be retrieved.");let blob=await imageResponse.blob();if(enhancedUrl)URL.revokeObjectURL(enhancedUrl);enhancedUrl=URL.createObjectURL(blob);$("enhancedImage").src=enhancedUrl;$("downloadEnhanced").href=enhancedUrl;$("downloadEnhanced").download=`${specimenId}-captain.jpg`;$("enhanceResult").hidden=false;setActivity("Complete",`Image received by browser · ${Math.round(blob.size/1024)} KB.`,{terminal:true,stage:"artifact_received"});$("cancelRun").hidden=true;evidence("captain-enhancement");return}}throw new Error("No terminal job state was observed before polling ended.")}
$("cancelRun").onclick=async()=>{if(!currentJobId)return;$("cancelRun").disabled=true;setActivity("Cancellation requested","Sending operator cancellation to the Workbench.",{stage:"cancel_requested"});try{let response=await fetch(`${workbench}/jobs/${currentJobId}/cancel`,{method:"POST"}),body=await jsonResponse(response);lastPollAt=Date.now();if(!response.ok)throw new Error(body.error||"Cancellation failed.");observeJob(body.job)}catch(error){setActivity("Cancel control failed",error.message,{failed:true,stage:"cancel_failure"})}finally{$("cancelRun").disabled=false}};
$("enhance").onclick=async()=>{let button=$("enhance"),g=window.currentGraph,engine=$("engine").value;button.disabled=true;$("cancelRun").hidden=true;$("activityEngine").textContent=engine==="codex"?"GPT Live Captain":"Gemini";$("enhanceResult").hidden=true;resetActivity();$("activityEngine").textContent=engine==="codex"?"GPT Live Captain":"Gemini";$("activityVisibility").textContent=engine==="codex"?"local orchestration · remote generation":"remote request/response only";setActivity("Preparing request","Browser is encoding the visible structural schematic.",{stage:"schematic_encoding"});try{let schematic=$("skeleton").toDataURL("image/png");setActivity("Submitting request",`Sending the packet to ${engine==="codex"?"GPT Live Captain":"Gemini"}.`,{stage:"request_submitting"});let response=await fetch(`${workbench}/jobs`,{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({recipe:g,schematic_png:schematic,engine})}),body=await jsonResponse(response);lastPollAt=Date.now();if(!response.ok)throw new Error(body.error||"Captain did not accept the specimen.");observeJob(body.job);$("cancelRun").hidden=false;await pollJob(body.job.id,g.id)}catch(error){setActivity("Failed",error.message,{failed:true,stage:"browser_failure"});}finally{button.disabled=false;$("cancelRun").hidden=true}};
