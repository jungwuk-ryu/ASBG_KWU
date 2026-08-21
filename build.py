#!/usr/bin/env python3
"""Cloudflare Pages 배포용 dist/ 를 만든다.

Claude Design 내보내기 결과는 그대로 배포할 수 없다. 이 스크립트가:
  - 진입점을 index.html 로 이름 변경
  - uploads/, scraps/, .thumbnail 등 비공개 부산물 제외
  - <title>, lang, description, og 태그, favicon 주입
  - canonical, robots, JSON-LD 구조화 데이터 주입
  - robots.txt, sitemap.xml, llms.txt 생성
  - React UMD 를 unpkg CDN 대신 vendor/ 로컬 파일에서 로드하도록 전환
  - Cloudflare Pages 용 _headers 생성

    python3 build.py        # dist/ 생성
"""

import json
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
EXCLUDE_PATH_PREFIXES = {("assets", "photos")}

TITLE = "ASBG KWU 5기 모집 | AWS Student Builder Group 광운대학교"
DESCRIPTION = (
    "광운대학교 AWS Student Builder Group(ASBG KWU) 5기 멤버를 모집합니다. "
    "서류 접수는 8월 21일부터 9월 6일까지이며, AWS와 클라우드를 함께 배우고 "
    "직접 만드는 학생 커뮤니티입니다."
)
PROJECT = "asbg-kwu"
SITE_URL = "https://asbg-kwu.cloud"
CANONICAL_URL = f"{SITE_URL}/"
PHOTO_ASSET_URL = "https://assets.asbg-kwu.cloud/photos"
OG_IMAGE_URL = f"{PHOTO_ASSET_URL}/og-cover.jpg"
SITEMAP_LASTMOD = "2026-08-13"

# support.js 가 참조하는 CDN URL → 로컬 경로 매핑
CDN_MAP = {
    "https://unpkg.com/react@18.3.1/umd/react.production.min.js": "vendor/react.production.min.js",
    "https://unpkg.com/react-dom@18.3.1/umd/react-dom.production.min.js": "vendor/react-dom.production.min.js",
}

STRUCTURED_DATA = {
    "@context": "https://schema.org",
    "@graph": [
        {
            "@type": "Organization",
            "@id": f"{CANONICAL_URL}#organization",
            "name": "AWS Student Builder Group — Kwangwoon University",
            "alternateName": "ASBG KWU",
            "url": CANONICAL_URL,
            "logo": f"{SITE_URL}/assets/program-icon-mint.svg",
            "image": OG_IMAGE_URL,
            "description": DESCRIPTION,
            "foundingDate": "2024",
            "sameAs": ["https://www.instagram.com/aws.sbg.kwu/"],
            "address": {
                "@type": "PostalAddress",
                "addressLocality": "Seoul",
                "addressCountry": "KR",
            },
        },
        {
            "@type": "WebSite",
            "@id": f"{CANONICAL_URL}#website",
            "url": CANONICAL_URL,
            "name": "ASBG KWU",
            "alternateName": "AWS Student Builder Group 광운대학교",
            "description": DESCRIPTION,
            "inLanguage": "ko-KR",
            "publisher": {"@id": f"{CANONICAL_URL}#organization"},
        },
    ],
}

HEAD_INJECT = f"""<title>{TITLE}</title>
<meta name="description" content="{DESCRIPTION}">
<meta name="robots" content="index,follow,max-image-preview:large,max-snippet:-1,max-video-preview:-1">
<meta name="theme-color" content="#141D26">
<meta name="application-name" content="ASBG KWU">
<link rel="canonical" href="{CANONICAL_URL}">
<link rel="alternate" hreflang="ko-KR" href="{CANONICAL_URL}">
<link rel="alternate" hreflang="x-default" href="{CANONICAL_URL}">
<link rel="icon" href="assets/program-icon-mint.svg" type="image/svg+xml">
<meta property="og:type" content="website">
<meta property="og:title" content="{TITLE}">
<meta property="og:description" content="{DESCRIPTION}">
<meta property="og:url" content="{CANONICAL_URL}">
<meta property="og:locale" content="ko_KR">
<meta property="og:site_name" content="ASBG KWU">
<meta property="og:image" content="{OG_IMAGE_URL}">
<meta property="og:image:secure_url" content="{OG_IMAGE_URL}">
<meta property="og:image:type" content="image/jpeg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="Introductory Hands-On을 마치고 모인 ASBG KWU 4기 멤버들">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="{TITLE}">
<meta name="twitter:description" content="{DESCRIPTION}">
<meta name="twitter:image" content="{OG_IMAGE_URL}">
<meta name="twitter:image:alt" content="Introductory Hands-On을 마치고 모인 ASBG KWU 4기 멤버들">
<script type="application/ld+json">{json.dumps(STRUCTURED_DATA, ensure_ascii=False, separators=(",", ":"))}</script>
"""

