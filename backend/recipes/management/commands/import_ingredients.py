import csv
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from recipes.models import Ingredient


class Command(BaseCommand):
    help = 'Загрузка данных из CSV-файлов'

    def bulk_create_ingredients(self, model, rows):
        ingredients = [
            model(name=name, measurement_unit=measurement_unit)
            for name, measurement_unit in rows
        ]

        model.objects.bulk_create(ingredients, ignore_conflicts=True)

        return len(rows)

    def handle(self, *args, **options):
        csv_path = os.path.join(settings.BASE_DIR, 'data', 'ingredients.csv')

        with open(csv_path, encoding='utf8') as csvfile:
            reader = csv.reader(csvfile)
            rows = list(reader)

            rows_count = len(rows)
            bulk_count = self.bulk_create_ingredients(Ingredient, rows)

        self.stdout.write(
            self.style.SUCCESS(
                f'Импорт ингредиентов завершился успешно! '
                f'Всего {bulk_count} записей было добавлено из {rows_count}.'
            )
        )
