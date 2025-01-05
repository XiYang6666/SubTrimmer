import re
import urllib.parse
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.responses import Response
from fastapi.requests import Request

from .geoip import init_geoip
from .trimmer import trim_yaml


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_geoip(reload=False)
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return "Hello SubTrimmer API"


@app.get("/trim/{path:path}")
async def trim(path: str, request: Request):
    # 获取请求信息
    match_result = re.match(r"^(?:([^/]*)/)?(https?://.*)$", path)
    if not match_result:
        return Response("Invalid link", status_code=400)
    group_name = match_result.group(1) or None
    url = match_result.group(2)
    # 下载订阅内容
    params = dict(request.query_params)
    async with httpx.AsyncClient(
        follow_redirects=True,
        headers={"User-Agent": "clash.meta"},
        params=params,
    ) as client:
        response = await client.get(url)
        content = response.content.decode()
    # 处理内容
    new_content = trim_yaml(content, name_format=group_name)
    # 处理 content-disposition 标头
    content_disposition_header = response.headers.get("content-disposition")
    if content_disposition_header is not None:
        content_disposition: dict[str, str] = {
            key.strip(): value.strip()
            for item in content_disposition_header.split(";")
            if "=" in item
            for key, value in [item.strip().split("=")]
        }
        print(content_disposition)
        # 处理filename
        if content_disposition.get("filename*"):
            match_result = re.match(
                r"^([a-zA-Z0-9-]+)(?:'([a-zA-Z-]+))?(?:''(.*))$",
                content_disposition["filename*"],
            )
            if match_result:
                encoding, lang, url_encoded_filename = match_result.groups()
                filename = urllib.parse.unquote(url_encoded_filename, encoding=encoding)
                filename += " - Trimmed"
                new_filename = "UTF-8"
                if lang:
                    new_filename += f"'{lang}"
                new_filename += f"''{urllib.parse.quote(filename,encoding='utf-8')}"
                content_disposition["filename*"] = new_filename
        elif content_disposition.get("filename"):
            content_disposition["filename"] = (
                '"'
                + content_disposition["filename"].removeprefix('"').removesuffix('"')
                + " - Trimmed"
                + '"'
            )
        if content_disposition.get("type"):
            content_disposition["type"] = "inline"
        new_content_disposition = "; ".join(
            f"{key}={value}" for key, value in content_disposition.items()
        )
    else:
        new_content_disposition = None
    # 返回响应
    headers = {
        "subscription-userinfo": response.headers.get("subscription-userinfo"),
        "profile-update-interval": response.headers.get("profile-update-interval"),
        "content-disposition": new_content_disposition,
    }
    headers = {k: v for k, v in headers.items() if v is not None}
    return Response(
        new_content,
        media_type="text/yaml",
        headers=headers,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
