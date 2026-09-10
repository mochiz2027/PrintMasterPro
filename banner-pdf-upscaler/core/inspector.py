import fitz  # PyMuPDF

class PDFInspector:
    @staticmethod
    def inspect_pdf(pdf_path: str) -> dict:
        doc = fitz.open(pdf_path)
        total_pages = len(doc)
        
        first_page = doc[0]
        rect = first_page.rect
        width_pt = rect.width
        height_pt = rect.height
        
        # 1 pt = 1/72 inch, 1 inch = 25.4 mm
        width_mm = (width_pt / 72.0) * 25.4
        height_mm = (height_pt / 72.0) * 25.4
        
        # 내부 이미지 및 벡터 요소 감지
        image_list = first_page.get_images(full=True)
        text_instances = first_page.get_text("text").strip()
        drawings = first_page.get_drawings()
        
        has_vector = (len(text_instances) > 0) or (len(drawings) > 0)
        has_raster = len(image_list) > 0
        
        image_details = []
        for img in image_list:
            xref = img[0]
            try:
                base_img = doc.extract_image(xref)
                image_details.append({
                    "xref": xref,
                    "width": base_img.get("width", 0),
                    "height": base_img.get("height", 0),
                    "ext": base_img.get("ext", "jpg"),
                    "colorspace": base_img.get("colorspace", "unknown")
                })
            except Exception:
                pass
            
        doc.close()
        
        return {
            "total_pages": total_pages,
            "width_pt": round(width_pt, 2),
            "height_pt": round(height_pt, 2),
            "width_mm": round(width_mm, 1),
            "height_mm": round(height_mm, 1),
            "width_cm": round(width_mm / 10, 1),
            "height_cm": round(height_mm / 10, 1),
            "has_vector": has_vector,
            "has_raster": has_raster,
            "image_count": len(image_list),
            "images": image_details,
            "is_pure_raster": has_raster and not has_vector
        }
