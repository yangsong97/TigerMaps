"""Seed the database with demo Princeton building and course data.

Reads the scraped JSON in ``scraping/`` and populates the Building and
Section tables so the public demo has real content to explore. Safe to run
on every deploy: it is a no-op once data exists unless ``--force`` is given.

    python manage.py seed_demo                 # seed only if empty
    python manage.py seed_demo --force         # wipe and reseed
    python manage.py seed_demo --max-courses 200
"""
import json
import os
from datetime import datetime

from django.conf import settings
from django.core.management.base import BaseCommand

from classes.models import Building, Section


def _parse_time(value):
    """Parse a scraped time string (e.g. '01:30:00 pm') into a time, or None."""
    value = (value or "").strip()
    if not value:
        return None
    for fmt in ("%I:%M:%S %p", "%I:%M %p", "%H:%M:%S", "%H:%M"):
        try:
            return datetime.strptime(value, fmt).time()
        except ValueError:
            continue
    return None


def _format_time(t):
    """Render a time as a compact 12-hour label, e.g. '1:30pm'."""
    if not t:
        return ""
    return t.strftime("%I:%M%p").lstrip("0").lower()


class Command(BaseCommand):
    help = "Seed the database with demo Princeton building and course data."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true",
            help="Delete existing buildings/sections and reseed from scratch.",
        )
        parser.add_argument(
            "--max-courses", type=int, default=0,
            help="Limit the number of courses seeded (0 = all). Useful for tests.",
        )

    def handle(self, *args, **options):
        scraping_dir = os.path.join(settings.BASE_DIR, "scraping")

        if Building.objects.exists() or Section.objects.exists():
            if not options["force"]:
                self.stdout.write(
                    "Database already contains data; skipping seed "
                    "(use --force to wipe and reseed)."
                )
                return
            self.stdout.write("Clearing existing buildings and sections...")
            Section.objects.all().delete()
            Building.objects.all().delete()

        buildings_by_id = self._seed_buildings(scraping_dir)
        self._seed_sections(scraping_dir, buildings_by_id, options["max_courses"])
        self.stdout.write(self.style.SUCCESS("Demo data seeded."))

    def _seed_buildings(self, scraping_dir):
        with open(os.path.join(scraping_dir, "buildids.json")) as f:
            raw = json.load(f)
        entries = raw.values() if isinstance(raw, dict) else raw

        objs = []
        for b in entries:
            try:
                building_id = int(b["building_id"])
            except (KeyError, TypeError, ValueError):
                continue
            objs.append(Building(
                names=b.get("names") or "",
                building_id=building_id,
                lat=b.get("lat"),
                lon=b.get("lon"),
            ))
        Building.objects.bulk_create(objs)
        self.stdout.write(f"Seeded {len(objs)} buildings.")
        return {b.building_id: b for b in Building.objects.all()}

    def _seed_sections(self, scraping_dir, buildings_by_id, max_courses):
        with open(os.path.join(scraping_dir, "courses.json")) as f:
            courses = json.load(f)
        if max_courses:
            courses = courses[:max_courses]

        sections = []
        for course in courses:
            listings = "".join(
                "/" + l.get("dept", "") + " " + l.get("number", "")
                for l in course.get("listings", [])
            )
            title = course.get("title", "")
            area = course.get("area", "")

            for meeting in course.get("classes", []):
                building = None
                bldg_id = meeting.get("bldg_id")
                if bldg_id:
                    try:
                        building = buildings_by_id.get(int(bldg_id))
                    except (TypeError, ValueError):
                        building = None

                start = _parse_time(meeting.get("starttime"))
                end = _parse_time(meeting.get("endtime"))
                days = meeting.get("days", "") or ""
                building_name = (
                    building.names.split("/")[0] if building
                    else (meeting.get("bldg") or "")
                )
                time_label = days
                if start:
                    time_label = (time_label + " " + _format_time(start)).strip()
                    if end:
                        time_label += "-" + _format_time(end)

                sections.append(Section(
                    course_id=course.get("courseid"),
                    building=building,
                    building_name=building_name,
                    room=meeting.get("roomnum"),
                    area=area,
                    section=meeting.get("section"),
                    listings=listings,
                    day=days,
                    title=title,
                    starttime=start,
                    endtime=end,
                    time=time_label,
                    enroll=meeting.get("enroll"),
                    capacity=meeting.get("limit"),
                ))

        Section.objects.bulk_create(sections, batch_size=500)
        self.stdout.write(f"Seeded {len(sections)} course sections.")
