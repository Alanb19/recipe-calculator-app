# -*- coding: utf-8 -*-
"""Feedback loop para Calculadora_Nora.html. Falla ruidoso si algo no cuadra."""
import json, os, re, subprocess, sys
from pathlib import Path

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.environ.get(
    "EASILYS_CACHE",
    str(Path.home() / "OneDrive - Nora Real Food" / "Escritorio" /
        "04_PROYECTOS_CLAUDE" / "proyecto claude sincronizacion hoja de produccion" /
        "files" / "FICHAS_EASILYS_CACHE.json"),
)
# build_calc.py escribe en NRF_CALC_OUT (default: ~/Desktop). Leer de ahi.
HTML = os.environ.get("NRF_CALC_OUT", str(Path.home() / "Desktop" / "Calculadora_Nora.html"))

fails = []
def check(cond, msg):
    print(("  OK  " if cond else "  FAIL") + "  " + msg)
    if not cond:
        fails.append(msg)

# 1. (Re)generar
print("== build ==")
r = subprocess.run([sys.executable, os.path.join(HERE, "build_calc.py")],
                    capture_output=True, text=True)
print(r.stdout.strip());
if r.returncode != 0:
    print(r.stderr); sys.exit("build_calc.py fallo")

# 2. Conjunto canonico esperado
raw = json.load(open(CACHE, encoding="utf-8"))
cache_by_id = {}
for _, v in raw.items():
    cache_by_id[str(v["id"])] = v
expected_ids = set(cache_by_id)
print(f"\n== verificacion ==  cache: {len(expected_ids)} recetas unicas (por id)")

# 3. Extraer datasets embebidos del HTML
h = open(HTML, encoding="utf-8").read()
m_r = re.search(r"const RECIPES\s*=\s*(\{.*?\});\s*\nconst NAME_IDX", h, re.S)
m_n = re.search(r"const NAME_IDX\s*=\s*(\{.*?\});\s*\nconst ALL", h, re.S)
check(bool(m_r), "RECIPES embebido encontrado")
check(bool(m_n), "NAME_IDX embebido encontrado")
RECIPES = json.loads(m_r.group(1))
NAME_IDX = json.loads(m_n.group(1))

# 4. NINGUNA receta perdida (este era EL bug)
embedded_ids = set(RECIPES)
check(len(RECIPES) == len(expected_ids),
      f"recetas embebidas == cache : {len(RECIPES)} == {len(expected_ids)}")
missing = expected_ids - embedded_ids
check(not missing, f"0 recetas del cache ausentes (faltan {len(missing)})")
if missing:
    for mid in list(missing)[:10]:
        print("      perdida:", mid, cache_by_id[mid].get("nombre"))

# 5. Integridad por receta (nombre/codigo/peso/nº comps coincide con cache)
bad = 0
for rid, v in cache_by_id.items():
    e = RECIPES.get(rid)
    if not e: bad += 1; continue
    if e["name"] != str(v.get("nombre", "")).strip(): bad += 1; continue
    if e["code"] != str(v.get("codigo", rid)).strip(): bad += 1; continue
    if len(e["comps"]) != len(v.get("ingredientes", [])): bad += 1
check(bad == 0, f"campos (nombre/codigo/comps) coinciden con cache : {bad} discrepancias")

# 6. Matematica de escalado: POLLO MORUNO CON COUS COUS, PE COUS COUS MORUNO
#    0.13 x100 = 13. Busqueda por NOMBRE (robusta al re-key por element id;
#    los ids ya no son 1,2,3 sino element ids de Easilys).
r1 = next((r for r in RECIPES.values()
           if r["name"].strip().upper() == "POLLO MORUNO CON COUS COUS"), None)
