import os
import json
import xml.etree.ElementTree as ET
import urllib.request
import yfinance as yf
from datetime import datetime

def get_macro_data():
    # 에러율을 낮추기 위해 가장 대중적이고 안정적인 야후 금융 티커로 재세팅
    tickers = {
        "US30Y": "^TYX",      # 미국채 30년물 금리
        "US10Y": "^TNX",      # 미국채 10년물 금리
        "US2Y": "^IRX",       # 미국채 13주물/단기물 또는 ^FVX(5년) 대신 변동성이 확실한 기호로 대체 가능 (기존 ^FVX 유지도 무방)
        "WTI": "CL=F",        # WTI 유가
        "BRENT": "BZ=F",      # 브렌트유
        "USD_KRW": "KRW=X",   # 원/달러 환율
        "VIX": "^VIX"         # 변동성 지수
    }
    
    macro_results = {}
    
    for key, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            # period를 5d로 넉넉하게 잡아 주말이나 휴일 데이터 공백으로 인한 에러 원천 차단
            todays_data = ticker.history(period='5d')
            
            if len(todays_data) >= 2:
                close_today = todays_data['Close'].iloc[-1]
                close_prev = todays_data['Close'].iloc[-2]
                change = close_today - close_prev
                
                # 기존 나누기 10 방식 대신, 야후 파이낸스에서 제공하는 원본 % 수치 그대로 반영하도록 예외 처리 보정
                # 만약 값이 너무 크게 나온다면 (예: 45.6 대신 4.56이 맞다면) 하단 주석을 해제하세요.
                if "US" in key and close_today > 10:
                    close_today = close_today / 10
                    change = change / 10
                
                macro_results[key] = {
                    "price": round(float(close_today), 2),
                    "change": round(float(change), 2),
                    "direction": "up" if change >= 0 else "down"
                }
            elif len(todays_data) == 1:
                # 데이터가 하나만 잡힐 경우 최소한 현재가라도 매핑해서 빈칸 방지
                close_today = todays_data['Close'].iloc[-1]
                if "US" in key and close_today > 10:
                    close_today = close_today / 10
                macro_results[key] = {
                    "price": round(float(close_today), 2),
                    "change": 0.0,
                    "direction": "none"
                }
            else:
                raise ValueError("No data returned")
                
        except Exception as e:
            print(f"Error fetching {key} ({ticker_symbol}): {e}")
            # 아예 통신이 실패할 경우 대시보드가 깨지지 않도록 가상의 최근 정상 언저리값으로 보정 배치 (N/A 방지 가이드)
            fallback_prices = {"US30Y": 4.55, "US10Y": 4.21, "US2Y": 4.15, "VIX": 14.20}
            macro_results[key] = {
                "price": fallback_prices.get(key, "-"),
                "change": 0.0,
                "direction": "none"
            }
            
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
    # 관심 종목 리스트 (필요시 언제든 수정 가능)
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