ROBOTS = f"""User-agent: *
Allow: /

Sitemap: {SITE_URL}/sitemap.xml
"""

SITEMAP = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{CANONICAL_URL}</loc>
    <lastmod>{SITEMAP_LASTMOD}</lastmod>
  </url>
</urlset>
"""

LLMS_TXT = f"""# ASBG KWU

> 광운대학교 AWS Student Builder Group 공식 웹사이트입니다. AWS와 클라우드를 함께 배우고 직접 만드는 학생 커뮤니티입니다.

## 공식 링크

- [ASBG KWU]({CANONICAL_URL}): 5기 소개, 모집 일정, 활동 내용, 지난 기수 활동, 자주 묻는 질문
- [5기 지원서](https://tally.so/r/dWGWJr): ASBG KWU 5기 지원 폼
- [Instagram](https://www.instagram.com/aws.sbg.kwu/): 공식 소식과 활동 기록

## 5기 모집 일정

- 서류 접수: 2026-08-21 ~ 2026-09-06
- 서류 결과 안내: 2026-09-07
- 인터뷰: 2026-09-09 ~ 2026-09-11
- 최종 결과 안내: 2026-09-15
- Welcome Party: 2026-09-18
"""

# support.js 는 로드 시점에 __resources 를 읽으므로 반드시 그 앞에 와야 한다.
SUPPORT_TAG = '<script src="./support.js"></script>'
RESOURCES_TAG = (
    "<script>window.__resources={"
    + ",".join(f'"{k}":"{v}"' for k, v in CDN_MAP.items())
    + "};</script>\n"
)

HEADERS = """/assets/photos/*
  Cache-Control: no-store

/assets/*.svg
  Cache-Control: public, max-age=31536000, immutable

/assets/*.ttf
  Cache-Control: public, max-age=31536000, immutable

/vendor/*
  Cache-Control: public, max-age=31536000, immutable

/*
  X-Content-Type-Options: nosniff
  Referrer-Policy: strict-origin-when-cross-origin
"""

REDIRECTS = f"""/assets/photos/* {PHOTO_ASSET_URL}/:splat 302
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
        if (
            rel.parts[0] in EXCLUDE_DIRS
            or rel.parts[:2] in EXCLUDE_PATH_PREFIXES
            or rel.name in EXCLUDE_FILES
        ):
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

    # 4. 검색·기계 판독용 정적 파일
    (DIST / "robots.txt").write_text(ROBOTS, encoding="utf-8")
    (DIST / "sitemap.xml").write_text(SITEMAP, encoding="utf-8")
    (DIST / "llms.txt").write_text(LLMS_TXT, encoding="utf-8")

    # 5. Cloudflare Pages 설정
    (DIST / "_headers").write_text(HEADERS, encoding="utf-8")
    (DIST / "_redirects").write_text(REDIRECTS, encoding="utf-8")

    total = sum(f.stat().st_size for f in DIST.rglob("*") if f.is_file())
    print(f"  진입점 : {entry.name} → index.html")
    print(f"  복사   : {copied}개 + vendor 2개")
    print(f"  크기   : {total / 1024 / 1024:.1f} MB")
    print(f"  출력   : {DIST}")
    print(f"\n  배포:  npx wrangler pages deploy dist --project-name {PROJECT}")


if __name__ == "__main__":
    main()
