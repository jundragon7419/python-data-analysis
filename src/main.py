"""
data/processed/consume_by_city/ 하위 도시별 CSV를 parquet으로 변환한다.
 
parquet은 컬럼 지향 포맷이라 CSV보다 파일 크기가 작고, 이후 날씨 데이터와
join하거나 EDA 단계에서 읽는 속도가 더 빠르다.
 
실행 위치 가정: 프로젝트 루트에서 실행
    python src/csv_to_parquet.py
"""
 
from pathlib import Path
import pandas as pd
 
PROCESSED_DIR = Path("reports")
 
 
def csv_to_parquet(csv_path: Path, parquet_path: Path | None = None) -> Path:
    """CSV 파일 하나를 읽어 같은 내용의 parquet 파일로 저장한다.
 
    Args:
        csv_path: 변환할 CSV 파일 경로
        parquet_path: 저장할 parquet 경로. 지정 안 하면 csv_path와 같은
            위치에 확장자만 .parquet으로 바꿔 저장한다.
 
    Returns:
        실제로 저장된 parquet 파일 경로
    """
    if parquet_path is None:
        parquet_path = csv_path.with_suffix(".parquet")
 
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    df.to_parquet(parquet_path, index=False)
 
    return parquet_path
 
 
def main():
    csv_files = sorted(PROCESSED_DIR.glob("*.csv"))
    if not csv_files:
        raise RuntimeError(f"{PROCESSED_DIR}에서 CSV 파일을 찾지 못했습니다.")
 
    for csv_path in csv_files:
        parquet_path = csv_to_parquet(csv_path)
        print(f"{csv_path.name} -> {parquet_path.name}")
 
 
if __name__ == "__main__":
    main()