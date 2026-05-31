from django.db import models
from datetime import datetime
import json
import re


class JSONArrayField(models.TextField):
    """Stores a list of strings as a JSON-encoded text column.

    Using a plain text column keeps the schema identical on both SQLite
    (local development) and PostgreSQL (production). The app only ever
    appends to / removes from / membership-tests these lists in Python, so
    a native PostgreSQL ArrayField would add a backend-specific column type
    (and migration) for no functional gain.
    """
    def from_db_value(self, value, expression, connection):
        if value is None:
            return []
        return json.loads(value)

    def to_python(self, value):
        if isinstance(value, list):
            return value
        if value is None:
            return []
        return json.loads(value)

    def get_prep_value(self, value):
        if value is None:
            return '[]'
        if isinstance(value, str):
            return value
        return json.dumps(value)

# Natural keys for buildings
class BuildingManager(models.Manager):
    def get_by_natural_key(self, building_id):
        return self.get(building_id=building_id)

class Building(models.Model):
    objects = BuildingManager()

    names = models.CharField(max_length=1000, blank=True, null=True)
    building_id = models.IntegerField(default=-1)
    lat = models.CharField(max_length=200, blank=True, null=True)
    lon = models.CharField(max_length=200, blank=True, null=True)
    searched = models.IntegerField(default=0)

    def natural_key(self):
        return self.building_id

    def __str__(self):
        return self.names.split("/")[0]

# A section of a course, such as a precept or lecture
class Section(models.Model):
    course_id = models.CharField(max_length=10, blank=True, null=True)
    building = models.ForeignKey(Building, blank=True, null=True, on_delete=models.CASCADE)
    # Storing the name here speeds up the search in the heatmap
    building_name = models.CharField(max_length=100, blank=True, null=True)
    room = models.CharField(max_length=200, blank=True, null=True)
    area = models.CharField(max_length=200, blank=True, null=True)
    section = models.CharField(max_length=200, blank=True, null=True)
    listings = models.CharField(max_length=200, blank=True, null=True)
    day = models.CharField(max_length=200, blank=True, null=True)
    title = models.CharField(max_length=200, blank=True, null=True)
    starttime = models.TimeField(blank=True, null=True)
    endtime = models.TimeField(blank=True, null=True)
    time = models.CharField(max_length=200, blank=True, null=True)
    enroll = models.CharField(max_length=200, blank=True, null=True)
    capacity = models.CharField(max_length=200, blank=True, null=True)
    searched = models.IntegerField(default=0)

    def __str__(self):
        return self.listings[1:]

class User(models.Model):
    netid = models.CharField(max_length=20, blank=True, null=True)
    courses = JSONArrayField(default='[]')
    buildings = JSONArrayField(default='[]')
