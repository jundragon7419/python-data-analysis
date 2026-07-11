"""
도시별 소비 데이터(parquet)에 권역별 날씨 데이터를 merge하여
하나의 최종 분석용 데이터셋으로 만든다.

권역 매핑: 포천시->북부, 하남시->동부, 나머지 7개 도시->남부

실행 위치 가정: 프로젝트 루트에서 실행
    python src/merge_weather.py

입력:
    data/processed/consume_by_city/{도시명}.parquet  (9개)
    data/processed/weather_by_region/weather_{권역명}.parquet (남부/동부/북부 3개)

출력:
    data/processed/consume_weather_merged.parquet  (9개 도시 통합 + 날씨 join 완료)
"""

from pathlib import Path
import pandas as pd

CONSUME_DIR = Path("data/processed/consume_by_city")
WEATHER_DIR = Path("data/processed/weather_by_region")
OUTPUT_PATH = Path("data/processed/consume_weather_merged.parquet")

CITY_TO_REGION = {
    "포천시": "북부",
    "하남시": "동부",
    "광명시": "남부",
    "수원시": "남부",
    "시흥시": "남부",
    "안산시": "남부",
    "안양시": "남부",
    "용인시": "남부",
    "화성시": "남부",
}

REGIONS = ["남부", "동부", "북부"]


def load_weather() -> pd.DataFrame:
    """남부/동부/북부 날씨 parquet 3개를 읽어 하나로 합친다."""
    frames = []
    for region in REGIONS:
        path = WEATHER_DIR / f"weather_{region}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"날씨 파일을 찾을 수 없습니다: {path}")
        frames.append(pd.read_parquet(path))

    weather = pd.concat(frames, ignore_index=True)
    weather["date"] = pd.to_datetime(weather["date"])
    return weather


def load_city_consume(city: str) -> pd.DataFrame:
    """도시 하나의 소비 데이터를 읽고 도시명/권역 컬럼을 붙인다."""
    path = CONSUME_DIR / f"{city}.parquet"
    df = pd.read_parquet(path)

    df["도시"] = city
    df["지점명"] = CITY_TO_REGION[city]

    # 날짜(예: 20220101, int) -> datetime 변환 (날씨 데이터와 키를 맞추기 위함)
    df["date"] = pd.to_datetime(df["날짜"].astype(str), format="%Y%m%d")

    return df


def main():
    weather = load_weather()

    merged_frames = []
    total_before_amt = 0
    total_before_rows = 0

    for city in CITY_TO_REGION:
        city_df = load_city_consume(city)

        before_amt = city_df["매출금액"].sum()
        before_rows = len(city_df)
        total_before_amt += before_amt
        total_before_rows += before_rows

        merged = city_df.merge(weather, on=["date", "지점명"], how="left")

        # merge 후 행 수가 늘거나 줄면 키 중복/누락이 있다는 뜻이므로 즉시 확인
        if len(merged) != before_rows:
            print(
                f"  [경고] {city}: merge 전후 행 수 불일치 "
                f"({before_rows:,} -> {len(merged):,})"
            )

        missing_weather = merged["평균기온(°C)"].isna().sum()
        if missing_weather > 0:
            print(f"  [경고] {city}: 날씨 매칭 안 된 행 {missing_weather}건")

        print(f"{city} ({CITY_TO_REGION[city]}): {len(merged):,}행 merge 완료")
        merged_frames.append(merged)

    final_df = pd.concat(merged_frames, ignore_index=True)

    # 최종 검증: merge 전체 과정에서 매출금액 총합/행 수가 그대로인지 확인
    total_after_amt = final_df["매출금액"].sum()
    total_after_rows = len(final_df)

    if total_before_amt != total_after_amt or total_before_rows != total_after_rows:
        print(
            f"  [불일치 경고] 행 수: {total_before_rows:,} -> {total_after_rows:,}, "
            f"매출금액: {total_before_amt:,} -> {total_after_amt:,}"
        )
    else:
        print(f"\n[검증 통과] 전체 merge 전후 행 수/매출금액 총합 일치 (행={total_after_rows:,})")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    final_df.to_parquet(OUTPUT_PATH, index=False)
    print(f"저장 완료: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()