# ⚡ 워뇨-AI (Wonyo-AI)

> **비트코인 전설의 트레이더 '워뇨띠' 144만 건 실거래 전수 복기 & 거래량 흡수(Volume Absorption) + 딥러닝(ONNX) 융합 실시간 직감 예측 터미널**

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-emerald?style=for-the-badge&logo=vercel)](https://wonyo-ai.vercel.app)
[![ONNX Runtime](https://img.shields.io/badge/ONNX%20Runtime-0.36ms%20Latency-005ced?style=for-the-badge&logo=onnx)](https://onnxruntime.ai/)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/badge/uv-Fast%20Packaging-purple?style=for-the-badge)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 📌 프로젝트 소개 (Overview)

**워뇨-AI**는 비트코인 선물 시장에서 14.5 BTC(수백만 원)로 출발하여 **+3,537.3 BTC(3,000억 원 이상)**의 누적 실현 수익을 기록한 전설적인 트레이더 '워뇨띠(aoa)'의 600MB 비트맥스(BitMEX) 원본 체결 데이터(1,444,583건)를 전수 분석·모델링한 **초저지연 퀀트 인텔리전스 터미널**입니다.

워뇨띠의 실거래 핵심 철학인 **[오더플로우 거래량 흡수(Volume Absorption) + 캔들 해석 + 리스크 한도 관리]** 퀀트 알고리즘과 함께, 원격 GPU로 학습된 **멀티태스크 심층 신경망(`WonyoImitationNet`)**을 C++ 최적화 **ONNX Runtime(추론 지연 0.36ms)**으로 결합하여 매 10초마다 실시간 시장을 진단하고 최적의 포지션을 가이드합니다.

🔗 **라이브 웹 터미널**: [https://wonyo-ai.vercel.app](https://wonyo-ai.vercel.app)

---

## 🧠 600MB 실거래 전수학습 딥러닝 아키텍처 (ONNX)

비트맥스 원본 체결 데이터(144만 행)에서 추출된 15분 단위 연속 시계열 텐서(`[Batch, 32, 12]`)를 바탕으로 워뇨띠의 진입·청산 의사결정과 베팅 크기를 모방 학습했습니다:

```
[15M 캔들 & 12대 퀀트 피처 (32-Bar Sequence)]
                     │
                     ▼
  ┌─────────────────────────────────────┐
  │  1D Dilated Conv1D Feature Extractor│ (국소 캔들/거래량 패턴 추출)
  └──────────────────┬──────────────────┘
                     ▼
  ┌─────────────────────────────────────┐
  │  Bidirectional GRU Sequence Layer   │ (양방향 장단기 문맥 파악)
  └──────────────────┬──────────────────┘
                     ▼
  ┌─────────────────────────────────────┐
  │    Temporal Self-Attention Layer    │ (핵심 변곡봉 가중치 집중)
  └──────────────────┬──────────────────┘
                     ▼
          ┌──────────┴──────────┐
          ▼                     ▼
  ┌───────────────┐     ┌───────────────┐
  │ Action Head   │     │  Sizing Head  │
  │ (4-Class)     │     │ (Continuous)  │
  │ • HOLD        │     │               │
  │ • BUY_LONG    │     │ Dynamic Kelly │
  │ • SELL_SHORT  │     │ Sizing Factor │
  │ • CLOSE       │     │               │
  └───────────────┘     └───────────────┘
```

* **원격 GPU 학습 파이프라인**: Google Colab CLI 기반 T4 GPU 원격 프로비저닝 및 30 Epoch 클래스 가중치 학습.
* **C++ 최적화 ONNX 배포**: 2GB가 넘는 무거운 PyTorch 런타임을 배제하고 13MB 초경량 `onnxruntime`으로 서빙하여, **평균 0.36ms(초당 약 2,700회)**의 초고속 CPU 추론 달성.
* **4-Class 확률 분포 출력**: `HOLD`(관망), `BUY_LONG`(매수), `SELL_SHORT`(매도), `CLOSE`(조기 청산) 확률을 실시간 게이지 바로 시각화.

---

## 🎯 트레이딩 핵심 집중형 UI (Streamlined Interface)

불필요하고 복잡한 부가 정보와 긴 설명을 걷어내고, 실제 매매자가 0.5초 만에 판단할 수 있는 **단일 화면(Single-Screen Bloomberg/TradingView 스타일)** 레이아웃으로 간소화되었습니다.

```
┌────────────────────────────────────────────────────────────────────────┐
│  [1] 슬림 헤더: 로고 | BTC 시세 ($85,200) | 5M/15M/1H | 표준/액티브 | LIVE    │
├──────────────────────────────────┬─────────────────────────────────────┤
│  [2-A] 워뇨띠 직감 마스터 시그널  │  [2-B] 600MB 실거래 ONNX 신경망     │
│   • 즉각 매수/매도/관망 3단 버튼  │   • 추론 속도: 0.36ms (C++ 엔진)     │
│   • 롱/숏 진입 준비도 게이지 (%) │   • HOLD / BUY / SELL / CLOSE 확률  │
│   • 핵심 플레이북 1줄 브리핑      │   • 매수흡수/매도저항/효율비 4대 칩  │
├──────────────────────────────────┴─────────────────────────────────────┤
│  [3] 메인 트레이딩 워크스페이스                                        │
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
2. **마스터 시그널 & ONNX 직감 보드 통합**:
   - 좌측: 워뇨띠 전통 오더플로우 룰 시그널 + 진입 준비도(%) 바.
   - 우측: 144만 건 실거래로 훈련된 `WonyoImitationNet` 신경망 확률 및 0.36ms 초저지연 상태.
3. **원스톱 포지션 & 실전 실행 패널**:
   - 3단 래더 목표 진입가, 1차 익절가(+1.2%), 칼손절가(-1.4%), 16.35분 보유 타이머, 60분 스크래치 탈출 상태 결합.
4. **미니 체결 장부 (5-Row Mini-Ledger)**:
   - `[실시간 체결 장부]`와 `[2021 전설 복기]` 탭 전환 지원.

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
* **머신러닝 & 추론 가속**:
  * **ONNX Runtime (v1.20+)**: C++ 최적화 초경량(13MB) 고속 추론 엔진
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

### 4. ONNX 추론 벤치마크 및 단위 테스트
```bash
# ONNX 초저지연 추론 벤치마크 실행
uv run python src/test_onnx_inference.py

# 24개 전수 단위 테스트 실행
uv run pytest
```

---

## 🌐 API 엔드포인트 규격 (API Endpoints)

| 메소드 | 엔드포인트 | 주요 파라미터 | 설명 |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | - | 트레이딩 핵심 집중형 통합 웹 터미널 UI |
| `GET` | `/api/predict` | `mode` (`live`/`replay`), `interval` (`5m`/`15m`/`1h`), `sensitivity` (`standard`/`active`) | 워뇨띠 직감 판단, 4대 리스크 매트릭스 및 ONNX 신경망 확률 통합 반환 |
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
│   ├── wonyo_nn_model.onnx     # 프로덕션 서빙용 ONNX 신경망 모델
│   ├── service_engine.py       # 3단 래더 및 리스크 가드 서비스 엔진
│   ├── risk_engine.py          # 4대 리스크 인풋 벡터 및 켈리 사이징 계산기
│   ├── feature_extractor.py    # 12대 퀀트 및 오더플로우 지표 추출기
│   ├── web_api.py              # FastAPI 메인 웹 애플리케이션
│   └── test_onnx_inference.py  # ONNX 추론 지연시간 벤치마크 스크립트
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
