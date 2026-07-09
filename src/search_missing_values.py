"""
data/raw/consume_data/ 하위 전체 CSV 파일(9개 도시 x 48개월)을 순회하며
컬럼별 결측치 현황을 종합하는 스크립트.

Raw 데이터의 경우 22년부터 25년까지 csv가 존재하는 도시 9개(하단 CITIES 참고)를 미리 추출

목적: 정규화(전처리) 방향을 결정하기 전, 결측치가 어디에 얼마나 있는지 파악하기 위한 사전 조사 단계.
이 스크립트는 결측치를 채우거나 삭제하지 않고, 현황만 집계해서 리포트로 남긴다.

출력:
    reports/missing_value_summary.csv - 파일별 X 컬럼별 결측치 현황
    콘솔에 컬럼별 전체 결측 비율 요약 출력
"""

from pathlib import Path # path용
import pandas as pd

RAW_DIR = Path("data/raw/consume_data") # Raw 데이터 path (csv는 git ignore되어있음)
REPORT_DIR = Path("reports") # 결과

CITIES = [
    "광명시", "수원시", "시흥시", "안산시", "안양시",
    "용인시", "포천시", "하남시", "화성시",
]
# 4개년동안 유지되지 않은 도시는 삭제. __init__.py 참고

YEARS = [2022, 2023, 2024, 2025]
MONTHS = range(1, 13)


def file_path(city: str, year: int, month: int) -> Path:
    """도시/연도/월로부터 예상 파일 경로를 만든다.

    구조: data/raw/consume_data/{year}/{year}_{month:02d}/{city}-{year}-{month:02d}.csv
    """
    month_folder = f"{year}_{month:02d}"
    filename = f"{city}-{year}-{month:02d}.csv"
    return RAW_DIR / str(year) / month_folder / filename # ex) data/raw/consume_data/2024/2024_06/광명시-2024-06.csv


def read_csv_safely(path: Path) -> pd.DataFrame | None:
    """인코딩이 UTF-8 또는 CP949(EUC-KR)일 수 있으므로 순차 시도한다.
    
    출력: 
        인코딩 성공시 DataFrame 출력
        인코딩 실패시 None -> scan_file에서 None 출력 -> 전체 결측 출력시 처리된 파일 x
    """
    for encoding in ("utf-8", "cp949"):
        try:
            return pd.read_csv(path, encoding=encoding)
        except UnicodeDecodeError: # 디코딩 에러시 다시 시도
            continue
        except Exception as e: # 위 에러 외 나머지 에러
            print(f"  [읽기 실패] {path}: {e}")
            return None
    print(f"  [인코딩 실패] {path}: utf-8/cp949 모두 실패")
    return None


def scan_file(path: Path, city: str, year: int, month: int) -> dict | None:
    """파일 하나를 읽어 컬럼별 결측 개수/비율과 기본 정보를 dict로 반환한다."""
    df = read_csv_safely(path)
    if df is None: # read_csv_safely docstring 확인
        return None

    total_rows = len(df)
    row = {
        "city": city,
        "year": year,
        "month": month,
        "file": path.name,
        "total_rows": total_rows,
    }

    for col in df.columns: # 결측치 계산 후 df.colmns의 각 결측 key를 만들어 dict에 추가
        missing = df[col].isna().sum()
        row[f"{col}__missing_cnt"] = missing
        row[f"{col}__missing_pct"] = (missing / total_rows * 100) if total_rows else 0.0

    return row


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    summary_rows = []

    total = len(CITIES) * len(YEARS) * len(MONTHS) # 전체 csv 파일 개수 = 9 * 4 * 12
    checked = 0

    for city in CITIES:
        for year in YEARS:
            for month in MONTHS:
                checked += 1
                path = file_path(city, year, month) # 파일 path 생성

                print(f"[{checked}/{total}] 처리 중: {path}") # 실시간으로 처리 중 파일 표시
                result = scan_file(path, city, year, month) # 인코딩이 실패하면 None 반환
                if result is not None:
                    summary_rows.append(result)

    # 파일별 결측 현황 저장
    summary_df = pd.DataFrame(summary_rows) # 데이터 프레임으로 전환 dict -> DataFrame
    summary_path = REPORT_DIR / "missing_value_summary.csv" # reports/missing_value_summary.csv
    summary_df.to_csv(summary_path, index=False, encoding="utf-8-sig") # csv로 저장
    print(f"\n파일별 결측치 요약 저장: {summary_path} ({len(summary_df)}개 파일)") # scan_file에서 None이 반환되면 len(summary_df) != 9 * 4 * 12임

    # 컬럼별 전체 결측 비율 콘솔 요약
    if not summary_df.empty: # 파일 루트가 잘못될 시 아무것도 담기지 않음 (인코딩 에러와는 다름)
        pct_cols = [c for c in summary_df.columns if c.endswith("__missing_pct")] # endswitch로 마지막 컬럼에 결측치 퍼센트 확인 후 c에 넣음 (접미사라 확인 가능)
        print("\n=== 컬럼별 평균 결측 비율 (전체 파일 기준) ===")
        for col in pct_cols: # 결측치 퍼센트
            col_name = col.replace("__missing_pct", "") # 원래 이름은 {col}__missing_pct로 포맷되어있기에 그걸 ""로 바꿔서 col만 출력 (scan_file 함수 참고)
            print(f"  {col_name:20s}: {summary_df[col].mean():.4f}%") # 20칸 포맷, 소수점 4자리
    else:
        print("\n처리된 파일이 없습니다. RAW_DIR 경로와 파일명을 확인하세요.")


if __name__ == "__main__":
    main()

"""
결과는 결측치가 없다고 뜸
카드사에서 결재 시의 정보를 자동으로 기록하기에 타당하다 판단 후 진행
"""