import os
import io
import fitz  # PyMuPDF
from PIL import Image
import streamlit as st
from core.inspector import PDFInspector
from core.exporter import DualExporter
from core.presets import CATEGORIZED_PRESETS, BANNER_PRESETS
from core.color_manager import ICC_PROFILES, ColorManager
from core.tiler import ImageTiler
import streamlit.components.v1 as components

# ----------------- 페이지 설정 -----------------
st.set_page_config(
    page_title="PrintMaster Pro v1.0 | 실사출력 & 인쇄 전용 CMYK / Tiling 변환기",
    page_icon="assets/logo.jpg" if os.path.exists("assets/logo.jpg") else "🖨️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 🔥 크롬/엣지 자동 번역기 개입 방지 (현수막->배너 왜곡 차단 및 DOM 충돌 방지)
components.html("""
<script>
    const forceNoTranslate = () => {
        try {
            const topDoc = window.parent.document;
            if (topDoc && topDoc.documentElement) {
                topDoc.documentElement.lang = 'ko';
                topDoc.documentElement.setAttribute('translate', 'no');
                topDoc.documentElement.classList.add('notranslate');
                if (!topDoc.querySelector('meta[name="google"][content="notranslate"]')) {
                    const meta = topDoc.createElement('meta');
                    meta.name = 'google';
                    meta.content = 'notranslate';
                    topDoc.head.appendChild(meta);
                }
            }
        } catch(e) {}
    };
    forceNoTranslate();
    setInterval(forceNoTranslate, 1500);
</script>
""", height=0, width=0)

# ----------------- 세션 상태 초기화 (다운로드 시 화면 유지용) -----------------
if "conversion_results" not in st.session_state:
    st.session_state.conversion_results = None
if "current_file_name" not in st.session_state:
    st.session_state.current_file_name = None

# ----------------- 글로벌 모던 디자인 시스템 (CSS) -----------------
CUSTOM_CSS = """<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/static/pretendard.css');
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
    --bg-dark: #0B0F17;
    --card-surface: rgba(21, 28, 44, 0.75);
    --card-border: rgba(255, 255, 255, 0.08);
    --accent-indigo: #4F46E5;
    --accent-indigo-light: #6366F1;
    --accent-cyan: #0EA5E9;
    --text-main: #F8FAFC;
    --text-muted: #94A3B8;
}

html, body, [class*="css"] {
    font-family: 'Pretendard', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    color: var(--text-main);
}

.stApp {
    background-color: var(--bg-dark);
}

/* Glassmorphic Hero Banner with New Logo */
.hero-container {
    background: linear-gradient(135deg, rgba(30, 41, 59, 0.8) 0%, rgba(15, 23, 42, 0.9) 100%);
    backdrop-filter: blur(16px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px 28px;
    margin-bottom: 20px;
    box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5), 0 8px 10px -6px rgba(0, 0, 0, 0.4);
    display: flex;
    align-items: center;
    gap: 22px;
}

.hero-logo-wrapper {
    flex-shrink: 0;
    width: 72px;
    height: 72px;
    border-radius: 14px;
    overflow: hidden;
    box-shadow: 0 0 20px rgba(56, 189, 248, 0.35);
    border: 1px solid rgba(56, 189, 248, 0.4);
}

.hero-logo-wrapper img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}

.hero-text-wrapper {
    flex-grow: 1;
}

.hero-title {
    font-size: 2.0rem;
    font-weight: 800;
    letter-spacing: -0.02em;
    background: linear-gradient(90deg, #FFFFFF 0%, #E2E8F0 45%, #38BDF8 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 10px;
}

.hero-subtitle {
    color: var(--text-muted);
    font-size: 0.95rem;
    line-height: 1.4;
}

/* Badges */
.badge-group {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}

.badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 9999px;
    font-size: 0.78rem;
    font-weight: 600;
    letter-spacing: 0.02em;
    border: 1px solid rgba(255, 255, 255, 0.1);
}

.badge-indigo {
    background: rgba(79, 70, 229, 0.18);
    color: #A5B4FC;
    border-color: rgba(99, 102, 241, 0.3);
}

.badge-cyan {
    background: rgba(14, 165, 233, 0.18);
    color: #7DD3FC;
    border-color: rgba(14, 165, 233, 0.3);
}

.badge-emerald {
    background: rgba(16, 185, 129, 0.18);
    color: #6EE7B7;
    border-color: rgba(16, 185, 129, 0.3);
}

/* 콤팩트 슬림 사각형 파일 업로더 디자인 */
[data-testid="stFileUploader"] {
    max-width: 100%;
}
[data-testid="stFileUploader"] section {
    padding: 10px 18px !important;
    min-height: 68px !important;
    border: 1px dashed rgba(56, 189, 248, 0.45) !important;
    border-radius: 10px !important;
    background: rgba(15, 23, 42, 0.55) !important;
    transition: all 0.2s ease;
}
[data-testid="stFileUploader"] section:hover {
    border-color: #38BDF8 !important;
    background: rgba(15, 23, 42, 0.8) !important;
    box-shadow: 0 0 14px rgba(56, 189, 248, 0.2);
}
[data-testid="stFileUploader"] button {
    padding: 5px 14px !important;
    font-size: 0.82rem !important;
    font-weight: 600 !important;
    border-radius: 8px !important;
    background: rgba(79, 70, 229, 0.25) !important;
    border: 1px solid rgba(99, 102, 241, 0.4) !important;
    color: #E2E8F0 !important;
}
[data-testid="stFileUploader"] section > div > div > span {
    font-size: 0.86rem !important;
    color: #94A3B8 !important;
}
[data-testid="stFileUploader"] section > div > div > small {
    display: none !important;
}

/* Glassmorphic Cards */
.glass-card {
    background: var(--card-surface);
    backdrop-filter: blur(12px);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 16px;
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
}

/* Workflow Step Title */
.step-header {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 1.05rem;
    font-weight: 700;
    color: #F8FAFC;
    margin-bottom: 10px;
    padding-bottom: 6px;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
}

.step-num {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border-radius: 6px;
    background: linear-gradient(135deg, #4F46E5, #6366F1);
    color: white;
    font-size: 0.8rem;
    font-weight: 800;
}

/* Button Customization */
div.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #4F46E5 0%, #6366F1 100%) !important;
    color: #FFFFFF !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    box-shadow: 0 4px 20px rgba(79, 70, 229, 0.4) !important;
    transition: all 0.2s ease-in-out !important;
}

div.stButton > button[kind="primary"]:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 24px rgba(79, 70, 229, 0.6) !important;
}

/* Metric styling */
[data-testid="stMetricValue"] {
    font-size: 1.35rem !important;
    font-weight: 700 !important;
    color: #38BDF8 !important;
}

[data-testid="stMetricLabel"] {
    color: #94A3B8 !important;
    font-size: 0.82rem !important;
}

/* Tiling Panel Simulation */
.tile-strip-container {
    display: flex;
    overflow-x: auto;
    gap: 8px;
    padding: 10px;
    background: rgba(11, 15, 23, 0.6);
    border-radius: 10px;
    border: 1px dashed rgba(14, 165, 233, 0.3);
    margin: 10px 0;
}

.tile-strip-item {
    flex: 1;
    min-width: 90px;
    background: rgba(30, 41, 59, 0.7);
    border: 1px solid rgba(99, 102, 241, 0.4);
    border-radius: 8px;
    padding: 8px 6px;
    text-align: center;
    font-size: 0.78rem;
}

.tile-strip-title {
    font-weight: 700;
    color: #38BDF8;
    margin-bottom: 2px;
}

/* 🌟 종류 선택 메뉴: Stitch 프리미엄 세로 확장형 라운드 사각 카드 스타일 (한 줄 고정) */
[data-testid="stMain"] [data-testid="stRadio"] [role="radiogroup"],
.main [data-testid="stRadio"] [role="radiogroup"],
[data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="stRadio"] [role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: wrap !important;
    gap: 10px !important;
    padding: 6px 0 16px 0 !important;
    width: 100% !important;
}

[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"],
.main [data-testid="stRadio"] label[data-baseweb="radio"],
[data-testid="stAppViewContainer"] section:not([data-testid="stSidebar"]) [data-testid="stRadio"] label[data-baseweb="radio"] {
    flex: 1 1 calc(16.6% - 10px) !important;
    min-width: 145px !important;
    min-height: 64px !important;
    background: linear-gradient(180deg, rgba(30, 41, 59, 0.75) 0%, rgba(15, 23, 42, 0.9) 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.12) !important;
    border-top: 1px solid rgba(255, 255, 255, 0.22) !important;
    border-radius: 14px !important;
    padding: 16px 12px !important;
    margin: 0 !important;
    cursor: pointer !important;
    transition: all 0.22s cubic-bezier(0.4, 0, 0.2, 1) !important;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.35) !important;
    align-items: center !important;
    justify-content: center !important;
    display: inline-flex !important;
    text-align: center !important;
    white-space: nowrap !important;
}

/* 라디오 원형 체크버튼 숨김 처리 */
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child,
.main [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {
    display: none !important;
}

/* 박스 내부 텍스트 스타일 (무조건 한 줄) */
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] p,
.main [data-testid="stRadio"] label[data-baseweb="radio"] [data-testid="stMarkdownContainer"] p {
    font-size: 0.94rem !important;
    font-weight: 700 !important;
    color: #CBD5E1 !important;
    margin: 0 !important;
    letter-spacing: -0.02em !important;
    white-space: nowrap !important;
    word-break: keep-all !important;
    overflow: hidden !important;
    text-overflow: clip !important;
    line-height: 1.2 !important;
    transition: all 0.2s ease !important;
}

/* 박스 호버(Hover) 시 세련된 림라이트 & 띄움 효과 */
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover,
.main [data-testid="stRadio"] label[data-baseweb="radio"]:hover {
    background: linear-gradient(180deg, rgba(51, 65, 85, 0.8) 0%, rgba(30, 41, 59, 0.95) 100%) !important;
    border-color: rgba(56, 189, 248, 0.6) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.4), 0 0 14px rgba(56, 189, 248, 0.25) !important;
}

[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover [data-testid="stMarkdownContainer"] p,
.main [data-testid="stRadio"] label[data-baseweb="radio"]:hover [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
}

/* 선택된 라운드 박스 (Active / Checked): 네온 사이언-인디고 3D 글로우 카드 */
[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked),
.main [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {
    background: linear-gradient(135deg, #0284C7 0%, #0369A1 100%) !important;
    border: 1px solid #38BDF8 !important;
    box-shadow: 0 8px 24px -3px rgba(14, 165, 233, 0.6), 0 0 16px rgba(56, 189, 248, 0.45), inset 0 1px 1px rgba(255, 255, 255, 0.4) !important;
    transform: translateY(-3px) scale(1.02) !important;
}

[data-testid="stMain"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] p,
.main [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: #FFFFFF !important;
    font-weight: 800 !important;
    font-size: 0.97rem !important;
    white-space: nowrap !important;
    text-shadow: 0 1px 3px rgba(0, 0, 0, 0.4) !important;
}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

# ----------------- 임시 폴더 설정 -----------------
TEMP_DIR = os.path.join(os.getcwd(), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# ----------------- 히어로 헤더 (새 로고 이미지 연동) -----------------
logo_path = "assets/logo.jpg"
if os.path.exists(logo_path):
    import base64
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f'<div class="hero-logo-wrapper"><img src="data:image/jpeg;base64,{logo_b64}" alt="Logo"></div>'
else:
    logo_html = '<div class="hero-logo-wrapper" style="display:flex;align-items:center;justify-content:center;font-size:32px;">🖨️</div>'

st.markdown(f"""
<div class="hero-container">
    {logo_html}
    <div class="hero-text-wrapper">
        <div class="hero-title">
            <span>PrintMaster Pro</span>
            <span style="font-size: 0.95rem; padding: 2px 8px; background: rgba(99, 102, 241, 0.25); border: 1px solid rgba(99, 102, 241, 0.5); border-radius: 6px; color: #A5B4FC; vertical-align: middle;">v1.0</span>
        </div>
        <div class="hero-subtitle">
            실사출력소(대형 플로터 RIP) 및 인쇄소 직결 규격 자동 변환 워크스테이션 — <strong>AI 쇼크필터 벡터형 글자 칼선 복원</strong>, <strong>무손실 Flate PDF 빌드</strong>, <strong>롤 원단 자동 분할(Tiling)</strong>
        </div>
        <div class="badge-group">
            <span class="badge badge-indigo">⚡ AI 텍스트 벡터화 쇼크필터</span>
            <span class="badge badge-cyan">🎨 LittleCMS Japan Color 2001 표준</span>
            <span class="badge badge-emerald">✂️ RIP 메모리 오류 방지 Auto-Tiling</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

# ----------------- 1. 상단 인쇄 메뉴 선택 바 (현수막, 게시대, 간판, 에어간판, 배너, 전단) -----------------
st.markdown("""
<div class="step-header">
    <span class="step-num">1</span>
    <span>인쇄 출력 목적 / 규격 메뉴 선택 (해당 규격으로 자동 리사이징 & 업스케일)</span>
</div>
""", unsafe_allow_html=True)

categories = list(CATEGORIZED_PRESETS.keys())
selected_category = st.radio(
    "출력물 카테고리 선택",
    categories,
    horizontal=True,
    label_visibility="collapsed"
)

col_preset, col_dims = st.columns([3, 2])
with col_preset:
    sub_presets = CATEGORIZED_PRESETS[selected_category]
    preset_name = st.selectbox(
        f"📐 {selected_category} 세부 규격 선택",
        list(sub_presets.keys())
    )
    preset_data = sub_presets[preset_name]
    st.caption(f"💡 **용도 안내**: {preset_data['desc']}")

with col_dims:
    col_w, col_h = st.columns(2)
    default_w = float(preset_data["width_cm"]) if preset_data["width_cm"] is not None else 0.0
    default_h = float(preset_data["height_cm"]) if preset_data["height_cm"] is not None else 0.0
    
    with col_w:
        width_cm = st.number_input("목표 가로 폭 (cm)", value=default_w, step=10.0, min_value=0.0)
    with col_h:
        height_cm = st.number_input("목표 세로 높이 (cm)", value=default_h, step=5.0, min_value=0.0)

# ----------------- 2. 사이드바 세부 제어 (DPI, 선명화 강도, 색상, 분할 롤 폭) -----------------
st.sidebar.markdown("""
<div class="step-header">
    <span class="step-num">⚙️</span>
    <span>고급 인쇄 & 선명화 제어</span>
</div>
""", unsafe_allow_html=True)

sharpen_option = st.sidebar.selectbox(
    "🔥 글자 외곽선 칼선 복원 (AI Shock Filter)",
    [
        "극대화 복원 (Ultra Sharp - 권장, 벡터급 글자 칼날 복원)",
        "강력 글자 선명화 (Strong - 일반 인쇄/현수막)",
        "부드럽게 (Normal - 사진/인물 위주 출력물)",
        "선명화 끄기 (None)"
    ],
    index=0
)
if "Strong" in sharpen_option:
    sharpen_strength = "strong"
elif "Normal" in sharpen_option:
    sharpen_strength = "normal"
elif "None" in sharpen_option:
    sharpen_strength = "none"
else:
    sharpen_strength = "ultra"

dpi_setting = st.sidebar.select_slider(
    "인쇄 출력 DPI 설정 (해상도)",
    options=[72, 100, 150, 200, 300, 400],
    value=preset_data["default_dpi"]
)

super_sample_option = st.sidebar.select_slider(
    "🎯 텍스트 벡터 선명도 & 슈퍼샘플링",
    options=["1.0x 표준 해상도", "1.5x 고해상도", "2.0x 극초고해상도 (벡터급 칼날 복원 - 추천)"],
    value="2.0x 극초고해상도 (벡터급 칼날 복원 - 추천)",
    help="비트맵 PDF의 글자 윤곽선을 1픽셀 칼날 벡터처럼 선명화하고 600 DPI급으로 슈퍼샘플링합니다."
)
if "2.0x" in super_sample_option:
    super_sample_factor = 2.0
elif "1.5x" in super_sample_option:
    super_sample_factor = 1.5
else:
    super_sample_factor = 1.0

# 예상 픽셀 수 계산 표기
if width_cm > 0 and height_cm > 0:
    base_px_w = int((width_cm / 2.54) * dpi_setting)
    base_px_h = int((height_cm / 2.54) * dpi_setting)
    final_px_w = int(base_px_w * super_sample_factor)
    final_px_h = int(base_px_h * super_sample_factor)
    st.sidebar.caption(f"📊 실렌더링 해상도: `{final_px_w:,} x {final_px_h:,} px` (슈퍼샘플링 {super_sample_factor}x 적용)")

st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 12px 0;'>", unsafe_allow_html=True)

# 색상 모드: 기본값을 RGB(모니터 쨍한 색감 & 디지털 출력 표준)로 설정!
color_mode_option = st.sidebar.radio(
    "출력 색상 모드 (Color Mode)",
    options=[
        "RGB (화면 & 고화질 디지털 출력용 - 원본 100% 쨍한 색감 & 선명도)",
        "CMYK (전통 오프셋 합판인쇄소 납품 직결용)"
    ],
    index=0
)
selected_color_mode = "CMYK" if "CMYK" in color_mode_option else "RGB"

if selected_color_mode == "CMYK":
    icc_profile_key = st.sidebar.selectbox(
        "적용할 표준 ICC 프로파일",
        list(ICC_PROFILES.keys()),
        index=0
    )
    profile_info = ICC_PROFILES[icc_profile_key]
    st.sidebar.caption(f"🎯 **TAC(총잉크량)**: `{profile_info['tac']}` — {profile_info['desc']}")
    st.sidebar.info("💡 윈도우 기본 사진 뷰어는 CMYK 핫핑크/원색을 갈색으로 탁하게 표시합니다. 모니터에서 원본과 같은 색을 보시려면 sRGB 이미지를 확인하세요.")
else:
    icc_profile_key = None

st.sidebar.markdown("<hr style='border-color: rgba(255,255,255,0.08); margin: 12px 0;'>", unsafe_allow_html=True)

enable_tiling = st.sidebar.checkbox("대형 출력 자동 분할(Auto-Tiling) 활성화", value=True)

if enable_tiling:
    roll_preset = st.sidebar.selectbox("실사 롤 원단 규격 폭", list(ImageTiler.ROLL_WIDTH_PRESETS.keys()), index=3) # 150cm 기본
    if roll_preset == "직접 입력":
        max_roll_width_cm = st.sidebar.number_input("최대 롤 원단 폭 (cm)", value=150.0, step=10.0, min_value=30.0)
    else:
        max_roll_width_cm = ImageTiler.ROLL_WIDTH_PRESETS[roll_preset]

    overlap_cm = st.sidebar.number_input("접합 겹침 여백 (Overlap, cm)", value=3.0, min_value=0.0, max_value=15.0, step=0.5)
    split_direction = st.sidebar.selectbox(
        "분할 절단 방향",
        ["가로 분할 (세로선 기준 절단, 현수막 권장)", "세로 분할 (가로선 기준 절단, 타워형 권장)"]
    )
    st.sidebar.caption("💡 각 분할 패널에 겹침 여백이 자동 연장되어 출력되며, 고주파 융착 및 미싱 시 어긋남이 방지됩니다.")

# ----------------- 3. 콤팩트 사각형 파일 업로더 -----------------
st.markdown("""
<div class="step-header">
    <span class="step-num">2</span>
    <span>PDF 파일 업로드 (크기 자동인식 및 규격 변환)</span>
</div>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader(
    "PDF 파일 첨부 (클릭하여 파일 선택 또는 사각형 안으로 드래그 앤 드롭)", 
    type=["pdf"],
    help="AI 디자인 조판 PDF, 일러스트레이터/포토샵/인디자인 내보내기 PDF, 일반 문서 PDF 모두 지원"
)

if uploaded_file is not None:
    # 다른 파일이 업로드되면 이전 변환 결과 초기화
    if st.session_state.current_file_name != uploaded_file.name:
        st.session_state.current_file_name = uploaded_file.name
        st.session_state.conversion_results = None

    input_pdf_path = os.path.join(TEMP_DIR, uploaded_file.name)
    with open(input_pdf_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

    # PDF 구조 및 원본 크기 100% 정밀 자동 분석
    with st.spinner("🔍 PDF 문서 구조, 원본 규격, 고화질 임베디드 래스터 분석 중..."):
        info = PDFInspector.inspect_pdf(input_pdf_path)

    # 목표 출력 크기 확정
    target_w = width_cm if width_cm > 0 else info["width_cm"]
    target_h = height_cm if height_cm > 0 else info["height_cm"]

    scale_x = target_w / info["width_cm"] if info["width_cm"] > 0 else 1.0
    scale_y = target_h / info["height_cm"] if info["height_cm"] > 0 else 1.0

    # 분할 계산
    if enable_tiling:
        tile_calc = ImageTiler.calculate_tiles(target_w, target_h, max_roll_width_cm, overlap_cm, split_direction)
    else:
        tile_calc = None

    # 원본 vs 타깃 규격 자동인식 비교 카드
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric(
            "📐 원본 크기 (자동인식)",
            f"{info['width_cm']:.1f} x {info['height_cm']:.1f} cm",
            f"{info['width_pt']:.0f} x {info['height_pt']:.0f} pt"
        )
    with m2:
        st.metric(
            f"🚀 목표 출력 규격 ({selected_category.split()[1]})",
            f"{target_w:.1f} x {target_h:.1f} cm",
            f"배율 {scale_x:.1f}x / {scale_y:.1f}x 업스케일"
        )
    with m3:
        st.metric(
            "🎨 색역 / 선명화",
            f"{selected_color_mode} 모드",
            f"선명화: {sharpen_strength.upper()} (벡터급)"
        )
    with m4:
        if enable_tiling and tile_calc and tile_calc["num_tiles"] > 1:
            st.metric("✂️ 롤 원단 분할", f"{tile_calc['num_tiles']}장 분할", f"폭 약 {tile_calc['base_tile_len_cm']}cm (+{overlap_cm}cm)")
        else:
            st.metric("✂️ 출력 형태", "단일 통출력", "원단 폭 이내")
    st.markdown('</div>', unsafe_allow_html=True)

    # 썸네일 & 분할 시뮬레이션
    col_prev, col_detail = st.columns([1, 2])
    with col_prev:
        st.markdown("##### 📄 PDF 원본 썸네일 미리보기")
        try:
            doc_thumb = fitz.open(input_pdf_path)
            thumb_page = doc_thumb[0]
            thumb_pix = thumb_page.get_pixmap(matrix=fitz.Matrix(0.4, 0.4), alpha=False)
            thumb_img = Image.frombytes("RGB", [thumb_pix.width, thumb_pix.height], thumb_pix.samples)
            st.image(thumb_img, use_container_width=True, caption=f"원본 규격: {info['width_cm']} x {info['height_cm']} cm ({info['total_pages']}페이지)")
            doc_thumb.close()
        except Exception:
            st.info("썸네일 렌더링 대기 중")

    with col_detail:
        st.markdown(f"##### 📐 [{preset_name}] 업스케일 및 분할 출력 시뮬레이션")
        if enable_tiling and tile_calc and tile_calc["num_tiles"] > 1:
            st.markdown(f"목표 출력 폭 **`{target_w}cm`**가 선택하신 롤 원단 폭 **`{max_roll_width_cm}cm`**를 초과하여, **`{tile_calc['num_tiles']}장의 패널`**로 자동 분할 출력됩니다.")
            
            tiles_html = '<div class="tile-strip-container">'
            for i in range(tile_calc["num_tiles"]):
                tiles_html += f"""
                <div class="tile-strip-item">
                    <div class="tile-strip-title">패널 #{i+1:02d}</div>
                    <div>약 {tile_calc['base_tile_len_cm']} cm</div>
                    <div style="color: #6EE7B7; font-size: 0.72rem;">+{overlap_cm}cm 접합여백</div>
                </div>
                """
            tiles_html += '</div>'
            st.markdown(tiles_html, unsafe_allow_html=True)
        else:
            st.markdown(f"선택하신 롤 원단 폭(`{max_roll_width_cm}cm` 이하) 내에서 **1장의 단일 통출력**으로 제작됩니다.")

        st.markdown(f"""
        - **적용 메뉴 규격**: `{preset_name}` ({target_w}cm x {target_h}cm)
        - **선명화 알고리즘**: AI 쇼크 필터(Shock Filter) 글자 외곽선 칼날 복원 (다운스케일 원천 차단)
        - **인쇄 PDF 압축**: 무손실 Flate (DEFLATE) 0% 압축 손실 보장
        """)

    st.markdown("<br>", unsafe_allow_html=True)

    # 변환 실행 버튼
    action_btn_text = f"🚀 [{preset_name}] 초고해상도 인쇄 규격 변환 시작 ({target_w}cm x {target_h}cm)"
    if st.button(action_btn_text, type="primary", use_container_width=True):
        progress_bar = st.progress(5)
        status_text = st.empty()

        base_filename = os.path.splitext(uploaded_file.name)[0]
        output_jpg_path = os.path.join(TEMP_DIR, f"{base_filename}_{selected_category.split()[1]}_{target_w:.0f}x{target_h:.0f}cm_{selected_color_mode}.jpg")
        output_pdf_path = os.path.join(TEMP_DIR, f"{base_filename}_인쇄소납품용_{selected_color_mode}.pdf")

        # 1. 래스터화 및 벡터급 칼선 복원
        status_text.markdown(f"⏳ **1/3단계:** 고화질 해상도 자동 보장 & AI 쇼크필터 글자 칼선 복원 중...")
        progress_bar.progress(35)

        img_res = DualExporter.export_ultra_high_res_image(
            input_pdf_path, output_jpg_path,
            target_width_cm=target_w, target_height_cm=target_h,
            target_dpi=dpi_setting,
            color_mode=selected_color_mode,
            icc_profile_key=icc_profile_key,
            sharpen_strength=sharpen_strength,
            super_sample_factor=super_sample_factor
        )

        # 2. 인쇄소 납품용 무손실 PDF 빌드
        status_text.markdown("⏳ **2/3단계:** 무손실 Flate 인코딩 기반 초고화질 인쇄소 납품 PDF 빌드 중...")
        progress_bar.progress(70)

        DualExporter.export_vector_print_pdf(
            input_pdf_path, output_pdf_path,
            is_pure_raster=info["is_pure_raster"],
            target_width_cm=target_w, target_height_cm=target_h,
            target_dpi=dpi_setting,
            color_mode=selected_color_mode,
            icc_profile_key=icc_profile_key,
            sharpen_strength=sharpen_strength,
            super_sample_factor=super_sample_factor
        )

        # 3. 분할 타일링 (활성화된 경우)
        tiling_result = None
        if enable_tiling:
            status_text.markdown("⏳ **3/3단계:** 롤 원단 규격 맞춤 분할(Tiling) 및 겹침 여백(Overlap) ZIP 패키징 중...")
            progress_bar.progress(90)

            tiling_result = DualExporter.export_tiled_packages(
                base_image=img_res["image_obj"],
                base_filename=base_filename,
                total_width_cm=target_w,
                total_height_cm=target_h,
                dpi=dpi_setting,
                max_roll_width_cm=max_roll_width_cm,
                overlap_cm=overlap_cm,
                split_direction=split_direction,
                color_mode=selected_color_mode
            )

        progress_bar.progress(100)
        status_text.markdown(f"✨ **[{preset_name}] 초고해상도 인쇄 파일 및 패키징 완료!**")
        st.balloons()

        # 메모리에 파일 바이너리 프리로드 (다운로드 클릭 시 세션 상태 유지용)
        with open(output_pdf_path, "rb") as f:
            pdf_bytes = f.read()
        with open(img_res["screen_path"], "rb") as f:
            screen_bytes = f.read()
        with open(img_res["png_path"], "rb") as f:
            png_bytes = f.read()
        with open(output_jpg_path, "rb") as f:
            jpg_bytes = f.read()

        # 세션 상태에 저장 -> 다운로드 버튼을 눌러도 화면이 절대 닫히지 않고 그대로 유지됨!
        st.session_state.conversion_results = {
            "preset_name": preset_name,
            "target_w": target_w,
            "target_h": target_h,
            "dpi_setting": dpi_setting,
            "selected_color_mode": selected_color_mode,
            "icc_profile_key": icc_profile_key,
            "output_jpg_path": output_jpg_path,
            "output_pdf_path": output_pdf_path,
            "img_res": img_res,
            "tiling_result": tiling_result,
            "enable_tiling": enable_tiling,
            "overlap_cm": overlap_cm,
            "pdf_bytes": pdf_bytes,
            "screen_bytes": screen_bytes,
            "png_bytes": png_bytes,
            "jpg_bytes": jpg_bytes
        }

    # ----------------- 변환 완료 화면 (다운로드 클릭 후에도 영구 유지) -----------------
    if st.session_state.conversion_results is not None:
        res = st.session_state.conversion_results
        img_res = res["img_res"]
        tiling_result = res["tiling_result"]
        overlap_cm = res["overlap_cm"]
        target_w = res["target_w"]
        target_h = res["target_h"]
        dpi_setting = res["dpi_setting"]
        selected_color_mode = res["selected_color_mode"]
        icc_profile_key = res["icc_profile_key"]
        output_jpg_path = res["output_jpg_path"]
        output_pdf_path = res["output_pdf_path"]

        st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 20px 0;'>", unsafe_allow_html=True)
        
        # 💡 [필독] 모니터 화면 검증 가이드 배너
        st.markdown(f"""
        <div class="glass-card" style="border-left: 5px solid #10B981; background: rgba(16, 185, 129, 0.08); padding: 16px 20px; margin-bottom: 24px;">
            <h4 style="margin: 0 0 8px 0; color: #34D399; font-size: 1.05rem;">
                💡 [대표님 필독] 모니터에서 글자 선명도 & 색상을 100% 쨍하게 확인하는 방법
            </h4>
            <div style="color: #CBD5E1; font-size: 0.9rem; line-height: 1.6;">
                • <strong>글씨가 벡터처럼 또렷한지 확인:</strong> 아래 <strong>[💎 100% 무손실 PNG]</strong> 또는 <strong>[📄 무손실 PDF]</strong>를 열어보세요. 글자 외곽에 1픽셀 압축 손실도 없이 칼날처럼 쨍하게 출력됩니다.<br>
                • <strong>Windows 기본 '사진' 뷰어의 CMYK 왜곡 주의:</strong> 윈도우 사진 뷰어로 <code>_CMYK.jpg</code>를 열면 인쇄기 전용 색공간(YCCK)을 해석하지 못해 <strong>핫핑크가 칙칙한 벽돌색으로 보이고 글씨 경계가 흐려 보입니다.</strong><br>
                • 모니터에서 검토하거나 웹/SNS에 게시할 때는 <strong>[💎 무손실 PNG]</strong> 또는 <strong>[🌟 초고화질 sRGB JPG]</strong>로 확인하셔야 원본 이상의 극선명 화질을 온전히 체감하실 수 있습니다!
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("### 📥 출력 패키지 다운로드")

        # 분할 타일 ZIP 다운로드 섹션 (Tiling 활성화 시)
        if res["enable_tiling"] and tiling_result and tiling_result["total_tiles"] > 1:
            st.markdown(f"""
            <div class="glass-card" style="border-left: 4px solid #0EA5E9;">
                <h4 style="margin: 0 0 6px 0; color: #38BDF8;">✂️ 실사출력소 롤 원단 분할 타일 패키지 (총 {tiling_result['total_tiles']}장 분할)</h4>
                <div style="color: #94A3B8; font-size: 0.88rem; margin-bottom: 12px;">
                    대형 플로터 RIP 메모리 초과를 방지하며 각 패널에 <strong>{overlap_cm}cm 접합 겹침 여백</strong>이 포함되어 있어 출력 후 고주파/미싱 작업이 편리합니다.
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label=f"📦 분할 타일 전체 ZIP 패키지 다운로드 ({tiling_result['total_tiles']}장 분할본, 고화질)",
                data=tiling_result["zip_bytes"],
                file_name=tiling_result["zip_filename"],
                mime="application/zip",
                type="primary",
                use_container_width=True,
                key="btn_download_zip"
            )

            with st.expander(f"🔍 생성된 {tiling_result['total_tiles']}개 타일의 개별 규격 세부 정보 보기"):
                cols_tile = st.columns(min(4, tiling_result["total_tiles"]))
                for idx, t in enumerate(tiling_result["tiles"]):
                    col_target = cols_tile[idx % len(cols_tile)]
                    with col_target:
                        st.markdown(f"""
                        **{t['label']}**  
                        - 해상도: `{t['width_px']} x {t['height_px']} px`  
                        - 실출력 폭: `{t['real_width_cm']} x {t['real_height_cm']} cm`
                        """)
            st.markdown("<br>", unsafe_allow_html=True)

        # 결과물 3열 레이아웃 (1순위 무손실 PNG + 2순위 무손실 PDF + 3순위 고화질 JPG)
        rc1, rc2, rc3 = st.columns(3)
        
        with rc1:
            st.markdown(f"""
            <div class="glass-card" style="border-top: 3px solid #0EA5E9;">
                <span style="background: #0284C7; color: #FFF; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: bold;">1순위 추천 (화면 검증 & 디지털)</span>
                <h4 style="margin: 6px 0 6px 0; color: #38BDF8;">💎 100% 무손실 PNG</h4>
                <ul style="color: #94A3B8; font-size: 0.85rem; padding-left: 18px; margin-bottom: 12px;">
                    <li><strong>선명도:</strong> 벡터급 칼선 (압축 손실 0%)</li>
                    <li><strong>색상:</strong> 핫핑크/네온 원본 100% 일치 (sRGB)</li>
                    <li><strong>용도:</strong> 모니터에서 글자 선명도 즉시 확인용</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label="📥 무손실 PNG 다운로드 (추천: 벡터급 선명도)",
                data=res["png_bytes"],
                file_name=os.path.basename(img_res["png_path"]),
                mime="image/png",
                type="primary",
                use_container_width=True,
                key="btn_download_png"
            )

        with rc2:
            st.markdown(f"""
            <div class="glass-card" style="border-top: 3px solid #6366F1;">
                <span style="background: #4F46E5; color: #FFF; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: bold;">인쇄소 납품 공식 규격</span>
                <h4 style="margin: 6px 0 6px 0; color: #A5B4FC;">📄 인쇄소 납품용 초고화질 PDF</h4>
                <ul style="color: #94A3B8; font-size: 0.85rem; padding-left: 18px; margin-bottom: 12px;">
                    <li><strong>압축 방식:</strong> 100% 무손실 Flate (글자 번짐 0%)</li>
                    <li><strong>해상도:</strong> <code>{img_res['width_px']:,} x {img_res['height_px']:,} px</code></li>
                    <li><strong>용도:</strong> 상업 인쇄소 및 합판인쇄소 납품 전용</li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label="📥 인쇄소 납품용 무손실 PDF 다운로드",
                data=res["pdf_bytes"],
                file_name=os.path.basename(res["output_pdf_path"]),
                mime="application/pdf",
                type="primary",
                use_container_width=True,
                key="btn_download_pdf"
            )

        with rc3:
            st.markdown(f"""
            <div class="glass-card" style="border-top: 3px solid #10B981;">
                <span style="background: #059669; color: #FFF; font-size: 0.72rem; padding: 2px 8px; border-radius: 4px; font-weight: bold;">모니터 뷰어 & 출력 겸용</span>
                <h4 style="margin: 6px 0 6px 0; color: #6EE7B7;">🖼️ 초고화질 {selected_color_mode} JPG</h4>
                <ul style="color: #94A3B8; font-size: 0.85rem; padding-left: 18px; margin-bottom: 12px;">
                    <li><strong>품질:</strong> Quality 100 (Subsampling 4:4:4)</li>
                    <li><strong>해상도:</strong> <code>{img_res['width_px']:,} x {img_res['height_px']:,} px</code></li>
                    <li><strong>용량:</strong> <code>{img_res['file_size_mb']} MB</code></li>
                </ul>
            </div>
            """, unsafe_allow_html=True)

            st.download_button(
                label=f"📥 초고화질 {selected_color_mode} JPG 다운로드",
                data=res["jpg_bytes"],
                file_name=os.path.basename(res["output_jpg_path"]),
                mime="image/jpeg",
                use_container_width=True,
                key="btn_download_jpg"
            )


        # 변환 결과 글자 선명도 즉시 확인 인터랙티브 뷰어
        with st.expander("🔍 변환 결과물 글자 디테일 확대 미리보기 (모니터 즉시 검증)", expanded=True):
            st.image(img_res["rgb_obj"], caption=f"초고해상도 AI 쇼크필터 칼선 복원 결과 ({img_res['width_px']} x {img_res['height_px']} px)", use_container_width=True)

else:
    st.info("👆 위 작은 사각형 드롭존에 PDF 파일을 드래그하거나 선택하면 원본 규격 자동인식 및 목표 규격 변환이 활성화됩니다.")

# ----------------- 하단 푸터 -----------------
st.markdown("<hr style='border-color: rgba(255,255,255,0.06); margin-top: 36px;'>", unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; color: #64748B; font-size: 0.82rem; padding: 10px 0;">
    PrintMaster Pro v1.0 • 실사출력 & 인쇄 전용 엔지니어링 워크스테이션 • Powered by PyMuPDF, LittleCMS & OpenCV
</div>
""", unsafe_allow_html=True)
