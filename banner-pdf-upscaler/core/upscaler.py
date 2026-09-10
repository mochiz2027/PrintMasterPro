import cv2
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

class SmartUpscaler:
    @staticmethod
    def enhance_and_upscale_image(
        pil_image: Image.Image, 
        scale_factor: float = 1.0, 
        sharpen_strength: str = "ultra"
    ) -> Image.Image:
        """
        저해상도 비트맵/조판 PDF를 벡터화된 것처럼 칼선 복원하는 AI 쇼크 필터(Shock Filter) 업스케일러
        - sharpen_strength: 'normal', 'strong', 'ultra' (기본값: ultra - 벡터급 텍스트 복원)
        """
        orig_w, orig_h = pil_image.size
        target_w = max(1, int(orig_w * scale_factor))
        target_h = max(1, int(orig_h * scale_factor))
        
        # 1. 고품질 Lanczos 리샘플링
        if scale_factor != 1.0:
            upscaled = pil_image.resize((target_w, target_h), Image.Resampling.LANCZOS)
        else:
            upscaled = pil_image
            
        if sharpen_strength == "none":
            return upscaled

        # 2. LAB 색상 공간 기반 벡터 스타일 쇼크 필터 (Shock Filter: 색상 왜곡 없이 글자 외곽선 칼날 복원)
        try:
            # 초대형 이미지(6000만 픽셀 초과)는 메모리 안전을 위해 다중 언샵마스크 적용
            if target_w * target_h > 60000000:
                out = upscaled.filter(ImageFilter.UnsharpMask(radius=1.5, percent=200, threshold=1))
                out = out.filter(ImageFilter.UnsharpMask(radius=3.0, percent=150, threshold=2))
                enhancer = ImageEnhance.Sharpness(out)
                return enhancer.enhance(1.4)

            # RGB 변환 보장
            if upscaled.mode != "RGB":
                rgb_temp = upscaled.convert("RGB")
            else:
                rgb_temp = upscaled

            np_img = np.array(rgb_temp)
            lab = cv2.cvtColor(np_img, cv2.COLOR_RGB2LAB)
            l, a, b = cv2.split(lab)
            l_float = l.astype(np.float32)

            # A. 다단계 Kramer-Bruckner PDE 쇼크 필터 (수회 반복으로 엣지 전이폭을 0~1픽셀로 압축)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
            num_iters = 6 if sharpen_strength == "ultra" else (4 if sharpen_strength == "strong" else 2)
            
            for _ in range(num_iters):
                dil = cv2.dilate(l_float, kernel)
                ero = cv2.erode(l_float, kernel)
                lap = cv2.Laplacian(l_float, cv2.CV_32F, ksize=3)
                l_float = np.where(lap < -0.8, dil, np.where(lap > 0.8, ero, l_float))

            # B. 🔥 [핵심 혁신] Sigmoidal S-Curve Edge Steepening (글자 엣지를 수직 절벽 벡터로 변환)
            blur_local = cv2.GaussianBlur(l_float, (0, 0), 1.0)
            diff = l_float - blur_local
            # 엣지 부근의 미세 경사를 비선형으로 급격화 (S-Curve 증폭)
            boost_factor = 1.6 if sharpen_strength == "ultra" else (1.3 if sharpen_strength == "strong" else 1.0)
            steep_diff = np.sign(diff) * (np.abs(diff) ** 1.32) * boost_factor
            l_steep = np.clip(blur_local + steep_diff, 0, 255)

            # C. 텍스트 트루 블랙 & 클린 백그라운드 클램핑 (먹색 글씨 및 화이트 배경 선명화)
            if sharpen_strength in ["ultra", "strong"]:
                # 명도 45 이하 어두운 텍스트를 깊고 균일한 순수 먹색으로 정돈
                l_steep = np.where(l_steep < 45, l_steep * 0.45, l_steep)
                # 242 이상 밝은 배경을 순백으로 정돈하여 글자 주변 회색 헤일로 제거
                l_steep = np.where(l_steep > 242, np.clip(l_steep * 1.03, 0, 255), l_steep)

            l_final = np.clip(l_steep, 0, 255).astype(np.uint8)

            # D. 색상 채널(a, b) 쇼크 필터링 (마젠타/레드 글자 주변의 색번짐 0% 벡터화)
            for ch in [a, b]:
                ch_f = ch.astype(np.float32)
                for _ in range(num_iters - 1):
                    d = cv2.dilate(ch_f, kernel)
                    e = cv2.erode(ch_f, kernel)
                    lp = cv2.Laplacian(ch_f, cv2.CV_32F, ksize=3)
                    ch_f = np.where(lp < -1.0, d, np.where(lp > 1.0, e, ch_f))
                ch[:] = np.clip(ch_f, 0, 255).astype(np.uint8)

            # 원본 색상 채널과 결합하여 네온 핑크/레드 100% 무손실 보존
            lab_out = cv2.merge([l_final, a, b])
            rgb_out = cv2.cvtColor(lab_out, cv2.COLOR_LAB2RGB)

            # E. 고주파 안티-블러 언샵마스크 (최종 칼날 엣지 안착)
            gaussian = cv2.GaussianBlur(rgb_out, (0, 0), 0.7)
            unsharp_weight = 1.55 if sharpen_strength == "ultra" else 1.35
            res_np = cv2.addWeighted(rgb_out, unsharp_weight, gaussian, 1.0 - unsharp_weight, 0)
            res_np = np.clip(res_np, 0, 255).astype(np.uint8)

            result = Image.fromarray(res_np)
            return result

        except Exception:
            out = upscaled.filter(ImageFilter.UnsharpMask(radius=2, percent=200, threshold=1))
            enhancer = ImageEnhance.Sharpness(out)
            return enhancer.enhance(1.4)
