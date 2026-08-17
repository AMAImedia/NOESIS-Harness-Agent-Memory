"""Dependency-free browser UI asset for the NOESIS control plane.

Patterns are borrowed from the NOESIS UI Contract v1, capability negotiation,
and local-first desktop control-plane shells; this asset contains presentation
only and performs no agent, model, filesystem, or session mutation.
"""

CONTROL_PLANE_HTML = r'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>NOESIS Control Plane</title>
<style>
:root{color-scheme:dark;font:16px system-ui,sans-serif;background:#0b1020;color:#e7ecff}
body{max-width:1060px;margin:0 auto;padding:2rem}h1{margin-bottom:.25rem}p{color:#aeb9d6}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:1rem}
.card{background:#151d35;border:1px solid #2b385e;border-radius:12px;padding:1rem;min-height:120px}
pre{white-space:pre-wrap;word-break:break-word;color:#b9f3cf}.status{font-weight:700;color:#7dd3fc}
small{color:#8e9ab9}button{background:#2563eb;color:#fff;border:0;border-radius:7px;padding:.55rem .8rem;cursor:pointer}button:disabled{background:#37415d;color:#93a0bd;cursor:not-allowed}
.model{border-top:1px solid #2b385e;padding:.7rem 0}.model strong{color:#fff}.badge{display:inline-block;border-radius:99px;padding:.15rem .45rem;margin:.2rem;background:#24554d;color:#b9f3cf;font-size:.8rem}.off{background:#493442;color:#f6b8c8}
</style></head>
<body>
<h1>NOESIS Control Plane</h1>
<p>Local, read-only observability surface. Model invocation and session mutation are intentionally not exposed here.</p>
<button id="refresh">Refresh</button> <span id="updated"><small>Not loaded</small></span>
<div class="grid">
<section class="card"><h2>Health</h2><div id="health" class="status">Loading…</div><pre id="health-detail"></pre></section>
<section class="card"><h2>Models & capabilities</h2><div id="models" class="status">Loading…</div><div id="model-list"></div><pre id="models-detail"></pre></section>
<section class="card"><h2>Sessions</h2><div class="status">Read-only inventory</div><p>No session mutation endpoint is enabled.</p><small>Session state remains in the local runtime boundary.</small></section>
</div>
<script>
const text=(x)=>JSON.stringify(x,null,2);
const esc=(x)=>String(x).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function renderModels(records){const root=document.getElementById('model-list');root.innerHTML='';if(!records.length){root.textContent='No verified models; selector unavailable.';return;}records.forEach(model=>{const caps=model.capabilities||{};const capabilities=['tools','vision','structured_output','streaming','long_context'];const badges=capabilities.map(k=>'<span class="badge '+(caps[k]?'':'off')+'">'+esc(k)+': '+(caps[k]?'on':'off')+'</span>').join('');const row=document.createElement('div');row.className='model';row.innerHTML='<strong>'+esc(model.id)+'</strong> <small>'+esc(model.provider)+' · '+esc(model.status)+'</small><div>'+badges+'</div><button disabled title="Model invocation is not exposed by P2-04">Invoke disabled</button>';root.appendChild(row);});}
async function load(path,target,detail){try{const r=await fetch(path,{cache:'no-store'});const data=await r.json();document.getElementById(target).textContent=data.status||'unknown';document.getElementById(detail).textContent=text(data.data||data.error||{});if(path==='/models')renderModels((data.data&&data.data.models)||[]);}catch(e){document.getElementById(target).textContent='unavailable';document.getElementById(detail).textContent='read failed: '+e.name;if(path==='/models')renderModels([]);}}
async function refresh(){await Promise.all([load('/health','health','health-detail'),load('/models','models','models-detail')]);document.getElementById('updated').textContent='Updated '+new Date().toLocaleTimeString();}
document.getElementById('refresh').addEventListener('click',refresh);refresh();
</script></body></html>'''

__all__ = ["CONTROL_PLANE_HTML"]
