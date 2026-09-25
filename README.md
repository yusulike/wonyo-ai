# ⚡ 워뇨-AI (Wonyo-AI)

> **비트코인 전설의 트레이더 '워뇨띠' 144만 건 실거래 전수 복기 & 거래량 흡수(Volume Absorption) + 딥러닝(ONNX) + TypeSafe Jev AI 융합 실시간 직감 예측 터미널**

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-emerald?style=for-the-badge&logo=vercel)](https://wonyo-ai.vercel.app)
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-0.36ms%20Latency-005ced?style=for-the-badge&logo=onnx)](https://onnxruntime.ai/)
[![TypeSafe Jev](https://img.shields.io/badge/TypeSafe-Jev%20System%20One-9333ea?style=for-the-badge)](https://typesafe.ai/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/badge/uv-Fast%20Packaging-purple?style=for-the-badge)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 📌 프로젝트 소개 (Overview)

**워뇨-AI**는 비트코인 선물 시장에서 14.5 BTC(수백만 원)로 출발하여 **+3,537.3 BTC(3,000억 원 이상)**의 누적 실현 수익을 기록한 전설적인 트레이더 '워뇨띠(aoa)'의 600MB 비트맥스(BitMEX) 원본 체결 데이터(1,444,583건)를 전수 분석·모델링한 **초저지연 퀀트 인텔리전스 터미널**입니다.

워뇨띠의 실거래 핵심 철학인 **[오더플로우 거래량 흡수(Volume Absorption) + 캔들 해석 + 리스크 한도 관리]** 퀀트 알고리즘과 함께, **듀얼 AI 엔진(Dual-AI Engine: ONNX 딥러닝 차트 예측 + TypeSafe Jev System One 외신 감성/블랙스완 분석)**을 결합하여 매 10초마다 실시간 시장을 진단하고 최적의 포지션을 가이드합니다.

🔗 **라이브 웹 터미널**: [https://wonyo-ai.vercel.app](https://wonyo-ai.vercel.app)

---

## 🤖 듀얼 AI 퀀트 엔진 구조 (Dual-AI Architecture)

워뇨-AI는 차트 미세구조(Microstructure)와 거시 외신 심리(Macro Sentiment)를 상호보완적으로 결합한 2개의 특화 AI 엔진으로 구동됩니다:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        실시간 시장 인풋 데이터 스트림                   │
└──────────────────┬──────────────────────────────────┬──────────────────┘
                   │                                  │
    [15M 캔들 & 12대 오더플로우 텐서]            [외신 RSS & 공포탐욕 지수]
                   │                                  │
                   ▼                                  ▼
┌──────────────────────────────────────┐ ┌──────────────────────────────────────┐
│  AI Engine 1: WonyoImitationNet      │ │  AI Engine 2: TypeSafe Jev System One│
│  (600MB 실거래 전수학습 ONNX 모델)   │ │  (실시간 외신 감성 & 블랙스완 가드)  │
├──────────────────────────────────────┤ ├──────────────────────────────────────┤
│ • Conv1D + BiGRU + Temporal Attention│ │ • Choice: 호재/악재/중립 방향 판별   │
│ • 추론 속도: 0.36ms (C++ 엔진)       │ │ • Score: 비트코인 시세 영향도 채점   │
│ • HOLD / BUY / SELL / CLOSE 4단 확률 │ │ • Noul: 거래소 파산 등 블랙스완 감지 │
│ • 동적 켈리 사이징 배율 계수 산출    │ │ • 캘리브레이션된 신뢰도(Confidence)  │
└──────────────────┬───────────────────┘ └──────────────────┬───────────────────┘
                   │                                        │
                   └───────────────────┬────────────────────┘
                                       ▼
                 ┌───────────────────────────────────────────┐
                 │  워뇨-AI 통합 마스터 시그널 & 리스크 가드 │
                 │  (진입 여부, 목표가, 손절가, 60분 스크래치)│
                 └───────────────────────────────────────────┘
```

### 1. 🧠 600MB 실거래 전수학습 딥러닝 아키텍처 (ONNX)
- **텐서 규격**: `[Batch, 32, 12]` (최근 32개 15분봉의 12대 퀀트 지표 시계열)
- **네트워크 구조**: 1D Dilated Conv1D (국소 패턴) $\rightarrow$ Bidirectional GRU (문맥) $\rightarrow$ Temporal Self-Attention (변곡봉 집중) $\rightarrow$ Multi-Task Output
- **C++ 최적화 ONNX 배포**: 2GB PyTorch 대신 13MB 초경량 `onnxruntime`을 탑재하여 **평균 0.36ms(초당 2,700회)**의 CPU 초저지연 달성.

### 2. ⚡ TypeSafe Jev System One 외신 감성 & 블랙스완 분석
- **실시간 속보 크롤링**: 코인텔레그래프 및 Google News 암호화폐 RSS 피드 자동 수신.
- **System One 모델 평가**: 단순 키워드 매칭의 한계를 넘어 문맥을 정밀 판별(호재, 악재, 중립)하고 영향도 점수 및 확신도(Confidence) 도출.
- **블랙스완 확률 가드 (`Noul`)**: 거래소 파산, 긴급 규제, 대형 해킹 등 시장 붕괴 위험을 감지하여 뇌동매매 및 시스템 리스크 사전 차단.

---

## 🎯 트레이딩 핵심 집중형 UI (Streamlined Interface)

불필요하고 복잡한 부가 정보와 긴 설명을 걷어내고, 실제 매매자가 0.5초 만에 판단할 수 있는 **단일 화면(Single-Screen Bloomberg/TradingView 스타일)** 레이아웃으로 개편되었습니다:

```
┌────────────────────────────────────────────────────────────────────────┐
│  [1] 슬림 헤더: 로고 | BTC 시세 ($85,200) | 5M/15M/1H | 표준/액티브 | LIVE    │
├────────────────────────────────────────────────────────────────────────┤
│  [2] TypeSafe Jev AI 실시간 속보 티커 | 탐욕·공포 | Jev 확신도 | 블랙스완 위험 │
├──────────────────────────────────┬─────────────────────────────────────┤
│  [3-A] 워뇨띠 직감 마스터 시그널  │  [3-B] 600MB 실거래 AI 신경망       │
│   • 즉각 매수/매도/관망 3단 버튼  │   • 추론 속도: 0.36ms (C++ 엔진)     │
│   • 롱/숏 진입 준비도 게이지 (%) │   • HOLD / BUY / SELL / CLOSE 확률  │
│   • 핵심 플레이북 1줄 브리핑      │   • 매수흡수/매도저항/효율비 4대 칩  │
├──────────────────────────────────┴─────────────────────────────────────┤
│  [4] 메인 트레이딩 워크스페이스                                        │
│  ┌───────────────────────────────┐ ┌─────────────────────────────────┐ │
│  │ TradingView 캔들 & 오더플로우 │ │ 실전 주문 & 가상 포지션 원스톱  │ │
│  │  • 390px 클린 차트            │ │  • 현재 포지션 / 레버리지 / PnL │ │
│  │  • 매수흡수(초록)/매도저항(빨강)│ │  • 목표 진입가/익절가/손절가    │ │
│  │  • 하단 4대 거래량/이격도 지표│ │  • 16분 보유 타이머/스크래치 탈출│ │
│  │                               │ ├─────────────────────────────────┤ │
│  │                               │ │ 최근 체결 미니 장부 (5행 콤팩트)│ │
│  │                               │ │  • [실시간 체결] vs [전설 복기] │ │
│  └───────────────────────────────┘ └─────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────────┘
```

1. **상단 네비게이션 슬림화 (1줄)**:
   - 비트코인 실시간 시세, 타임프레임(5m/15m/1h), 민감도(표준/액티브), 모드(LIVE/리플레이) 원스톱 제어.
2. **헤드라인 바로 아래 TypeSafe Jev AI 속보 티커 바**:
   - 외신 속보를 3.5초 주기로 롤링하며, Jev 확신도 및 블랙스완 위험도(%)를 상단에서 즉시 확인.
3. **마스터 시그널 & AI 신경망 직감 보드 통합**:
   - 좌측: 워뇨띠 전통 오더플로우 룰 시그널 + 진입 준비도(%) 바.
   - 우측: 144만 건 실거래로 훈련된 `WonyoImitationNet` 신경망 확률 및 0.36ms 초저지연 상태.
4. **원스톱 포지션 & 실전 실행 패널**:
   - 3단 래더 목표 진입가, 1차 익절가(+1.2%), 칼손절가(-1.4%), 16.35분 보유 타이머, 60분 스크래치 탈출 상태 결합.
5. **미니 체결 장부 (5-Row Mini-Ledger)**:
   - `[실시간 체결 장부]`와 `[2021 전설 복기]` 탭 전환 지원.
6. **초심자를 위한 인터랙티브 툴팁 지원**:
   - 블랙스완, 바닥 매수흡수, 고점 매도저항, 카우프만 효율비, 스크래치 탈출, 체결장부 등 10여 개 핵심 퀀트 용어에 마우스 오버 시 직관적인 팝업 설명 제공.

---

## 📊 워뇨띠 퀀트 팩트 레퍼런스 (Quantitative Facts)

비트맥스(BitMEX) 원본 체결 데이터 전수 분석을 통해 확인된 실거래 파라미터가 모델 전반에 적용되어 있습니다:

| 지표 | 워뇨띠 실거래 데이터 분석치 | 워뇨-AI 모델 반영 |
| :--- | :---: | :---: |
| **누적 실현 손익** | **+3,537.3 BTC** (출금 2,832.5 BTC) | 벤치마크 알파 모델 |
| **사이클 승률** | **77.79%** (이익 +1.13% / 손실 -1.49%) | 3단 분할 래더 진입 단가 최적화 |
| **포지션 보유 시간** | **익절 16.35분 / 손절 88.46분** | 타이트한 15분~60분 보유 타임아웃 |
| **주문 실행 유형** | **99.38% 지정가(Limit), 66.91% 메이커** | Post-Only 메이커 수수료 리베이트 전략 |
| **레버리지 스케일** | **5.38배(초기) $\rightarrow$ 1.08배(후기)** | 시드 규모 기반 켈리 베팅 동적 축소 |
| **조기 탈출 룰** | **보유 60분 경과 시 약반등 탈출** | Scratch Exit (-0.4% 회귀 시 전량 청산) |

---

## 🛠️ 기술 스택 (Tech Stack)

* **언어 및 런타임**: Python 3.12, JavaScript (ES6+)
* **패키지 & 의존성 관리**: [`uv`](https://github.com/astral-sh/uv) (Astral 초고속 패키지 관리자)
* **머신러닝 & AI 추론 엔진**:
  * **ONNX Runtime (v1.20+)**: C++ 최적화 초경량(13MB) 고속 시계열 추론 엔진 (0.36ms Latency)
  * **TypeSafe SDK (Jev System One)**: 외신 감성 분류, 확률 캘리브레이션, 블랙스완 가드
  * **PyTorch (v2.6)**: Colab GPU 학습 모델 빌더 및 ONNX 익스포터
  * **DuckDB / Polars**: 600MB 체결 CSV 초고속 SQL ETL 파이프라인
* **백엔드 프레임워크**: FastAPI, Uvicorn, Pydantic, Requests
* **프론트엔드**: Vanilla HTML5, Tailwind CSS, TradingView Lightweight Charts (v4.2.0 고정)
* **클라우드 & 인프라**: Google Colab CLI (GPU 분산 학습), Vercel Serverless Functions, Edge CDN

---

## 🚀 로컬 설치 및 실행 방법 (Getting Started)

### 1. 사전 요구사항
* Python 3.12 이상
* [uv](https://docs.astral.sh/uv/) 설치:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

### 2. 저장소 복제 및 패키지 설치
```bash
git clone https://github.com/yusulike/wonyo-ai.git
cd wonyo-ai

# uv를 사용한 초고속 패키지 동기화
uv sync
```

### 3. 로컬 서버 실행
```bash
uv run python -m uvicorn src.web_api:app --host 127.0.0.1 --port 8000 --reload
```
브라우저에서 `http://127.0.0.1:8000`에 접속하여 실시간 대시보드를 확인합니다.

### 4. AI 추론 및 단위 테스트
```bash
# ONNX 초저지연 추론 벤치마크 실행
uv run python src/test_onnx_inference.py

# TypeSafe Jev System One 감성 분석 검증
uv run python src/test_predict_api.py

# 24개 전수 단위 테스트 실행
uv run pytest
```

---

## 🌐 API 엔드포인트 규격 (API Endpoints)

| 메소드 | 엔드포인트 | 주요 파라미터 | 설명 |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | - | 트레이딩 핵심 집중형 통합 웹 터미널 UI |
| `GET` | `/api/predict` | `mode` (`live`/`replay`), `interval` (`5m`/`15m`/`1h`), `sensitivity` (`standard`/`active`) | 워뇨띠 직감 판단, 4대 리스크 매트릭스, ONNX 신경망 확률 및 TypeSafe Jev 외신 감성 통합 반환 |
| `GET` | `/api/nn-prediction` | `mode`, `interval` | C++ 최적화 ONNX 런타임 전용 초저지연 신경망 예측 결과 반환 |
| `GET` | `/api/candles` | `mode`, `interval`, `limit` | 실시간 캔들스틱 및 거래량 흡수(Bull/Bear Absorption) 오버레이 데이터 |
| `GET` | `/api/trades` | - | 실시간 가상 체결 내역 및 2021년 전설의 매매 복기 장부 반환 |

---

## 📂 프로젝트 구조 (Project Structure)

```
wonyo-ai/
├── api/                        # Vercel 서버리스 배포 진입점 (Serverless Functions)
│   ├── predict.py              # /api/predict 라우트 핸들러
│   ├── candles.py              # /api/candles 라우트 핸들러
│   ├── trades.py               # /api/trades 라우트 핸들러
│   └── index.py                # ASGI 프록시 및 메인 라우터
├── public/                     # Edge CDN 정적 호스팅 자산
│   └── index.html              # 프론트엔드 터미널 (Streamlined single-screen)
├── src/                        # 백엔드 코어 소스코드 & 인공지능 모델
│   ├── static/
│   │   └── index.html          # 로컬 대시보드 템플릿
│   ├── build_real_dataset.py   # 144만 건 체결 로그 DuckDB ETL 파이프라인
│   ├── train_colab_nn.py       # Google Colab GPU 원격 모델 학습 스크립트
│   ├── export_onnx.py          # PyTorch -> ONNX (Opset 17) 변환기
│   ├── onnx_predictor.py       # 초경량 ONNX Runtime C++ 추론 엔진
│   ├── news_sentiment.py       # TypeSafe Jev System One 외신 감성 및 블랙스완 엔진
│   ├── wonyo_nn_model.onnx     # 프로덕션 서빙용 ONNX 신경망 모델
│   ├── service_engine.py       # 3단 래더 및 리스크 가드 서비스 엔진
│   ├── risk_engine.py          # 4대 리스크 인풋 벡터 및 켈리 사이징 계산기
│   ├── feature_extractor.py    # 12대 퀀트 및 오더플로우 지표 추출기
│   ├── web_api.py              # FastAPI 메인 웹 애플리케이션
│   ├── test_onnx_inference.py  # ONNX 추론 지연시간 벤치마크 스크립트
│   └── test_predict_api.py     # TypeSafe Jev 및 API 예측 응답 검증 스크립트
├── tests/                      # 자동화 테스트 스위트
│   ├── test_onnx.py            # ONNX 추론 정확성 및 입출력 규격 검증
│   ├── test_risk_engine.py     # 켈리 공식 및 리스크 한도 검증
│   └── test_web_api.py         # 웹 API 엔드포인트 및 서버리스 핸들러 테스트
├── pyproject.toml              # 프로젝트 메타데이터 및 uv 패키지 정의
├── requirements.txt            # Vercel 배포용 경량 런타임 의존성
├── vercel.json                 # Vercel 라우팅 및 리라이트 설정
├── AGENTS.md                   # AI 에이전트 운용 지침 및 실수 방지 철칙
└── README.md                   # 프로젝트 종합 설명서
```

---

## ⚠️ 면책 조항 (Disclaimer)

* 본 프로젝트는 전설적인 트레이더 워뇨띠의 과거 공개 거래 데이터와 매매 패턴을 학술적·통계적으로 모델링한 오픈소스 퀀트 리서치 도구입니다.
* 제공되는 모든 예측, 시그널 및 가상 포지션은 **투자 권유나 금융 자문이 아니며**, 실제 매매의 최종 책임은 전적으로 사용자 본인에게 있습니다.
