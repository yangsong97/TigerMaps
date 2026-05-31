from django.contrib import admin

from .models import Building, Section, User


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'building_id', 'lat', 'lon', 'searched')
    search_fields = ('names',)
    ordering = ('-searched',)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ('listings', 'title', 'section', 'building_name', 'day', 'time', 'searched')
    list_filter = ('day',)
    search_fields = ('listings', 'title', 'building_name')
    raw_id_fields = ('building',)
    ordering = ('listings',)


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('netid',)
    search_fields = ('netid',)
