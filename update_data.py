import os
import json
import xml.etree.ElementTree as ET
import urllib.request
import yfinance as yf
from datetime import datetime

def get_macro_data():
    tickers = {
        "US30Y": "^TYX",      # 미국채 30년물
        "US10Y": "^TNX",      # 미국채 10년물
        "US2Y": "^FVX",       # 미국채 5년물(2년 데이터 보정 대용)
        "WTI": "CL=F",        # WTI 유가
        "BRENT": "BZ=F",      # 브렌트유
        "USD_KRW": "KRW=X",   # 원/달러 환율
        "VIX": "^VIX"         # 변동성 지수
    }
    macro_results = {}
    for key, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            todays_data = ticker.history(period='2d')
            if len(todays_data) >= 2:
                close_today = todays_data['Close'].iloc[-1]
                close_prev = todays_data['Close'].iloc[-2]
                change = close_today - close_prev
                if "US" in key:
                    close_today = close_today / 10
                    change = change / 10
                macro_results[key] = {
                    "price": round(close_today, 2),
                    "change": round(change, 2),
                    "direction": "up" if change >= 0 else "down"
                }
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            macro_results[key] = {"price": "-", "change": 0.0, "direction": "none"}
    return macro_results

def get_korean_dart_rss(target_stocks):
    dart_results = {}
    for stock in target_stocks:
        try:
            enc_text = urllib.parse.quote(f"{stock} 공시")
            url = f"https://news.google.com/rss/search?q={enc_text}+when:7d&hl=ko&gl=KR&ceid=KR:ko"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req).read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            stock_news = []
            for item in items[:3]:
                title = item.find('title').text
                link = item.find('link').text
                stock_news.append({"title": title, "link": link})
            dart_results[stock] = stock_news if stock_news else [{"title": "최근 7일간 주요 공시성 뉴스가 없습니다.", "link": "#"}]
        except Exception as e:
            print(f"Error fetching DART RSS for {stock}: {e}")
            dart_results[stock] = []
    return dart_results

def get_us_news_rss(target_stocks):
    news_results = {}
    for stock in target_stocks:
        try:
            url = f"https://news.google.com/rss/search?q={stock}+stock+when:2d&hl=en-US&gl=US&ceid=US:en"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            xml_data = urllib.request.urlopen(req).read()
            root = ET.fromstring(xml_data)
            items = root.findall('.//item')
            stock_news = []
            for item in items[:4]:
                title = item.find('title').text
                link = item.find('link').text
                stock_news.append({"title": title, "link": link})
            news_results[stock] = stock_news
        except Exception as e:
            print(f"Error fetching US RSS for {stock}: {e}")
            news_results[stock] = []
    return news_results

if __name__ == "__main__":
    # 원장님의 보유 및 가치투자 관심 주식 세팅
    kr_stocks = ["SK하이닉스", "현대차", "POSCO홀딩스", "삼성전자", "가비아"]
    us_stocks = ["GOOGL", "AMZN", "NVDA", "TSLA"]
    
    print("데이터 수집 엔진 가동...")
    combined_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "macro": get_macro_data(),
        "kr_dart": get_korean_dart_rss(kr_stocks),
        "us_news": get_us_news_rss(us_stocks)
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=4)
    print("data.json 데이터 빌드 완료!")
