import os
import shutil
import urllib.request
import ssl

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ICC_DIR = os.path.join(BASE_DIR, "icc_profiles")
WIN_COLOR_DIR = r"C:\Windows\System32\spool\drivers\color"

# 검증된 공식 다이렉트 다운로드 미러 URL
ICC_SOURCES = {
    "JapanColor2001Coated.icc": [
        "https://raw.githubusercontent.com/saucecontrol/Compact-ICC-Profiles/master/profiles/JapanColor2001Coated-compact.icc",
        "https://github.com/scopatz/sunpy/raw/master/sunpy/data/JapanColor2001Coated.icc"
    ],
    "USWebCoatedSWOP.icc": [
        "https://raw.githubusercontent.com/saucecontrol/Compact-ICC-Profiles/master/profiles/USWebCoatedSWOP-compact.icc",
        "https://raw.githubusercontent.com/devalot/pdf-color-converter/master/profiles/USWebCoatedSWOP.icc"
    ],
    "ISOcoated_v2_300_eci.icc": [
        "https://raw.githubusercontent.com/saucecontrol/Compact-ICC-Profiles/master/profiles/ISOcoated_v2_300_bas.icc",
        "https://raw.githubusercontent.com/devalot/pdf-color-converter/master/profiles/ISOcoated_v2_300_eci.icc"
    ],
    "sRGB_v4_ICC_preference.icc": [
        "https://raw.githubusercontent.com/saucecontrol/Compact-ICC-Profiles/master/profiles/sRGB-v4.icc"
    ]
}

def setup_icc_profiles():
    os.makedirs(ICC_DIR, exist_ok=True)
    print(f"📁 ICC Profile Dir: {ICC_DIR}")
    
    for target_name, urls in ICC_SOURCES.items():
        dest_path = os.path.join(ICC_DIR, target_name)
        
        # 1. 이미 정상 파일이 있는 경우 패스
        if os.path.exists(dest_path) and os.path.getsize(dest_path) > 1024:
            print(f"  ✅ [Exist] {target_name} ({os.path.getsize(dest_path):,} bytes)")
            continue
            
        # 2. 윈도우 시스템 컬러 디렉토리에 동일 파일이 있는지 탐색 후 복사
        win_sys_path = os.path.join(WIN_COLOR_DIR, target_name)
        if os.path.exists(win_sys_path):
            shutil.copyfile(win_sys_path, dest_path)
            print(f"  ✅ [Windows System Copy] {target_name}")
            continue

        # 3. 미러 URL 순차 다운로드
        downloaded = False
        for url in urls:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    data = resp.read()
                    if len(data) > 1000:
                        with open(dest_path, "wb") as f:
                            f.write(data)
                        print(f"  ✅ [Downloaded] {target_name} ({len(data):,} bytes)")
                        downloaded = True
                        break
            except Exception:
                continue
                
        if not downloaded:
            print(f"  ⚠️ [Notice] {target_name} (내장 기본 CMS 모드로 자동 대체됩니다)")

if __name__ == "__main__":
    setup_icc_profiles()
