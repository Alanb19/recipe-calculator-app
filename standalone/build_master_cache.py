"""
BUILD MASTER CACHE — Parsea TODAS las fichas HTML de Easilys y genera
FICHAS_EASILYS_CACHE.json con todas las PEs y subPEs disponibles.

Uso: python build_master_cache.py
Requiere: pip install beautifulsoup4
"""
import json, re, os
from pathlib import Path
from bs4 import BeautifulSoup

# ── Rutas ────────────────────────────────────────────────────────────────────
DOWNLOADS = r"C:\Users\Usuario\Downloads"
CACHE_OUT  = r"C:\Users\Usuario\OneDrive - Nora Real Food\Escritorio\04_PROYECTOS_CLAUDE\proyecto claude sincronizacion hoja de produccion\files\FICHAS_EASILYS_CACHE.json"

SOURCE_FILES = [
    rf"{DOWNLOADS}\RAW_FICHAS_EASILYS.json",
    rf"{DOWNLOADS}\fichas_easilys_lote2.json",
    rf"{DOWNLOADS}\fichas_easilys_lote3.json",
    rf"{DOWNLOADS}\fichas_easilys_lote4.json",
    rf"{DOWNLOADS}\fichas_easilys_lote5.json",
    rf"{DOWNLOADS}\fichas_easilys_loteFINAL.json",
    rf"{DOWNLOADS}\fichas_easilys_w18.json",
    rf"{DOWNLOADS}\fichas_masiva_W19.json",
    rf"{DOWNLOADS}\fichas_rueda_menus_20260511.json",
    rf"{DOWNLOADS}\fichas_easilys_lote2_W19_20260504.json",
    rf"{DOWNLOADS}\fichas_easilys_lote_W18_20260428.json",
    rf"{DOWNLOADS}\fichas_easilys_retry_INCONNU_20260421.json",
    rf"{DOWNLOADS}\fichas_easilys_W19_platos.json",
    rf"{DOWNLOADS}\fichas_easilys_W19_v3.json",
    # Doble-check cartas "previs claude (3).xlsx": 20 platos + 10 PE
    # (element ids resueltos vía listado, extCode == Codigo carta)
    rf"{DOWNLOADS}\fichas_easilys_faltantes_v2_20260525.json",
]

# ── Parser HTML ───────────────────────────────────────────────────────────────
def parse_ficha(eid, html):
    """Parsea una ficha HTML de Easilys. Devuelve dict o None."""
    try:
        soup = BeautifulSoup(html, 'html.parser')
        tables = soup.find_all('table')
        if not tables:
            return None

        # --- Nombre y código: primera <td> de tabla 0, párrafos internos ---
        nombre = ""
        codigo = str(eid)
        first_td = tables[0].find('td')
        if first_td:
            ps = [re.sub(r'\s+', ' ', p.get_text(' ', strip=True)).strip()
                  for p in first_td.find_all('p') if p.get_text(strip=True)]
            if len(ps) >= 2:
                nombre = ps[0]
                codigo = re.sub(r'\s+', '', ps[-1]).strip() or str(eid)
            elif len(ps) == 1:
                # nombre y código juntos en un párrafo
                raw = ps[0]
                m = re.search(r'\s+(SR\s*\d+|PDT|[A-Z]{1,3}\d{3,})\s*$', raw, re.I)
                if m:
                    nombre = raw[:m.start()].strip()
                    codigo = re.sub(r'\s+', '', m.group(1)).strip()
                else:
                    nombre = raw
            else:
                # sin párrafos: texto plano normalizado
                raw = re.sub(r'\s+', ' ', first_td.get_text(' ', strip=True)).strip()
                m = re.search(r'\s+(SR\s*\d+|PDT|[A-Z]{1,3}\d{3,})\s*$', raw, re.I)
                if m:
                    nombre = raw[:m.start()].strip()
                    codigo = re.sub(r'\s+', '', m.group(1)).strip()
                else:
                    nombre = raw or f"FICHA_{eid}"

        # Normalizar nombre
        header_text = re.sub(r'\s+', ' ', tables[0].get_text(' ', strip=True)).strip()

        # Limpiar nombre
        nombre = re.sub(r'\s+', ' ', nombre).strip()

        # --- Peso referencia ---
        peso_match = re.search(
            r'Peso\s+de\s+referencia\s*:\s*([\d.,]+)\s*g', header_text, re.I
        )
        peso = float(peso_match.group(1).replace(',', '.')) if peso_match else 0.0

        # --- Ingredientes: buscar tabla con 7 columnas en filas de datos ---
        ingredientes = []
        for t in tables:
            rows = t.find_all('tr')
            data_rows = [r for r in rows if len(r.find_all(['td', 'th'])) == 7]
            if not data_rows:
                continue
            for row in data_rows:
                tds = row.find_all(['td', 'th'])
                col0 = re.sub(r'\s+', ' ', tds[0].get_text(' ', strip=True))
                col1 = tds[1].get_text(strip=True)   # PP Si/No
                col2 = tds[2].get_text(strip=True)   # cant_neta
                col3 = tds[3].get_text(strip=True)   # unidad
                col4 = tds[4].get_text(strip=True)   # cant_bruta

                # Determinar tipo y nombre ingrediente
                es_pe = False
                if re.search(r'\s+Subrecetas?\s*$', col0, re.I):
                    es_pe = True
                    ing_name = re.sub(r'\s+Subrecetas?\s*$', '', col0, flags=re.I).strip()
                elif re.search(r'\s+Ingredientes?\s*$', col0, re.I):
                    ing_name = re.sub(r'\s+Ingredientes?\s*$', '', col0, flags=re.I).strip()
                else:
                    ing_name = col0.strip()
                    # Si empieza por PE → subreceta
                    if ing_name.upper().startswith('PE '):
                        es_pe = True

                # Parsear cantidades (formato europeo: coma decimal)
                def to_float(s):
                    try:
                        return float(s.replace(',', '.').replace(' ', ''))
                    except:
                        return 0.0

                cant_neta  = to_float(col2)
                cant_bruta = to_float(col4) if col4 not in ('0,0000', '0.0000', '') else cant_neta

                # Normalizar unidad
                unidad = col3.strip().upper()
                if unidad in ('KG', 'KILOGRAMME', 'KILOGRAMO'):
                    unidad = 'kg'
                elif unidad in ('L', 'LITRE', 'LITRO'):
                    unidad = 'L'
                elif unidad in ('PO', 'PORCION', 'PORCIONES', 'PORTION'):
                    unidad = 'PO'
                else:
                    unidad = col3.strip()

                pp = 'Si' if col1.strip().lower() in ('si', 'sí', 'yes') else 'No'

                ingredientes.append({
                    'nombre': ing_name,
                    'es_pe': es_pe,
                    'cant_neta': cant_neta,
                    'cant_bruta': cant_bruta,
                    'unidad': unidad,
                    'pp': pp,
                })
            if ingredientes:
                break  # primera tabla con datos válidos

        return {
            'id': str(eid),
            'nombre': nombre,
            'codigo': codigo,
            'peso_referencia': peso,
            'ingredientes': ingredientes,
        }
    except Exception as e:
        print(f"  PARSE ERROR {eid}: {e}")
        return None


