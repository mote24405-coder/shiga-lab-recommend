"""
ダウンロードしたPDFからテキストを抽出。
実行: docker compose run --rm web python scripts/extract_pdf_text.py

入力: data/raw/pdfs/{repo_id}.pdf + data/raw/theses.json
出力: data/processed/pdf_texts.json

抽出方針:
- 先頭5ページのテキストを取得（表紙・目次・要旨・序論が含まれる）
- 文字化け判定: 抽出文字数が少ない場合はfallback
- OpenAIへの入力は最大3000文字に制限（コスト節約）
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    import pypdf
except ImportError:
    print("pypdfがインストールされていません: pip install pypdf")
    sys.exit(1)

THESES_JSON = "data/raw/theses.json"
PDF_DIR = "data/raw/pdfs"
OUTPUT = "data/processed/pdf_texts.json"
MAX_PAGES = 200   # 実質全ページ
MAX_CHARS = 60000 # 全文（gpt-4o-mini 128K context に収まる上限）


def extract_text(pdf_path: str) -> tuple[str, int]:
    """(text, pages_extracted) を返す"""
    try:
        reader = pypdf.PdfReader(pdf_path)
        total_pages = len(reader.pages)
        pages_to_read = min(MAX_PAGES, total_pages)

        texts = []
        for i in range(pages_to_read):
            try:
                page_text = reader.pages[i].extract_text() or ""
                texts.append(page_text)
            except Exception:
                continue

        full_text = "\n".join(texts)
        # 連続する空白・改行を整理
        import re
        full_text = re.sub(r'\n{3,}', '\n\n', full_text)
        full_text = re.sub(r'[ \t]+', ' ', full_text)

        return full_text[:MAX_CHARS], pages_to_read
    except Exception as e:
        return f"[抽出エラー: {e}]", 0


def main():
    if not os.path.exists(THESES_JSON):
        print(f"{THESES_JSON} が見つかりません。")
        return

    with open(THESES_JSON, encoding="utf-8") as f:
        theses = json.load(f)

    os.makedirs("data/processed", exist_ok=True)

    # 既存結果を読み込み（中断再開対応）
    existing = {}
    if os.path.exists(OUTPUT):
        with open(OUTPUT, encoding="utf-8") as f:
            existing = {int(k): v for k, v in json.load(f).items()}

    results = dict(existing)
    success, failed, skipped = 0, 0, 0

    for thesis in theses:
        repo_id = thesis["repo_id"]
        pdf_path = os.path.join(PDF_DIR, f"{repo_id}.pdf")

        if repo_id in results:
            skipped += 1
            continue

        if not os.path.exists(pdf_path):
            results[repo_id] = {
                "title": thesis["title"],
                "text": "",
                "pages_extracted": 0,
                "status": "no_pdf",
            }
            failed += 1
            continue

        print(f"[{repo_id}] {thesis['title'][:50]}")
        text, pages = extract_text(pdf_path)

        char_count = len(text.strip())
        status = "ok" if char_count > 50 else "low_quality"

        results[repo_id] = {
            "title": thesis["title"],
            "authors": thesis.get("authors", []),
            "year": thesis.get("year"),
            "text": text,
            "pages_extracted": pages,
            "char_count": char_count,
            "status": status,
        }

        if status == "ok":
            success += 1
            print(f"  → {char_count} 文字抽出 ({pages} ページ)")
        else:
            failed += 1
            print(f"  → 文字数不足 ({char_count} 文字) ※スキャンPDFの可能性")

        # 10件ごとに中間保存
        if (success + failed) % 10 == 0:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump({str(k): v for k, v in results.items()}, f, ensure_ascii=False, indent=2)

    print(f"\n=== 結果 ===")
    print(f"  成功: {success} 件")
    print(f"  失敗/低品質: {failed} 件")
    print(f"  スキップ(既存): {skipped} 件")
    print(f"  合計: {len(results)} 件 → {OUTPUT}")


if __name__ == "__main__":
    main()
