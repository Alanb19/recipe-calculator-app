# -*- coding: utf-8 -*-
"""
Genera C:\\Users\\Usuario\\Desktop\\Calculadora_Nora.html  (standalone, file://, sin servidor)

Fuente canonica de verdad: FICHAS_EASILYS_CACHE.json
Indexado por ID interno de Easilys (NO por codigo) -> no se pierde ninguna receta
aunque varias compartan el mismo 'codigo'.
"""
import json, os, html as _html
from pathlib import Path

# Rutas configurables por variable de entorno; default relativo a la carpeta
# del usuario (sin C:\Users\<usuario> hardcodeado -> repo publico seguro).
_DEFAULT_CACHE = Path.home() / "OneDrive - Nora Real Food" / "Escritorio" / \
    "04_PROYECTOS_CLAUDE" / "proyecto claude sincronizacion hoja de produccion" / \
    "files" / "FICHAS_EASILYS_CACHE.json"
CACHE = os.environ.get("EASILYS_CACHE", str(_DEFAULT_CACHE))
OUT = os.environ.get("NRF_CALC_OUT", str(Path.home() / "Desktop" / "Calculadora_Nora.html"))


def build_dataset(cache_path: str):
    raw = json.load(open(cache_path, encoding="utf-8"))

    # El JSON viene duplicado: clave numerica (id) Y clave = codigo, ambas al
    # mismo objeto. Deduplicamos por 'id' interno -> conjunto canonico.
    by_id = {}
    for _, v in raw.items():
        by_id[str(v["id"])] = v

    recipes = {}
    for rid, v in by_id.items():
        comps = []
        for ing in v.get("ingredientes", []):
            qty = ing.get("cant_neta")
            if qty in (None, ""):
                qty = ing.get("cant_bruta") or 0
            comps.append({
                "name": str(ing.get("nombre", "")).strip(),
                "qty": float(qty or 0),
                "unit": str(ing.get("unidad", "")).strip(),
                "pe": bool(ing.get("es_pe")),
                "pp": str(ing.get("pp", "No")) == "Si",
            })
        recipes[rid] = {
            "id": rid,
            "code": str(v.get("codigo", rid)).strip(),
            "name": str(v.get("nombre", "")).strip(),
            "weight": float(v.get("peso_referencia") or 0),
            "comps": comps,
        }

    # Indice nombre(lower) -> id. Ante colision de nombre, preferimos la ficha
    # CON ingredientes (la vacia no aporta nada al desglose de una PE).
    name_idx = {}
    for rid, r in recipes.items():
        key = r["name"].lower()
        if not key:
            continue
        cur = name_idx.get(key)
        if cur is None or (not recipes[cur]["comps"] and r["comps"]):
            name_idx[key] = rid

    return recipes, name_idx


