"""
data/raw/consume_data/ 하위 9개 도시 x 48개월 CSV를 도시 단위로 통합하고,
[날짜, 업종중분류(card_tpbuz_nm_2), 연령그룹] 기준으로 매출금액/매출건수를
집계하여 도시별 CSV 1개씩(총 9개) 생성한다.

집계 과정에서 행정동, 시간대, 성별, 업종코드는 값 자체가
버려지고 합산에 흡수된다 (더 이상 구분하지 않음).
중요할 수 있으나 이 정보들로만 충분히 분석 가능하다 생각해 이대로 진행.
필요시 다시 추가 예정.

연령 그룹 매핑 (원본 age 코드 기준):
    1, 2            -> 그룹1 (미분류/어린이/청소년)
    3, 4            -> 그룹2 (청년/사회초년생)
    5, 6, 7         -> 그룹3 (중장년)
    8, 9, 10, 11    -> 그룹4 (노년)

출력:
    data/processed/consume_by_city/{도시명}.csv  (도시당 1개, 총 9개)
"""

from pathlib import Path # path용
import pandas as pd

RAW_DIR = Path("data/raw/consume_data") # 결측치 처리 후 실행 요함
OUTPUT_DIR = Path("data/processed/consume_by_city")

CITIES = [ # 선정된 9개 도시
    "광명시", "수원시", "시흥시", "안산시", "안양시",
    "용인시", "포천시", "하남시", "화성시",
]
YEARS = [2022, 2023, 2024, 2025]
MONTHS = range(1, 13)

# 사용할 컬럼 (날짜, 대분류, 소분류, 나이대, 매출액, 매출건수)
USE_COLS = ["ta_ymd", "card_tpbuz_nm_1", "card_tpbuz_nm_2", "age", "amt", "cnt"]

AGE_GROUP_MAP = {
    1: 1,
    2: 1,
    3: 2,
    4: 2,
    5: 3,
    6: 3,
    7: 3,
    8: 4,
    9: 4,
    10: 4,
    11: 4,
}


def file_path(city: str, year: int, month: int) -> Path: # 파일 path 출력, search_missing_values의 함수와 동일한 방식
    month_folder = f"{year}_{month:02d}"
    filename = f"{city}-{year}-{month:02d}.csv"
    return RAW_DIR / str(year) / month_folder / filename


def read_csv_safely(path: Path) -> pd.DataFrame | None:# 인코딩 결과 출력, search_missing_values의 함수와 동일한 방식
    for encoding in ("utf-8", "cp949"):
        try:
            return pd.read_csv(path, usecols=USE_COLS, encoding=encoding)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"  [읽기 실패] {path}: {e}")
            return None
    print(f"  [인코딩 실패] {path}: utf-8/cp949 모두 실패")
    return None


def aggregate_one_month(df: pd.DataFrame) -> pd.DataFrame:
    """월별 원본 하나를 [ta_ymd, card_tpbuz_nm_2, age_group] 기준으로 즉시 집계한다.

    월 단위로 바로 groupby해서 원본(수십만 행)을 작은 집계 결과(수백~수천 행)로 줄인 뒤 버리는 게 핵심이다.
    48개월 원본을 전부 메모리에 쌓아두지 않기위한 설계다.

    처음에는 전체 단위를 들고 있었으나 메모리 부족으로 인해 errupt가 일어나 수정한 결과이다.
    """
    df = df.copy() # 원본 수정 x
    df["age"] = df["age"].astype(int) # int로 바꿈
    df["age_group"] = df["age"].map(AGE_GROUP_MAP) # 그룹으로 매핑

    unmapped = df["age_group"].isna().sum() # 결측치가 없는 것으로 확인되었으나 1 미만 11 초과의 값이 있을 수 있기에 확인
    if unmapped > 0:
        unmapped_ages = df.loc[df["age_group"].isna(), "age"].unique() # age_group이 매핑되지 않은 마스크를 구하고 그 age 값을 모두(unique) 출력
        # 이는 map이 오류를 띄우지 않고 NaN을 넣을 수 있기 때문
        print(f"  [경고] 매핑 안 된 age 코드 발견: {unmapped_ages} ({unmapped}건)")

    result = df.groupby( # 날짜, 대분류, 소분류, 나이그룹으로 그룹바이
        ["ta_ymd", "card_tpbuz_nm_1", "card_tpbuz_nm_2", "age_group"], as_index=False # 해당 컬럼들을 인덱스화 X
    ).agg(amt=("amt", "sum"), cnt=("cnt", "sum")) # 매출금액과 매출건수를 합산해서 결과
    # 성별, 시간대, 행정동은 사라짐

    return result


def normalize_city(city: str) -> tuple[pd.DataFrame, int]:
    """한 도시의 48개월 파일을 월별로 읽어 즉시 집계하고, 작은 집계 결과만 concat한다.

    Returns:
        최종 집계 결과, 원본 총 행 수, 원본 amt 총합, 원본 cnt 총합
    """
    monthly_aggs = []
    raw_row_count = 0
    raw_amt_sum = 0.0
    raw_cnt_sum = 0

    for year in YEARS:
        for month in MONTHS:
            path = file_path(city, year, month)
            if not path.exists(): # 파일 유무 확인
                print(f"[파일 없음] {path}")
                continue

            df = read_csv_safely(path)
            if df is None: # 인코딩 실패시
                continue

            raw_row_count += len(df) # 전체 행 개수 파악용

            monthly_result = aggregate_one_month(df)
            monthly_aggs.append(monthly_result)

            del df  # 원본은 즉시 버려서 메모리에 안 남긴다

    if not monthly_aggs: # 결과가 없을시 (어처피 한 파일씩 읽어서 내놓기에 해당 파일 없을 시 와 동일)
        raise RuntimeError(f"{city}: 읽을 수 있는 파일이 하나도 없습니다.")

    # 날짜는 월마다 겹치지 않으므로 단순 concat으로 충분하며 그룹바이 없이 그대로 사용한다.
    city_result = pd.concat(monthly_aggs, ignore_index=True).sort_values( # 합친 후 정렬
        ["ta_ymd", "card_tpbuz_nm_1", "card_tpbuz_nm_2", "age_group"]
    )

    return city_result, raw_row_count


def main():

    for city in CITIES:
        print(f"\n=== {city} 처리 시작 ===")
        result, raw_row_count= normalize_city(city)

        output_path = OUTPUT_DIR / f"{city}.csv"

        result["amt_per_cnt"] = (result["amt"] / result["cnt"]).round(2) # 매출금액/매출건수.round(2)를 마지막 열에 추가

        result = result[ # 결과 추출
            [
                "ta_ymd",
                "card_tpbuz_nm_1",
                "card_tpbuz_nm_2",
                "age_group",
                "amt",
                "cnt",
                "amt_per_cnt",
            ]
        ]
        result.columns = [ # 컬럼명 한글화
            "날짜",
            "대분류",
            "소분류",
            "연령 그룹",
            "매출금액",
            "매출건수",
            "건당 매출금액",
        ]

        result.to_csv(output_path, index=False, encoding="utf-8-sig") #csv로 저장
        print(f"  원본 {raw_row_count:,}행 -> 집계 후 {len(result):,}행")
        print(f"  저장 완료: {output_path}")


if __name__ == "__main__":
    main()