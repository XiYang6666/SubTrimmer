import os

GEOIP_DB_URL = os.environ.get(
    "GEOIP_DB_URL",
    "https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/country.mmdb",
)
GEOIP_DB_PATH = os.environ.get("GEOIP_DB_PATH", "./data/GeoLite2-Country.mmdb")
