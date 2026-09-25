# Agent Operational Guidelines & Mistake Prevention Log (agent.md)

이 문서는 AI 에이전트(Antigravity)가 이 프로젝트를 수행하며 저지른 실수와 교훈을 기록하고, 동일한 실수를 절대 반복하지 않기 위해 준수해야 할 **철칙(Zero-Tolerance Rules)** 및 **핵심 스킬(Superpowers & Ponytail) 융합 운용 지침**입니다.

---

## ⚡ Superpowers & Ponytail 듀얼 엔진 운용 전략

우리는 상반되지만 상호보완적인 두 가지 핵심 스킬셋을 프로젝트 성격에 맞춰 똑똑하게 취사선택한다:

| 영역 | 채택 스킬 | 운용 기준 및 행동 요령 |
| :--- | :--- | :--- |
| **금융 수학 / 리스크 한도** | **Superpowers** (Rigor) | • **TDD 우선**: 켈리 공식, 드로우다운 패널티, 포지션 사이징 공식은 테스트 코드를 먼저 작성 후 구현.<br>• **검증주의**: 보고 전 스크립트 실행 로그와 수치를 대조하여 100% 검증(`verification-before-completion`).<br>• **추측 금지**: 버그 발생 시 원본 스키마와 데이터 타입을 체계적으로 역추적(`systematic-debugging`). |
| **데이터 파이프라인 / ETL** | **Ponytail** (Simplicity) | • **YAGNI & 미니멀리즘**: 불필요한 마이크로서비스나 과도한 추상화 클래스를 금지하고 가장 단순하고 빠른 경로 선택.<br>• **고성능 도구 직결**: 600MB 대용량 CSV는 복잡한 프레임워크 대신 DuckDB / Polars로 수 줄의 쿼리로 초고속 집계.<br>• **군더더기 없는 구조**: 보일러플레이트를 최소화하고 직관적이고 유지보수 쉬운 단일 책임 파일 구성. |
| **전략 모델링 & 백테스트** | **Hybrid** (Balanced) | • 신호 추출과 백테스트는 단순하고 빠른 룰(Ponytail)로 프로토타이핑하되,<br>• 슬리피지, 호가 대기열, 수수료 리베이트 등 금융적 정밀성(Superpowers)은 한 치의 오차도 없이 반영. |

---

## 🚨 절대 반복 금지 실수 목록 (Mistake Log & Prevention Rules)

### 1. PowerShell 인라인 명령 줄넘김 및 따옴표 이스케이프 오류
- **실수 내용**: PowerShell 환경에서 `python -c "con.sql('''...''')"` 와 같이 인라인 문자열에 삼중 따옴표나 중첩 따옴표를 사용하여 파이썬 구문 오류(`SyntaxError: unterminated string literal`)를 다수 발생시킴.
- **방지 철칙**: 
  - 복잡한 로직이나 SQL 쿼리가 포함된 파이썬 코드는 **절대로 터미널 인라인(`-c`)으로 실행하지 않는다.**
  - 반드시 `src/` 디렉터리에 명시적인 `.py` 스크립트 파일을 생성하고 파일 단위로 실행한다.

### 2. 패키지 및 환경 관리 도구 불일치 (pip vs uv)
- **실수 내용**: 사용자의 프로젝트 기본 지침(uv 사용)을 미리 확인하지 않고 초기 파이썬 환경에서 `python -m pip install`을 시도함.
- **방지 철칙**:
  - 본 프로젝트의 모든 패키지 설치는 **`uv add <package>`**를 사용한다.
  - 모든 스크립트 실행은 반드시 **`uv run python <script.py>`**를 사용한다.

### 3. 비트맥스 원본 체결 데이터의 특성 누락 (정렬 및 타입 필터링)
- **실수 내용**: 체결 CSV가 시간순으로 정렬되어 있다고 가정하고, `Funding`(펀딩비 지급), `Settlement`(정산) 행을 제외하지 않아 누적 포지션 합산이 왜곡됨.
- **방지 철칙**:
  - 비트맥스 체결 로그 분석 시 반드시 `exectype = 'Trade'`를 필터링한다.
  - 반드시 `transacttime` 타임스탬프를 파싱하여 시간순 정렬(`ORDER BY transacttime ASC`)을 명시적으로 수행한다.

### 4. 전략 타임프레임 불일치 (1시간봉 vs 25분 스캘핑)
- **실수 내용**: 워뇨띠의 실제 매매 보유 시간 중앙값은 **25.86분**(42%가 15분 미만)임에도 불구하고, 1시간(1h) 캔들로 백테스트를 수행하여 미세 거래량 흡수 및 오더플로우 시그널을 희석시킴.
- **방지 철칙**:
  - 초단타/스캘핑 행동 모방 모델은 반드시 1분, 5분, 15분 단위의 고해상도 시계열을 기본으로 사용한다.
  - 포지션 타임아웃 역시 실제 보유 분포(익절 16분, 손절 88분)에 맞게 타이트하게 설정한다.

