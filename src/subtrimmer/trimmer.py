import yaml
from typing import Optional, Iterable, TypeGuard, Any, TYPE_CHECKING
from collections import defaultdict

if TYPE_CHECKING:
    from _typeshed import SupportsItems

from .geoip import lookup
from .util import get_region_data


def is_mapping(obj: Any) -> TypeGuard["SupportsItems"]:
    return hasattr(obj, "items") and callable(obj.items)


class SubDumper(yaml.Dumper):
    def increase_indent(self, flow=None, indentless=None):
        return super().increase_indent(flow, False)

    def represent_mapping(
        self,
        tag: str,
        mapping: "SupportsItems[Any, Any] | Iterable[tuple[Any, Any]]",
        flow_style: bool | None = None,
    ) -> yaml.MappingNode:
        if is_mapping(mapping):
            mapping_keys = {item[0] for item in mapping.items()}
        elif isinstance(mapping, Iterable):
            mapping_keys = {item[0] for item in mapping}
        else:
            return super().represent_mapping(tag, mapping, flow_style)
        proxies_keys = {"name", "type", "server", "port"}
        proxy_group_keys = {"name", "type", "proxies"}
        if proxies_keys <= mapping_keys or proxy_group_keys <= mapping_keys:
            flow_style = True
        return super().represent_mapping(tag, mapping, flow_style)


class DefaultDict(defaultdict):
    def __missing__(self, key: Any) -> Any:
        return "{" + key + "}"


def get_proxy_abstract(proxy: dict):
    return (proxy.get("server"), proxy.get("port"))


def trim_yaml(content: str, name_format: Optional[str]) -> str:
    config = yaml.safe_load(content)

    # 处理 proxy
    trimmed_proxies = []
    trimmed_proxies_abstract = []
    trimmed_proxies_names = {}
    for proxy in config.get("proxies", []):
        # 对比摘要是否重复
        if get_proxy_abstract(proxy) in trimmed_proxies_abstract:
            continue
        # 获取信息
        ip_iso_code = lookup(proxy.get("server"))
        ip_region_data = get_region_data(ip_iso_code) if ip_iso_code else None

        # 格式化名称
        proxy_info = {
            "type": proxy.get("type").lower(),
            "ip_iso_code": ip_iso_code,
            "ip_region_en": ip_region_data and ip_region_data["en"] or "UNKNOWN",
            "ip_region_zh": ip_region_data and ip_region_data["zh"] or "UNKNOWN",
            "ip_region_tw": ip_region_data and ip_region_data["tw"] or "UNKNOWN",
            "ip_region_emoji": ip_region_data and ip_region_data["emoji"] or "🤔",
        }
        safe_proxy_info = DefaultDict()
        safe_proxy_info.update(proxy_info)
        new_name = (
            name_format.format_map(safe_proxy_info)
            if name_format
            else proxy.get("name")
        )
        if new_name in trimmed_proxies_names:
            trimmed_proxies_names[new_name] += 1
            new_name = f"{new_name}-{(trimmed_proxies_names[new_name])}"
        else:
            trimmed_proxies_names[new_name] = 0
        trimmed_proxies.append({**proxy, "name": new_name})
        trimmed_proxies_abstract.append(get_proxy_abstract(proxy))

    # 处理 proxy-groups
    proxies_name_list = [trimmed_proxy["name"] for trimmed_proxy in trimmed_proxies]
    proxy_group_proxy = {
        "name": "代理组",
        "type": "select",
        "proxies": proxies_name_list,
    }
    proxy_group_auto = {
        "name": "自动选择",
        "type": "url-test",
        "proxies": proxies_name_list,
        "url": "http://www.gstatic.com/generate_204",
        "interval": 300,
    }
    proxy_group_fallback = {
        "name": "故障转移",
        "type": "fallback",
        "proxies": proxies_name_list,
        "url": "http://www.gstatic.com/generate_204",
        "interval": 300,
    }
    proxy_groups = []
    proxy_groups.append(proxy_group_proxy)
    # 按协议分组
    proxy_protocol_groups: dict[str, list[str]] = {}
    for trimmed_proxy in trimmed_proxies:
        proxy_protocol = trimmed_proxy["type"]
        if proxy_protocol not in proxy_protocol_groups:
            proxy_protocol_groups[proxy_protocol] = []
        proxy_protocol_groups[proxy_protocol].append(trimmed_proxy["name"])
    for proxy_protocol, proxy_names in proxy_protocol_groups.items():
        proxy_group = {
            "name": f"协议: {proxy_protocol.upper()}",
            "type": "select",
            "proxies": proxy_names,
        }
        proxy_groups.append(proxy_group)
    proxy_groups.append(proxy_group_auto)
    proxy_groups.append(proxy_group_fallback)
    # 为代理组添加其他分组
    for proxy_group in proxy_groups[1:]:
        proxy_groups[0]["proxies"].insert(0, proxy_group["name"])
    # 处理 rules
    new_rules = []
    for rule in config.get("rules", []):
        rule: str
        rule_info = rule.split(",")
        if len(rule_info) >= 3 and rule_info[2] not in ["DIRECT", "REJECT"]:
            new_rule = rule_info.copy()
            new_rule[2] = "代理组"
            new_rules.append(",".join(new_rule))
        elif (
            len(rule_info) == 2
            and rule_info[0] == "MATCH"
            and rule_info[1] not in ["DIRECT", "REJECT"]
        ):
            new_rule = rule_info.copy()
            new_rule[1] = "代理组"
            new_rules.append(",".join(new_rule))
        else:
            new_rules.append(rule)
    # 返回新配置
    new_config = {
        **config,
        "proxies": trimmed_proxies,
        "proxy-groups": proxy_groups,
        "rules": new_rules,
    }
    return yaml.dump(
        new_config,
        allow_unicode=True,
        sort_keys=False,
        width=float("inf"),
        Dumper=SubDumper,
    )
