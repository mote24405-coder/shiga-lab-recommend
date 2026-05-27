"""
data/raw/theses.json の論文タイトルからルールベースでラベルを抽出。
結果を data/processed/thesis_labels.json に保存。
実行: docker compose run --rm web python scripts/extract_labels_rule_based.py
"""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from app.services.label_matcher import RuleBasedLabelExtractor, LABEL_RULES

INPUT = "data/raw/theses.json"
OUTPUT = "data/processed/thesis_labels.json"


def main():
    if not os.path.exists(INPUT):
        print(f"{INPUT} が見つかりません。先に crawl_repo_items.py を実行してください。")
        return

    with open(INPUT, encoding="utf-8") as f:
        theses = json.load(f)

    extractor = RuleBasedLabelExtractor()
    all_label_names = list(LABEL_RULES.keys())

    results = []
    for thesis in theses:
        text = (thesis.get("title") or "") + " " + (thesis.get("abstract") or "")
        matched = extractor.extract(text, all_label_names)
        if matched:
            results.append({
                "title": thesis["title"],
                "repo_url": thesis.get("repo_url"),
                "year": thesis.get("year"),
                "author_name": thesis.get("author_name"),
                "matched_labels": matched,
            })
            print(f"  {thesis['title'][:50]}: {matched}")

    os.makedirs("data/processed", exist_ok=True)
    with open(OUTPUT, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n{len(results)} 件を {OUTPUT} に保存しました。")


if __name__ == "__main__":
    main()
