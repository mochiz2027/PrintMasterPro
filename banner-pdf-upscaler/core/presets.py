"""현수막, 게시대, 간판, 에어간판, 배너, 전단 출력용 표준 카테고리 및 규격 프리셋"""

CATEGORIZED_PRESETS = {
    "🚩 현수막": {
        "현수막 기본 (500cm x 90cm)": {
            "width_cm": 500.0,
            "height_cm": 90.0,
            "default_dpi": 150,
            "desc": "길거리 일반 현수막 표준 규격"
        },
        "현수막 소형 (400cm x 70cm)": {
            "width_cm": 400.0,
            "height_cm": 70.0,
            "default_dpi": 150,
            "desc": "실내 행사 및 소형 게시장소용"
        },
        "현수막 대형 (600cm x 90cm)": {
            "width_cm": 600.0,
            "height_cm": 90.0,
            "default_dpi": 150,
            "desc": "광폭 대로변 홍보용 대형 현수막"
        }
    },
    "🏛️ 게시대 현수막": {
        "게시대 기본 (580cm x 70cm)": {
            "width_cm": 580.0,
            "height_cm": 70.0,
            "default_dpi": 150,
            "desc": "전국 지자체 표준 지정게시대 규격"
        },
        "게시대 광폭 (600cm x 70cm)": {
            "width_cm": 600.0,
            "height_cm": 70.0,
            "default_dpi": 150,
            "desc": "일부 지자체 전용 6M 게시대 규격"
        }
    },
    "🏢 간판 / 후렉스": {
        "후렉스 전면간판 표준 (300cm x 100cm)": {
            "width_cm": 300.0,
            "height_cm": 100.0,
            "default_dpi": 150,
            "desc": "매장 전면 조명/비조명 후렉스 간판"
        },
        "후렉스 대형간판 (500cm x 120cm)": {
            "width_cm": 500.0,
            "height_cm": 120.0,
            "default_dpi": 150,
            "desc": "대형 매장 및 빌딩 전면 간판"
        },
        "돌출간판 (80cm x 100cm)": {
            "width_cm": 80.0,
            "height_cm": 100.0,
            "default_dpi": 200,
            "desc": "측면 돌출 포인트 간판"
        },
        "후렉스 / 유포지 맞춤 (크기 직접입력)": {
            "width_cm": None,
            "height_cm": None,
            "default_dpi": 200,
            "desc": "원본 비율 유지 또는 원하는 실측 크기 직접 입력"
        }
    },
    "🎈 에어간판": {
        "원형 에어간판 (124cm x 300cm)": {
            "width_cm": 124.0,
            "height_cm": 300.0,
            "default_dpi": 150,
            "desc": "실외 원통형 회전/스탠드 에어간판"
        },
        "슬림 에어간판 (100cm x 300cm)": {
            "width_cm": 100.0,
            "height_cm": 300.0,
            "default_dpi": 150,
            "desc": "인도 점유율이 적은 슬림형 에어간판"
        },
        "소형 에어간판 (80cm x 200cm)": {
            "width_cm": 80.0,
            "height_cm": 200.0,
            "default_dpi": 150,
            "desc": "골목 및 실내 행사용 콤팩트 에어간판"
        }
    },
    "🧍 X배너 / 페트": {
        "X배너 / 페트배너 표준 (60cm x 180cm)": {
            "width_cm": 60.0,
            "height_cm": 180.0,
            "default_dpi": 200,
            "desc": "실내외 스탠드형 X배너 / 물통배너 표준"
        },
        "롤업 배너 (85cm x 200cm)": {
            "width_cm": 85.0,
            "height_cm": 200.0,
            "default_dpi": 200,
            "desc": "전시회 및 박람회용 롤업 거치대"
        },
        "미니 X배너 (15cm x 30cm)": {
            "width_cm": 15.0,
            "height_cm": 30.0,
            "default_dpi": 300,
            "desc": "카운터 및 테이블 비치용 미니 배너"
        }
    },
    "📑 전단 / 포스터": {
        "A4 전단 (21cm x 29.7cm)": {
            "width_cm": 21.0,
            "height_cm": 29.7,
            "default_dpi": 300,
            "desc": "고품질 홍보 전단지 표준"
        },
        "16절 전단 (18.5cm x 26cm)": {
            "width_cm": 18.5,
            "height_cm": 26.0,
            "default_dpi": 300,
            "desc": "국내 상가 배포용 16절지 전단 표준"
        },
        "A3 포스터 (29.7cm x 42cm)": {
            "width_cm": 29.7,
            "height_cm": 42.0,
            "default_dpi": 300,
            "desc": "실내 게시용 중간 크기 포스터"
        },
        "A1 포스터 (59.4cm x 84.1cm)": {
            "width_cm": 59.4,
            "height_cm": 84.1,
            "default_dpi": 300,
            "desc": "옥외 및 전시벽면용 대형 포스터"
        }
    }
}

# 기존 코드와의 호환성을 위한 평탄화(Flat) 딕셔너리
BANNER_PRESETS = {}
for cat_name, sub_dict in CATEGORIZED_PRESETS.items():
    for name, data in sub_dict.items():
        BANNER_PRESETS[name] = data
