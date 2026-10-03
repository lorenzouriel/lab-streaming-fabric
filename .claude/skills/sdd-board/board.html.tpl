<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Board __FEATURE__</title>
<style>
:root{--bg:#fff;--fg:#1a1a1a;--card:#f4f5f7;--line:#e2e4e8;--mut:#666;--panel:#fff;--code:#eceef1;--shadow:rgba(0,0,0,.18)}
@media(prefers-color-scheme:dark){:root{--bg:#141414;--fg:#eee;--card:#222;--line:#333;--mut:#9a9a9a;--panel:#1c1c1c;--code:#2b2b2b;--shadow:rgba(0,0,0,.6)}}
*{box-sizing:border-box}
body{margin:0;padding:16px;background:var(--bg);color:var(--fg);font:14px/1.45 system-ui,sans-serif}
header{display:flex;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:12px}
h1{font-size:18px;margin:0}
.prog{flex:1;min-width:140px;max-width:320px;height:6px;background:var(--line);border-radius:3px;overflow:hidden}
.prog>i{display:block;height:100%;background:#22c55e}
.mut{color:var(--mut);font-size:12px}
.board{display:grid;grid-template-columns:repeat(6,minmax(190px,1fr));gap:12px;overflow-x:auto;padding-bottom:8px}
.col h2{font-size:12px;text-transform:uppercase;letter-spacing:.04em;border-bottom:3px solid;padding-bottom:4px;margin:0 0 8px}
.col h2 i{color:var(--mut);font-weight:400;font-style:normal}
.card{display:block;width:100%;text-align:left;background:var(--card);color:inherit;border:1px solid transparent;border-radius:6px;padding:8px;margin-bottom:8px;cursor:pointer;font:inherit}
.card:hover,.card:focus-visible{border-color:var(--mut);outline:none}
.card.sel{border-color:#3b82f6}
.card b{font-size:12px}.card .t{margin-top:2px}
.meta{display:flex;gap:8px;flex-wrap:wrap;margin-top:6px;color:var(--mut);font-size:12px}
.wait{color:#ef4444}
.bar{height:4px;background:var(--line);border-radius:2px;margin-top:6px;overflow:hidden}
.bar>i{display:block;height:100%;background:#3b82f6}
#veil{position:fixed;inset:0;background:var(--shadow);display:none}
#veil.on{display:block}
aside{position:fixed;top:0;right:0;bottom:0;width:min(560px,100%);background:var(--panel);border-left:1px solid var(--line);transform:translateX(100%);transition:transform .15s;overflow-y:auto;padding:16px 16px 40px}
aside.on{transform:none;box-shadow:-8px 0 24px var(--shadow)}
aside .top{display:flex;justify-content:space-between;align-items:center;gap:8px}
aside h3{font-size:17px;margin:8px 0 12px}
aside h4{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut);margin:18px 0 6px}
.pill{display:inline-block;padding:1px 8px;border-radius:10px;font-size:12px;color:#fff}
.x{background:none;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:2px 10px;cursor:pointer;font:inherit}
.chips{display:flex;gap:6px;flex-wrap:wrap}
.chip{background:var(--card);border:1px solid var(--line);color:inherit;border-radius:12px;padding:1px 10px;font:inherit;font-size:12px;cursor:pointer}
.chip .d{display:inline-block;width:8px;height:8px;border-radius:50%;margin-right:5px}
.file{background:var(--code);border-radius:4px;padding:1px 6px;font:12px ui-monospace,Consolas,monospace}
.kv{display:grid;grid-template-columns:90px 1fr;gap:4px 8px}.kv dt{color:var(--mut)}.kv dd{margin:0}
.md h2{font-size:14px;margin:16px 0 6px;border-bottom:1px solid var(--line);padding-bottom:2px}
.md p{margin:6px 0}.md ul{margin:6px 0;padding-left:20px}.md li.cb{list-style:none;margin-left:-20px}
.md code{background:var(--code);border-radius:4px;padding:0 4px;font:12px ui-monospace,Consolas,monospace}
.md pre{background:var(--code);border-radius:6px;padding:8px;overflow-x:auto;font:12px ui-monospace,Consolas,monospace}
.md pre code{background:none;padding:0}
.log{font:12px ui-monospace,Consolas,monospace;color:var(--mut);margin:0;padding:0;list-style:none}
@media(max-width:720px){.board{grid-template-columns:repeat(6,220px)}}
</style>
</head>
<body>
<header>
  <h1>__FEATURE__</h1>
  <div class="prog"><i id="pbar"></i></div>
  <span class="mut" id="ptxt"></span>
  <span class="mut">Click a card for details. Esc closes.</span>
</header>
<div class="board" id="board"></div>
<div id="veil"></div>
<aside id="panel" aria-label="Task details"></aside>
<script>
var DATA = __DATA__;
var STATUSES = ["backlog","ready","in-progress","review","done","blocked"];
var COLORS = {"backlog":"#8a8f98","ready":"#3b82f6","in-progress":"#f59e0b","review":"#a855f7","done":"#22c55e","blocked":"#ef4444"};
var T = {}; DATA.tasks.forEach(function(t){ T[t.id] = t; });
function esc(s){ return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;"); }
function crit(t){ var a = (t.body.match(/^\s*- \[x\]/gim)||[]).length, b = (t.body.match(/^\s*- \[ \]/gim)||[]).length; return {done:a,total:a+b}; }
function waiting(t){ return (t.status==="backlog"||t.status==="ready") && t.deps.some(function(d){ return !T[d] || T[d].status!=="done"; }); }
function blocks(t){ return DATA.tasks.filter(function(u){ return u.deps.indexOf(t.id)>=0; }); }

function inline(s){
  s = esc(s);
  s = s.replace(/`([^`]+)`/g,"<code>$1</code>");
  s = s.replace(/\*\*([^*]+)\*\*/g,"<b>$1</b>");
  return s;
}
function md(src){
  var out = [], lines = src.split(/\r?\n/), i = 0, list = false;
  function close(){ if(list){ out.push("</ul>"); list = false; } }
  while(i < lines.length){
    var l = lines[i];
    if(/^```/.test(l)){
      close(); var buf = []; i++;
      while(i < lines.length && !/^```/.test(lines[i])){ buf.push(lines[i]); i++; }
      out.push("<pre><code>"+esc(buf.join("\n"))+"</code></pre>"); i++; continue;
    }
    var h = l.match(/^#{1,4}\s+(.*)/);
    var cb = l.match(/^\s*- \[( |x)\]\s+(.*)/i);
    var li = l.match(/^\s*(?:[-*]|\d+\.)\s+(.*)/);
    if(h){ close(); out.push("<h2>"+inline(h[1])+"</h2>"); }
    else if(cb){ if(!list){ out.push("<ul>"); list = true; }
      out.push('<li class="cb"><input type="checkbox" disabled '+(cb[1]!==" "?"checked":"")+"> "+inline(cb[2])+"</li>"); }
    else if(li){ if(!list){ out.push("<ul>"); list = true; } out.push("<li>"+inline(li[1])+"</li>"); }
    else if(l.trim()===""){ close(); }
    else { close(); out.push("<p>"+inline(l)+"</p>"); }
    i++;
  }
  close(); return out.join("");
}

function chip(id){
  var t = T[id];
  if(!t) return '<span class="chip">'+esc(id)+' (missing)</span>';
  return '<button class="chip" data-open="'+esc(id)+'"><span class="d" style="background:'+COLORS[t.status]+'"></span>'+esc(id)+" "+esc(t.title)+"</button>";
}

function renderBoard(){
  var done = DATA.tasks.filter(function(t){ return t.status==="done"; }).length;
  document.getElementById("pbar").style.width = (DATA.tasks.length ? 100*done/DATA.tasks.length : 0)+"%";
  document.getElementById("ptxt").textContent = done+"/"+DATA.tasks.length+" done";
  var html = STATUSES.map(function(s){
    var cards = DATA.tasks.filter(function(t){ return t.status===s; }).map(function(t){
      var c = crit(t), m = "";
      if(t.agent) m += "<span>@"+esc(t.agent)+"</span>";
      if(t.deps.length) m += '<span class="'+(waiting(t)?"wait":"")+'">needs '+esc(t.deps.join(", "))+"</span>";
      var bar = c.total ? '<div class="bar"><i style="width:'+(100*c.done/c.total)+'%"></i></div>' : "";
      return '<button class="card" data-open="'+esc(t.id)+'" id="c-'+esc(t.id)+'"><b>'+esc(t.id)+'</b><div class="t">'+esc(t.title)+'</div><div class="meta">'+m+"</div>"+bar+"</button>";
    }).join("");
    return '<section class="col"><h2 style="border-color:'+COLORS[s]+'">'+s+" <i>"+DATA.tasks.filter(function(t){return t.status===s;}).length+"</i></h2>"+cards+"</section>";
  }).join("");
  document.getElementById("board").innerHTML = html;
}

function openTask(id){
  var t = T[id]; if(!t) return;
  var c = crit(t), b = blocks(t);
  var hist = DATA.log.filter(function(e){ return e.id===id; });
  var h = '<div class="top"><span class="pill" style="background:'+COLORS[t.status]+'">'+esc(t.status)+'</span><button class="x" id="close">Close</button></div>';
  h += "<h3>"+esc(t.id)+" &middot; "+esc(t.title)+"</h3>";
  h += '<dl class="kv"><dt>Agent</dt><dd>'+(t.agent?esc(t.agent):"general")+"</dd><dt>Updated</dt><dd>"+esc(t.updated||"-")+"</dd><dt>File</dt><dd><span class=\"file\">"+esc(t.path)+"</span></dd>";
  if(c.total) h += "<dt>Criteria</dt><dd>"+c.done+"/"+c.total+' <div class="bar"><i style="width:'+(100*c.done/c.total)+'%"></i></div></dd>';
  h += "</dl>";
  h += "<h4>Depends on</h4>"+(t.deps.length ? '<div class="chips">'+t.deps.map(chip).join("")+"</div>" : '<span class="mut">nothing (foundation)</span>');
  h += "<h4>Blocks</h4>"+(b.length ? '<div class="chips">'+b.map(function(u){return chip(u.id);}).join("")+"</div>" : '<span class="mut">nothing</span>');
  if(t.files.length) h += "<h4>Files</h4><div class=\"chips\">"+t.files.map(function(f){ return '<span class="file">'+esc(f)+"</span>"; }).join("")+"</div>";
  h += '<div class="md">'+md(t.body)+"</div>";
  h += "<h4>History</h4>"+(hist.length ? '<ul class="log">'+hist.map(function(e){ return "<li>"+esc(e.text)+"</li>"; }).join("")+"</ul>" : '<span class="mut">no moves logged</span>');
  var p = document.getElementById("panel"); p.innerHTML = h; p.classList.add("on"); p.scrollTop = 0;
  document.getElementById("veil").classList.add("on");
  Array.prototype.forEach.call(document.querySelectorAll(".card.sel"), function(e){ e.classList.remove("sel"); });
  var card = document.getElementById("c-"+id); if(card) card.classList.add("sel");
  if(location.hash !== "#"+id) history.replaceState(null, "", "#"+id);
}
function closePanel(){
  document.getElementById("panel").classList.remove("on");
  document.getElementById("veil").classList.remove("on");
  Array.prototype.forEach.call(document.querySelectorAll(".card.sel"), function(e){ e.classList.remove("sel"); });
  history.replaceState(null, "", location.pathname);
}
document.addEventListener("click", function(e){
  var o = e.target.closest("[data-open]");
  if(o){ openTask(o.getAttribute("data-open")); return; }
  if(e.target.id==="close" || e.target.id==="veil") closePanel();
});
document.addEventListener("keydown", function(e){ if(e.key==="Escape") closePanel(); });
renderBoard();
if(location.hash.length > 1) openTask(decodeURIComponent(location.hash.slice(1)));
</script>
</body>
</html>
