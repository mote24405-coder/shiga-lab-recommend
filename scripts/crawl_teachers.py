"""
滋賀大学DS研究科 教員ページのスクレイピング。
実行: docker compose run --rm web python scripts/crawl_teachers.py

取得結果: data/raw/teachers.json

ページ構造:
  一覧: table > tr > td > a (名前・URL) / td > span (専門分野)
  個別: h1 (氏名), p.pos (職位), table th/td (専門分野・キーワード),
        h3「ゼミ情報」「教員より」(bio), 関連リンク (researchmap等)
"""
import json, time, os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://www.ds.shiga-u.ac.jp"
MEMBER_URL = f"{BASE_URL}/member/"
OUTPUT = "data/raw/teachers.json"
DELAY = 2.0

# 専任・特任・特別招聘を対象（インダストリアルアドバイザーは除外）
TARGET_SECTIONS = {"専任教員", "特任教員", "特別招聘教員等"}

HEADERS = {"User-Agent": "shiga-lab-search/1.0 (research use)"}


def fetch(url: str) -> BeautifulSoup | None:
    try:
        resp = requests.get(url, timeout=20, headers=HEADERS)
        resp.raise_for_status()
        resp.encoding = resp.apparent_encoding
        return BeautifulSoup(resp.text, "lxml")
    except Exception as e:
        print(f"  ERROR {url}: {e}")
        return None


def parse_profile_page(url: str) -> dict:
    """個別教員ページから詳細情報を取得"""
    soup = fetch(url)
    if not soup:
        return {}

    result = {}

    # 氏名 (h1)
    h1 = soup.find("h1")
    if h1:
        result["name"] = h1.get_text(strip=True)

    # かな / ローマ字 (p.kana)
    kana = soup.find("p", class_="kana")
    if kana:
        result["name_kana"] = kana.get_text(strip=True)

    # 職位 (p.pos)
    pos = soup.find("p", class_="pos")
    if pos:
        result["position"] = pos.get_text(strip=True)

    # 専任/特任 区分 (span.type)
    type_span = soup.find("span", class_="type")
    if type_span:
        result["teacher_type"] = type_span.get_text(strip=True)

    # info3Wrap テーブル: 専門分野・研究キーワード
    info_table = soup.find("div", class_="info3Wrap")
    if info_table:
        for row in info_table.find_all("tr"):
            th = row.find("th")
            td = row.find("td")
            if not th or not td:
                continue
            key = th.get_text(strip=True)
            val = td.get_text(strip=True)
            if "専門分野" in key:
                result["specialties"] = [s.strip() for s in re.split(r"[,、/／・]", val) if s.strip()]
            elif "キーワード" in key:
                result["keywords"] = [k.strip() for k in re.split(r"[,、/／・]", val) if k.strip()]

    # entryWrap: h3 見出し別にテキスト取得
    entry = soup.find("div", class_="entryWrap")
    bio_parts = []
    if entry:
        current_heading = None
        for tag in entry.children:
            if not hasattr(tag, "name") or tag.name is None:
                continue
            if tag.name in ("h2", "h3", "h4"):
                current_heading = tag.get_text(strip=True)
            elif tag.name == "p" and current_heading in ("ゼミ情報", "教員より"):
                text = tag.get_text(strip=True)
                if text:
                    bio_parts.append(text)
            elif tag.name == "ul" and current_heading == "関連リンク":
                for a in tag.find_all("a", href=True):
                    href = a["href"]
                    link_text = a.get_text(strip=True)
                    if "researchmap.jp" in href:
                        result["researchmap_url"] = href
                    elif any(kw in link_text for kw in ["研究室", "Lab", "ラボ", "HP", "ホームページ"]):
                        result["lab_site_url"] = href
                    elif href.startswith("http") and BASE_URL not in href and "shiga-u.ac.jp" not in href:
                        if "lab_site_url" not in result:
                            result["lab_site_url"] = href

    if bio_parts:
        result["bio"] = "\n\n".join(bio_parts)[:1000]

    return result


def crawl_member_list() -> list[dict]:
    """一覧ページから専任・特任教員の名前とURLを取得"""
    print(f"教員一覧を取得: {MEMBER_URL}")
    soup = fetch(MEMBER_URL)
    if not soup:
        return []

    members = []
    for section in soup.find_all("section"):
        h2 = section.find("h2")
        section_name = h2.get_text(strip=True) if h2 else ""
        if section_name not in TARGET_SECTIONS:
            continue

        for row in section.find_all("tr"):
            tds = row.find_all("td")
            if len(tds) < 2:
                continue

            a = tds[0].find("a", href=True)
            if not a:
                continue

            name = a.get_text(strip=True)
            href = a["href"]
            profile_url = href if href.startswith("http") else BASE_URL + href

            # td[1]: 所属職位 + span(専門分野)
            td2 = tds[1]
            span = td2.find("span")
            specialty_hint = span.get_text(strip=True) if span else ""
            # spanを除いたテキストが所属+職位
            if span:
                span.extract()
            affiliation = td2.get_text(strip=True)

            members.append({
                "name": name,
                "profile_url": profile_url,
                "affiliation": affiliation,
                "specialty_hint": specialty_hint,
                "section": section_name,
            })
            print(f"  [{section_name}] {name}")

    return members


def main():
    os.makedirs("data/raw", exist_ok=True)

    members = crawl_member_list()
    if not members:
        print("教員リストを取得できませんでした。")
        return

    print(f"\n{len(members)} 名を発見。個別ページを取得中...\n")
    results = []

    for i, member in enumerate(members, 1):
        print(f"[{i}/{len(members)}] {member['name']}")
        detail = parse_profile_page(member["profile_url"])

        teacher = {
            "name": detail.get("name") or member["name"],
            "name_kana": detail.get("name_kana", ""),
            "profile_url": member["profile_url"],
            "affiliation": member["affiliation"],
            "position": detail.get("position", ""),
            "teacher_type": detail.get("teacher_type", member["section"]),
            "specialties": detail.get("specialties") or (
                [s.strip() for s in re.split(r"[,、/]", member["specialty_hint"]) if s.strip()]
            ),
            "keywords": detail.get("keywords", []),
            "bio": detail.get("bio", ""),
            "lab_site_url": detail.get("lab_site_url", ""),
            "researchmap_url": detail.get("researchmap_url", ""),
        }
        results.append(teacher)
        print(f"  職位: {teacher['position']}")
        print(f"  専門: {', '.join(teacher['specialties'][:4])}")
        if teacher["bio"]:
            print(f"  bio: {teacher['bio'][:60]}...")
        time.sleep(DELAY)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"\n=== 完了 ===")
    print(f"  {len(results)} 名 → {OUTPUT}")


if __name__ == "__main__":
    main()
