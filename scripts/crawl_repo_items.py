"""
滋賀大学学術情報リポジトリから修士論文メタデータ・PDF URLを取得。
JSON APIを使用。レスポンスは item_XXXXX_YYYY 形式の動的フィールド。

実行: docker compose run --rm web python scripts/crawl_repo_items.py

取得結果: data/raw/theses.json
令和2年度(2021-03) 〜 令和6年度(2025-03) の修士論文を対象とする。
"""
import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests

SEARCH_API = "https://shiga-u.repo.nii.ac.jp/api/records/"
OUTPUT = "data/raw/theses.json"
DELAY = 1.5
PAGE_SIZE = 20

# 令和2年度=2021-03修了 〜 令和6年度=2025-03修了
YEAR_RANGE = range(2021, 2026)

HEADERS = {
    "Accept": "application/json",
    "User-Agent": "shiga-lab-search/1.0 (research use)",
}


# ── API レスポンス解析ユーティリティ ─────────────────────────────────────


def _iter_attrs(meta: dict):
    """metadata の全 attribute オブジェクトをイテレートする。"""
    for val in meta.values():
        if isinstance(val, dict) and "attribute_name" in val:
            yield val


def _find_attr(meta: dict, *, name: str | None = None, attr_type: str | None = None) -> dict | None:
    for attr in _iter_attrs(meta):
        if name and attr.get("attribute_name") == name:
            return attr
        if attr_type and attr.get("attribute_type") == attr_type:
            return attr
    return None


def _extract_title(meta: dict) -> str:
    attr = _find_attr(meta, name="タイトル")
    if attr:
        for v in attr.get("attribute_value_mlt", []):
            t = v.get("subitem_title", "") or v.get("title", "")
            if t and any(ord(c) > 0x3000 for c in str(t)):
                return str(t)
        vals = attr.get("attribute_value_mlt", [])
        if vals:
            v = vals[0]
            return str(v.get("subitem_title", "") or v.get("title", ""))
    # 旧形式 fallback
    titles = meta.get("title", [])
    if isinstance(titles, list) and titles:
        return str(titles[0])
    return ""


def _extract_authors(meta: dict) -> list[str]:
    attr = _find_attr(meta, name="作成者")
    if attr:
        authors: list[str] = []
        for creator in attr.get("attribute_value_mlt", []):
            names = creator.get("creatorNames", [])
            # 日本語名を優先
            ja = next((n["creatorName"] for n in names if n.get("creatorNameLang") == "ja"), None)
            en = next((n.get("creatorName", "") for n in names), None)
            name = ja or en or ""
            if name:
                authors.append(name.replace(", ", " "))
        return authors
    # 旧形式 fallback
    authors = []
    for c in meta.get("_creator_info", []):
        name = c.get("creatorNames", {}).get("creatorName", "")
        if name:
            authors.append(name.replace(", ", " ").replace(",", " "))
    return authors


def _extract_issued_year(meta: dict) -> int | None:
    # 新形式: 発行日 attribute
    attr = _find_attr(meta, name="発行日")
    if attr:
        for v in attr.get("attribute_value_mlt", []):
            date_str = v.get("subitem_date_issued_date", "") or v.get("date", "")
            m = re.search(r"(20\d{2})", str(date_str))
            if m:
                return int(m.group(1))
    # 旧形式: date[].dateType == "Issued"
    for d in meta.get("date", []):
        if d.get("dateType") == "Issued":
            m = re.search(r"(20\d{2})", str(d.get("value", "")))
            if m:
                return int(m.group(1))
    # publish_date fallback (公開日なので不正確だが最終手段)
    m = re.search(r"(20\d{2})", str(meta.get("publish_date", "")))
    return int(m.group(1)) if m else None


def _extract_pdfs(meta: dict) -> dict[str, str]:
    """主論文PDF URL と要旨PDF URL を {'fulltext_pdf_url': ..., 'abstract_pdf_url': ...} で返す。"""
    attr = _find_attr(meta, attr_type="file")
    file_list: list[dict] = (
        attr.get("attribute_value_mlt", []) if attr else meta.get("_files_info", [])
    )

    result: dict[str, str] = {}
    for f in file_list:
        url_field = f.get("url", {})
        if isinstance(url_field, dict):
            # 新形式: url が {url: "...", objectType: "..."}
            url = url_field.get("url", "")
            obj_type = url_field.get("objectType", "fulltext")
        else:
            # 旧形式 (_files_info): url が文字列、label で種別判定
            url = str(url_field)
            label = f.get("label", "")
            obj_type = "abstract" if "要旨" in label else "fulltext"

        if not url:
            continue

        # PDFか確認 (mimetype または extention または拡張子)
        mimetype = f.get("mimetype", "") or f.get("format", "") or f.get("extention", "")
        if "pdf" not in str(mimetype).lower() and not url.lower().endswith(".pdf"):
            continue

        # アクセス制限がかかっているものはスキップ
        if f.get("accessrole") == "open_restricted":
            continue

        # filename でも要旨判定 (念のため)
        filename = f.get("filename", "")
        if obj_type == "abstract" or "要旨" in filename:
            result["abstract_pdf_url"] = url
        else:
            result["fulltext_pdf_url"] = url

    return result


