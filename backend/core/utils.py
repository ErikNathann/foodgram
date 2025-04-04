from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from django.http import HttpResponse
from rest_framework.response import Response
from rest_framework import status

import csv
from io import StringIO


class FileFactory:
    @classmethod
    def create_file(cls, ingredients, file_format):
        """Создает файл в нужном формате."""
        if file_format == 'csv':
            return cls._generate_csv(ingredients)
        elif file_format == 'txt':
            return cls._generate_txt(ingredients)
        elif file_format == 'pdf':
            return cls._generate_pdf(ingredients)
        return None

    @classmethod
    def _generate_csv(cls, ingredients):
        """Генерация CSV файла"""
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['Ingredient', 'Total Amount'])
        for ingredient in ingredients:
            writer.writerow([
                ingredient['recipe__recipe_ingredients__ingredient__name'],
                ingredient['total_amount']
            ])
        output.seek(0)
        return output.getvalue()

    @classmethod
    def _generate_txt(cls, ingredients):
        """Генерация TXT файла"""
        output = StringIO()
        for ingredient in ingredients:
            output.write(
                f"{ingredient['recipe__recipe_ingredients__ingredient__name']}"
                f":{ingredient['total_amount']}\n"
            )
        output.seek(0)
        return output.getvalue()

    @classmethod
    def _generate_pdf(cls, ingredients):
        """Генерация PDF файла"""
        buffer = StringIO()
        p = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter
        p.drawString(100, height - 40, "Shopping Cart Ingredients")
        y_position = height - 60
        for ingredient in ingredients:
            p.drawString(
                100,
                y_position,
                f"{ingredient['recipe__recipe_ingredients__ingredient__name']}"
                f":{ingredient['total_amount']}"
            )
            y_position -= 20
            if y_position < 60:
                p.showPage()
                y_position = height - 60
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        return pdf


class FileResponseFactory:
    @classmethod
    def create_response(cls, file_data, file_format):
        """Создает HttpResponse с файлом в зависимости от формата."""
        if file_format == 'csv':
            response = HttpResponse(file_data, content_type='text/csv')
            response[
                'Content-Disposition'
            ] = 'attachment; filename="shopping_cart.csv"'
        elif file_format == 'txt':
            response = HttpResponse(file_data, content_type='text/plain')
            response[
                'Content-Disposition'
            ] = 'attachment; filename="shopping_cart.txt"'
        elif file_format == 'pdf':
            response = HttpResponse(file_data, content_type='application/pdf')
            response[
                'Content-Disposition'
            ] = 'attachment; filename="shopping_cart.pdf"'
        else:
            return Response(
                {'detail': 'Unsupported file format'},
                status=status.HTTP_400_BAD_REQUEST
            )
        return response
