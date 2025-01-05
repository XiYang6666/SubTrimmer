from typing import TypedDict, Optional
import ipaddress
import json


class CountryData(TypedDict):
    code: int
    en: str
    zh: str
    tw: str
    locale: str
    emoji: str


with open("./data/countryData.json", encoding="utf-8") as f:
    country_data: list[CountryData] = json.load(f)
country_data.append({
    "code": 0,
    "en": "Cloudflare",
    "zh": "Cloudflare",
    "tw": "Cloudflare",
    "locale": "CLOUDFLARE",
    "emoji": "🌏"
  })

def is_ip(content: str):
    try:
        ipaddress.ip_address(content)
        return True
    except ValueError:
        return False


def get_region_data(locale: str) -> Optional[CountryData]:
    for data in country_data:
        if data["locale"] == locale:
            return data
