"""대형 실사출력용 자동 분할(Tiling) 및 겹침 여백(Overlap) 처리 모듈"""

import os
import io
import math
import zipfile
from PIL import Image

class ImageTiler:
    # 실사출력 롤 원단 표준 폭 프리셋 (cm)
    ROLL_WIDTH_PRESETS = {
        "직접 입력": None,
        "90cm 롤 (일반 현수막 원단)": 90.0,
        "120cm 롤 (소형 실사/유포지)": 120.0,
        "150cm 롤 (중형 배너/텐트천)": 150.0,
        "180cm 롤 (대형 배너/후렉스)": 180.0,
        "240cm 롤 (광폭 후렉스)": 240.0,
        "320cm 롤 (초광폭 그랜드 프린터)": 320.0,
    }

    @staticmethod
    def calculate_tiles(
        total_width_cm: float,
        total_height_cm: float,
        max_roll_width_cm: float = 150.0,
        overlap_cm: float = 3.0,
        split_direction: str = "가로 분할 (세로선 기준 절단)"
    ) -> dict:
        """
        출력 크기와 롤 폭에 따른 최적 타일 수 및 좌표 계산
        """
        # 가로 분할: 좌우로 긴 현수막을 세로로 쪼갬 (대부분의 현수막/간판)
        if "가로 분할" in split_direction:
            primary_len = total_width_cm
        else:
            primary_len = total_height_cm

        num_tiles = math.ceil(primary_len / max_roll_width_cm)
        if num_tiles < 1:
            num_tiles = 1

        base_tile_len = primary_len / num_tiles

        return {
            "num_tiles": num_tiles,
            "base_tile_len_cm": round(base_tile_len, 2),
            "overlap_cm": overlap_cm,
            "split_direction": split_direction
        }

    @staticmethod
    def slice_image(
        pil_image: Image.Image,
        total_width_cm: float,
        total_height_cm: float,
        dpi: int,
        max_roll_width_cm: float = 150.0,
        overlap_cm: float = 3.0,
        split_direction: str = "가로 분할 (세로선 기준 절단)"
    ) -> list:
        """
        Pillow 이미지를 계산된 겹침 여백을 포함하여 타일 단위로 슬라이스
        """
        img_w, img_h = pil_image.size
        px_per_cm = dpi / 2.54

        overlap_px = int(overlap_cm * px_per_cm)
        tiles_info = ImageTiler.calculate_tiles(
            total_width_cm, total_height_cm, max_roll_width_cm, overlap_cm, split_direction
        )
        num_tiles = tiles_info["num_tiles"]

        sliced_tiles = []

        if "가로 분할" in split_direction:
            # X축 기준 균등 분할
            base_px = img_w / num_tiles
            for i in range(num_tiles):
                x_start = int(i * base_px)
                x_end = int((i + 1) * base_px)

                # 첫 번째 타일이 아니면 좌측 겹침 여백 추가
                left = max(0, x_start - (overlap_px if i > 0 else 0))
                # 마지막 타일이 아니면 우측 겹침 여백 추가
                right = min(img_w, x_end + (overlap_px if i < num_tiles - 1 else 0))

                tile_crop = pil_image.crop((left, 0, right, img_h))
                
                sliced_tiles.append({
                    "tile_index": i + 1,
                    "total_tiles": num_tiles,
                    "image": tile_crop,
                    "width_px": tile_crop.width,
                    "height_px": tile_crop.height,
                    "real_width_cm": round(tile_crop.width / px_per_cm, 1),
                    "real_height_cm": round(tile_crop.height / px_per_cm, 1),
                    "label": f"Tile_{i+1:02d}_of_{num_tiles:02d}"
                })
        else:
            # Y축 기준 균등 분할 (세로로 긴 타워형 간판 등)
            base_px = img_h / num_tiles
            for i in range(num_tiles):
                y_start = int(i * base_px)
                y_end = int((i + 1) * base_px)

                top = max(0, y_start - (overlap_px if i > 0 else 0))
                bottom = min(img_h, y_end + (overlap_px if i < num_tiles - 1 else 0))

                tile_crop = pil_image.crop((0, top, img_w, bottom))
                
                sliced_tiles.append({
                    "tile_index": i + 1,
                    "total_tiles": num_tiles,
                    "image": tile_crop,
                    "width_px": tile_crop.width,
                    "height_px": tile_crop.height,
                    "real_width_cm": round(tile_crop.width / px_per_cm, 1),
                    "real_height_cm": round(tile_crop.height / px_per_cm, 1),
                    "label": f"Tile_{i+1:02d}_of_{num_tiles:02d}"
                })

        return sliced_tiles

    @staticmethod
    def create_zip_archive(tiles: list, base_filename: str, dpi: int, color_mode: str = "CMYK") -> bytes:
        """
        분할된 모든 타일 이미지를 단일 ZIP 파일로 패키징
        """
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            for tile in tiles:
                img = tile["image"]
                img_buffer = io.BytesIO()
                
                # CMYK / RGB 무손실 JPEG 저장
                img.save(img_buffer, format="JPEG", quality=98, subsampling=0, dpi=(dpi, dpi))
                
                file_name = f"{base_filename}_{tile['label']}_{color_mode}.jpg"
                zip_file.writestr(file_name, img_buffer.getvalue())

        return zip_buffer.getvalue()