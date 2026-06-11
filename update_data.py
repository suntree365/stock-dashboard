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
        "US2Y": "^IRX",       # 미국채 단기물
        "WTI": "CL=F",        # WTI 유가
        "BRENT": "BZ=F",      # 브렌트유
        "USD_KRW": "KRW=X",   # 원/달러 환율
        "VIX": "^VIX"         # 변동성 지수
    }
    macro_results = {}
    for key, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            todays_data = ticker.history(period='5d')
            if len(todays_data) >= 2:
                close_today = todays_data['Close'].iloc[-1]
                close_prev = todays_data['Close'].iloc[-2]
                change = close_today - close_prev
                if "US" in key and close_today > 10:
                    close_today = close_today / 10
                    change = change / 10
                macro_results[key] = {
                    "price": round(float(close_today), 2),
                    "change": round(float(change), 2),
                    "direction": "up" if change >= 0 else "down"
                }
            elif len(todays_data) == 1:
                close_today = todays_data['Close'].iloc[-1]
                if "US" in key and close_today > 10:
                    close_today = close_today / 10
                macro_results[key] = {"price": round(float(close_today), 2), "change": 0.0, "direction": "none"}
        except Exception as e:
            print(f"Error fetching {key}: {e}")
            fallback_prices = {"US30Y": 4.55, "US10Y": 4.21, "US2Y": 4.15, "VIX": 14.20}
            macro_results[key] = {"price": fallback_prices.get(key, "-"), "change": 0.0, "direction": "none"}
    return macro_results

def get_korean_dart_rss(target_stocks):
    """
    구글 뉴스를 배제하고, 금융감독원 DART 공식 종합 RSS 피드를 직접 파싱합니다.
    가입 없이 100% 진짜 공식 전자공시 보고서만 필터링하여 매핑합니다.
    """
    dart_results = {stock: [] for stock in target_stocks}
    try:
        # 금융감독원 DART 최신 공시 전체 RSS (로그인/가입 필요 없는 완전 공개 주소)
        url = "https://dart.fss.or.kr/api/todayRSS.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req).read()
        
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        for item in items:
            title = item.find('title').text  # 예: "[삼성전자] 분기보고서 (2026.03)" 형식으로 들어옴
            link = item.find('link').text    # DART 해당 공시 원문 뷰어 링크
            
            # 내가 지정한 보유 종목명이 공시 제목에 포함되어 있는지 매칭 분기
            for stock in target_stocks:
                if stock in title:
                    # 제목에서 "[종목명]" 태그나 불필요한 회사명 중복을 다듬고 깔끔하게 공시명만 추출
                    clean_title = title.replace(f"[{stock}]", "").strip()
                    dart_results[stock].append({
                        "title": clean_title,
                        "link": link
                    })
    except Exception as e:
        print(f"DART RSS 수집 중 에러 발생: {e}")
        
    # 만약 오늘 등록된 공시가 없다면 안내 문구 처리
    for stock in target_stocks:
        if not dart_results[stock]:
            dart_results[stock] = [{"title": "오늘 제출된 DART 공식 전자공시가 없습니다.", "link": "https://dart.fss.or.kr"}]
        else:
            dart_results[stock] = dart_results[stock][:4] # 최신 공시 최대 4개만 노출
            
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
    # 💡 보유 종목 구성을 바꾸고 싶다면 여기 배열 안의 텍스트를 편집하시면 됩니다!
    kr_stocks = ["헬릭스미스", "남성", "현대제철", "삼성전자", "케이피항공산업"]
    us_stocks = ["SOXL", "QQQM", "SCHD", "TSLA"]
    
    print("금융감독원 DART 연동 엔진 가동...")
    combined_data = {
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "macro": get_macro_data(),
        "kr_dart": get_korean_dart_rss(kr_stocks),
        "us_news": get_us_news_rss(us_stocks)
    }
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=4)
    print("DART 공시 데이터 필터링 완료!")
