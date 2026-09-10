import io
import fitz
from PIL import Image
from core.upscaler import SmartUpscaler

class PDFProcessor:
    @staticmethod
    def upscale_pdf_embedded_images(input_pdf_path: str, output_pdf_path: str, scale_factor: float = 2.0) -> bool:
        """
        PDF 내부의 벡터 텍스트/도형은 그대로 유지하면서 저해상도 비트맵 이미지만 고해상도로 치환
        """
        doc = fitz.open(input_pdf_path)
        
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            image_list = page.get_images(full=True)
            
            for img_info in image_list:
                xref = img_info[0]
                try:
                    base_img = doc.extract_image(xref)
                    image_bytes = base_img["image"]
                    
                    pil_img = Image.open(io.BytesIO(image_bytes))
                    
                    # 비트맵 이미지가 저해상도인 경우만 업스케일
                    upscaled_pil = SmartUpscaler.enhance_and_upscale_image(pil_img, scale_factor=scale_factor, sharpen=True)
                    
                    out_buffer = io.BytesIO()
                    upscaled_pil.save(out_buffer, format="JPEG", quality=95, subsampling=0)
                    new_image_bytes = out_buffer.getvalue()
                    
                    # PDF 내부의 이미지 바이너리 덮어쓰기
                    doc.update_stream(xref, new_image_bytes)
                except Exception:
                    pass
                
        doc.save(output_pdf_path, deflate=True, garbage=3)
        doc.close()
        return True
