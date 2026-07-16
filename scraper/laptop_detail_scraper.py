# scraper/laptop_detail_scraper.py
# 다나와 상품 상세페이지에서 전체 스펙표 + 상세정보(홍보) 이미지를 가져오는 모듈
#
# 다나와 상세페이지는 스펙표/상세이미지를 초기 HTML이 아니라
# ./ajax/getProductDescription.ajax.php 로 별도 로드한다.
# 이 ajax 호출에 필요한 파라미터(cate1~4, UICategoryCode, makerName 등)는
# 상세페이지 HTML에 내장된 oGlobalSetting / oProductDescriptionInfo 자바스크립트 객체에서 추출한다.

import json
import re
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36",
}

DESCRIPTION_AJAX_URL = "https://prod.danawa.com/info/ajax/getProductDescription.ajax.php"


def _extract_object_block(html: str, var_name: str) -> str:
    """`var {var_name} = {...};` 형태의 자바스크립트 객체 리터럴 원문을 추출"""
    marker = f"var {var_name} = {{"
    start = html.find(marker)
    if start == -1:
        return ""
    brace_start = html.find("{", start)
    end = html.find("};", brace_start)
    if end == -1:
        return ""
    return html[brace_start:end + 1]


def _field(block: str, key: str) -> str:
    """객체 리터럴 블록에서 `key: "value"` 형태의 문자열 값 추출"""
    m = re.search(rf'{re.escape(key)}\s*:\s*"([^"]*)"', block)
    return m.group(1) if m else ""


def _build_description_params(html: str, pcode: str) -> dict:
    global_setting = _extract_object_block(html, "oGlobalSetting")
    desc_info_raw = _extract_object_block(html, "oProductDescriptionInfo")

    try:
        desc_info = json.loads(desc_info_raw) if desc_info_raw else {}
    except json.JSONDecodeError:
        desc_info = {}

    return {
        "pcode": pcode,
        "cate1": _field(global_setting, "nCategoryCode1"),
        "cate2": _field(global_setting, "nCategoryCode2"),
        "cate3": _field(global_setting, "nCategoryCode3"),
        "cate4": _field(global_setting, "nCategoryCode4"),
        "UICategoryCode": _field(global_setting, "nCategoryCode"),
        "powerLinkKeyword": _field(global_setting, "powerLinkKeyword"),
        "minPrice": _field(global_setting, "nMinPrice"),
        "keyword": _field(global_setting, "sKeyword"),
        "NaPm": _field(global_setting, "sNaPm"),
        "makerName": desc_info.get("makerName", ""),
        "brandName": desc_info.get("brandName", ""),
        "makerUrl": desc_info.get("makerUrl", ""),
        "kccode": desc_info.get("kccode", ""),
        "kpscode": desc_info.get("kpscode", ""),
        "circulName": desc_info.get("circulName", ""),
        "productName": desc_info.get("productName", ""),
        "prodType": desc_info.get("prodType", ""),
        "displayMakeDate": desc_info.get("displayMakeDate", ""),
        "productFullName": _field(global_setting, "sProductName"),
    }


def _parse_spec_table(soup: BeautifulSoup) -> dict:
    """table.spec_tbl 을 {스펙명: 값} 딕셔너리로 변환 (섹션 헤더 행은 건너뜀)"""
    spec_dict = {}
    spec_tbl = soup.select_one("table.spec_tbl")
    if not spec_tbl:
        return spec_dict

    for tr in spec_tbl.select("tr"):
        cells = tr.find_all(["th", "td"])
        i = 0
        while i < len(cells) - 1:
            if cells[i].name == "th" and cells[i + 1].name == "td":
                key = cells[i].get_text(strip=True)
                value = cells[i + 1].get_text(strip=True)
                if key and value:
                    spec_dict[key] = value
                i += 2
            else:
                i += 1
    return spec_dict


def _parse_detail_images(soup: BeautifulSoup) -> list:
    """제조사 제공 상세정보/홍보 이미지 URL 목록"""
    images = []
    detail_cont = soup.select_one("div.detail_cont")
    if not detail_cont:
        return images
    for img in detail_cont.select("img"):
        src = img.get("src") or img.get("data-src") or ""
        if src.startswith("//"):
            src = "https:" + src
        if src.startswith("http") and src not in images:
            images.append(src)
    return images


def fetch_product_detail(pcode: str, cate: str) -> dict:
    """상품 상세페이지에서 전체 스펙 + 상세이미지를 가져온다.

    반환값: {detail_url, raw_spec_text, spec_dict, detail_images}
    """
    detail_url = f"https://prod.danawa.com/info/?pcode={pcode}&cate={cate}"

    page_resp = requests.get(detail_url, headers=HEADERS, timeout=15)
    page_resp.raise_for_status()
    html = page_resp.text

    params = _build_description_params(html, pcode)

    ajax_headers = dict(HEADERS)
    ajax_headers["X-Requested-With"] = "XMLHttpRequest"
    ajax_headers["Referer"] = detail_url

    desc_resp = requests.post(DESCRIPTION_AJAX_URL, headers=ajax_headers, data=params, timeout=15)
    desc_resp.raise_for_status()

    soup = BeautifulSoup(desc_resp.text, "html.parser")
    spec_dict = _parse_spec_table(soup)
    raw_spec_text = "\n".join(f"{k}: {v}" for k, v in spec_dict.items())
    detail_images = _parse_detail_images(soup)

    return {
        "detail_url": detail_url,
        "raw_spec_text": raw_spec_text,
        "spec_dict": spec_dict,
        "detail_images": detail_images,
    }
