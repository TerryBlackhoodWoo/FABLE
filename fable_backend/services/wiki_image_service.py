"""
캐릭터/장면 관련 이미지를 위키백과 · Wikimedia Commons에서 검색하는 서비스.

전략:
  1) 장면 기반 검색 (우선): Gemini가 만든 "Achilles rage Agamemnon Briseis painting" 같은
     구체적 검색어로 Commons를 검색. 인물 이름만으로 검색하면 동명이인(예: 화가 이름이
     "Achilles"인 경우)이 걸릴 위험이 크므로, 장면을 특정하는 단어를 반드시 포함시켜 위험을 줄인다.
  2) 장면 기반 검색이 실패하거나 결과가 없으면: 위키백과 문서(예: "Achilles")의
     대표 이미지(인포박스 썸네일)로 대체 — 최소한 "그 인물"은 정확히 맞는 이미지를 보장.

키 불필요. Wikimedia 정책상 요청마다 식별 가능한 User-Agent만 포함하면 된다.
"""

import re
import httpx

from config import WIKIMEDIA_USER_AGENT

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
COMMONS_API_URL = "https://commons.wikimedia.org/w/api.php"


def _strip_html(raw: str) -> str:
    return re.sub(r"<[^>]+>", "", raw).strip()


async def _search_commons_scene(client: httpx.AsyncClient, query: str) -> dict | None:
    """장면 기반 전체 텍스트 검색. 결과가 없거나 이미지 정보가 없으면 None."""
    if not query:
        return None

    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": f"{query} filetype:bitmap",  # PDF/문서 스캔본 제외, 실제 이미지 파일만
        "gsrnamespace": "6",  # File 네임스페이스만
        "gsrlimit": "1",
        "prop": "imageinfo",
        "iiprop": "url|extmetadata",
        "iiurlwidth": "800",
        "format": "json",
    }
    response = await client.get(COMMONS_API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    page = next(iter(pages.values()))
    imageinfo = page.get("imageinfo")
    if not imageinfo:
        return None

    info = imageinfo[0]
    meta = info.get("extmetadata", {})

    def meta_value(key: str, default: str = "") -> str:
        raw = meta.get(key, {}).get("value", default)
        return _strip_html(raw) if raw else default

    return {
        "title": page.get("title", "").removeprefix("File:"),
        "thumb_url": info.get("thumburl") or info.get("url"),
        "source_url": info.get("descriptionurl", ""),
        "artist": meta_value("Artist"),
        "license": meta_value("LicenseShortName", "Public Domain"),
    }


async def _get_wikipedia_page_image(
    client: httpx.AsyncClient, title: str
) -> dict | None:
    """폴백용: 위키백과 문서의 대표 이미지(인포박스 썸네일) + 파일명 조회."""
    if not title:
        return None

    params = {
        "action": "query",
        "titles": title,
        "prop": "pageimages",
        "piprop": "thumbnail|name",
        "pithumbsize": "800",
        "format": "json",
        "redirects": "1",
    }
    response = await client.get(WIKIPEDIA_API_URL, params=params)
    response.raise_for_status()
    data = response.json()

    pages = data.get("query", {}).get("pages", {})
    if not pages:
        return None

    page = next(iter(pages.values()))
    thumbnail = page.get("thumbnail")
    filename = page.get("pageimage")
    if not thumbnail or not filename:
        return None

    meta_params = {
        "action": "query",
        "titles": f"File:{filename}",
        "prop": "imageinfo",
        "iiprop": "extmetadata",
        "format": "json",
    }
    meta_response = await client.get(COMMONS_API_URL, params=meta_params)
    meta_response.raise_for_status()
    meta_data = meta_response.json()
    meta_pages = meta_data.get("query", {}).get("pages", {})

    artist, license_name = "", "Public Domain"
    if meta_pages:
        meta_page = next(iter(meta_pages.values()))
        imageinfo = meta_page.get("imageinfo")
        if imageinfo:
            meta = imageinfo[0].get("extmetadata", {})

            def meta_value(key: str, default: str = "") -> str:
                raw = meta.get(key, {}).get("value", default)
                return _strip_html(raw) if raw else default

            artist = meta_value("Artist")
            license_name = meta_value("LicenseShortName", "Public Domain")

    return {
        "title": filename,
        "thumb_url": thumbnail["source"],
        "source_url": f"https://commons.wikimedia.org/wiki/File:{filename}",
        "artist": artist,
        "license": license_name,
    }


async def search_character_image(
    image_query: str, fallback_wikipedia_title: str
) -> dict | None:
    """
    1) image_query(장면 기반 검색어)로 Commons에서 먼저 찾고,
    2) 실패하면 fallback_wikipedia_title(예: "Achilles")의 위키백과 대표 이미지로 대체한다.
    둘 다 실패하면 None (이미지는 부가 기능이라 실패해도 답변 자체엔 영향 없어야 함).
    """
    headers = {"User-Agent": WIKIMEDIA_USER_AGENT}

    try:
        async with httpx.AsyncClient(timeout=5.0, headers=headers) as client:
            result = await _search_commons_scene(client, image_query)
            if result:
                return result

            return await _get_wikipedia_page_image(client, fallback_wikipedia_title)
    except (httpx.HTTPError, ValueError):
        return None
