import os
import sys
import fitz
from PIL import Image

if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
from core.inspector import PDFInspector
from core.exporter import DualExporter
from core.color_manager import ColorManager, ICC_PROFILES
from core.tiler import ImageTiler

def run_tests():
    print("🚀 [PrintMaster Pro v1.0] 종합 무결성 및 엔진 검증 시작...")
    os.makedirs("./temp", exist_ok=True)
    test_pdf_path = "./temp/test_banner.pdf"

    # 1. 테스트용 PDF 생성 (500cm x 90cm 비율, 벡터 텍스트 및 비트맵 포함)
    print("\n1️⃣ 테스트 PDF 파일 생성 중 (벡터 + 래스터)...")
    doc = fitz.open()
    # 500pt x 90pt (1:1 축소 비율)
    page = doc.new_page(width=500, height=90)
    
    # 벡터 텍스트 삽입
    page.insert_text(fitz.Point(30, 50), "PrintMaster Pro Test Banner", fontsize=24, color=(0.1, 0.2, 0.8))
    page.draw_rect(fitz.Rect(10, 10, 490, 80), color=(0.8, 0.1, 0.1), width=2)
    
    # 비트맵 이미지 임베딩
    sample_pil = Image.new("RGB", (100, 50), (30, 180, 100))
    sample_img_bytes = fitz.open()
    import io
    buf = io.BytesIO()
    sample_pil.save(buf, format="PNG")
    page.insert_image(fitz.Rect(350, 20, 450, 70), stream=buf.getvalue())
    
    doc.save(test_pdf_path)
    doc.close()
    print(f"  ✅ 테스트 PDF 생성 완료: {test_pdf_path}")

    # 2. PDF 분석기 검증
    print("\n2️⃣ PDFInspector 구조 분석 검증...")
    info = PDFInspector.inspect_pdf(test_pdf_path)
    print(f"  - 크기: {info['width_cm']}cm x {info['height_cm']}cm")
    print(f"  - 벡터 요소 존재: {info['has_vector']}")
    print(f"  - 래스터 이미지 수: {info['image_count']}")
    assert info['has_vector'] == True, "벡터 감지 실패!"
    assert info['image_count'] >= 1, "이미지 감지 실패!"
    print("  ✅ PDFInspector 검증 통과!")

    # 3. 색상 관리자 및 ICC 프로파일 검증
    print("\n3️⃣ ColorManager & ICC 프로파일 검증...")
    ColorManager.ensure_profiles_exist()
    test_img = Image.new("RGB", (300, 200), (255, 128, 0))
    cmyk_img = ColorManager.convert_rgb_to_cmyk(test_img, "Japan Color 2001 Coated (국내 인쇄/실사 표준)")
    print(f"  - 변환 후 모드: {cmyk_img.mode}")
    assert cmyk_img.mode == "CMYK", "CMYK 변환 모드 불일치!"
    enhanced_cmyk = ColorManager.apply_black_text_enhancement(cmyk_img)
    assert enhanced_cmyk.mode == "CMYK", "블랙 보정 후 모드 불일치!"
    print("  ✅ ColorManager CMYK 매트릭스 검증 통과!")

    # 4. 자동 분할(Tiling) 및 겹침 여백(Overlap) 검증
    print("\n4️⃣ ImageTiler 분할 엔진 및 ZIP 패키징 검증...")
    tiles_calc = ImageTiler.calculate_tiles(
        total_width_cm=500.0,
        total_height_cm=90.0,
        max_roll_width_cm=150.0,
        overlap_cm=3.0,
        split_direction="가로 분할"
    )
    print(f"  - 계산된 분할 타일 수: {tiles_calc['num_tiles']} 장 (기대값: 4장)")
    assert tiles_calc['num_tiles'] == 4, "분할 수 계산 오류!"
    
    # 슬라이싱 테스트
    banner_sim = Image.new("CMYK", (2000, 360), (0, 100, 100, 0))
    sliced = ImageTiler.slice_image(
        pil_image=banner_sim,
        total_width_cm=500.0,
        total_height_cm=90.0,
        dpi=150,
        max_roll_width_cm=150.0,
        overlap_cm=3.0,
        split_direction="가로 분할"
    )
    print(f"  - 생성된 타일 객체 수: {len(sliced)} 개")
    assert len(sliced) == 4, "타일 슬라이스 개수 오류!"

    zip_bytes = ImageTiler.create_zip_archive(sliced, "test_banner", dpi=150, color_mode="CMYK")
    print(f"  - 생성된 ZIP 아카이브 용량: {len(zip_bytes):,} bytes")
    assert len(zip_bytes) > 1000, "ZIP 파일 생성 실패!"
    print("  ✅ ImageTiler 및 ZIP 패키징 검증 통과!")

    # 5. DualExporter 전체 파이프라인 검증
    print("\n5️⃣ DualExporter 초고해상도 렌더링 & 인쇄 PDF 출력 검증...")
    out_jpg = "./temp/test_out_cmyk.jpg"
    out_pdf = "./temp/test_out_print.pdf"
    
    # 200cm x 50cm, 100 DPI 테스트
    res = DualExporter.export_ultra_high_res_image(
        pdf_path=test_pdf_path,
        output_image_path=out_jpg,
        target_width_cm=200.0,
        target_height_cm=50.0,
        target_dpi=100,
        color_mode="CMYK"
    )
    print(f"  - 렌더링 해상도: {res['width_px']} x {res['height_px']} px")
    print(f"  - 파일 크기: {res['file_size_mb']} MB")
    assert os.path.exists(out_jpg), "출력 JPG 미생성!"
    
    DualExporter.export_vector_print_pdf(
        pdf_path=test_pdf_path,
        output_pdf_path=out_pdf,
        is_pure_raster=False,
        target_width_cm=200.0,
        target_height_cm=50.0,
        target_dpi=100,
        color_mode="CMYK"
    )
    assert os.path.exists(out_pdf), "출력 PDF 미생성!"
    print("  ✅ DualExporter 렌더링 & PDF 빌드 검증 통과!")

    print("\n🎉 [ALL TESTS PASSED] PrintMaster Pro v1.0 엔진의 모든 기능이 정상 작동함을 확인했습니다!")

if __name__ == "__main__":
    run_tests()
