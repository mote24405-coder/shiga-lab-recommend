"""
data/raw/theses.json のPDF URLからPDFをダウンロード。
実行: docker compose run --rm web python scripts/download_pdfs.py

保存先: data/raw/pdfs/{repo_id}.pdf
失敗・スキップは data/raw/pdf_status.json に記録。
"""
import json, time, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import requests

THESES_JSON = "data/raw/theses.json"
PDF_DIR = "data/raw/pdfs"
STATUS_FILE = "data/raw/pdf_status.json"
DELAY = 3.0
HEADERS = {"User-Agent": "shiga-lab-search/1.0 (research use)"}


def load_status() -> dict:
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}


def save_status(status: dict):
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)


def download_pdf(repo_id: int, pdf_url: str, status: dict) -> str:
    """'ok' / 'skip' / 'no_url' / 'error' を返す"""
    key = str(repo_id)
    dest = os.path.join(PDF_DIR, f"{repo_id}.pdf")

    if os.path.exists(dest):
        return "skip"
    if not pdf_url:
        status[key] = "no_url"
        return "no_url"
    if status.get(key) == "error_403":
        return "skip_403"

    try:
        r = requests.get(pdf_url, headers=HEADERS, timeout=60, stream=True)
        if r.status_code == 403:
            print(f"  [{repo_id}] 403 Forbidden (アクセス制限) → スキップ")
            status[key] = "error_403"
            return "error_403"
        r.raise_for_status()

        content_type = r.headers.get("content-type", "")
        if "pdf" not in content_type and "octet-stream" not in content_type:
            print(f"  [{repo_id}] 非PDFレスポンス: {content_type}")
            status[key] = f"error_content:{content_type}"
            return "error"

        with open(dest, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

        size_kb = os.path.getsize(dest) // 1024
        print(f"  [{repo_id}] OK ({size_kb} KB)")
        status[key] = "ok"
        return "ok"

    except Exception as e:
        print(f"  [{repo_id}] ERROR: {e}")
        status[key] = f"error:{str(e)[:50]}"
        return "error"


def main():
    if not os.path.exists(THESES_JSON):
        print(f"{THESES_JSON} が見つかりません。先に crawl_repo_items.py を実行してください。")
        return

    with open(THESES_JSON, encoding="utf-8") as f:
        theses = json.load(f)

    os.makedirs(PDF_DIR, exist_ok=True)
    status = load_status()

    counts = {"ok": 0, "skip": 0, "no_url": 0, "error": 0}

    print(f"PDFダウンロード開始: {len(theses)} 件")
    for i, thesis in enumerate(theses, 1):
        repo_id = thesis["repo_id"]
        pdf_url = thesis.get("fulltext_pdf_url") or thesis.get("pdf_url", "")
        title_short = thesis.get("title", "")[:40]
        print(f"[{i}/{len(theses)}] {repo_id}: {title_short}")

        result = download_pdf(repo_id, pdf_url, status)
        base_result = result.split("_")[0]
        counts[base_result] = counts.get(base_result, 0) + 1

        # 進捗保存
        if i % 10 == 0:
            save_status(status)

        if result in ("ok",):
            time.sleep(DELAY)

    save_status(status)

    print("\n=== 結果 ===")
    for k, v in counts.items():
        print(f"  {k}: {v} 件")
    ok_count = len([v for v in status.values() if v == "ok"])
    total_pdfs = len([f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")])
    print(f"  ダウンロード済みPDF: {total_pdfs} 件")


if __name__ == "__main__":
    main()
