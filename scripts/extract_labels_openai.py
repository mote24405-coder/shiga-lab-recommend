"""
OpenAI APIを使って修士論文PDFから直接ラベル・指導教員・言語を抽出。
pypdfを使わず、PDFファイルをbase64でAPIに直接渡す。

実行: docker compose run --rm web python scripts/extract_labels_openai.py [--force]

入力: data/raw/pdfs/{repo_id}.pdf + data/raw/theses.json
出力: data/processed/openai_labels.json

--force: 既存結果を無視して全件再実行

■ ラベルマスタ（v3: MASTER_LABELS準拠）
[method] 機械学習・深層学習/統計的モデリング/自然言語処理/画像処理・CV/
         最適化/時系列解析/シミュレーション

[data]   テキスト・言語データ/画像・映像データ/時系列・センサーデータ/
         音声データ/医療・生体データ/地理空間データ/数値・表形式データ

[theme]  機械学習/統計・数理/テキスト・言語処理/画像・映像/最適化/
         医療・ヘルスケア/社会・政策/経済・ビジネス/IoT・センサー・時系列/
         空間・交通/製造・農業・環境/音楽・メディア・デザイン
"""
import base64, json, os, sys, time, argparse
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

try:
    from openai import OpenAI
except ImportError:
    print("openai がインストールされていません。")
    sys.exit(1)

from dotenv import load_dotenv

THESES_JSON = "data/raw/theses.json"
PDF_DIR = "data/raw/pdfs"
OUTPUT = "data/processed/openai_labels.json"

METHOD_LABELS = [
    "機械学習・深層学習", "統計的モデリング", "自然言語処理",
    "画像処理・CV", "最適化", "時系列解析", "シミュレーション",
]
DATA_LABELS = [
    "テキスト・言語データ", "画像・映像データ", "時系列・センサーデータ",
    "音声データ", "医療・生体データ", "地理空間データ", "数値・表形式データ",
]
THEME_LABELS = [
    "機械学習", "統計・数理", "テキスト・言語処理", "画像・映像",
    "最適化", "医療・ヘルスケア", "社会・政策", "経済・ビジネス",
    "IoT・センサー・時系列", "空間・交通", "製造・農業・環境", "音楽・メディア・デザイン",
]

SYSTEM_PROMPT = f"""あなたは滋賀大学データサイエンス研究科の修士論文を分類する専門家です。
論文PDFを読み、以下のJSONのみを出力してください。説明文は不要です。

## ラベルマスタ

[method] 研究手法（最大3個）
{" / ".join(METHOD_LABELS)}

[data] 使用データ種別（最大3個）
{" / ".join(DATA_LABELS)}

[theme] 応用テーマ（最大2個）
{" / ".join(THEME_LABELS)}

## 出力形式
{{
  "supervisor_name": "指導教員の氏名（姓名、敬称なし。例: 市川 治）",
  "method": ["ラベルマスタから最大3個"],
  "data": ["ラベルマスタから最大3個"],
  "theme": ["ラベルマスタから最大2個"],
  "method_raw": ["論文で実際に使われた手法の細粒度名称（例: LSTM, VAE, XGBoost）"],
  "data_raw": ["使用データの具体的説明（例: 電力会社の30分間隔スマートメーターデータ）"],
  "programming_language": ["使用プログラミング言語（例: Python, R, Julia）"],
  "summary_ja": "100字程度の日本語要約（学生が研究室を選ぶときに参考になる情報）",
  "confidence": "high / medium / low"
}}

## ルール
- supervisor_name: 表紙・謝辞・指導教員欄から抽出。「指導教員」「指導教官」「主査」の直後の氏名。見つからない場合は ""
- method / data / theme: マスタ外のラベルは絶対に使わない
- method_raw: 細粒度で（「深層学習」ではなく「LSTM」「Transformer」「U-Net」）
- data_raw: 具体的に（「数値データ」ではなく「市販薬の月次販売数量データ（2010-2020年）」）
- programming_language: コード・実装の記述がない場合は []
- confidence: PDFが読めた場合は high、内容が不明瞭な場合は low
"""


def load_pdf_as_base64(pdf_path: str) -> str | None:
    try:
        with open(pdf_path, "rb") as f:
            data = f.read()
        return base64.standard_b64encode(data).decode("utf-8")
    except Exception as e:
        print(f"  PDF読み込みエラー: {e}")
        return None


