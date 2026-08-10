#!/usr/bin/env python3
"""Cloudflare Pages 배포용 dist/ 를 만든다.

Claude Design 내보내기 결과는 그대로 배포할 수 없다. 이 스크립트가:
  - 진입점을 index.html 로 이름 변경
  - uploads/, scraps/, .thumbnail 등 비공개 부산물 제외
  - <title>, lang, description, og 태그, favicon 주입
  - React UMD 를 unpkg CDN 대신 vendor/ 로컬 파일에서 로드하도록 전환
  - Cloudflare Pages 용 _headers 생성

    python3 build.py        # dist/ 생성
"""

import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).parent
SITE_DIR = ROOT / "AWS Student Builder 웹사이트"
VENDOR_DIR = ROOT / "vendor"
DIST = ROOT / "dist"

# 배포에 포함하지 않을 것 — 에디터 부산물과 원본 소재
EXCLUDE_DIRS = {"uploads", "scraps"}
EXCLUDE_FILES = {".thumbnail", ".DS_Store"}

TITLE = "AWS Student Builder Group — 광운대학교"
DESCRIPTION = (
    "광운대학교 AWS Student Builder Group 5기 멤버를 모집합니다. "
    "클라우드·AI·데이터·개발을 함께 배우고 만드는 학생 빌더 커뮤니티입니다."
)
PROJECT = "asbg-kwu"
SITE_URL = "https://asbg-kwu.cloud"

# support.js 가 참조하는 CDN URL → 로컬 경로 매핑
CDN_MAP = {
    "https://unpkg.com/react@18.3.1/umd/react.production.min.js": "vendor/react.production.min.js",
    "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js": "vendor/react-dom.production.min.js",
}

HEAD_INJECT = f"""<title>{TITLE}</title>
<meta name="description" content="{DESCRIPTION}">
<link rel="icon" href="assets/program-icon-mint.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{SITE_URL}">
<meta property="og:locale" content="ko_KR">
<meta name="twitter:card" content="summary_large_image">
"""

# support.js 는 로드 시점에 __resources 를 읽으므로 반드시 그 앞에 와야 한다.
SUPPORT_TAG = '<script src="./support.js"></script>'
RESOURCES_TAG = (
    "<script>window.__resources={"
    + ",".join(f'"{k}":"{v}"' for k, v in CDN_MAP.items())
    + "};</script>\n"
)

HEADERS = """/assets/*
  Cache-Control: public, max-age=31536000, immutable

/vendor/*
  Cache-Control: public, max-age=31536000, immutable

/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
"""


def find_entry():
    candidates = sorted(SITE_DIR.glob("*.dc.html")) or sorted(SITE_DIR.glob("*.html"))
    if not candidates:
        sys.exit(f"[error] {SITE_DIR} 안에 html 파일이 없습니다.")
    return candidates[0]


def main():
    if not SITE_DIR.is_dir():
        sys.exit(f"[error] 사이트 폴더가 없습니다: {SITE_DIR}")
    for name in CDN_MAP.values():
        if not (ROOT / name).is_file():
            sys.exit(f"[error] {name} 이 없습니다. vendor/ 파일을 먼저 받아두세요.")

    entry = find_entry()
    shutil.rmtree(DIST, ignore_errors=True)
    DIST.mkdir()

    # 1. 정적 파일 복사 (제외 목록 제외)
    copied = 0
    for src in SITE_DIR.rglob("*"):
        rel = src.relative_to(SITE_DIR)
        if rel.parts[0] in EXCLUDE_DIRS or rel.name in EXCLUDE_FILES:
            continue
        if src == entry or not src.is_file():
            continue
        dest = DIST / rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied += 1

    # 2. vendor
    shutil.copytree(VENDOR_DIR, DIST / "vendor")

    # 3. index.html — head 주입 + lang
    html = entry.read_text(encoding="utf-8")
    html = html.replace("<html>", '<html lang="ko">', 1)
    if "<title>" in html:
        sys.exit("[error] 이미 <title>이 있습니다. HEAD_INJECT 와 충돌하는지 확인하세요.")
    if SUPPORT_TAG not in html:
        sys.exit(f"[error] support.js 태그를 찾지 못했습니다: {SUPPORT_TAG}")
    html = html.replace(SUPPORT_TAG, RESOURCES_TAG + SUPPORT_TAG, 1)
    html = html.replace("</head>", HEAD_INJECT + "</head>", 1)
    (DIST / "index.html").write_text(html, encoding="utf-8")

    # 4. Cloudflare Pages 설정
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")

    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"  진입점 : {entry.name} → index.html")
    print(f"  복사   : {copied}개 + vendor 2개")
    print(f"  크기   : {total / 1024 / 1024:.1f} MB")
    print(f"  출력   : {DIST}")
    print(f"\n  배포:  npx wrangler pages deploy dist --project-name {PROJECT}")


if __name__ == "__main__":
    main()
