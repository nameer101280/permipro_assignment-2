"""Load mock data files for geo and regulation sources."""
from functools import lru_cache
from pathlib import Path
import csv

from django.conf import settings


GEO_FILE = "mock_geo_data.csv"
REGULATION_FILE = "mock_regulation_data.txt"


@lru_cache(maxsize=1)
def load_geo_rows() -> list:
    path = Path(settings.BASE_DIR) / GEO_FILE
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


@lru_cache(maxsize=1)
def load_regulation_text() -> str:
    path = Path(settings.BASE_DIR) / REGULATION_FILE
    return path.read_text(encoding="utf-8")
