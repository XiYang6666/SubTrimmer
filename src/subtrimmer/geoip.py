from typing import Optional
from pathlib import Path

import geoip2.database
import geoip2.errors
import dns.resolver
import httpx

from . import config
from .util import is_ip

reader: Optional[geoip2.database.Reader] = None


async def init_geoip(reload: bool = True):
    geodb_path = Path(config.GEOIP_DB_PATH)
    if reload or not geodb_path.exists():
        async with httpx.AsyncClient(follow_redirects=True) as client:
            response = await client.get(config.GEOIP_DB_URL)
            with open(geodb_path, "wb") as f:
                f.write(await response.aread())
    global reader
    reader = geoip2.database.Reader(geodb_path)


def lookup_ip(ip_address: str) -> Optional[str]:
    if not reader:
        raise RuntimeError("GeoIP database not initialized")
    try:
        response = reader.country(ip_address)
        return response.country.iso_code
    except geoip2.errors.AddressNotFoundError:
        return None


def lookup_domain(domain: str) -> Optional[str]:
    # 解析域名
    ip_addresses: list[str] = []
    try:
        for item in dns.resolver.query(domain, "A").response.answer[-1].items:
            ip_addresses.append(str(item))
        if not ip_addresses:
            return None
    except dns.resolver.NoAnswer:
        return None
    # 查询 IP
    ip_address = ip_addresses[0]
    return lookup_ip(ip_address)


def lookup(target: str) -> Optional[str]:
    if is_ip(target):
        return lookup_ip(target)
    else:
        return lookup_domain(target)
