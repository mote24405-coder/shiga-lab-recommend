"""
滋賀大学学術情報リポジトリから修士論文メタデータを取得。
実行: docker compose run --rm web python scripts/crawl_repo_items.py

取得結果は data/raw/theses.json に保存。
"""
import json, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup

REPO_URL = "https://shiga-u.repo.nii.ac.jp/search"
PARAMS_BASE = {
    "page": 1,
    "size": 20,
    "sort": "controlnumber",
    "search_type": 2,
    "q": "1873",
}
OUTPUT = "data/raw/theses.json"
DELAY = 3.0


def fetch_page(page: int) -> list[dict]:
    params = {**PARAMS_BASE, "page": page}
    try:
        resp = requests.get(REPO_URL, params=params, timeout=20,
                            headers={"User-Agent": "lab-search-bot/1.0 (research use)"})
        resp.raise_for_status()
    except Exception as e:
        print(f"  ERROR page {page}: {e}")
        return []

    soup = BeautifulSoup(resp.text, "lxml")
    items = []
    for item in soup.select(".item-list li, .search-result-item, article.search-result"):
        title_el = item.select_one(".title a, h3 a, .item-title a")
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        item_url = title_el.get("href", "")
        if item_url and not item_url.startswith("http"):
            item_url = "https://shiga-u.repo.nii.ac.jp" + item_url

        year_el = item.select_one(".date, .year, time")
        year = None
        if year_el:
            import re
            m = re.search(r"(20\d{2}|19\d{2})", year_el.get_text())
            if m:
                year = int(m.group(1))

        author_el = item.select_one(".creator, .author, .contributor")
        author = author_el.get_text(strip=True) if author_el else None

        items.append({"title": title, "repo_url": item_url, "year": year, "author_name": author})
        print(f"  取得: {title[:60]}")

    return items


def main():
    os.makedirs("data/raw", exist_ok=True)
    all_items = []
    for page in range(1, 20):  # 最大 19 ページ
        print(f"\nページ {page} を取得中...")
        items = fetch_page(page)
        if not items:
            print("  これ以上データなし。終了。")
            break
        all_items.extend(items)
        time.sleep(DELAY)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(all_items, f, ensure_ascii=False, indent=2)
    print(f"\n合計 {len(all_items)} 件を {OUTPUT} に保存しました。")


if __name__ == "__main__":
    main()
