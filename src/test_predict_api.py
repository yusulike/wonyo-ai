import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.web_api import get_prediction

def test_api():
    print("Calling get_prediction(mode='live', interval='15m')...")
    res = get_prediction(mode="live", interval="15m", sensitivity="standard")
    
    assert "intuitive_verdict" in res, "intuitive_verdict missing"
    verdict = res["intuitive_verdict"]
    news_factor = verdict.get("news_factor", {})
    
    print("\n=== PREDICT RESPONSE VERIFICATION ===")
    print(f"Action: {res.get('action')} @ {res.get('limit_price')}")
    print(f"Verdict: {verdict.get('verdict_badge')}")
    print(f"Composite Score: {verdict.get('composite_score')}")
    print(f"News Engine: {news_factor.get('engine')}")
    print(f"News Confidence: {news_factor.get('avg_confidence')}")
    print(f"Black Swan Risk: {news_factor.get('black_swan_risk')}")
    print(f"Overall Market Bias: {news_factor.get('overall_market_bias')}")
    print(f"Fear & Greed: {news_factor.get('fear_greed_score')} ({news_factor.get('fear_greed_label')})")
    print(f"Top Headlines Count: {len(news_factor.get('top_headlines', []))}")
    
    assert news_factor.get("engine") == "TypeSafe Jev System One", f"Unexpected engine: {news_factor.get('engine')}"
    print("\n[SUCCESS] TypeSafe Jev System One is fully integrated and operational in get_prediction()!")

if __name__ == "__main__":
    test_api()
