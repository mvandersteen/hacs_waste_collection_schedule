import logging
import math
from datetime import date, timedelta

import requests
from waste_collection_schedule import Collection
from waste_collection_schedule.exceptions import SourceArgumentNotFound
from waste_collection_schedule.service.ArcGis import ArcGisError, geocode

TITLE = "North West Resource Recovery and Recycling"
DESCRIPTION = "Source for North West Resource Recovery and Recycling (NWRRR) waste collection in Northwest Tasmania, Australia."
URL = "https://www.nwrrr.com.au"
COUNTRY = "au"

TEST_CASES = {
    "14 Stirling Street Burnie": {"address": "14 Stirling Street, Burnie"},
    "1 Formby Road Devonport": {"address": "1 Formby Road, Devonport"},
    "Main Road Strahan": {"address": "Main Road, Strahan"},
    "Esmond Street Rosebery": {"address": "Esmond Street, Rosebery"},
    "17 Church Street Stanley": {"address": "17 Church Street, Stanley"},
}

ICON_MAP = {
    "General Waste": "mdi:trash-can",
    "Recycling": "mdi:recycle",
    "FOGO": "mdi:leaf",
}

HOW_TO_GET_ARGUMENTS_DESCRIPTION = {
    "en": "Visit https://www.nwrrr.com.au/map and search for your address to find your collection zone. Use your full street address including suburb.",
}

PARAM_DESCRIPTIONS = {
    "en": {
        "address": "Full street address including suburb (e.g. '14 Stirling Street, Burnie')",
    },
}

PARAM_TRANSLATIONS = {
    "en": {
        "address": "Street Address",
    },
}

_LOGGER = logging.getLogger(__name__)

GEOJSON_URL = "https://nwrrr.eskspatial.com.au/assets/all_councils.geojson"

# GeoJSON coordinates are in EPSG:3857 (Web Mercator).
# ArcGIS geocoder returns WGS84 (EPSG:4326), so the point must be converted.

_FREQ_DAYS = {
    "weekly": 7,
    "bi-weekly": 14,
    "monthly": 28,
}


def _to_epsg3857(lon: float, lat: float):
    """Convert WGS84 lon/lat to Web Mercator (EPSG:3857) x/y."""
    x = lon * 20037508.34 / 180
    y = (
        math.log(math.tan((90 + lat) * math.pi / 360))
        / (math.pi / 180)
        * 20037508.34
        / 180
    )
    return x, y


def _point_in_polygon(x: float, y: float, polygon: list) -> bool:
    """Ray-casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    p1x, p1y = polygon[0]
    for i in range(1, n + 1):
        p2x, p2y = polygon[i % n]
        if min(p1y, p2y) < y <= max(p1y, p2y) and x <= max(p1x, p2x):
            if p1y != p2y:
                xinters = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
            if p1x == p2x or x <= xinters:
                inside = not inside
        p1x, p1y = p2x, p2y
    return inside


def _next_occurrences(seed_str, freq, weeks_ahead=16):
    """Generate upcoming collection dates from a seed date and frequency string."""
    if not seed_str or not freq or freq not in _FREQ_DAYS:
        return []
    seed = date.fromisoformat(seed_str)
    delta = timedelta(days=_FREQ_DAYS[freq])
    today = date.today()
    end = today + timedelta(weeks=weeks_ahead)
    while seed < today:
        seed += delta
    dates = []
    while seed <= end:
        dates.append(seed)
        seed += delta
    return dates


class Source:
    def __init__(self, address: str):
        self._address = address.strip()

    def fetch(self) -> list[Collection]:
        try:
            loc = geocode(f"{self._address}, Tasmania, Australia")
        except ArcGisError as e:
            raise SourceArgumentNotFound("address", self._address) from e

        mx, my = _to_epsg3857(loc["x"], loc["y"])

        r = requests.get(GEOJSON_URL, timeout=60)
        r.raise_for_status()
        features = r.json()["features"]

        zone = None
        for feature in features:
            geom = feature.get("geometry")
            if not geom:
                continue
            for polygon in geom["coordinates"]:
                if _point_in_polygon(mx, my, polygon[0]):
                    zone = feature["properties"]
                    break
            if zone is not None:
                break

        if zone is None:
            raise SourceArgumentNotFound("address", self._address)

        _LOGGER.debug("Address %s → zone %s", self._address, zone.get("region_name"))

        entries: list[Collection] = []

        for d in _next_occurrences(
            zone.get("landfill_date"), zone.get("landfill_freq")
        ):
            entries.append(Collection(d, "General Waste", ICON_MAP["General Waste"]))

        for d in _next_occurrences(
            zone.get("recycling_date"), zone.get("recycling_freq")
        ):
            entries.append(Collection(d, "Recycling", ICON_MAP["Recycling"]))

        for d in _next_occurrences(zone.get("fogo_date"), zone.get("fogo_freq")):
            entries.append(Collection(d, "FOGO", ICON_MAP["FOGO"]))

        return entries
