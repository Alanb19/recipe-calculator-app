import json
import os
import pickle
from dataclasses import dataclass, field
from pathlib import Path

CACHE_JSON = os.environ.get(
    "EASILYS_CACHE",
    r"C:\Users\Usuario\OneDrive - Nora Real Food\Escritorio\proyecto claude sincronizacion hoja de produccion\files\FICHAS_EASILYS_CACHE.json",
)
PICKLE_PATH = Path(__file__).parent / ".recipes_cache.pkl"


@dataclass
class Component:
    name: str
    quantity: float   # per 1 portion (cant_neta from Easilys)
    unit: str         # "kg", "L", "PO"
    type: str         # "subreceta" | "ingrediente"
    is_principal: bool = False


@dataclass
class Recipe:
    id: str           # Easilys internal id
    code: str         # external code
    name: str
    weight_per_portion: float  # grams
    components: list = field(default_factory=list)


def _load_from_json(path: str) -> dict[str, Recipe]:
    with open(path, encoding="utf-8") as f:
        raw = json.load(f)

    recipes: dict[str, Recipe] = {}
    for easilys_id, data in raw.items():
        recipe = Recipe(
            id=easilys_id,
            code=str(data.get("codigo", easilys_id)),
            name=str(data.get("nombre", "")).strip(),
            weight_per_portion=float(data.get("peso_referencia") or 0),
        )
        for ing in data.get("ingredientes", []):
            qty = ing.get("cant_neta") or ing.get("cant_bruta") or 0
            recipe.components.append(Component(
                name=str(ing.get("nombre", "")).strip(),
                quantity=float(qty),
                unit=str(ing.get("unidad", "")).strip(),
                type="subreceta" if ing.get("es_pe") else "ingrediente",
                is_principal=ing.get("pp", "No") == "Si",
            ))
        # index by internal id AND by external code
        recipes[easilys_id] = recipe
        ext = str(data.get("codigo", "")).strip()
        if ext and ext not in recipes:
            recipes[ext] = recipe

    return recipes


def load_recipes(force_reload: bool = False) -> dict[str, Recipe]:
    json_path = Path(CACHE_JSON)
    loader_mtime = Path(__file__).stat().st_mtime
    if not force_reload and PICKLE_PATH.exists():
        pkl_mtime = PICKLE_PATH.stat().st_mtime
        src_mtime = json_path.stat().st_mtime if json_path.exists() else 0
        if pkl_mtime >= max(src_mtime, loader_mtime):
            with open(PICKLE_PATH, "rb") as f:
                return pickle.load(f)

    recipes = _load_from_json(CACHE_JSON)
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump(recipes, f)
    return recipes
