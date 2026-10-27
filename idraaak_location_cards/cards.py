"""Offline, dependency-free rendering of printable location cards."""

from dataclasses import dataclass
from html import escape
import math
from pathlib import Path
from string import Template
from urllib.parse import urlencode

ARTICLE_URL = "https://idraaak.com/share-live-location-whatsapp-google-maps/"
MAX_CARDS = 1000


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float

    def __post_init__(self):
        if (
            not math.isfinite(self.latitude)
            or not math.isfinite(self.longitude)
            or not -90 <= self.latitude <= 90
            or not -180 <= self.longitude <= 180
        ):
            raise ValueError(
                "Coordinates must be finite WGS84 latitude/longitude."
            )

    @property
    def coordinates(self):
        return f"{self.latitude:.6f}, {self.longitude:.6f}"

    @property
    def maps_url(self):
        query = f"{self.latitude:.6f},{self.longitude:.6f}"
        return "https://www.google.com/maps/search/?" + urlencode(
            {"api": "1", "query": query}
        )


def render_cards(locations, title="Location cards", language="ar"):
    """Return offline HTML without tracking or automatic network calls."""
    locations = list(locations)
    if not locations:
        raise ValueError("No valid locations to export.")
    if len(locations) > MAX_CARDS:
        raise ValueError(f"Choose at most {MAX_CARDS} locations per export.")
    if language not in ("ar", "en"):
        raise ValueError("Supported card languages: ar, en.")
    ar = language == "ar"
    labels = {
        "open": "فتح الموقع في خرائط Google" if ar else "Open in Google Maps",
        "fixed": (
            "نقاط ثابتة وليست تتبعًا مباشرًا"
            if ar
            else "Static points, not live tracking"
        ),
        "coordinates": (
            "الإحداثيات: خط العرض، خط الطول"
            if ar
            else "Coordinates: latitude, longitude"
        ),
        "privacy": (
            "هذا الملف يحتوي مواقعك. شاركه فقط مع من تريد إطلاعهم عليها. "
            "لا ترسل هذه الصفحة بيانات تلقائيًا؛ فتح رابط الخرائط يرسل "
            "الإحداثيات إلى Google."
            if ar
            else "This file contains your locations. Share it only with "
            "intended recipients. This page sends no data automatically; "
            "opening a map link sends its coordinates to Google."
        ),
        "help": (
            "شرح الفرق بين مشاركة نقطة ثابتة والموقع المباشر على إدراك"
            if ar
            else "Static points and live location sharing explained "
            "on Idraaak (Arabic)"
        ),
        "print": "طباعة أو حفظ PDF" if ar else "Print or save PDF",
        "count": (
            f"عدد المواقع: {len(locations)}"
            if ar
            else f"Locations: {len(locations)}"
        ),
    }
    items = []
    for index, location in enumerate(locations, start=1):
        if not isinstance(location, Location):
            raise TypeError("Each card must be a Location.")
        column = (2 if index % 2 else 1) if ar else (1 if index % 2 else 2)
        items.append(
            f'<article class="card" style="grid-row:{(index + 1) // 2};'
            f'grid-column:{column}">'
            f'<div class="number">{index:02d}</div>'
            f'<h2 dir="auto">{escape(str(location.name))}</h2>'
            f'<p class="label">{labels["coordinates"]}</p>'
            f'<p class="coordinates" dir="ltr">{location.coordinates}</p>'
            '<a class="map-link" '
            f'href="{escape(location.maps_url, quote=True)}">'
            f'{labels["open"]}</a>'
            f'<p class="url" dir="ltr">{escape(location.maps_url)}</p>'
            "</article>"
        )
    direction = "rtl" if ar else "ltr"
    template = Template(
        Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    )
    return template.substitute(
        language=language,
        direction=direction,
        title=escape(str(title)),
        count=labels["count"],
        fixed=labels["fixed"],
        print_label=labels["print"],
        cards="".join(items),
        privacy=labels["privacy"],
        article_url=ARTICLE_URL,
        help=labels["help"],
    )
