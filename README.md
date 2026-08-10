# AWS Student Builder Group — 랜딩 페이지

광운대학교 AWS Student Builder Group 홍보/리크루팅 원 페이지 사이트.

## 로컬에서 띄우기

```bash
python3 serve.py          # http://localhost:5173 (브라우저 자동 실행)
python3 serve.py 8080     # 포트 지정
```

`file://` 로 직접 열면 안 됩니다. `.dc.html` 런타임(`support.js`)이 React/Babel을
CDN에서 받아오고 로컬 폰트도 CORS에 걸리기 때문에 **HTTP로 서빙해야** 합니다.
따라서 첫 로드에는 **인터넷 연결이 필요**합니다.

## Claude Design 수정 내용 가져오기

Claude Design 문서에는 자동 동기화 API가 없습니다 (`DesignSync` 도구는
design-system 타입 프로젝트만 다룹니다). 웹에서 수정했다면 내보내기 zip을 받아
`AWS Student Builder 웹사이트/` 폴더를 통째로 교체하면 됩니다.

⚠️ **로컬에서 `.dc.html` 을 직접 고치면 다음 교체 때 사라집니다.** 디자인/구조 변경은
웹에서 하고, 로컬은 확인용으로 쓰는 것이 안전합니다.

## Cloudflare Pages 배포

내보내기 결과를 **그대로 올리면 안 됩니다.** `build.py` 가 배포 가능한 `dist/` 를 만듭니다.

현재 Cloudflare Pages 프로젝트는 **Direct Upload** 방식입니다. `build.py`로 `dist/`를
재생성하고 소스와 함께 커밋한 다음 Wrangler로 직접 배포합니다.

```bash
python3 build.py                    # dist/ 재생성
git add -A && git commit -m "..."   # dist/ 포함해서 커밋
npx wrangler pages deploy dist --project-name asbg-kwu --branch main
```

`wrangler.jsonc`의 `pages_build_output_dir`가 `dist/`를 Pages 빌드 출력 디렉터리로 지정합니다.

`build.py` 가 하는 일:

| 처리 | 이유 |
|---|---|
| `ASBG Landing.dc.html` → `index.html` | Pages 는 `index.html` 을 찾음. 파일명 공백도 제거 |
| `uploads/`, `scraps/`, `.thumbnail` 제외 | AWS PPT 템플릿·원본 이미지가 공개 URL 로 노출되는 것 방지 (21MB → 1MB) |
| `<title>`, `lang="ko"`, description, og 태그, favicon 주입 | 원본에 전혀 없음. 공유 시 미리보기·검색 노출 |
| React UMD 를 `vendor/` 로컬 파일로 전환 | unpkg 장애 시 사이트가 빈 화면이 되는 것 방지 |
| `_headers` 생성 | `assets/`·`vendor/` 는 1년 캐시, 보안 헤더 |

React 는 `support.js` 의 `window.__resources` 훅으로 갈아끼웁니다. **`__resources` 선언이
`support.js` 태그보다 앞에 와야** 하며, `build.py` 가 그 순서를 보장합니다.

Babel 은 로드되지 않습니다 (JSX `x-import` 가 있을 때만 받아옴).

dist 미리보기:

```bash
cd dist && python3 -m http.server 5174
```

### 배포 전 확인

- 운영 주소는 `https://asbg-kwu.cloud`이며, Pages 기본 주소는 `https://asbg-kwu.pages.dev`입니다
- `build.py` 의 `SITE_URL`은 운영 주소와 동일하게 유지해야 합니다 — 공유 시 사용하는 `og:url`에 반영됩니다
- 지원 폼 URL: `https://tally.so/r/dWGWJr`
- 활동 사진 (현재 placeholder)
- Pretendard·Archivo·IBM Plex Mono 는 여전히 외부 CDN 입니다. 폰트라 실패해도
  fallback 으로 동작하지만, 완전히 자립시키려면 이것도 vendor 로 내려야 합니다

## 구성

```
serve.py                          로컬 개발 서버 (의존성 없음)
build.py                          Cloudflare Pages 배포용 dist/ 빌드
vendor/                           React UMD (CDN 대체)
DESIGN_BRIEF.md                   디자인 브리프 (구조/모션 스펙)
AWS Student Builder 웹사이트/      Claude Design 내보내기 결과
  ├─ ASBG Landing.dc.html         마크업 + 하단 <script>에 데이터/로직
  ├─ support.js                   .dc.html 런타임 (수정 금지, 생성물)
  ├─ image-slot.js                <image-slot> 커스텀 엘리먼트
  ├─ assets/                      로고, 아이콘, Amazon Ember 폰트
  └─ uploads/                     디자인 작업 시 참고용 원본 파일
```

## 콘텐츠 수정하는 곳

전부 `ASBG Landing.dc.html` 하단 `<script type="text/x-dc">` 안에 있습니다.

| 대상 | 위치 |
|---|---|
| 지난 기수 활동 | `const PAST = { '4기': [...], ... }` |
| FAQ | `const FAQS = [...]` |
| 리크루팅 일정 | `renderVals()` 안의 `stepData` |
| 현재 진행 단계 (NOW 뱃지) | `stepData` 의 `start`/`end` 기준으로 서울 날짜에서 자동 계산 |
| 기수 번호 | `data-props` 의 `cohort` |

## 아직 안 채운 것

- [ ] 교내 이벤트·Welcome Party 실제 날짜 — 현재 `추후 안내`
- [ ] 지난 기수 활동 사진 — 아래 참고
- [ ] 운영진 소개 (FAQ 6번에서 "곧 공개" 로 처리 중)

### 사진에 대해

활동 카드의 `<image-slot>` 은 Claude Design 에디터 안에서만 이미지가 저장됩니다
(에디터 호스트와 postMessage로 통신). 로컬/배포 환경에서는 placeholder만 보입니다.

실제 사진을 넣으려면 이미지를 `assets/photos/` 에 두고 `src` 를 직접 지정하면 됩니다:

```html
<image-slot src="assets/photos/4기-데모데이.jpg" shape="rect"></image-slot>
```

`PAST` 항목에 `photo:false` 를 주면 "NO PHOTO" 상태로 렌더링되므로,
사진이 없는 활동은 그대로 두어도 레이아웃이 깨지지 않습니다.
