"""
Wonyo-Quant News & SNS Sentiment Pipeline
Implements Wonyotti's '주목도(Attention)' and external sentiment analysis:
- Live Alternative.me Fear & Greed Index
- CoinTelegraph & Google News RSS headlines parser
- TypeSafe Jev System One Model with calibrated probabilities & confidence
- Lexicon-based Crypto Sentiment Analyzer (Robust Fallback)
"""

import os
import time
import requests
import xml.etree.ElementTree as ET
from typing import Dict, Any, List, Optional

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

try:
    from typesafe_sdk import TypeSafeClient, Choice, Score, Noul
    TYPESAFE_AVAILABLE = True
except ImportError:
    TYPESAFE_AVAILABLE = False

# Crypto Financial Sentiment Lexicon (Fallback)
BULLISH_KEYWORDS = {
    "surge": 2.0, "soar": 2.0, "rally": 1.8, "bull": 1.5, "jump": 1.4, "high": 1.2,
    "gain": 1.2, "breakout": 1.8, "accumulate": 1.5, "etf": 1.2, "inflow": 1.5,
    "record": 1.3, "support": 1.0, "bounce": 1.4, "upgrade": 1.2, "adoption": 1.4,
    "blackrock": 1.1, "institutional": 1.2, "rebound": 1.3, "soars": 2.0, "soaring": 2.0
}

BEARISH_KEYWORDS = {
    "crash": -2.2, "dump": -2.0, "plunge": -2.0, "drop": -1.3, "fall": -1.2,
    "bear": -1.5, "loss": -1.2, "low": -1.1, "ban": -2.0, "sec": -1.3, "lawsuit": -1.8,
    "hack": -2.5, "fraud": -2.5, "liquidation": -1.8, "selloff": -1.8, "slump": -1.5,
    "panic": -2.0, "scam": -2.5, "probe": -1.5, "crackdown": -1.8, "bankrupt": -2.5
}

