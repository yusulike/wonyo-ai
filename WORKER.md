# 🤖 24시간 상시 워커 (Personal Server Worker)

Vercel 대시보드는 페이지가 열려있을 때만 동작합니다(브라우저의 10초 폴밍이 유일한 심장).
이 워커는 개인 리눅스 서버에서 **24시간** 같은 엔진을 구동해, 페이지를 닫아도 가상 포지션이
진입·익절·손절되고 체결 장부에 자동 기록되게 합니다.

## 아키텍처 (하이브리드)

```
[개인 서버: src/worker.py 10초 루프]          [Vercel: wonyo-ai.vercel.app]
 ① Binance 실시간 가격/캔들 수집                대시보드 (얼굴)
 ② 워뇨 모델 진입 판단 (15m 봉 마감 시)  ──┐         │
 ③ 포지션 수명 관리                        │    장부 조회 GET /api/trades
    SL → TP → 60분 스크래치 → 120분 타임아웃 │         ▼
 ④ 체결 기록 ─────────────────────────────┴──▶ Neon Postgres (공유 장부)
```

- 개인 서버는 **아웃바운드 연결만** 사용 (포트 개방/역방향 프록시 불필요)
- `POSTGRES_URL`(Neon)이 있으면 대시보드와 같은 장부에 기록, 없으면 로컬 SQLite 폴백
- 워커 상태(계좌·오픈 포지션)는 `data/worker_state.json`에 저장되어 재시작 시 이어서 운용

## 설치 (Linux + systemd)

```bash
# 1. 서버에 클론 & 의존성 설치
git clone https://github.com/yusulike/wonyo-ai.git /opt/wonyo-ai
cd /opt/wonyo-ai
uv sync

# 2. 연결 문자열 준비: Vercel 대시보드 -> Storage(Neon) -> Connect -> URI 복사

# 3. systemd 서비스 등록
sudo cp deploy/wonyo-worker.service /etc/systemd/system/
sudo nano /etc/systemd/system/wonyo-worker.service
#   - User / WorkingDirectory 를 실제 환경으로 수정
#   - Environment=POSTGRES_URL=... 에 복사한 URI 붙여넣기
sudo systemctl daemon-reload
sudo systemctl enable --now wonyo-worker

# 4. 확인
journalctl -u wonyo-worker -f
# → "[worker] started | equity=10.0000 BTC | ledger=Postgres(Neon) ..."
# 대시보드 체결 장부(실시간 탭)에 시간이 지나면 자동 기록이 쌓임
```

## 동작 규칙 (워뇨띠 상용 원칙 반영)

| 규칙 | 값 |
|---|---|
| 진입 판단 | 15분 봉 **마감 확정** 시점 (미완성 봉 미사용) |
| 손절 / 익절 | 리스크 엔진 ATR 동적 SL/TP 가격 도달 |
| 스크래치 탈출 | 60분 경과 + 손실이 -0.4% 이내 회귀 시 전량 청산 |
| 하드 타임아웃 | 120분 (실측 손절 중앙값 88분 + 버퍼) |
| 수수료 | 메이커 리베이트 -0.025% (진입+청산 양측, BTC 환산) |
| 포지션 사이징 | 프랙셔널 켈리(0.35×) + 시드 규모별 레버리지 감쇠 |

## 스모크 테스트

```bash
# 2틱만 돌고 종료 (네트워크·DB·상태파일 전체 경로 검증)
WONYO_WORKER_MAX_TICKS=2 uv run python -m src.worker
uv run pytest tests/test_worker.py -v   # 라이프사이클 단위 테스트
```
