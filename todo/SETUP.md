# 개발 환경 셋업 (시작 전 딱 한 번)

> 이 문서를 Claude Code 에 던지면 도구 설치·실행까지 도와준다.
> 백엔드 담당은 **1 + 2**, 프론트 담당은 **1 + 3** 만 하면 된다.
> 파트별 할 일은 각자 `BACKEND.md` / `FRONTEND.md` 참고.

---

## 0. 사전 준비 (공통)
- [ ] **Git** 설치 — https://git-scm.com (Windows) / Mac 은 `xcode-select --install`
- [ ] **저장소 받기** (clone) — 깃 처음이면 팀 리드가 5분 도와줌
  ```bash
  git clone https://github.com/SAVE-THE-FARMS/Soltalk.git
  cd Soltalk
  ```
- [ ] 편집기: VS Code 권장

> ⚠️ **OPENAI_API_KEY 는 팀 리드가 제공/관리한다.** 학생은 키를 발급받거나 커밋할 필요 없음.
> (백엔드 담당은 리드가 준 `backend/env/.env` 파일을 받아서 그 위치에 두기만.)

---

## 1. 공통 확인
- [ ] 버전 확인 (설치돼 있으면 숫자가 뜬다)
  ```bash
  git --version
  ```

---

## 2. 백엔드 셋업 (백엔드 담당)

### 2-1. uv 설치 (파이썬 패키지 매니저)
- **Windows (PowerShell)**
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```
- **Mac / Linux**
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- 설치 후 새 터미널 열고 확인: `uv --version`
- (파이썬은 uv 가 알아서 준비함. 따로 설치 안 해도 됨.)

### 2-2. 의존성 설치 + 실행
```bash
cd backend
# 리드가 준 .env 를 env/ 폴더에 두기 (없으면 예시 복사)
#   cp env/.env.example env/.env
uv sync                        # 패키지 설치
uv run python app/server.py    # 서버 실행
```
- [ ] 브라우저에서 http://localhost:8000/docs 열림 → 성공
- [ ] `/health` 눌러 `{"status":"ok"}` 확인

---

## 3. 프론트 셋업 (프론트 담당)

### 3-1. Node.js 설치
- **Node 20 LTS** 권장 — https://nodejs.org (LTS 버튼)
- 설치 후 새 터미널에서 확인: `node --version` (v20 이상), `npm --version`

### 3-2. 의존성 설치 + 실행
```bash
cd frontend
npm install
npm run dev        # http://localhost:5173
```
- [ ] 브라우저에서 http://localhost:5173 열려 채팅 화면 뜸 → 성공
- [ ] (백엔드도 8000 에 같이 켜두면) 메시지 보냈을 때 응답 말풍선이 뜸

---

## 4. 자주 겪는 문제
- **`uv` / `node` 명령을 못 찾음** → 설치 후 **터미널을 새로 열어야** 인식됨
- **포트가 이미 사용 중** (8000/5173) → 기존에 켜둔 서버 끄거나 포트 변경
- **프론트에서 응답이 안 옴** → 백엔드(8000)도 켜져 있는지 확인
- **한글 응답이 깨져 보임** → 브라우저에서는 정상. 터미널/curl 만 깨질 수 있음
- 그래도 막히면 → **이 SETUP.md + 자기 파트 문서(BACKEND/FRONTEND.md)** 를 Claude Code 에 첨부하고 상황 설명

---

## 절대 하지 말 것
- `.env` / API 키 커밋 금지 (이미 `.gitignore` 처리됨)
- 실제 농가 데이터 / 솔캐스트 관련 내용 금지 — 자세히는 `CLAUDE.md`