HEAD = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>Calculadora de Recetas &mdash; Nora Real Food</title>
<style>
:root{--navy:#192850;--navy2:#2c3e6b;--accent:#e84c20;--bg:#f0f2f7;--panel:#fff;--border:#dde2ee;--text:#1a2233;--muted:#6b7a99;--sub-bg:#eaf1fb}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,"Segoe UI",sans-serif;background:var(--bg);color:var(--text);height:100vh;display:flex;flex-direction:column;overflow:hidden}
header{background:var(--navy);color:#fff;display:flex;align-items:center;gap:1rem;padding:0 1.5rem;height:56px;flex-shrink:0;box-shadow:0 2px 6px rgba(0,0,0,.3)}
.logo-ring{width:36px;height:36px;border-radius:50%;background:var(--accent);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:14px;color:#fff;flex-shrink:0}
header h1{font-size:.95rem;font-weight:600;letter-spacing:.03em;flex:1}
.badge{background:rgba(255,255,255,.15);color:#fff;padding:.3rem .7rem;border-radius:4px;font-size:.75rem}
.btn-exp{background:var(--accent);color:#fff;border:none;padding:.45rem 1rem;border-radius:5px;font-size:.82rem;font-weight:600;cursor:pointer}
.btn-exp:disabled{background:#555;cursor:default;opacity:.6}
.layout{display:flex;flex:1;overflow:hidden}
.sidebar{width:300px;flex-shrink:0;background:var(--navy2);color:#e8edf8;display:flex;flex-direction:column;overflow:hidden}
.sidebar-top{padding:.75rem .75rem .5rem}
.search-wrap{position:relative}
.search-wrap svg{position:absolute;left:.6rem;top:50%;transform:translateY(-50%);opacity:.5;pointer-events:none}
#search-input{width:100%;padding:.5rem .75rem .5rem 2rem;background:rgba(255,255,255,.12);border:1px solid rgba(255,255,255,.18);border-radius:6px;color:#fff;font-size:.85rem}
#search-input::placeholder{color:rgba(255,255,255,.5)}
#search-input:focus{outline:none;background:rgba(255,255,255,.18)}
.list-header{padding:.5rem .75rem .35rem;font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:rgba(255,255,255,.45);display:flex;justify-content:space-between}
#recipe-list{flex:1;overflow-y:auto;padding:0 .4rem .75rem}
#recipe-list::-webkit-scrollbar{width:4px}
#recipe-list::-webkit-scrollbar-thumb{background:rgba(255,255,255,.2);border-radius:2px}
.recipe-item{padding:.55rem .6rem;border-radius:6px;cursor:pointer;transition:background .12s;border-left:3px solid transparent;margin-bottom:2px}
.recipe-item:hover{background:rgba(255,255,255,.1)}
.recipe-item.active{background:rgba(255,255,255,.15);border-left-color:var(--accent)}
.recipe-item .rname{font-size:.85rem;font-weight:500;color:#eef2ff;line-height:1.3}
.recipe-item .rcode{font-size:.72rem;color:rgba(255,255,255,.45);margin-top:1px}
.more{padding:.5rem;text-align:center}
.more button{background:none;border:1px solid rgba(255,255,255,.25);color:rgba(255,255,255,.6);font-size:.75rem;padding:.3rem .9rem;border-radius:4px;cursor:pointer}
.detail{flex:1;overflow-y:auto;padding:1.5rem}
.empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;height:100%;color:var(--muted);text-align:center;gap:.75rem}
.empty-state svg{opacity:.25}
.recipe-header{background:var(--panel);border-radius:10px;padding:1.25rem 1.5rem;margin-bottom:1rem;box-shadow:0 1px 3px rgba(0,0,0,.07)}
.recipe-title{font-size:1.2rem;font-weight:700;color:var(--navy);margin-bottom:.35rem}
.recipe-meta{display:flex;gap:1rem;flex-wrap:wrap}
.meta-chip{background:var(--sub-bg);color:var(--navy2);font-size:.78rem;font-weight:600;padding:.25rem .65rem;border-radius:4px}
.portions-bar{display:flex;align-items:center;gap:.75rem;background:#f5f7fd;border:1.5px solid var(--border);border-radius:8px;padding:.5rem .85rem;margin-bottom:1rem}
.portions-bar label{font-size:.82rem;font-weight:700;color:var(--muted);white-space:nowrap}
.portions-input{width:110px;padding:.45rem .7rem;border:1.5px solid var(--border);border-radius:6px;font-size:1.1rem;font-weight:700;color:var(--navy2);text-align:center}
.portions-input:focus{outline:none;border-color:var(--navy2)}
.portions-hint{font-size:.8rem;color:var(--muted)}
.portions-total{margin-left:auto;font-size:.82rem;font-weight:600;color:var(--navy2);background:var(--sub-bg);padding:.3rem .75rem;border-radius:5px;display:none}
.section-card{background:var(--panel);border-radius:10px;box-shadow:0 1px 3px rgba(0,0,0,.07);overflow:hidden}
.section-head{padding:.75rem 1.25rem;border-bottom:1px solid var(--border);font-size:.8rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--muted);display:flex;align-items:center;gap:.5rem}
.badge-count{background:var(--navy2);color:#fff;border-radius:999px;font-size:.68rem;padding:.1rem .45rem}
table{width:100%;border-collapse:collapse;font-size:.86rem}
thead th{padding:.55rem 1rem;text-align:left;background:#f5f7fc;font-weight:600;color:var(--muted);font-size:.76rem;text-transform:uppercase;letter-spacing:.04em;border-bottom:1px solid var(--border)}
thead th.right{text-align:right}
tbody td{padding:.5rem 1rem;border-bottom:1px solid #f2f4fa;vertical-align:middle}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:#fafbff}
tbody tr.lvl1 td{background:var(--sub-bg)}
tbody tr.lvl1:hover td{background:#dce8f8}
tbody tr.lvl2 td{background:#f0f5ff}
tbody tr.lvl3 td{background:#eef6ee}
tbody tr.pehdr td{background:#dce8f8;font-size:.74rem;font-weight:700;color:var(--navy2);text-transform:uppercase;letter-spacing:.04em}
tbody tr.warn td{color:#c0392b;font-size:.8rem}
.type-badge{display:inline-block;padding:.18rem .55rem;border-radius:4px;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.03em}
.type-sub{background:#d4e4fb;color:#1d4ed8}
.type-ing{background:#e6faf0;color:#166534}
.qty-cell{text-align:right;font-variant-numeric:tabular-nums;font-weight:500}
.qty-total{color:var(--navy2);font-weight:700}
.unit-cell{color:var(--muted);font-size:.82rem}
.pe-toggle{background:none;border:1.5px solid #b0c4e8;border-radius:4px;width:20px;height:20px;font-size:.6rem;cursor:pointer;color:var(--navy2);padding:0;display:inline-flex;align-items:center;justify-content:center;transition:transform .15s;vertical-align:middle;margin-right:.45rem}
.pe-toggle:hover{background:#d4e4fb}
.pe-toggle.open{transform:rotate(90deg);background:var(--navy2);color:#fff;border-color:var(--navy2)}
</style>
</head>
<body>
<header>
<div class="logo-ring">NR</div>
<h1>CALCULADORA DE RECETAS &mdash; NORA REAL FOOD</h1>
<span class="badge" id="total-badge">...</span>
<button class="btn-exp" id="btn-export" onclick="exportCSV()" disabled>&#8595; Exportar CSV</button>
</header>
<div class="layout">
<aside class="sidebar">
<div class="sidebar-top"><div class="search-wrap">
<svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
<input id="search-input" type="text" placeholder="Buscar por nombre, codigo o id..." oninput="onSearch()"/>
</div></div>
<div class="list-header"><span>Recetas</span><span id="count-label">-</span></div>
<div id="recipe-list"></div>
</aside>
<main class="detail" id="detail">
<div class="empty-state">
<svg width="64" height="64" fill="none" stroke="currentColor" stroke-width="1.2" viewBox="0 0 24 24"><path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2"/><rect x="9" y="3" width="6" height="4" rx="1"/><path d="M9 12h6M9 16h4"/></svg>
<p>Selecciona una receta<br>para calcular cantidades</p>
</div>
</main>
</div>
"""

SCRIPT = r"""
<script>
const RECIPES = __RECIPES__;
const NAME_IDX = __NAMEIDX__;
const ALL = Object.values(RECIPES).sort((a,b)=>a.name.localeCompare(b.name,'es'));

let filtered = ALL;
let shown = 0;
const PAGE = 120;
let currentId = null;
let portions = null;
const expanded = new Set();   // set of path strings ("2", "2.0", "2.0.1")

function init(){
  document.getElementById('total-badge').textContent = ALL.length.toLocaleString('es-ES')+' recetas';
  renderList(true);
}

let _st;
function onSearch(){
  clearTimeout(_st);
  _st=setTimeout(()=>{
    const q=document.getElementById('search-input').value.trim().toLowerCase();
    filtered = !q ? ALL : ALL.filter(r =>
      r.name.toLowerCase().includes(q) ||
      r.code.toLowerCase().includes(q) ||
      r.id===q);
    renderList(true);
  },180);
}

function renderList(reset){
  if(reset) shown=0;
  shown=Math.min(filtered.length, shown+PAGE || PAGE);
  document.getElementById('count-label').textContent=filtered.length.toLocaleString('es-ES');
  const slice=filtered.slice(0,shown);
  let h=slice.map(r=>
    '<div class="recipe-item'+(r.id===currentId?' active':'')+'" onclick="sel(\''+r.id+'\')">'
    +'<div class="rname">'+esc(r.name)+'</div>'
    +'<div class="rcode">Cod: '+esc(r.code)+' &middot; id '+r.id+' &middot; '+fmt(r.weight)+'g/p</div></div>'
  ).join('');
  if(shown<filtered.length)
    h+='<div class="more"><button onclick="renderList(false)">Cargar mas ('+(filtered.length-shown)+')</button></div>';
  document.getElementById('recipe-list').innerHTML=h;
}

function sel(id){
  currentId=id; portions=null; expanded.clear();
  document.querySelectorAll('.recipe-item').forEach(e=>e.classList.remove('active'));
  renderDetail();
}

// Resuelve el nombre de una PE a una receta del dataset.
function resolvePE(name){
  const k=String(name||'').toLowerCase();
  let id=NAME_IDX[k];
  if(id==null && k.startsWith('pe ')) id=NAME_IDX[k.slice(3)];
  if(id==null) id=NAME_IDX['pe '+k];
  return id!=null ? RECIPES[id] : null;
}

function pecPortions(totalQty, unit, weightG){
  if(unit==='PO') return totalQty;          // ya viene en porciones
  if(!weightG) return totalQty;
  return totalQty*1000/weightG;             // kg/L -> nº porciones de la PE
}

// Genera filas (recursivo). 'mult' = porciones efectivas de la receta padre.
// 'ancestry' = Set de ids para cortar ciclos.
function buildRows(recipe, mult, prefix, depth, ancestry){
  let html='';
  recipe.comps.forEach((c,i)=>{
    const path = prefix ? prefix+'.'+i : String(i);
    const total = mult!=null ? r3(c.qty*mult) : null;
    const lvl = depth>=3?3:depth;
    const pad = .6 + depth*1.6;
    const isExp = expanded.has(path);
    let toggle='<span style="display:inline-block;width:26px"></span>';
    let resolvable=false;
    if(c.pe){
      const pe=resolvePE(c.name);
      resolvable=!!pe;
      if(pe) toggle='<button class="pe-toggle'+(isExp?' open':'')+'" onclick="togg(\''+path+'\')">&#9654;</button>';
    }
    html+='<tr class="lvl'+lvl+'">'
      +'<td style="padding-left:'+pad+'rem">'+toggle+esc(c.name)+'</td>'
      +'<td><span class="type-badge '+(c.pe?'type-sub':'type-ing')+'">'+(c.pe?'Subreceta':'Ingrediente')+'</span></td>'
      +'<td class="qty-cell">'+fmt(c.qty)+'</td>'
      +'<td class="unit-cell">'+esc(c.unit)+'</td>'
      +'<td class="qty-cell'+(total!=null?' qty-total':'')+'">'+(total!=null?fmt(total):'-')+'</td></tr>';

    if(c.pe && isExp){
      const pe=resolvePE(c.name);
      if(!pe){
        html+='<tr class="warn"><td colspan="5" style="padding-left:'+(pad+1.4)+'rem">Ficha no encontrada para esta PE ('+esc(c.name)+')</td></tr>';
      }else if(ancestry.has(pe.id)){
        html+='<tr class="warn"><td colspan="5" style="padding-left:'+(pad+1.4)+'rem">Referencia circular: '+esc(pe.name)+' (no se expande)</td></tr>';
      }else{
        const parentTotal = (mult!=null?c.qty*mult:c.qty);
        const peMult = pecPortions(parentTotal, c.unit, pe.weight);
        html+='<tr class="pehdr"><td colspan="2" style="padding-left:'+(pad+1.4)+'rem">&#8627; '
          +esc(pe.name)+' &mdash; '+fmt(r3(peMult))+' porciones de PE</td>'
          +'<td class="qty-cell">Cant. x1</td><td>Uds.</td>'
          +'<td class="qty-cell">'+(mult!=null?'x'+fmt(r3(mult)):'x1')+'</td></tr>';
        if(!pe.comps.length){
          html+='<tr class="warn"><td colspan="5" style="padding-left:'+(pad+1.4)+'rem">(Esta ficha no tiene ingredientes cargados)</td></tr>';
        }else{
          const na=new Set(ancestry); na.add(pe.id);
          html+=buildRows(pe, mult!=null?peMult:null, path, depth+1, na);
        }
      }
    }
  });
  return html;
}

function renderDetail(){
  const r=RECIPES[currentId];
  if(!r){return;}
  window._cur=r;
  const subs=r.comps.filter(c=>c.pe).length, ings=r.comps.length-subs;
  const body = buildRows(r, portions, '', 0, new Set([r.id]));
  const tk = portions!=null ? r3(r.weight*portions/1000) : null;
  document.getElementById('detail').innerHTML=
    '<div class="recipe-header"><div class="recipe-title">'+esc(r.name)+'</div>'
    +'<div class="recipe-meta">'
    +'<span class="meta-chip">Cod: '+esc(r.code)+'</span>'
    +'<span class="meta-chip">id '+r.id+'</span>'
    +'<span class="meta-chip">Peso ref: '+fmt(r.weight)+' g/porcion</span>'
    +'<span class="meta-chip">'+subs+' subrecetas &middot; '+ings+' ingredientes</span></div></div>'
    +'<div class="portions-bar"><label>N&ordm; de platos</label>'
    +'<input class="portions-input" id="pi" type="number" min="1" max="100000" placeholder="ej. 15" '
    +'value="'+(portions!=null?portions:'')+'" oninput="calc()" onchange="calc()"/>'
    +'<span class="portions-hint">Escribe un numero &rarr; calcula automaticamente</span>'
    +'<span class="portions-total" id="pt"'+(tk!=null?' style="display:block"':'')+'>'
    +(tk!=null?'Peso total aprox. '+tk.toLocaleString('es-ES')+' kg':'')+'</span></div>'
    +'<div class="section-card"><div class="section-head">Componentes '
    +'<span class="badge-count">'+r.comps.length+'</span>'
    +'<span style="margin-left:auto;font-size:.75rem;color:var(--muted);font-weight:500">Cant. total</span></div>'
    +'<table><thead><tr><th>Nombre</th><th>Tipo</th><th class="right">Cant. x1</th>'
    +'<th>Unidad</th><th class="right">'+(portions!=null?'x'+portions:'Total')+'</th></tr></thead>'
    +'<tbody>'+body+'</tbody></table></div>';
  document.getElementById('btn-export').disabled = portions==null;
  const pi=document.getElementById('pi'); if(pi){pi.focus(); pi.setSelectionRange(pi.value.length,pi.value.length);}
}

function calc(){
  const v=parseInt(document.getElementById('pi').value);
  portions = (!v||v<1) ? null : v;
  renderDetail();
}

function togg(path){
  if(expanded.has(path)) expanded.delete(path);
  else expanded.add(path);
  renderDetail();
}

// ---- Export CSV (offline, Excel-friendly: ; separador, coma decimal, BOM) ----
function csvNum(n){ return (n==null?'':String(n).replace('.',',')); }
function csvCell(s){ s=String(s==null?'':s); return /[;"\n]/.test(s)?'"'+s.replace(/"/g,'""')+'"':s; }

function flatten(recipe, mult, depth, ancestry, out){
  recipe.comps.forEach(c=>{
    const total = mult!=null ? r3(c.qty*mult) : '';
    out.push([ '  '.repeat(depth)+c.name, c.pe?'Subreceta':'Ingrediente',
               c.qty, c.unit, total ]);
    if(c.pe){
      const pe=resolvePE(c.name);
      if(pe && !ancestry.has(pe.id) && pe.comps.length){
        const parentTotal=(mult!=null?c.qty*mult:c.qty);
        const peMult=pecPortions(parentTotal,c.unit,pe.weight);
        const na=new Set(ancestry); na.add(pe.id);
        flatten(pe, mult!=null?peMult:null, depth+1, na, out);
      }
    }
  });
}

function exportCSV(){
  const r=window._cur; if(!r||portions==null) return;
  const rows=[['RECETA: '+r.name+'  |  Cod: '+r.code+'  |  id '+r.id
              +'  |  '+portions+' platos  |  '+r.weight+' g/porcion']];
  rows.push(['Nombre','Tipo','Cant. x1','Unidad','Cant. x'+portions]);
  const out=[]; flatten(r, portions, 0, new Set([r.id]), out);
  out.forEach(o=>rows.push([o[0],o[1],csvNum(o[2]),o[3],csvNum(o[4])]));
  const csv='﻿'+rows.map(r=>r.map(csvCell).join(';')).join('\r\n');
  const blob=new Blob([csv],{type:'text/csv;charset=utf-8'});
  const a=document.createElement('a');
  a.href=URL.createObjectURL(blob);
  a.download=(r.name.replace(/[\\/:*?"<>|]/g,'-').slice(0,40))+'_'+portions+'p.csv';
  a.click(); URL.revokeObjectURL(a.href);
}

function esc(s){return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');}
function fmt(n){if(n==null||n==='')return '-';return Number(n).toLocaleString('es-ES',{maximumFractionDigits:3});}
function r3(n){return Math.round(n*1000)/1000;}

init();
</script>
</body>
</html>"""


def main():
    recipes, name_idx = build_dataset(CACHE)
    rec_json = json.dumps(recipes, ensure_ascii=False, separators=(",", ":"))
    idx_json = json.dumps(name_idx, ensure_ascii=False, separators=(",", ":"))
    html = HEAD + SCRIPT.replace("__RECIPES__", rec_json).replace("__NAMEIDX__", idx_json)

    if os.path.exists(OUT):
        try:
            os.replace(OUT, OUT + ".bak")
        except OSError:
            pass
    open(OUT, "w", encoding="utf-8").write(html)

    print(f"OK -> {OUT}")
    print(f"   recetas embebidas : {len(recipes)}")
    print(f"   indice de nombres : {len(name_idx)}")
    print(f"   tamano            : {os.path.getsize(OUT)//1024} KB")


if __name__ == "__main__":
    main()
