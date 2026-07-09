"""
data/processed/consume_by_city/ 하위 9개 도시 CSV를 모두 읽어
대분류-소분류 고유 조합을 뽑아 정리한다.

normalize_by_city.py 실행 후 사용 (그 결과물에 대분류/소분류 컬럼이
남아있으므로, 원본(raw) 432개 파일을 다시 읽을 필요 없이 훨씬 가볍게 처리).

실행 위치 가정: 프로젝트 루트에서 실행
    python src/list_categories.py

출력:
    reports/category_list.csv  (대분류, 소분류, 소분류 개수)
    콘솔에 대분류별 소분류 목록 출력
"""

from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path("data/processed/consume_by_city")
REPORT_DIR = Path("reports")


def main():
    files = sorted(PROCESSED_DIR.glob("*.csv"))
    if not files:
        raise RuntimeError(f"{PROCESSED_DIR}에서 CSV 파일을 찾지 못했습니다. normalize_by_city.py를 먼저 실행하세요.")

    frames = [pd.read_csv(f, usecols=["대분류", "소분류"]) for f in files]
    all_df = pd.concat(frames, ignore_index=True)

    unique_pairs = all_df.drop_duplicates().sort_values(["대분류", "소분류"])

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = REPORT_DIR / "category_list.csv"
    unique_pairs.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"저장 완료: {output_path} (총 {len(unique_pairs)}개 소분류)\n")

    print(f"=== 대분류 목록 ({unique_pairs['대분류'].nunique()}개) ===")
    for major in sorted(unique_pairs["대분류"].unique()):
        minors = unique_pairs.loc[unique_pairs["대분류"] == major, "소분류"].tolist()
        print(f"\n[{major}] ({len(minors)}개)")
        print("  " + ", ".join(minors))


if __name__ == "__main__":
    main()