# SubTrimmer

Clash 订阅修剪器

大多 Clash 订阅链接看似有大量节点, 实际上仅为几个节点重复.
这个工具可以用于修建订阅链接, 去除重复节点, 按 ip 属地重命名节点并按代理协议类型分类.

## 使用方法

调用 API

`GET http://<host>:<port>/trim/<subcribe_url>`

返回 yaml 格式订阅数据

## 已搭建的服务

[trimmer.shirosakihana.moe](http://trimmer.shirosakihana.moe/)

## 数据来源

GeoIp 数据库 来自 [MetaCubeX/meta-rules-dat](https://github.com/MetaCubeX/meta-rules-dat)

countryData.json 来自 [wyq2214368/country-info/](https://github.com/wyq2214368/country-info/)
