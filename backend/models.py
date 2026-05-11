from pydantic import BaseModel, Field, validator
from typing import List


class IngredientInput(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    quantity: float = Field(..., gt=0, description="grams per serving")


class IngredientOutput(BaseModel):
    name: str
    grams: float
    kilograms: float


class RecipeRequest(BaseModel):
    ingredients: List[IngredientInput] = Field(..., min_items=1, max_items=200)
    servings: int = Field(..., ge=1, le=10000)


class RecipeResponse(BaseModel):
    results: List[IngredientOutput]


class PredictionResponse(BaseModel):
    recommended_servings: int
