from models import IngredientOutput

_HIGH_VOLUME_THRESHOLD_G = 500
_HIGH_VOLUME_FACTOR = 0.2
_MANY_INGREDIENTS_THRESHOLD = 5
_MANY_INGREDIENTS_FACTOR = 0.1


def scale_recipe(data) -> list[IngredientOutput]:
    results = []
    for ing in data.ingredients:
        total = ing.quantity * data.servings
        results.append(
            IngredientOutput(
                name=ing.name,
                grams=round(total, 2),
                kilograms=round(total / 1000, 3),
            )
        )
    return results


def predict_servings(data) -> int:
    total_grams = sum(i.quantity for i in data.ingredients)
    factor = 1.0
    # Scale up estimate for high-volume or complex recipes
    if total_grams > _HIGH_VOLUME_THRESHOLD_G:
        factor += _HIGH_VOLUME_FACTOR
    if len(data.ingredients) > _MANY_INGREDIENTS_THRESHOLD:
        factor += _MANY_INGREDIENTS_FACTOR
    return max(int(data.servings * factor), 1)