# ── Recolectar todos los HTMLs únicos ────────────────────────────────────────
# Los lotes ANTIGUOS están cacheados por recipe.id; las descargas
# dirigidas "faltantes_*" están cacheadas por ELEMENT id (el que usa
# recipe-i18n/element/{id}). Ambos son numéricos y colisionan
# (p.ej. 5490 = recipe PE ENCAPSULAR SALSA TARTARA  vs  element
# POLLO MIEL Y MOSTAZA). Las descargas dirigidas son AUTORITATIVAS
# para sus claves -> deben SOBRESCRIBIR a los lotes antiguos.
print("Leyendo fuentes...")
all_htmls = {}  # {id_str: html_str}

def _is_override(fpath):
    return 'faltantes' in Path(fpath).name.lower()

for fpath in SOURCE_FILES:
    if not os.path.exists(fpath):
        continue
    data = json.load(open(fpath, encoding='utf-8'))
    if isinstance(data, dict) and 'fichas' in data:
        data = data['fichas']
    override = _is_override(fpath)
    count_new = 0
    count_ovr = 0
    for k, v in data.items():
        if not (isinstance(v, str) and '<!DOCTYPE' in v):
            continue
        if k in all_htmls:
            if override:
                all_htmls[k] = v   # descarga dirigida gana la colisión
                count_ovr += 1
            continue
        all_htmls[k] = v
        count_new += 1
    extra = f"  (override {count_ovr})" if override and count_ovr else ""
    print(f"  +{count_new:4d} nuevos  ({len(all_htmls)} total)  {Path(fpath).name}{extra}")

print(f"\nTotal fichas HTML únicas a parsear: {len(all_htmls)}")

# ── Parsear ───────────────────────────────────────────────────────────────────
print("\nParseando...")
cache = {}
ok = err = 0

for i, (eid, html) in enumerate(sorted(all_htmls.items(), key=lambda x: int(x[0]) if x[0].isdigit() else 0)):
    result = parse_ficha(eid, html)
    if result:
        cache[eid] = result
        # Indexar también por código externo
        code = result.get('codigo', '').strip()
        if code and code != eid and code not in cache:
            cache[code] = result
        ok += 1
    else:
        err += 1
    if (i + 1) % 200 == 0:
        print(f"  {i+1}/{len(all_htmls)} — {ok} ok, {err} errores")

print(f"\nParseadas: {ok} | Errores: {err}")
print(f"Entradas en cache (con aliases): {len(cache)}")

# ── Estadísticas ──────────────────────────────────────────────────────────────
pes   = [v for v in cache.values() if isinstance(v,dict) and v.get('nombre','').upper().startswith('PE ')]
total = [v for v in cache.values() if isinstance(v,dict) and v.get('id')]
unique_ids = {v['id'] for v in cache.values() if isinstance(v,dict) and v.get('id')}
print(f"Fichas únicas: {len(unique_ids)}")
print(f"Fichas PE: {len(set(v['id'] for v in pes if isinstance(v,dict)))}")
print(f"Fichas no-PE (platos): {len(unique_ids) - len(set(v['id'] for v in pes if isinstance(v,dict)))}")

# ── Guardar ───────────────────────────────────────────────────────────────────
print(f"\nGuardando en:\n  {CACHE_OUT}")
json.dump(cache, open(CACHE_OUT, 'w', encoding='utf-8'), ensure_ascii=False, indent=2)
size_kb = os.path.getsize(CACHE_OUT) // 1024
print(f"Listo. Tamaño: {size_kb} KB")
print(f"\n✅ Cache maestro guardado con {len(unique_ids)} fichas únicas.")
