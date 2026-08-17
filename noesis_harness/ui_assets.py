"""Self-contained local-first Web UI assets for the NOESIS control plane."""

CONTROL_PLANE_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOESIS Agent OS</title>
<style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;background:#0b1020;color:#e7ecff}
body{max-width:1120px;margin:0 auto;padding:2rem}h1{margin-bottom:.25rem}p{color:#aeb9d6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:1rem}.wide{grid-column:1/-1}
.card{background:#151d35;border:1px solid #2b385e;border-radius:12px;padding:1rem;min-height:120px}
pre{white-space:pre-wrap;word-break:break-word;color:#b9f3cf;max-height:280px;overflow:auto}.status{font-weight:700;color:#7dd3fc}
small{color:#8e9ab9}button{background:#2563eb;color:#fff;border:0;border-radius:7px;padding:.55rem .8rem;cursor:pointer;margin:.2rem}button:disabled{background:#37415d;color:#93a0bd;cursor:not-allowed}
input,textarea{background:#0e1530;border:1px solid #35436d;border-radius:7px;color:#fff;padding:.55rem;width:100%;box-sizing:border-box;margin:.25rem 0}.model{border-top:1px solid #2b385e;padding:.7rem 0}.model strong{color:#fff}.badge{display:inline-block;border-radius:99px;padding:.15rem .45rem;margin:.2rem;background:#24554d;color:#b9f3cf;font-size:.8rem}.off{background:#493442;color:#f6b8c8}
</style></head>
<body>
<h1>NOESIS Agent OS</h1>
<p>Local-first Hermes-style console. Session commands are versioned, bounded and approval-aware; model/tool output is treated as data and is never executed by the UI. No session mutation endpoint is enabled by default unless the server receives an explicit session store.</p>
<button id="refresh">Refresh</button> <span id="updated"><small>Not loaded</small></span>
<div class="grid">
<section class="card"><h2>Health</h2><div id="health" class="status">Loading…</div><pre id="health-detail"></pre></section>
<section class="card"><h2>Models & capabilities</h2><div id="models" class="status">Loading…</div><div id="model-list"></div><pre id="models-detail"></pre><small>Invoke disabled in the metadata surface; provider calls require the explicit versioned session and Gatekeeper path.</small></section>
<section class="card wide"><h2>Sessions</h2><h3>Interactive session</h3><div id="session-status" class="status">Session API capability is detected from the response.</div>
<label>Owner<input id="owner" value="local-user" maxlength="80"></label><button id="create-session">Create session</button><label>Session ID<input id="session-id" placeholder="created session id"></label><button id="resume-session">Resume</button>
<label>Message<textarea id="message" rows="3" maxlength="12000" placeholder="Send a bounded message to the local session ledger"></textarea></label><button id="send-message">Append message</button><pre id="session-detail">No session selected.</pre><pre id="event-stream"></pre></section>
</div>
<script>
const text=(x)=>JSON.stringify(x,null,2);const esc=(x)=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let sessionId='';
function renderModels(records){const root=document.getElementById('model-list');root.innerHTML='';if(!records.length){root.textContent='No verified models; selector unavailable.';return;}records.forEach(model=>{const caps=model.capabilities||{};const keys=['tools','vision','structured_output','streaming','long_context'];const badges=keys.map(k=>'<span class="badge '+(caps[k]?'':'off')+'">'+esc(k)+': '+(caps[k]?'on':'off')+'</span>').join('');const row=document.createElement('div');row.className='model';row.innerHTML='<strong>'+esc(model.id)+'</strong> <small>'+esc(model.provider)+' · '+esc(model.status)+'</small><div>'+badges+'</div><button disabled>Invoke disabled</button>';root.appendChild(row);});}
async function load(path,target,detail){try{const r=await fetch(path,{cache:'no-store'});const data=await r.json();document.getElementById(target).textContent=data.status||'unknown';document.getElementById(detail).textContent=text(data.data||data.error||{});if(path==='/models')renderModels((data.data&&data.data.models)||[]);}catch(e){document.getElementById(target).textContent='unavailable';document.getElementById(detail).textContent='read failed: '+e.name;if(path==='/models')renderModels([]);}}
async function refresh(){await Promise.all([load('/health','health','health-detail'),load('/models','models','models-detail')]);document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();}
async function createSession(){const r=await fetch('/api/sessions',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({owner:document.getElementById('owner').value})});const data=await r.json();if(data.ok){sessionId=data.data.session.session_id;document.getElementById('session-id').value=sessionId;document.getElementById('session-status').textContent='Session '+sessionId+' ready';await resumeSession();}else document.getElementById('session-detail').textContent=text(data.error);}
async function resumeSession(){sessionId=document.getElementById('session-id').value.trim();if(!sessionId)return;const r=await fetch('/api/sessions/'+encodeURIComponent(sessionId),{cache:'no-store'});const data=await r.json();document.getElementById('session-detail').textContent=text(data.data||data.error);if(data.ok){const ev=await fetch('/api/sessions/'+encodeURIComponent(sessionId)+'/events',{cache:'no-store'});document.getElementById('event-stream').textContent=await ev.text();}}
async function sendMessage(){if(!sessionId){document.getElementById('session-detail').textContent='Create or resume a session first.';return;}const content=document.getElementById('message').value;if(!content.trim())return;const r=await fetch('/api/sessions/'+encodeURIComponent(sessionId)+'/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({role:'user',content})});const data=await r.json();document.getElementById('session-detail').textContent=text(data);document.getElementById('message').value='';await resumeSession();}
document.getElementById('refresh').addEventListener('click',refresh);document.getElementById('create-session').addEventListener('click',createSession);document.getElementById('resume-session').addEventListener('click',resumeSession);document.getElementById('send-message').addEventListener('click',sendMessage);refresh();
</script></body></html>'''

__all__ = ["CONTROL_PLANE_HTML"]
