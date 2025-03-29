from django.contrib import admin
from .models import (
    Tag, Ingredient, Recipe, RecipeIngredient,
    Subscription, Favorite, ShoppingCart
)


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'slug')
    search_fields = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}
    verbose_name = ('Тег',)
    verbose_name_plural = ('Теги',)


@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'measurement_unit')
    search_fields = ('name',)
    list_filter = ('name',)
    verbose_name = ('Ингредиент',)
    verbose_name_plural = ('Ингредиенты',)


class RecipeIngredientInline(admin.TabularInline):
    model = RecipeIngredient
    extra = 1
    verbose_name = ('Ингредиент рецепта',)
    verbose_name_plural = ('Ингредиенты рецепта',)


@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'author', 'cooking_time')
    search_fields = ('name', 'author__username')
    list_filter = ('tags',)
    inlines = (RecipeIngredientInline,)
    verbose_name = ('Рецепт',)
    verbose_name_plural = ('Рецепты',)


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'author')
    search_fields = ('user__username', 'author__username')
    list_filter = ('user',)
    verbose_name = ('Подписка',)
    verbose_name_plural = ('Подписки',)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    verbose_name = ('Избранное',)
    verbose_name_plural = ('Избранные рецепты',)


@admin.register(ShoppingCart)
class ShoppingCartAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'recipe')
    search_fields = ('user__username', 'recipe__name')
    verbose_name = ('Корзина покупок',)
    verbose_name_plural = ('Корзины покупок',)