class WonyoNewsSentimentEngine:
    def __init__(self, cache_ttl_sec: int = 180): # Cache for 3 minutes
        self.cache_ttl = cache_ttl_sec
        self.last_fetch_time = 0.0
        self.cached_result: Dict[str, Any] = {}

    def fetch_fear_and_greed(self) -> Dict[str, Any]:
        """Fetch Alternative.me Fear & Greed Index."""
        try:
            r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=4)
            if r.status_code == 200:
                data = r.json().get("data", [{}])[0]
                return {
                    "score": int(data.get("value", 50)),
                    "label": data.get("value_classification", "Neutral")
                }
        except Exception as e:
            print(f"Fear & Greed fetch error: {e}")
        return {"score": 50, "label": "Neutral"}

    def fetch_breaking_news(self) -> List[Dict[str, Any]]:
        """Fetch live breaking headlines from CoinTelegraph and Google News RSS."""
        headlines = []
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

        # 1. CoinTelegraph RSS
        try:
            r = requests.get("https://cointelegraph.com/rss", headers=headers, timeout=4)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:15]:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    pub_elem = item.find("pubDate")
                    if title_elem is not None and title_elem.text:
                        headlines.append({
                            "title": title_elem.text.strip(),
                            "link": link_elem.text.strip() if link_elem is not None else "",
                            "source": "CoinTelegraph",
                            "pubDate": pub_elem.text.strip() if pub_elem is not None else ""
                        })
        except Exception as e:
            print(f"CoinTelegraph RSS error: {e}")

        # 2. Google News RSS for Bitcoin
        try:
            r = requests.get("https://news.google.com/rss/search?q=Bitcoin+crypto+when:1d&hl=en-US&gl=US&ceid=US:en", headers=headers, timeout=4)
            if r.status_code == 200:
                root = ET.fromstring(r.content)
                for item in root.findall(".//item")[:10]:
                    title_elem = item.find("title")
                    link_elem = item.find("link")
                    if title_elem is not None and title_elem.text:
                        headlines.append({
                            "title": title_elem.text.strip(),
                            "link": link_elem.text.strip() if link_elem is not None else "",
                            "source": "Google News",
                            "pubDate": ""
                        })
        except Exception as e:
            print(f"Google News RSS error: {e}")

        return headlines

    def analyze_sentiment(self, text: str) -> float:
        """Analyzes sentiment polarity of a single headline (-1.0 to +1.0) using lexicon."""
        lower = text.lower()
        score = 0.0
        words = lower.split()

        for w in words:
            clean_w = "".join(c for c in w if c.isalnum())
            if clean_w in BULLISH_KEYWORDS:
                score += BULLISH_KEYWORDS[clean_w]
            elif clean_w in BEARISH_KEYWORDS:
                score += BEARISH_KEYWORDS[clean_w]

        return max(-1.0, min(1.0, score / 3.0))

    def analyze_with_jev(self, news_items: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Uses TypeSafe Jev System One model to evaluate news headlines with calibrated probabilities.
        Returns a dict of analyzed headlines and aggregate metrics, or None if evaluation fails.
        """
        api_key = os.getenv("TYPESAFE_API_KEY")
        if not TYPESAFE_AVAILABLE or not api_key:
            return None

        # Take top 6 breaking headlines for low latency and high relevance
        items_to_eval = news_items[:6]
        if not items_to_eval:
            return None

        state = {
            "market": "Bitcoin & Crypto Derivatives Market",
            "headlines": [{"id": i, "title": it["title"], "source": it["source"]} for i, it in enumerate(items_to_eval)]
        }

        questions = {}
        for i in range(len(items_to_eval)):
            questions[f"impact_{i}"] = Choice(
                instructions=f"What is the immediate Bitcoin market price impact of headline `headlines[{i}].title`?",
                criteria={
                    "bullish": "Positive catalyst, accumulation, institutional inflow, ETF adoption, or legal win",
                    "bearish": "Negative catalyst, selloff, liquidation, outflow, regulatory penalty, or hack",
                    "neutral": "Routine updates, opinion, or negligible price impact"
                }
            )
            questions[f"score_{i}"] = Score(
                instructions=f"Rate the impact intensity of headline `headlines[{i}].title` on Bitcoin price action.",
                criteria=[
                    "Strong Bearish (-2.0)",
                    "Mild Bearish (-1.0)",
                    "Neutral (0.0)",
                    "Mild Bullish (+1.0)",
                    "Strong Bullish (+2.0)"
                ]
            )

        questions["overall_bias"] = Choice(
            instructions="Considering all `headlines`, what is the overall market sentiment for crypto?",
            criteria={
                "bullish": "Positive momentum and risk-on sentiment dominates",
                "bearish": "Negative sentiment, FUD, or risk-off dominates",
                "neutral": "Mixed, balanced, or indecisive news flow"
            }
        )
        questions["black_swan"] = Noul(
            instructions="Do any of the headlines indicate a severe black swan event (e.g. exchange insolvency, emergency ban, or systemic collapse)?"
        )

        try:
            with TypeSafeClient(timeout=8.0) as client:
                res = client.system_one(state=state, questions=questions)

            analyzed = []
            total_sentiment = 0.0
            confidences = []

            for i, it in enumerate(items_to_eval):
                imp = res.choices[f"impact_{i}"]
                sc = res.scores[f"score_{i}"]
                confidences.append(imp.confidence)
                
                # Convert Score (0.0 ~ 4.0) to [-1.0, 1.0] range
                norm_score = max(-1.0, min(1.0, (sc.score - 2.0) / 2.0))
                
                # Align direction with choice
                if imp.choice == "bullish" and norm_score < 0.1:
                    norm_score = max(0.25, norm_score)
                elif imp.choice == "bearish" and norm_score > -0.1:
                    norm_score = min(-0.25, norm_score)
                elif imp.choice == "neutral":
                    norm_score = norm_score * 0.5

                total_sentiment += norm_score
                analyzed.append({
                    "title": it["title"],
                    "source": it["source"],
                    "link": it.get("link", ""),
                    "sentiment_score": round(norm_score, 2),
                    "impact": imp.choice,
                    "confidence": round(imp.confidence, 2),
                    "is_bullish": imp.choice == "bullish" or norm_score > 0.15,
                    "is_bearish": imp.choice == "bearish" or norm_score < -0.15
                })

            avg_sent = total_sentiment / len(items_to_eval) if items_to_eval else 0.0
            avg_conf = sum(confidences) / len(confidences) if confidences else 0.0
            black_swan_prob = float(res.nouls["black_swan"].noul)
            overall_bias = res.choices["overall_bias"].choice

            return {
                "analyzed_headlines": analyzed,
                "avg_sentiment": avg_sent,
                "avg_confidence": round(avg_conf, 2),
                "black_swan_risk": round(black_swan_prob, 3),
                "overall_market_bias": overall_bias,
                "engine": "TypeSafe Jev System One"
            }
        except Exception as e:
            print(f"[WonyoNewsSentimentEngine] TypeSafe Jev evaluation failed ({e}), falling back to lexicon.")
            return None

    def get_market_sentiment(self) -> Dict[str, Any]:
        """Returns synthesized News + SNS Attention metrics with caching."""
        now = time.time()
        if self.cached_result and (now - self.last_fetch_time < self.cache_ttl):
            return self.cached_result

        fng = self.fetch_fear_and_greed()
        news_items = self.fetch_breaking_news()

        # Try Jev System One evaluation first
        jev_res = self.analyze_with_jev(news_items)
        if jev_res is not None:
            analyzed_headlines = jev_res["analyzed_headlines"]
            avg_sentiment = jev_res["avg_sentiment"]
            engine_name = jev_res["engine"]
            black_swan_risk = jev_res["black_swan_risk"]
            overall_bias = jev_res["overall_market_bias"]
            avg_confidence = jev_res["avg_confidence"]
        else:
            # Fallback to keyword lexicon
            engine_name = "Keyword Lexicon (Fallback)"
            black_swan_risk = 0.0
            overall_bias = "neutral"
            avg_confidence = 0.50
            total_sentiment = 0.0
            analyzed_headlines = []
            for item in news_items:
                sent_val = self.analyze_sentiment(item["title"])
                total_sentiment += sent_val
                analyzed_headlines.append({
                    "title": item["title"],
                    "source": item["source"],
                    "link": item["link"],
                    "sentiment_score": round(sent_val, 2),
                    "impact": "bullish" if sent_val > 0.1 else ("bearish" if sent_val < -0.1 else "neutral"),
                    "confidence": 0.60,
                    "is_bullish": sent_val > 0.1,
                    "is_bearish": sent_val < -0.1
                })
            avg_sentiment = (total_sentiment / len(news_items)) if news_items else 0.0

        # Wonyotti's '주목도(Attention)' Level:
        # High attention if volume of breaking headlines is large and Fear & Greed is extreme
        fng_score = fng["score"]
        attention_score = min(100, int(len(news_items) * 2.5 + abs(fng_score - 50) * 1.0))

        if attention_score >= 70:
            attention_level = "VERY_HIGH (시장 주목도 극대화)"
        elif attention_score >= 45:
            attention_level = "MODERATE (일반적인 관심도)"
        else:
            attention_level = "LOW (대중 관심 소강/침체)"

        # Composite External News Score (-100 to +100)
        # 50% Fear & Greed (-50 to +50) + 50% News Headlines (-50 to +50)
        fng_normalized = (fng_score - 50) # -50 to +50
        news_normalized = avg_sentiment * 50 # -50 to +50
        composite_news_score = int(fng_normalized * 0.5 + news_normalized * 0.5)

        # Black Swan Penalty: If black swan risk is detected (> 40%), severely penalize news score
        if black_swan_risk >= 0.40:
            composite_news_score = min(composite_news_score, -50)
            sentiment_badge = "🚨 블랙스완 리스크 감지 (CRITICAL RISK)"
            sentiment_desc = f"Jev System One이 시스템적 리스크(블랙스완 확률 {black_swan_risk:.1%})를 감지했습니다. 긴급 리스크 관리가 필요합니다."
        elif composite_news_score >= 20:
            sentiment_badge = "🔥 호재 및 탐욕 우세 (BULLISH)"
            sentiment_desc = f"뉴스 헤드라인의 긍정 톤이 우세하며, 공포탐욕지수({fng_score}pt {fng['label']})가 투자 심리를 견인하고 있습니다."
        elif composite_news_score <= -20:
            sentiment_badge = "❄️ 악재 및 공포 우세 (BEARISH)"
            sentiment_desc = f"규제/매도 관련 악재 헤드라인이 증가하고 공포탐욕지수({fng_score}pt)가 하락 심리를 자극하고 있습니다."
        else:
            sentiment_badge = "⚖️ 뉴스/심리 중립 (NEUTRAL)"
            sentiment_desc = f"공포탐욕지수({fng_score}pt)와 최근 뉴스 흐름이 중립적인 균형을 이루고 있습니다."

        result = {
            "engine": engine_name,
            "fear_and_greed": fng,
            "headline_count": len(news_items),
            "avg_news_sentiment": round(avg_sentiment, 2),
            "avg_confidence": avg_confidence,
            "black_swan_risk": black_swan_risk,
            "overall_market_bias": overall_bias,
            "composite_news_score": composite_news_score, # -100 to +100
            "sentiment_badge": sentiment_badge,
            "sentiment_desc": sentiment_desc,
            "attention_level": attention_level,
            "attention_score": attention_score,
            "top_headlines": analyzed_headlines[:6]
        }

        self.cached_result = result
        self.last_fetch_time = now
        return result

# Singleton instance
news_engine = WonyoNewsSentimentEngine()

if __name__ == "__main__":
    res = news_engine.get_market_sentiment()
    print("=== LIVE NEWS & SNS SENTIMENT ===")
    print(f"Engine: {res['engine']}")
    print(f"Fear & Greed: {res['fear_and_greed']['score']} ({res['fear_and_greed']['label']})")
    print(f"Composite News Score: {res['composite_news_score']} pt")
    print(f"Black Swan Risk: {res['black_swan_risk']:.1%}")
    print(f"Average Confidence: {res['avg_confidence']:.2f}")
    print(f"Attention Level: {res['attention_level']}")
    print("\nTop Headlines:")
    for h in res['top_headlines'][:4]:
        safe_title = h['title'].encode('ascii', 'ignore').decode('ascii')
        conf_str = f" [conf: {h.get('confidence', 0):.2f}]" if 'confidence' in h else ""
        print(f"[{'+' if h['sentiment_score'] > 0 else ''}{h['sentiment_score']} | {h.get('impact', 'N/A').upper()}{conf_str}] ({h['source']}) {safe_title}")