def _is_thesis(meta: dict) -> bool:
    # 新形式: 資源タイプ attribute
    for attr in _iter_attrs(meta):
        if attr.get("attribute_name") in ("資源タイプ", "Resource Type"):
            for v in attr.get("attribute_value_mlt", []):
                rt = v.get("resourcetype", "") or v.get("subitem_resource_type", "")
                if "thesis" in str(rt).lower():
                    return True
    # 旧形式 fallback
    types = meta.get("type", [])
    return any("thesis" in str(t).lower() for t in (types if isinstance(types, list) else []))


# ── ページング取得 ────────────────────────────────────────────────────────


def fetch_page(query: str, page: int) -> dict:
    params = {
        "size": PAGE_SIZE,
        "page": page,
        "q": query,
        "sort": "controlnumber",
    }
    try:
        r = requests.get(SEARCH_API, params=params, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  ERROR page {page}: {e}")
        return {}


def parse_item(item: dict) -> dict | None:
    meta = item.get("metadata", {})

    if not _is_thesis(meta):
        return None

    year = _extract_issued_year(meta)
    if year not in YEAR_RANGE:
        return None

    title = _extract_title(meta)
    if not title:
        return None

    authors = _extract_authors(meta)
    pdfs = _extract_pdfs(meta)

    return {
        "repo_id": item["id"],
        "title": title,
        "authors": authors,
        "year": year,
        "repo_url": f"https://shiga-u.repo.nii.ac.jp/records/{item['id']}",
        **pdfs,  # fulltext_pdf_url, abstract_pdf_url (存在する場合のみ)
    }


def crawl(query: str, seen_ids: set[int]) -> list[dict]:
    print(f"\n検索クエリ: {query!r}")
    results: list[dict] = []
    page = 1

    while True:
        print(f"  page {page}...", end=" ", flush=True)
        data = fetch_page(query, page)
        hits = data.get("hits", {})
        total = hits.get("total", 0)
        items = hits.get("hits", [])

        if not items:
            print("終了")
            break

        count = 0
        for item in items:
            if item["id"] in seen_ids:
                continue
            parsed = parse_item(item)
            if parsed:
                seen_ids.add(parsed["repo_id"])
                results.append(parsed)
                count += 1

        print(f"{count} 件追加 (total={total})")

        if len(items) < PAGE_SIZE:
            break
        page += 1
        time.sleep(DELAY)

    return results


def main():
    os.makedirs("data/raw", exist_ok=True)

    all_theses: dict[int, dict] = {}
    seen_ids: set[int] = set()

    queries = [
        "データサイエンス研究科 修士論文",
        "データサイエンス 修士",
        "Graduate School of Data Science thesis",
        "shiga university data science master",
    ]
    for q in queries:
        items = crawl(q, seen_ids)
        for item in items:
            all_theses[item["repo_id"]] = item
        time.sleep(DELAY * 2)

    result_list = sorted(all_theses.values(), key=lambda x: (x["year"] or 0, x["title"]))

    from collections import Counter

    year_counts = Counter(t["year"] for t in result_list)
    print("\n=== 取得結果 ===")
    for y, c in sorted(year_counts.items()):
        nendo = y - 2019  # 令和N年度: N = year - 2019 (3月修了)
        print(f"  令和{nendo}年度 ({y}-03): {c} 件")
    print(f"  合計: {len(result_list)} 件")
    print(f"  主論文PDF取得: {sum(1 for t in result_list if t.get('fulltext_pdf_url'))} 件")
    print(f"  要旨PDF取得:   {sum(1 for t in result_list if t.get('abstract_pdf_url'))} 件")

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(result_list, f, ensure_ascii=False, indent=2)
    print(f"\n{OUTPUT} に保存しました。")


if __name__ == "__main__":
    main()
