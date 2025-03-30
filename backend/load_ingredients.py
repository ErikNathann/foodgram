import json

from food.models import Ingredient


def load_ingredients_from_json(file_path):
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
        for item in data:
            ingredient = Ingredient(
                name=item['name'],
                measurement_unit=item['measurement_unit']
            )
            ingredient.save()


load_ingredients_from_json('ingreients.json')