def extract_labels(client: OpenAI, title: str, authors: list[str], pdf_b64: str) -> dict:
    user_content = [
        {
            "type": "text",
            "text": f"タイトル: {title}\n著者: {', '.join(authors) if authors else '不明'}\n\n上記の修士論文PDFを分析してください。",
        },
        {
            "type": "file",
            "file": {
                "filename": "thesis.pdf",
                "file_data": f"data:application/pdf;base64,{pdf_b64}",
            },
        },
    ]

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0.1,
            max_tokens=800,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        result = json.loads(content)
        result["_tokens"] = {
            "input": response.usage.prompt_tokens,
            "output": response.usage.completion_tokens,
        }
        return result
    except Exception as e:
        print(f"  OpenAI ERROR: {e}")
        return {
            "supervisor_name": "",
            "method": [], "data": [], "theme": [],
            "method_raw": [], "data_raw": [],
            "programming_language": [],
            "summary_ja": "", "confidence": "low",
            "error": str(e),
        }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="既存結果を無視して全件再実行")
    args = parser.parse_args()

    load_dotenv()
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("OPENAI_API_KEY が設定されていません。")
        sys.exit(1)

    client = OpenAI(api_key=api_key)

    with open(THESES_JSON, encoding="utf-8") as f:
        theses = {str(t["repo_id"]): t for t in json.load(f)}

    existing = {}
    if not args.force and os.path.exists(OUTPUT):
        with open(OUTPUT, encoding="utf-8") as f:
            existing = json.load(f)

    # PDFファイルが存在するもののみ対象
    pdf_files = {
        os.path.splitext(fn)[0]: os.path.join(PDF_DIR, fn)
        for fn in os.listdir(PDF_DIR)
        if fn.endswith(".pdf")
    }

    results = dict(existing)
    success, skipped, errors, no_pdf = 0, 0, 0, 0
    total_input_tokens = 0
    targets = sorted(pdf_files.keys(), key=lambda x: int(x))
    total = len(targets)

    print(f"PDF直接渡しでラベル抽出開始: {total} 件{'（--force: 全件再実行）' if args.force else ''}")

    for i, repo_id_str in enumerate(targets, 1):
        if repo_id_str in results and not args.force:
            skipped += 1
            continue

        thesis = theses.get(repo_id_str, {})
        title = thesis.get("title", f"ID:{repo_id_str}")
        authors = thesis.get("authors", [])
        pdf_path = pdf_files[repo_id_str]

        file_size_kb = os.path.getsize(pdf_path) // 1024
        print(f"[{i}/{total}] {repo_id_str}: {title[:45]} ({file_size_kb}KB)")

        pdf_b64 = load_pdf_as_base64(pdf_path)
        if not pdf_b64:
            no_pdf += 1
            print(f"  → PDFスキップ")
            continue

        labels = extract_labels(client, title, authors, pdf_b64)
        labels["repo_id"] = int(repo_id_str)
        labels["title"] = title
        labels["year"] = thesis.get("year")
        labels["authors"] = authors
        labels["repo_url"] = thesis.get("repo_url", "")
        labels["pdf_url"] = thesis.get("pdf_url", "")

        results[repo_id_str] = labels

        tokens = labels.get("_tokens", {})
        total_input_tokens += tokens.get("input", 0)
        print(f"  指導教員: {labels.get('supervisor_name', '—') or '—'}")
        print(f"  手法: {labels.get('method', [])}")
        print(f"  データ: {labels.get('data', [])}")
        print(f"  テーマ: {labels.get('theme', [])}")
        print(f"  言語: {labels.get('programming_language', [])}")
        if tokens:
            print(f"  tokens: in={tokens.get('input')} out={tokens.get('output')}")

        if "error" in labels:
            errors += 1
        else:
            success += 1

        if (success + errors) % 5 == 0:
            with open(OUTPUT, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)

        time.sleep(0.5)

    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    est_cost = total_input_tokens * 0.15 / 1_000_000
    print(f"\n=== 結果 ===")
    print(f"  成功: {success} 件")
    print(f"  スキップ: {skipped} 件")
    print(f"  エラー: {errors} 件")
    print(f"  PDFなし: {no_pdf} 件")
    print(f"  総inputトークン: {total_input_tokens:,}")
    print(f"  推定コスト: ${est_cost:.4f} (約¥{est_cost*150:.0f})")
    print(f"  → {OUTPUT}")


if __name__ == "__main__":
    main()
