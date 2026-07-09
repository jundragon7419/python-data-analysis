"""
data/processed/consume_weather_merged.parquet을 소분류(card_tpbuz_nm_2) 기준으로
'필수/애매/불필요' 3개 그룹으로 나눠 각각 별도 parquet 파일로 저장한다.

분류 기준: "날씨에 따른 일반 사람들의 소비패턴"이라는 분석 목적에 맞는가.
- 필수: 날씨 반응 가설이 뚜렷한 카테고리 (음식, 일상소매, 야외활동/여가 등)
- 애매: 정기성/계획성이 섞여있어 상관관계 확인 후 재판단이 필요한 카테고리
- 불필요: 기관/B2B성, 내구재, 계획적 고액지출 등 날씨와 인과관계가 억지스러운 카테고리

실행 위치 가정: 프로젝트 루트에서 실행
    python src/split_by_category.py

출력:
    data/processed/consume_weather_by_category/필수.parquet
    data/processed/consume_weather_by_category/애매.parquet
    data/processed/consume_weather_by_category/불필요.parquet
"""

from pathlib import Path
import pandas as pd

INPUT_PATH = Path("data/processed/consume_weather_merged.parquet")
OUTPUT_DIR = Path("data/processed/consume_weather_by_category")

ESSENTIAL = [
    # 음식
    "간이주점", "고기요리", "닭/오리요리", "별식/퓨전요리", "분식", "양식",
    "음식배달서비스", "일식/수산물", "중식", "커피/음료", "패스트푸드", "한식",
    "제과/제빵/떡/케익",
    # 일상 소매
    "건강/기호식품", "음/식료품소매", "의복/의류", "종합소매점", "패션잡화",
    # 야외활동/여가
    "스포츠/레져용품", "일반스포츠", "취미/오락",
    # 이동/생활
    "교통서비스", "연료판매",
    # 건강
    "의약/의료품",
]

AMBIGUOUS = [
    "공연관람", "문화서비스", "전시장", "경기관람",
    "인터넷쇼핑",
    "렌탈서비스", "미용서비스", "사우나/휴게시설", "세탁/가사서비스",
    "서적/도서", "화장품소매",
    "숙박", "요가/단전/마사지",
    "부페", "유흥주점", "휴게소/대형업체",
    "일반병원",
]

UNNECESSARY = [
    "공공기관", "기업", "단체", "종교", "학교",
    "기타결제", "방송/미디어", "시스템/통신",
    "가례서비스", "광고/인쇄/인화", "무점포서비스", "보안/운송", "부동산",
    "수리서비스", "여행/유학대행", "전문서비스", "차량관리/서비스", "회비/공과금",
    "금융상품/서비스",
    "가전제품", "기타용품", "방문판매", "사무/교육용품", "선물/완구", "악기/공예",
    "유아용품", "인테리어/가정용품", "제조/도매", "차량관리/부품", "차량판매",
    "기타의료", "수의업", "종합병원", "특화병원",
    "기술/직업교육학원", "기타교육", "독서실/고시원", "예체능계학원",
    "외국어학원", "유아교육", "입시학원", "자동차학원",
]

CATEGORY_GROUPS = {
    "필수": ESSENTIAL,
    "애매": AMBIGUOUS,
    "불필요": UNNECESSARY,
}


def main():
    df = pd.read_parquet(INPUT_PATH)

    # 세 리스트 중 어디에도 없는 소분류가 있는지 확인 (누락 방지)
    all_listed = set(ESSENTIAL) | set(AMBIGUOUS) | set(UNNECESSARY)
    actual_categories = set(df["소분류"].unique())
    unlisted = actual_categories - all_listed
    if unlisted:
        print(f"[경고] 분류 리스트에 없는 소분류 발견: {sorted(unlisted)}")
        print("       이 소분류들은 어느 출력 파일에도 포함되지 않습니다.")

    # 리스트에는 있는데 실제 데이터엔 없는 소분류도 참고로 알려줌 (오탈자 확인용)
    not_in_data = all_listed - actual_categories
    if not_in_data:
        print(f"[참고] 분류 리스트엔 있지만 데이터에 없는 소분류: {sorted(not_in_data)}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    total_rows = len(df)
    split_rows = 0

    for group_name, category_list in CATEGORY_GROUPS.items():
        group_df = df[df["소분류"].isin(category_list)]
        split_rows += len(group_df)

        output_path = OUTPUT_DIR / f"{group_name}.parquet"
        group_df.to_parquet(output_path, index=False)
        print(f"{group_name}: {len(group_df):,}행 ({group_df['소분류'].nunique()}개 소분류) -> {output_path}")

    # 검증: 세 그룹으로 나눈 행 수 합이 unlisted를 제외한 원본과 일치하는지 확인
    unlisted_rows = len(df[df["소분류"].isin(unlisted)]) if unlisted else 0
    expected_rows = total_rows - unlisted_rows

    if split_rows == expected_rows:
        print(f"\n[검증 통과] 분류된 행 수 합계 일치 (원본 {total_rows:,}행 중 {split_rows:,}행 분류됨)")
    else:
        print(f"\n[불일치 경고] 원본 {total_rows:,}행, 분류 후 합계 {split_rows:,}행 (차이: {total_rows - split_rows:,})")


if __name__ == "__main__":
    main()