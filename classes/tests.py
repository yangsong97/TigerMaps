"""Tests for the classes app.

Run with the local (SQLite) settings, which avoid the Postgres/CAS
requirements of the production configuration:

    python manage.py test --settings=classmaps.settings_local
"""
from datetime import time

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Building, Section, User
from . import views


class JSONArrayFieldTests(TestCase):
    """The custom JSONArrayField is used to store saved courses/buildings
    when running without PostgreSQL ArrayField support."""

    def test_round_trip_preserves_list(self):
        user = User.objects.create(netid="abc123", courses=["1", "2"], buildings=["3"])
        reloaded = User.objects.get(pk=user.pk)
        self.assertEqual(reloaded.courses, ["1", "2"])
        self.assertEqual(reloaded.buildings, ["3"])

    def test_empty_list_round_trip(self):
        user = User.objects.create(netid="empty")
        reloaded = User.objects.get(pk=user.pk)
        self.assertEqual(reloaded.courses, [])
        self.assertEqual(reloaded.buildings, [])

    def test_append_then_save_persists(self):
        user = User.objects.create(netid="appender")
        # Re-fetch so the field is deserialized into a real list.
        user = User.objects.get(pk=user.pk)
        user.courses.append("42")
        user.save()
        self.assertEqual(User.objects.get(pk=user.pk).courses, ["42"])


class ModelStrTests(TestCase):
    def test_building_str_uses_first_alias(self):
        b = Building(names="Friend Center/Friend/EQuad", building_id=1)
        self.assertEqual(str(b), "Friend Center")

    def test_section_str_strips_leading_separator(self):
        # listings are stored as "/DEPT NUM[/DEPT NUM...]" (see scraping/merge.py)
        s = Section(listings="/COS 333/MAT 378")
        self.assertEqual(str(s), "COS 333/MAT 378")


class SearchTermsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.friend = Building.objects.create(
            names="Friend Center/Friend", building_id=1, lat="40.35", lon="-74.65"
        )
        cls.frist = Building.objects.create(
            names="Frist Campus Center/Frist", building_id=2, lat="40.34", lon="-74.65"
        )
        cls.cos333 = Section.objects.create(
            listings="/COS 333", title="Advanced Programming Techniques",
            section="L01", time="MWF 11:00-11:50", building=cls.friend,
            building_name="Friend Center", day="MWF",
        )
        cls.cos126 = Section.objects.create(
            listings="/COS 126", title="Computer Science: An Interdisciplinary Approach",
            section="L01", time="MWF 10:00-10:50", building=cls.friend,
            building_name="Friend Center", day="MWF",
        )
        cls.crosslisted = Section.objects.create(
            listings="/COS 233/MAT 233", title="Cross Listed", section="L01",
            time="TTh 13:30-14:50", building=cls.frist,
            building_name="Frist Campus Center", day="TTh",
        )

    def test_none_query_returns_everything(self):
        courses, buildings, names = views.search_terms(None)
        self.assertEqual(courses.count(), 3)
        self.assertEqual(buildings.count(), 2)

    def test_empty_query_returns_no_buildings(self):
        courses, buildings, names = views.search_terms("")
        self.assertEqual(courses.count(), 3)
        self.assertEqual(buildings.count(), 0)

    def test_search_by_department(self):
        courses, buildings, names = views.search_terms("COS")
        listings = sorted(str(c) for c in courses)
        self.assertEqual(listings, ["COS 126", "COS 233/MAT 233", "COS 333"])

    def test_search_by_listing_number(self):
        courses, _, _ = views.search_terms("COS 333")
        self.assertEqual([str(c) for c in courses], ["COS 333"])

    def test_concatenated_dept_and_number(self):
        # "cos333" with no space should still resolve to COS 333.
        courses, _, _ = views.search_terms("cos333")
        self.assertIn("COS 333", [str(c) for c in courses])

    def test_search_by_building_name(self):
        _, buildings, _ = views.search_terms("Frist")
        self.assertEqual([b.building_id for b in buildings], [2])

    def test_invalid_regex_does_not_raise(self):
        # An unbalanced bracket is an invalid regex; it must be handled gracefully.
        courses, buildings, names = views.search_terms("[")
        self.assertEqual(courses.count(), 0)
        self.assertEqual(buildings.count(), 0)

    def test_comma_is_ored(self):
        courses, _, _ = views.search_terms("COS 126, COS 333")
        self.assertEqual(sorted(str(c) for c in courses), ["COS 126", "COS 333"])


class SearchDayTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        b = Building.objects.create(names="X", building_id=1)
        cls.mwf = Section.objects.create(listings="/A 1", day="MWF", building=b)
        cls.tth = Section.objects.create(listings="/B 2", day="TTh", building=b)
        cls.th_only = Section.objects.create(listings="/C 3", day="Th", building=b)

    def _filter(self, **days):
        flags = {"mon": None, "tues": None, "wed": None, "thurs": None, "fri": None}
        flags.update(days)
        return views.search_day(
            Section.objects.all(), None,
            flags["mon"], flags["tues"], flags["wed"], flags["thurs"], flags["fri"],
        )

    def test_no_day_selected_returns_all(self):
        self.assertEqual(self._filter().count(), 3)

    def test_monday_filter(self):
        results = self._filter(mon="M")
        self.assertEqual([str(s) for s in results], ["A 1"])

    def test_tuesday_excludes_thursday_only(self):
        # The key regex T(?!h): Tuesday matches, a Thursday-only class must not.
        results = self._filter(tues="T")
        listings = sorted(str(s) for s in results)
        self.assertEqual(listings, ["B 2"])

    def test_thursday_matches_tth_and_th(self):
        results = self._filter(thurs="Th")
        listings = sorted(str(s) for s in results)
        self.assertEqual(listings, ["B 2", "C 3"])


class SearchTimeAndDayStringTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        b = Building.objects.create(names="X", building_id=1)
        cls.morning = Section.objects.create(
            listings="/A 1", starttime=time(10, 0), endtime=time(10, 50), building=b
        )
        cls.afternoon = Section.objects.create(
            listings="/B 2", starttime=time(13, 30), endtime=time(14, 50), building=b
        )

    def test_search_time_matches_class_in_session(self):
        results = views.search_time("10:30AM", Section.objects.all())
        self.assertEqual([str(s) for s in results], ["A 1"])

    def test_search_time_invalid_input_returns_empty(self):
        results = views.search_time("not-a-time", Section.objects.all())
        self.assertEqual(results.count(), 0)

    def test_get_day_string(self):
        self.assertEqual(views.get_day_string("M", None, "W", None, "F"), "MWF")
        self.assertEqual(views.get_day_string(None, "T", None, "Th", None), "TTh")
        self.assertEqual(views.get_day_string(None, None, None, None, None), "")


class ViewAuthTests(TestCase):
    def test_index_requires_login(self):
        response = self.client.get(reverse("classes:index"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("/accounts/login", response["Location"])

    def test_about_is_public(self):
        response = self.client.get("/about/")
        self.assertEqual(response.status_code, 200)


class SaveFlowTests(TestCase):
    def setUp(self):
        AuthUser = get_user_model()
        self.auth_user = AuthUser.objects.create_user(username="netid1", password="pw")
        self.client.force_login(self.auth_user)
        self.building = Building.objects.create(
            names="Friend Center/Friend", building_id=1, lat="40.35", lon="-74.65"
        )
        self.section = Section.objects.create(
            listings="/COS 333", title="Adv Prog", section="L01",
            time="MWF 11:00-11:50", building=self.building,
            building_name="Friend Center", day="MWF",
        )

    def test_index_creates_app_user(self):
        self.client.get(reverse("classes:index"))
        self.assertTrue(User.objects.filter(netid="netid1").exists())

    def test_save_and_remove_building(self):
        self.client.get(reverse("classes:index"))  # ensure app user exists
        save_id = f"{self.building.id}b"
        self.client.post(reverse("classes:save"), {"s": save_id})
        user = User.objects.get(netid="netid1")
        self.assertIn(str(self.building.id), user.buildings)

        self.client.post(reverse("classes:remove"), {"r": save_id})
        user = User.objects.get(netid="netid1")
        self.assertNotIn(str(self.building.id), user.buildings)

    def test_save_increments_searched_count(self):
        self.client.get(reverse("classes:index"))
        self.client.post(reverse("classes:save"), {"s": f"{self.section.id}c"})
        self.section.refresh_from_db()
        self.assertEqual(self.section.searched, 1)

    def test_saved_locations_returns_json(self):
        self.client.get(reverse("classes:index"))
        self.client.post(reverse("classes:save"), {"s": f"{self.section.id}c"})
        response = self.client.get(reverse("classes:saved_locations"))
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["courses"]), 1)
        self.assertEqual(data["courses"][0]["building_name"], "Friend Center")


class QueryApiTests(TestCase):
    def setUp(self):
        AuthUser = get_user_model()
        self.auth_user = AuthUser.objects.create_user(username="netid2", password="pw")
        self.client.force_login(self.auth_user)
        self.building = Building.objects.create(
            names="Frist Campus Center/Frist", building_id=2, lat="40.34", lon="-74.65"
        )
        self.section = Section.objects.create(
            listings="/COS 226", title="Algorithms and Data Structures", section="L01",
            time="MWF 11:00-11:50", building=self.building,
            building_name="Frist Campus Center", day="MWF", enroll="100",
        )

    def test_query_returns_matches(self):
        response = self.client.get(reverse("classes:query"), {"q": "COS 226"})
        self.assertEqual(response.status_code, 200)
        results = response.json()
        self.assertTrue(any(r["type"] == "course" for r in results))

    def test_enroll_aggregates_by_building(self):
        response = self.client.get(reverse("classes:enroll"), {"q": "COS"})
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["Frist Campus Center"]["students"], 100)
        self.assertEqual(data["Frist Campus Center"]["courses"], 1)
