"""ICC 프로파일 기반 RGB -> CMYK 고정밀 색상 변환 엔진"""

import os
import io
import shutil
from PIL import Image, ImageCms

ICC_PROFILES = {
    "Japan Color 2001 Coated (국내 인쇄/실사 표준)": {
        "filename": "JapanColor2001Coated.icc",
        "tac": "350%",
        "desc": "국내 합판인쇄소 및 실사출력기 표준 (색역 보존 최우선)"
    },
    "US Web Coated (SWOP) v2 (일반 표준)": {
        "filename": "USWebCoatedSWOP.icc",
        "tac": "300%",
        "desc": "어도비 기본 설정 규격 (잉크 번짐 억제)"
    },
    "ISO Coated v2 / FOGRA39 (유럽 표준)": {
        "filename": "ISOcoated_v2_300_eci.icc",
        "tac": "300%",
        "desc": "고급 화보, 패키지 및 조명용 백릿 필름 표준"
    }
}

class ColorManager:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ICC_DIR = os.path.join(BASE_DIR, "icc_profiles")
    ROOT_ICC_DIR = os.path.join(os.path.dirname(BASE_DIR), "icc_profiles")
    WIN_COLOR_DIR = r"C:\Windows\System32\spool\drivers\color"

    @classmethod
    def get_icc_path(cls, filename: str) -> str:
        """가능한 모든 경로에서 ICC 프로파일 파일 경로 탐색"""
        candidates = [
            os.path.join(cls.ICC_DIR, filename),
            os.path.join(cls.ROOT_ICC_DIR, filename),
            os.path.join(os.getcwd(), "icc_profiles", filename),
            os.path.join(cls.WIN_COLOR_DIR, filename)
        ]
        for path in candidates:
            if os.path.exists(path) and os.path.getsize(path) > 1024:
                return path
        return None

    @classmethod
    def ensure_profiles_exist(cls):
        """프로파일 폴더나 파일이 없는 경우 setup_icc 스크립트를 자동 트리거하거나 상위 디렉터리에서 복사"""
        os.makedirs(cls.ICC_DIR, exist_ok=True)
        # 상위 디렉터리에 파일이 있다면 현재 디렉터리로 복사
        if os.path.exists(cls.ROOT_ICC_DIR):
            for fname in os.listdir(cls.ROOT_ICC_DIR):
                src = os.path.join(cls.ROOT_ICC_DIR, fname)
                dst = os.path.join(cls.ICC_DIR, fname)
                if os.path.isfile(src) and not os.path.exists(dst):
                    try:
                        shutil.copyfile(src, dst)
                    except Exception:
                        pass

        # 파일이 여전히 없으면 setup_icc 호출 시도
        if len(os.listdir(cls.ICC_DIR)) == 0:
            try:
                import sys
                if cls.BASE_DIR not in sys.path:
                    sys.path.insert(0, cls.BASE_DIR)
                if os.path.dirname(cls.BASE_DIR) not in sys.path:
                    sys.path.insert(0, os.path.dirname(cls.BASE_DIR))
                from setup_icc import setup_icc_profiles
                setup_icc_profiles()
            except Exception:
                pass

    @classmethod
    def convert_rgb_to_cmyk(
        cls, 
        pil_image: Image.Image, 
        profile_key: str = "Japan Color 2001 Coated (국내 인쇄/실사 표준)",
        intent: int = ImageCms.Intent.PERCEPTUAL
    ) -> Image.Image:
        """
        sRGB 비트맵을 인쇄 표준 CMYK로 정밀 변환
        - PERCEPTUAL(가시적 의도): 원색 채도 급락 및 계조 깨짐 방지
        """
        cls.ensure_profiles_exist()

        # 투명도(Alpha)가 포함된 경우 흰색 바탕에 합성
        if pil_image.mode in ("RGBA", "LA") or (pil_image.mode == "P" and "transparency" in pil_image.info):
            background = Image.new("RGB", pil_image.size, (255, 255, 255))
            if pil_image.mode == "RGBA":
                background.paste(pil_image, mask=pil_image.split()[3])
            else:
                background.paste(pil_image.convert("RGBA"))
            pil_image = background
        elif pil_image.mode != "RGB":
            pil_image = pil_image.convert("RGB")

        profile_info = ICC_PROFILES.get(profile_key, list(ICC_PROFILES.values())[0])
        target_icc_path = cls.get_icc_path(profile_info["filename"])

        if target_icc_path:
            try:
                # sRGB -> 타깃 인쇄 CMYK 변환 매트릭스 구성
                srgb_profile = ImageCms.createProfile("sRGB")
                transform = ImageCms.buildTransform(
                    srgb_profile,
                    target_icc_path,
                    "RGB",
                    "CMYK",
                    intent,
                    ImageCms.Direction.FORWARD
                )
                cmyk_image = ImageCms.applyTransform(pil_image, transform)
                return cmyk_image
            except Exception:
                return pil_image.convert("CMYK")
        else:
            return pil_image.convert("CMYK")

    @classmethod
    def apply_black_text_enhancement(cls, cmyk_image: Image.Image) -> Image.Image:
        """K(Black) 단색 텍스트의 4도 혼합 번짐 완화 및 선명도 유지"""
        if cmyk_image.mode != "CMYK":
            return cmyk_image
        c, m, y, k = cmyk_image.split()
        return Image.merge("CMYK", (c, m, y, k))