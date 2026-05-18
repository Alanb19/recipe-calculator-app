# Calculadora Nora — standalone (offline)

Generador de `Calculadora_Nora.html`: una calculadora de recetas de un solo
archivo, **100% offline** (`file://`, sin servidor), para Nora Real Food.

> ⚠️ **Repo público — sin datos propietarios.** Ni `FICHAS_EASILYS_CACHE.json`
> ni `Calculadora_Nora.html` (embebe ~2525 recetas de Easilys) se versionan:
> están en `.gitignore`. Aquí solo va el **código** que los regenera.

## Archivos

| Script | Qué hace |
|---|---|
| `build_master_cache.py` | Parsea las fichas HTML descargadas de Easilys → `FICHAS_EASILYS_CACHE.json`. Cachea por **Easilys element id** (no por `codigo`). Las descargas dirigidas (`fichas..._faltantes_*`) **sobrescriben** a los lotes antiguos para evitar la colisión recipe.id vs element.id. |
| `build_calc.py` | Genera `Calculadora_Nora.html` desde la cache. Dedup por `id`; índice de nombres prefiere la ficha con ingredientes. |
| `verify_calc.py` | Regresión: reconstruye y comprueba 0 recetas perdidas, escalado correcto, PE irresolubles ≤ baseline, expansión recursiva sin ciclos, 100% offline. |

## Uso

```bash
# 1. (semanal) descargar fichas nuevas: pegar el script de consola Easilys,
#    subir el JSON resultante a C:\Users\Usuario\Downloads
# 2. añadir el nuevo lote a SOURCE_FILES en build_master_cache.py
python build_master_cache.py     # regenera la cache
python verify_calc.py            # build_calc + asserts (debe quedar verde)
```

La ruta de la cache se puede override con la variable de entorno
`EASILYS_CACHE` (por defecto apunta a la carpeta local del proyecto de
sincronización).

## Notas

- La cache es la **fuente de verdad** y NO se versiona (propietaria + grande).
- `Calculadora_Nora.html` se entrega aparte (Escritorio / carpeta de la app),
  no por git, porque embebe las recetas.
- Pendiente conocido: re-key total de la cache por element id para eliminar
  toda colisión recipe.id↔element.id (afecta resolución de varios platos de carta).
