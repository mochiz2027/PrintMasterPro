import os
import io
import math
import fitz
from PIL import Image
from core.upscaler import SmartUpscaler
from core.color_manager import ColorManager
from core.tiler import ImageTiler

class DualExporter:
    @staticmethod
    def calculate_render_matrix(
        page: fitz.Page, 
        target_width_cm: float = None, 
        target_height_cm: float = None, 
        target_dpi: int = 150,
        doc: fitz.Document = None,
        super_sample_factor: float = 1.0
    ) -> tuple:
        rect = page.rect
        orig_w_pt = max(rect.width, 1.0)
        orig_h_pt = max(rect.height, 1.0)
        
        # 1. 대상 규격 기반 픽셀 수 계산
        if target_width_cm and target_height_cm and target_width_cm > 0 and target_height_cm > 0:
            target_w_inch = target_width_cm / 2.54
            target_h_inch = target_height_cm / 2.54
            required_w_px = max(1, int(target_w_inch * target_dpi))
            required_h_px = max(1, int(target_h_inch * target_dpi))
        else:
            required_w_px = max(1, int(orig_w_pt * (target_dpi / 72.0)))
            required_h_px = max(1, int(orig_h_pt * (target_dpi / 72.0)))

        # 2. 🔥 [핵심] 원본 고화질 임베디드 이미지(4K 등)보다 해상도가 낮아지는 다운스케일링 원천 차단!
        if doc is not None:
            max_embed_w = 0
            max_embed_h = 0
            for img in page.get_images():
                try:
                    base = doc.extract_image(img[0])
                    max_embed_w = max(max_embed_w, base.get("width", 0))
                    max_embed_h = max(max_embed_h, base.get("height", 0))
                except Exception:
                    pass
            
            # 원본에 고화질 이미지가 들어있다면 목표 크기가 원본보다 작아지지 않도록 1.25x 이상 업스케일 보장
            if max_embed_w > 0 and max_embed_h > 0:
                if required_w_px < max_embed_w or required_h_px < max_embed_h:
                    scale_mult = max(max_embed_w / required_w_px, max_embed_h / required_h_px) * 1.25
                    required_w_px = int(required_w_px * scale_mult)
                    required_h_px = int(required_h_px * scale_mult)

        # 3. 🚀 벡터급 초고해상도 슈퍼샘플링 배율 적용 (글자 칼선 극대화)
        if super_sample_factor > 1.0:
            required_w_px = int(required_w_px * super_sample_factor)
            required_h_px = int(required_h_px * super_sample_factor)

        zoom_x = required_w_px / orig_w_pt
        zoom_y = required_h_px / orig_h_pt
        return zoom_x, zoom_y, required_w_px, required_h_px

    @staticmethod
    def render_base_image(
        pdf_path: str,
        target_width_cm: float = None,
        target_height_cm: float = None,
        target_dpi: int = 150,
        color_mode: str = "RGB",
        icc_profile_key: str = "Japan Color 2001 Coated (국내 인쇄/실사 표준)",
        sharpen_strength: str = "ultra",
        super_sample_factor: float = 1.0
    ) -> tuple[Image.Image, Image.Image]:
        """
        PDF를 초고해상도로 렌더링하고 글자 외곽선 칼선 복원 적용
        반환: (final_print_img, rgb_screen_img)
        """
        doc = fitz.open(pdf_path)
        try:
            page = doc[0]
            rect = page.rect
            zoom_x, zoom_y, required_w_px, required_h_px = DualExporter.calculate_render_matrix(
                page, target_width_cm, target_height_cm, target_dpi, doc=doc, super_sample_factor=super_sample_factor
            )
            
            mat = fitz.Matrix(zoom_x, zoom_y)
            
            # 단일 픽스맵 한계(12,000px 이상) 초과 시 스트립 분할 렌더링
            max_strip_px = 8000
            if required_w_px > 12000 or required_h_px > 12000:
                raw_img = Image.new("RGB", (required_w_px, required_h_px), (255, 255, 255))
                chunk_w_pt = max_strip_px / zoom_x
                
                x_pt = 0.0
                x_px = 0
                while x_pt < rect.width:
                    next_x_pt = min(rect.width, x_pt + chunk_w_pt)
                    clip_rect = fitz.Rect(x_pt, 0, next_x_pt, rect.height)
                    pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
                    strip_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    raw_img.paste(strip_img, (x_px, 0))
                    x_px += pix.width
                    x_pt = next_x_pt
            else:
                try:
                    pix = page.get_pixmap(matrix=mat, alpha=False)
                    raw_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                except Exception:
                    raw_img = Image.new("RGB", (required_w_px, required_h_px), (255, 255, 255))
                    chunk_w_pt = 6000 / zoom_x
                    x_pt = 0.0
                    x_px = 0
                    while x_pt < rect.width:
                        next_x_pt = min(rect.width, x_pt + chunk_w_pt)
                        clip_rect = fitz.Rect(x_pt, 0, next_x_pt, rect.height)
                        pix = page.get_pixmap(matrix=mat, clip=clip_rect, alpha=False)
                        strip_img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                        raw_img.paste(strip_img, (x_px, 0))
                        x_px += pix.width
                        x_pt = next_x_pt
        finally:
            doc.close()
        
        # 🔥 글자 외곽선 및 텍스트 엣지 칼날 복원 (AI Shock Filter 적용)
        enhanced_rgb = SmartUpscaler.enhance_and_upscale_image(
            raw_img, scale_factor=1.0, sharpen_strength=sharpen_strength
        )
        
        # 색상 변환
        if color_mode == "CMYK":
            cmyk_img = ColorManager.convert_rgb_to_cmyk(enhanced_rgb, profile_key=icc_profile_key)
            final_print_img = ColorManager.apply_black_text_enhancement(cmyk_img)
        else:
            final_print_img = enhanced_rgb

        return final_print_img, enhanced_rgb

    @staticmethod
    def export_ultra_high_res_image(
        pdf_path: str, 
        output_image_path: str, 
        target_width_cm: float = None, 
        target_height_cm: float = None, 
        target_dpi: int = 150,
        color_mode: str = "RGB",
        icc_profile_key: str = "Japan Color 2001 Coated (국내 인쇄/실사 표준)",
        sharpen_strength: str = "ultra",
        super_sample_factor: float = 1.0
    ) -> dict:
        final_img, enhanced_rgb = DualExporter.render_base_image(
            pdf_path, target_width_cm, target_height_cm, target_dpi, color_mode, icc_profile_key, sharpen_strength, super_sample_factor
        )
        
        # 1. 기본 출력 JPG (Quality 100, Subsampling 0 으로 압축 손실 최소화)
        final_img.save(
            output_image_path, 
            format="JPEG", 
            quality=100, 
            subsampling=0, 
            dpi=(target_dpi, target_dpi)
        )
        
        # 2. 모니터 검토 및 디지털 인쇄용 초고화질 sRGB JPG (윈도우 사진 뷰어에서 100% 쨍하고 선명하게 보임)
        screen_jpg_path = output_image_path.replace(".jpg", "_초고화질_sRGB.jpg")
        enhanced_rgb.save(
            screen_jpg_path,
            format="JPEG",
            quality=100,
            subsampling=0,
            dpi=(target_dpi, target_dpi)
        )

        # 3. 💎 100% 무손실 PNG (압축 손실 0%, 벡터급 칼날 선명도)
        lossless_png_path = output_image_path.replace(".jpg", "_무손실_PNG.png")
        enhanced_rgb.save(
            lossless_png_path,
            format="PNG",
            compress_level=3
        )
        
        file_size_mb = os.path.getsize(output_image_path) / (1024 * 1024)
        
        return {
            "width_px": final_img.width,
            "height_px": final_img.height,
            "dpi": target_dpi,
            "color_mode": color_mode,
            "file_size_mb": round(file_size_mb, 2),
            "output_path": output_image_path,
            "screen_path": screen_jpg_path,
            "png_path": lossless_png_path,
            "image_obj": final_img,
            "rgb_obj": enhanced_rgb
        }

    @staticmethod
    def export_tiled_packages(
        base_image: Image.Image,
        base_filename: str,
        total_width_cm: float,
        total_height_cm: float,
        dpi: int,
        max_roll_width_cm: float,
        overlap_cm: float,
        split_direction: str,
        color_mode: str = "RGB"
    ) -> dict:
        """분할 타일링을 수행하고 ZIP 파일 바이너리 반환"""
        tiles = ImageTiler.slice_image(
            pil_image=base_image,
            total_width_cm=total_width_cm,
            total_height_cm=total_height_cm,
            dpi=dpi,
            max_roll_width_cm=max_roll_width_cm,
            overlap_cm=overlap_cm,
            split_direction=split_direction
        )
        
        zip_bytes = ImageTiler.create_zip_archive(
            tiles=tiles,
            base_filename=base_filename,
            dpi=dpi,
            color_mode=color_mode
        )
        
        return {
            "tiles": tiles,
            "total_tiles": len(tiles),
            "zip_bytes": zip_bytes,
            "zip_filename": f"{base_filename}_분할출력_{len(tiles)}장_패키지.zip"
        }

    @staticmethod
    def export_vector_print_pdf(
        pdf_path: str, 
        output_pdf_path: str, 
        is_pure_raster: bool = False, 
        target_width_cm: float = None, 
        target_height_cm: float = None, 
        target_dpi: int = 150,
        color_mode: str = "RGB",
        icc_profile_key: str = "Japan Color 2001 Coated (국내 인쇄/실사 표준)",
        sharpen_strength: str = "ultra",
        super_sample_factor: float = 1.0
    ) -> str:
        """
        초고해상도 무손실 Flate 압축 인쇄용 PDF 빌드 (글자 번짐 및 DCT 아티팩트 0%)
        """
        final_img, enhanced_rgb = DualExporter.render_base_image(
            pdf_path, target_width_cm, target_height_cm, target_dpi, color_mode, icc_profile_key, sharpen_strength, super_sample_factor
        )
        
        # 1. 목표 pt 크기 계산 (1 inch = 72 pt, 1 inch = 2.54 cm)
        if target_width_cm and target_height_cm and target_width_cm > 0 and target_height_cm > 0:
            target_w_pt = (target_width_cm / 2.54) * 72.0
            target_h_pt = (target_height_cm / 2.54) * 72.0
        else:
            target_w_pt = (final_img.width / target_dpi) * 72.0
            target_h_pt = (final_img.height / target_dpi) * 72.0

        # 2. PyMuPDF를 사용하여 무손실(Deflate) 고품질 PDF 직접 생성
        out_doc = fitz.open()
        out_page = out_doc.new_page(width=target_w_pt, height=target_h_pt)
        
        # 무손실 PNG 버퍼 생성
        buf = io.BytesIO()
        enhanced_rgb.save(buf, format="PNG", compress_level=3)
        img_bytes = buf.getvalue()
        
        # 페이지 전체 영역에 무손실 래스터 배치
        out_page.insert_image(out_page.rect, stream=img_bytes)
        
        # 3. 🔥 [핵심] PDF 뷰어(Acrobat, Edge 등)의 축소/확대 블러 보간을 원천 차단하고 칼날 엣지 유지
        for img_info in out_page.get_images():
            try:
                out_doc.xref_set_key(img_info[0], "Interpolate", "false")
            except Exception:
                pass
        
        out_doc.save(output_pdf_path, deflate=True, garbage=3)
        out_doc.close()
        
        return output_pdf_path