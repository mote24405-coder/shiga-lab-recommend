"""
滋賀大学DS研究科 教員ページのスクレイピング。
実行: docker compose run --rm web python scripts/crawl_teachers.py

取得結果は data/raw/teachers.json に保存。
人間が確認・修正後、seed または admin画面からDBに反映。
"""
import json, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ds.shiga-u.ac.jp"
MEMBER_URL = f"{BASE_URL}/member/"
OUTPUT = "data/raw/teachers.json"
DELAY = 2.0  # robots.txt遵守 & 過負荷防止


def fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "lab-search-bot/1.0 (research use)"})
        resp.raise_for_status()
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  ERROR {url}: {e}")
        return None


def crawl() -> list[dict]:
    print(f"教員一覧ページを取得: {MEMBER_URL}")
    soup = fetch(MEMBER_URL)
    if not soup:
        return []

    teachers = []
    # ページ構造に応じて調整が必要
    for card in soup.select(".member-item, .faculty-item, article.member"):
        name_el = card.select_one(".name, h2, h3, .faculty-name")
        if not name_el:
            continue
        name = name_el.get_text(strip=True)

        profile_link = card.select_one("a[href]")
        profile_url = None
        if profile_link:
            href = profile_link["href"]
            profile_url = href if href.startswith("http") else BASE_URL + href

        specialties = []
        spec_el = card.select_one(".specialty, .research-field, .keywords")
        if spec_el:
            specialties = [s.strip() for s in spec_el.get_text(separator="、").split("、") if s.strip()]

        teachers.append({
            "name": name,
            "profile_url": profile_url,
            "specialties": specialties,
            "bio": "",
        })
        print(f"  取得: {name}")
        time.sleep(DELAY)

    return teachers


def main():
    os.makedirs("data/raw", exist_ok=True)
    teachers = crawl()
    if not teachers:
        print("教員データが取得できませんでした。ページ構造を確認してください。")
        return
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(teachers, f, ensure_ascii=False, indent=2)
    print(f"\n{len(teachers)} 件を {OUTPUT} に保存しました。")


if __name__ == "__main__":
    main()
