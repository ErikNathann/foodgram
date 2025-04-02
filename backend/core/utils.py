from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

import csv
from io import StringIO


class FileFactory:
    def __init__(self, ingredients, file_format):
        self.ingredients = ingredients
        self.file_format = file_format

    def create_file(self):
        if self.file_format == 'csv':
            return self._generate_csv()
        elif self.file_format == 'txt':
            return self._generate_txt()
        elif self.file_format == 'pdf':
            return self._generate_pdf()
        return None

    def _generate_csv(self):
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ingredient', 'Total Amount'])
        for ingredient in self.ingredients:
            writer.writerow([
                ingredient['recipe__recipe_ingredients__ingredient__name'],
                ingredient['total_amount']
            ])
        output.seek(0)
        return output.getvalue()

    def _generate_txt(self):
        output = StringIO()
        for ingredient in self.ingredients:
            output.write(
                f"{ingredient['recipe__recipe_ingredients__ingredient__name']}"
                f":{ingredient['total_amount']}\n"
            )
        output.seek(0)
        return output.getvalue()

    def _generate_pdf(self):
        buffer = StringIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        p.drawString(100, height - 40, "Shopping Cart Ingredients")
        y_position = height - 60
        for ingredient in self.ingredients:
            p.drawString(
                100,
                y_position,
                f"{ingredient['recipe__recipe_ingredients__ingredient__name']}"
                f":{ingredient['total_amount']}")
            y_position -= 20
            if y_position < 60:
                p.showPage()
                y_position = height - 60
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf
