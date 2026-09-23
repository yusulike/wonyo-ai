# ⚡ 워뇨-AI (Wonyo-AI)

> **비트코인 전설의 트레이더 '워뇨띠(Wonyo)' 실거래 복기 & 오더플로우 거래량 흡수(Volume Absorption) 기반 실시간 직감 예측 엔진**

[![Vercel Deployment](https://img.shields.io/badge/Vercel-Live%20Demo-emerald?style=for-the-badge&logo=vercel)](https://wonyo-ai.vercel.app)
[![Python](https://img.shields.io/badge/Python-3.12-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![uv](https://img.shields.io/badge/uv-Fast%20Packaging-purple?style=for-the-badge)](https://github.com/astral-sh/uv)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

---

## 📌 프로젝트 소개 (Overview)

**워뇨-AI**는 비트코인 선물 시장에서 14.5 BTC(수백만 원)로 출발하여 **+3,537.3 BTC(3,000억 원 이상)**의 누적 수익을 기록한 전설적인 트레이더 '워뇨띠'의 체결 로그 600MB 전수 분석 데이터와 매매 행동 패턴을 모델링한 **실시간 퀀트 인텔리전스 터미널**입니다.

복잡한 보조지표 대신 워뇨띠의 실제 매매 핵심 철학인 **[거래량 흡수(Volume Absorption) + 캔들 해석 + 리스크 관리 한도]**를 수식화하여, 매 10초마다 실시간 시장을 진단하고 명쾌한 포지션 가이드를 제공합니다.

🔗 **라이브 웹 터미널**: [https://wonyo-ai.vercel.app](https://wonyo-ai.vercel.app)

---

## 🎯 핵심 기능 (Key Features)

### 1. 👑 상단 마스터 이그제큐티브 패널 (0.5초 직관성)
* **패널 1: "지금 워뇨띠라면?" (BUY / SELL / HOLD 3-Way Selector)**
  * 오더플로우 거래량 흡수율과 외부 거시 지표를 종합하여 **매수(BUY), 매도(SELL), 관망(HOLD)**을 네온 컬러와 함께 0.5초 만에 판단.
  * 거래량이 터지기 전 무리한 뇌동매매를 방지하는 실전 플레이북 가이드 제시.
* **패널 2: "만약 들어갔다면?" (가상 포지션 & 손익 모니터링)**
  * 진입 방향(LONG/SHORT), 3단 래더 분할 진입가, 계약 규모(USD), 동적 켈리 레버리지 계산.
  * 실시간 미실현 손익(PnL) 및 목표가(익절 16.35분 기준) / 손절가 / 60분 스크래치 조기 탈출 타이머 추적.

### 2. 📊 초고속 TradingView 캔들 & 오더플로우 차트
* TradingView Lightweight Charts 기반 120개 실시간 캔들 및 거래량 히스토그램 렌더링.
* 고래의 급격한 매도 흡수(Bullish Absorption) 및 매수 흡수(Bearish Absorption) 마커 실시간 차트 오버레이.
* 5분봉(5m), 15분봉(15m), 1시간봉(1h) 타임프레임 전환 지원.

### 3. 🛡️ 워뇨띠 4대 현실적 리스크 가드 (Risk Matrix)
1. **거래량 고갈 & 호가 흡수율 (Alpha Signal)**: 볼륨 Z-Score 및 호가창 체결 흡수 강도.
2. **마이크로스트럭처 리스크 (Microstructure Risk)**: Amihud 비유동성 지수 및 호가 스프레드 슬리피지 방어.
3. **시장 레짐 & 변동성 쇼크 (Regime Risk)**: 파킨슨 실현 변동성 및 카우프만 추세 효율비(ER).
4. **포트폴리오 리스크 (Portfolio Risk)**: High Water Mark(HWM) 드로우다운 및 연속 손실 억제 켈리 사이징.

### 4. 📰 시장 심리 & 외신 속보 티커
* 얼터너티브(Alternative.me) 암호화폐 공포·탐욕 지수(Fear & Greed Index) 실시간 연동.
* 코인텔레그래프 등 주요 외신 RSS 피드 실시간 수신 및 **호재 / 악재 / 속보** 감성 분류 (3.5초 롤링 티커).

### 5. ⚡ 10초 무중단 백그라운드 자동 갱신
* 브라우저 새로고침(F5) 없이 10초마다 백그라운드 폴링 스트리밍.
* 헤더에 초록 펄스 램프(`LIVE`) 및 실시간 갱신 타임스탬프(`• 갱신 HH:MM:SS`) 제공.

---

## 🧠 워뇨띠 팩트 레퍼런스 (Quantitative Facts)

비트맥스(BitMEX) 원본 체결 데이터 전수 분석을 통해 확인된 실거래 파라미터가 시스템에 반영되어 있습니다:

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
* **패키지 & 가상환경 관리**: [`uv`](https://github.com/astral-sh/uv) (초고속 Rust 기반 패키지 매니저)
* **백엔드 프레임워크**: FastAPI, Uvicorn, Pydantic
* **데이터 분석 & 퀀트**: NumPy, Pandas, DuckDB (로컬 분석용)
* **프론트엔드**: Vanilla HTML5/JS, Tailwind CSS (CDN), TradingView Lightweight Charts (v4.2.0)
* **클라우드 & 인프라**: Vercel Serverless Functions, Edge CDN, GitHub Actions

---

## 🚀 로컬 설치 및 실행 방법 (Getting Started)

### 1. 사전 요구사항
* Python 3.12 이상
* [uv](https://docs.astral.sh/uv/) 설치 권장:
  ```powershell
  powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
  ```

### 2. 저장소 복제 및 의존성 설치
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

### 4. 테스트 코드 실행
```bash
uv run pytest tests/test_web_api.py -v
```

---

## 🌐 API 엔드포인트 규격 (API Endpoints)

| 메소드 | 엔드포인트 | 파라미터 | 설명 |
| :---: | :--- | :--- | :--- |
| `GET` | `/` | - | 웹 인텔리전스 대시보드 UI |
| `GET` | `/api/predict` | `mode` (`live`/`replay`), `interval` (`5m`/`15m`/`1h`) | 실시간 워뇨띠 직감 예측 및 리스크 진단 JSON |
| `GET` | `/api/candles` | `mode`, `interval`, `limit` (기본 120) | 실시간/리플레이 캔들스틱 및 거래량 히스토그램 데이터 |

---

## 📂 프로젝트 구조 (Project Structure)

```
wonyo_ai/
├── api/                   # Vercel 서버리스 진입점 (Serverless Functions)
│   ├── predict.py         # /api/predict 핸들러
│   └── candles.py         # /api/candles 핸들러
├── public/                # Vercel 정적 호스팅 자산 (Edge CDN)
│   └── index.html         # 프로덕션 프론트엔드 터미널
├── src/                   # 백엔드 코어 소스코드
│   ├── static/index.html  # 로컬 개발용 대시보드 템플릿
│   ├── web_api.py         # FastAPI 메인 웹 애플리케이션
│   ├── service_engine.py  # 실시간 워뇨띠 신호 및 래더 주문 생성 엔진
│   ├── risk_gate.py       # 4대 리스크 인풋 벡터 계산 모듈
│   └── wonyo_layer.py     # 볼륨 흡수 및 워뇨띠 매매 행동 모델
├── tests/                 # 자동화 단위/통합 테스트
│   └── test_web_api.py    # API 엔드포인트 및 서버리스 핸들러 테스트
├── pyproject.toml         # 프로젝트 메타데이터 및 의존성 정의
├── requirements.txt       # Vercel 배포용 경량 런타임 의존성
├── vercel.json            # Vercel 라우팅 및 빌드 설정
└── README.md              # 프로젝트 안내 문서
```

---

## ⚠️ 면책 조항 (Disclaimer)

* 본 프로젝트는 전설적인 트레이더 워뇨띠의 과거 공개 거래 데이터와 매매 패턴을 학술적·통계적으로 모델링한 오픈소스 퀀트 리서치 도구입니다.
* 제공되는 모든 예측, 시그널 및 가상 포지션은 **투자 권유나 금융 자문이 아니며**, 실제 매매의 최종 책임은 전적으로 사용자 본인에게 있습니다.
