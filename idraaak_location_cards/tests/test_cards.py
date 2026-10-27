"""Regression checks for exported HTML and coordinate handling."""

import unittest
from html.parser import HTMLParser
from urllib.parse import parse_qs, urlparse

from idraaak_location_cards.cards import Location, render_cards


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.remote_assets = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "a":
            self.links.append(attrs.get("href"))
        if tag == "script":
            self.scripts += 1
        if tag in ("script", "img", "iframe", "link"):
            self.remote_assets.append(attrs)


class CardsTest(unittest.TestCase):
    def test_google_maps_coordinate_order(self):
        location = Location("Test", 52.3731, 4.8936)
        query = parse_qs(urlparse(location.maps_url).query)
        self.assertEqual(query["query"], ["52.373100,4.893600"])
        self.assertEqual(query["api"], ["1"])

    def test_invalid_coordinates(self):
        for lat, lon in [
            (91, 0),
            (-91, 0),
            (0, 181),
            (0, -181),
            (float("nan"), 0),
            (0, float("inf")),
        ]:
            with self.subTest(lat=lat, lon=lon), self.assertRaises(ValueError):
                Location("Invalid", lat, lon)

    def test_boundaries_and_southern_western_coordinates(self):
        self.assertEqual(
            Location("Boundary", -90, -180).coordinates,
            "-90.000000, -180.000000",
        )
        self.assertEqual(
            Location("Zero", 0, 0).coordinates, "0.000000, 0.000000"
        )

    def test_feature_and_title_cannot_inject_html(self):
        document = render_cards(
            [Location("<script>alert(1)</script>", 1, 2)],
            "<img src=x onerror=alert(1)>",
            "ar",
        )
        parser = Links()
        parser.feed(document)
        self.assertEqual(parser.scripts, 0)
        self.assertEqual(parser.remote_assets, [])
        self.assertIn("&lt;script&gt;", document)
        self.assertIn("&lt;img", document)

    def test_arabic_and_english_layouts(self):
        places = [Location("اسم عربي & English", 1, 2)]
        for lang, direction in [("ar", "rtl"), ("en", "ltr")]:
            doc = render_cards(places, language=lang)
            self.assertIn(f'<html lang="{lang}" dir="{direction}">', doc)
            self.assertIn("اسم عربي &amp; English", doc)
            parser = Links()
            parser.feed(doc)
            self.assertEqual(len(parser.links), 2)
            self.assertEqual(parser.remote_assets, [])

    def test_no_empty_or_excessive_exports(self):
        with self.assertRaises(ValueError):
            render_cards([])
        with self.assertRaises(ValueError):
            render_cards([Location("Point", 0, 0)] * 1001)


if __name__ == "__main__":
    unittest.main()