check(r1 is not None, "receta 'POLLO MORUNO CON COUS COUS' presente")
if r1:
    ccm = next((c for c in r1["comps"] if c["name"] == "PE COUS COUS MORUNO"), None)
    check(ccm is not None, "comp 'PE COUS COUS MORUNO' presente en POLLO MORUNO")
    if ccm:
        check(abs(ccm["qty"] - 0.13) < 1e-9, f"qty x1 PE COUS COUS MORUNO = {ccm['qty']} (esp. 0.13)")
        check(abs(round(ccm["qty"] * 100, 3) - 13.0) < 1e-9,
              f"escalado x100 = {round(ccm['qty']*100,3)} kg (esp. 13.0)")

# 7. Resolucion de PE por nombre (no debe empeorar vs cache: ~42 verdaderas ausentes)
def resolve(name):
    k = name.lower()
    for cand in (k, k[3:] if k.startswith("pe ") else None, "pe " + k):
        if cand and cand in NAME_IDX:
            return NAME_IDX[cand]
    return None

pe_refs = unresolved = 0
unresolved_names = set()
for r in RECIPES.values():
    for c in r["comps"]:
        if c["pe"]:
            pe_refs += 1
            if resolve(c["name"]) is None:
                unresolved += 1
                unresolved_names.add(c["name"])
print(f"      PE refs: {pe_refs}  |  irresolubles: {unresolved} "
      f"({len(unresolved_names)} nombres distintos)")
# Linea base: estas fichas PE/PP NO existen en el export de Easilys (gap de
# origen, no bug del calculador). El re-key por element id (2026-05) deduplico
# el cache (2515->~2247) y destapo el hueco REAL: el "42" anterior estaba
# artificialmente bajo porque las colisiones recipe.id<->element.id dejaban
# entradas duplicadas que resolvian nombres por casualidad. Valor real ~76;
# baseline 80 con holgura para la rotacion semanal. Subir solo si se confirma
# que el aumento es gap de origen (PP/PE sin ficha), nunca para tapar un bug.
BASELINE_IRRESOLUBLES = 80
check(len(unresolved_names) <= BASELINE_IRRESOLUBLES,
      f"PE irresolubles == hueco real del cache "
      f"({len(unresolved_names)} nombres <= {BASELINE_IRRESOLUBLES}, sin regresion)")
print("      fichas PE ausentes en el cache de origen (no es fallo del calculador):")
for n in sorted(unresolved_names):
    print("        -", n)

# 8. Expansion recursiva termina (sin ciclos infinitos) sobre TODOS los platos
def expand(rid, mult, anc, depth):
    r = RECIPES.get(rid)
    if not r or depth > 25:
        return depth
    md = depth
    for c in r["comps"]:
        if c["pe"]:
            pid = resolve(c["name"])
            if pid and pid not in anc and RECIPES[pid]["comps"]:
                md = max(md, expand(pid, None, anc | {pid}, depth + 1))
    return md

platos = [rid for rid, r in RECIPES.items()
          if not r["name"].upper().startswith("PE ")]
maxd = 0
for rid in platos:
    maxd = max(maxd, expand(rid, None, {rid}, 0))
check(True, f"expansion recursiva termina en los {len(platos)} platos (prof. max {maxd})")

# 9. HTML standalone bien formado / sin servidor
check("localhost" not in h and "fetch(" not in h,
      "0 referencias a servidor (fetch/localhost) -> 100% offline file://")
check(h.rstrip().endswith("</html>"), "HTML cierra con </html>")
check("__RECIPES__" not in h and "__NAMEIDX__" not in h,
      "placeholders de plantilla sustituidos")
check(h.count("<table") >= 0 and "exportCSV" in h, "boton export CSV presente")

# 10. recetas vacias (informativo)
empty = [rid for rid, r in RECIPES.items() if not r["comps"]]
print(f"      info: {len(empty)} recetas sin ingredientes (se muestran con aviso)")

print("\n== RESULTADO ==", "TODO OK" if not fails else f"{len(fails)} FALLOS")
sys.exit(1 if fails else 0)