### 5. 파이썬 서브패키지 모듈 임포트 경로 누락
- **실수 내용**: `uv run python src/run_simulation.py` 실행 시 루트 디렉터리가 `sys.path`에 포함되지 않아 `ModuleNotFoundError: No module named 'src'` 발생.
- **방지 철칙**:
  - 실행 진입점 스크립트 최상단에 항상 루트 경로를 `sys.path.insert(0, ...)`로 보장하거나, `uv run python -m src.module_name` 형태로 실행한다.

### 6. 외부 프론트엔드 CDN 라이브러리 버전 미고정
- **실수 내용**: Lightweight Charts 스크립트 로드 시 버전을 명시하지 않아 최신 v5.2.1이 로드되며 `addCandlestickSeries` 함수 제거로 인한 프론트엔드 렌더링 중단 발생.
- **방지 철칙**:
  - 외부 CDN 스크립트는 항상 검증된 버전(`@4.2.0`)을 엄격하게 명시(Version Pinning)하고, API 지원 여부를 확인하는 방어 코드(`typeof chart.addCandlestickSeries === 'function'`)를 병행한다.

---

## 🧠 워뇨-AI 핵심 퀀트 팩트 & 공식 레퍼런스
- **총 실현 손익**: +3,537.3 BTC (입금 14.5 BTC $\rightarrow$ 출금 2,832.5 BTC)
- **사이클 승률**: 77.79% / 평균 이익 +1.13% / 평균 손실 -1.49%
- **익절/손절 보유 시간**: 익절 중앙값 16.35분 / 손절 중앙값 88.46분
- **주문 실행 특성**: 99.38% 지정가(Limit) 주문, 66.91% 메이커 리베이트 수취
- **레버리지 스케일링**: 시드 증가에 따라 5.38배(2018) $\rightarrow$ 1.08배(2021)로 동적 축소
- **4대 리스크 인풋 벡터**:
  1. 거래량 고갈 & 호가 흡수율 (Alpha)
  2. 스프레드 위험도 & 아미후드 비유동성 지수 (Microstructure Risk)
  3. 실현 변동성 쇼크 & 카우프만 효율비 (Market Regime Risk)
  4. HWM 드로우다운 & 연속 손실 횟수 (Portfolio Risk)

---

## 🚀 상용화(Commercial Service) 아키텍처 원칙
1. **3단 분할 래더 진입 (Multi-Leg Scaled Entry)**:
   - 1차 Touch 진입(40%) $\rightarrow$ 2차 -0.5 ATR(30%) $\rightarrow$ 3차 -1.0 ATR(30%)
   - 단일 진입 대비 노이즈 흡수 및 슬리피지 방어, 평균 체결 레그 2.3개로 단가 최적화.
2. **스크래치 풀백 조기 탈출 (Scratch Exit)**:
   - 보유 60분 경과 시점에 손실 상태이나 약반등(-0.4% 이내 회귀) 시 전량 탈출(Scratch)하여 풀스탑 손실 35% 이상 사전 차단.
3. **상용 서비스 엔진 구조 (`src/service_engine.py`)**:
   - 실시간 캔들 스트림 수신 $\rightarrow$ 4대 리스크 인풋 동적 계산 $\rightarrow$ JSON 신호 규격 즉시 발행.
   - 출력 필드: `action`, `limit_price`, `size_usd_contracts`, `stop_loss`, `take_profit`, `expected_holding_minutes`, `risk_state`, `status`.
4. **웹 기반 인텔리전스 터미널 (`src/web_api.py`, `src/static/index.html`)**:
   - 실시간 비트코인 시세 및 TradingView Lightweight 차트 연동.
   - 워뇨띠 4대 현실적 리스크 가드 레이더 & 거래량 흡수율(Absorption) 실시간 시각화.
   - 실시간(LIVE) 모드 및 2021 전설의 폭락장 리플레이(REPLAY) 모드 지원.
   - 주소: `http://127.0.0.1:8000`.
5. **듀얼 AI 퀀트 엔진 연동 (Dual-AI Engine)**:
   - **ONNX 신경망 (`WonyoImitationNet`)**: 144만 건 실거래 전수학습 기반 C++ 0.36ms 초저지연 오더플로우 및 캔들 시계열 방향성/사이징 예측.
   - **TypeSafe Jev System One (`news_sentiment.py`)**: 실시간 외신 감성 분석(호재/악재/중립), 확률 캘리브레이션, 거래소 파산 등 시스템 붕괴 감지 블랙스완 리스크 가드.
6. **트레이딩 핵심 집중형 UI 원칙 (Single-Screen Bloomberg Style)**:
   - 1줄 슬림 헤더 $\rightarrow$ 마스터 직감 & ONNX 확률 보드 $\rightarrow$ 390px 클린 차트 $\rightarrow$ 원스톱 포지션 패널 $\rightarrow$ 5행 미니 장부 $\rightarrow$ 하단 Jev AI 속보 티커 바 구성.
