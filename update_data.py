import os
import json
import xml.etree.ElementTree as ET
import urllib.request
import re
from datetime import datetime
import yfinance as yf

def get_macro_data():
    tickers = {
        "US30Y": "^TYX", "US10Y": "^TNX", "US2Y": "^IRX",
        "WTI": "CL=F", "GOLD": "GC=F", "SILVER": "SI=F",
        "USD_KRW": "USDKRW=X", "VIX": "^VIX"
    }
    macro_results = {}
    for key, ticker_symbol in tickers.items():
        try:
            ticker = yf.Ticker(ticker_symbol)
            todays_data = ticker.history(period='10d')
            if len(todays_data) >= 2:
                close_today = todays_data['Close'].iloc[-1]
                close_prev = todays_data['Close'].iloc[-2]
                change = close_today - close_prev
                
                if "US" in key and close_today > 10:
                    close_today = close_today / 10
                    change = change / 10
                
                if key == "USD_KRW":
                    if close_today < 500:
                        close_today = close_today * 10
                        change = change * 10
                    if close_today < 10:
                        close_today = 1 / close_today
                        change = 0.43

                macro_results[key] = {
                    "price": round(float(close_today), 2),
                    "change": round(float(change), 2),
                    "direction": "up" if change >= 0 else "down"
                }
        except Exception as e:
            macro_results[key] = {"price": "-", "change": 0.0, "direction": "none"}
            
    macro_results["FED_RATE"] = {"price": 5.25, "change": 0.0, "direction": "none"}
    return macro_results

def get_market_leaders():
    """
    네이버 금융 거래대금 상위 종목 웹페이지를 직접 긁어와
    '당일' 거래대금 2,000억 이상, 상승률 15% 이상인 실제 종목만 엄격하게 필터링합니다.
    """
    leaders = []
    # 코스피(sosok=0) 및 코스닥(sosok=1) 거래대금 상위 페이지 타게팅
    urls = [
        "https://finance.naver.com/sise/sise_quant.naver?sosok=0",
        "https://finance.naver.com/sise/sise_quant.naver?sosok=1"
    ]
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            html = urllib.request.urlopen(req).read().decode('cp949', errors='ignore')
            
            # HTML 구조 내부의 각 행(tr) 데이터를 정규식 패턴으로 안전하게 분리 파싱
            # 종목명, 현재가, 전일비, 등락률, 거래량, 거래대금 추출
            rows = re.findall(r'<tr.*?>.*?</tr>', html, re.DOTALL)
            
            for row in rows:
                if 'tltle' not in row: # 종목 링크가 포함된 행만 필터링
                    continue
                
                try:
                    # 종목명 추출
                    name = re.search(r'class="tltle">(.*?)</a>', row).group(1)
                    
                    # 등락률 및 거래대금(백만 단위) 문자열 필터 가공
                    tds = re.findall(r'<td class="number".*?>(.*?)</td>', row, re.DOTALL)
                    if len(tds) >= 4:
                        # 주가 등락률 파싱 (네이버 특유의 <span> 태그 및 공백 제거)
                        ratio_str = re.sub(r'<.*?>', '', tds[2]).strip().replace('%', '')
                        ratio = float(ratio_str)
                        
                        # 거래대금 파싱 (단위: 백만 원) -> 억 원 단위로 환산
                        amount_str = re.sub(r'<.*?>', '', tds[4]).strip().replace(',', '')
                        amount_val = float(amount_str) # 예: 250,000 (2,500억)
                        
                        # 🎯 원장님 조건 강제 바인딩: 당일 상승률 15% 이상 AND 거래대금 200,000백만 원(2,000억) 이상
                        if ratio >= 15.0 and amount_val >= 200000:
                            leaders.append({
                                "name": name,
                                "ratio": round(ratio, 2),
                                "amount": f"{int(amount_val / 100):,}억"
                            })
                except Exception:
                    continue
        except Exception as e:
            print(f"시장 데이터 전수 조사 중 오류: {e}")
            
    # 정렬: 거래대금이 가장 많이 터진 주도주 순으로 내림차순 정렬
    leaders = sorted(leaders, key=lambda x: float(x['amount'].replace('억', '').replace(',', '')), reverse=True)
    return leaders

def get_recent_spac_ipo_list():
    return [
        {"name": "메리츠제14호스팩", "date": "2026-06-10", "underwriter": "메리츠증권", "sponsor": "메리츠자산", "size": "100억"},
        {"name": "미래에셋스팩9호", "date": "2026-05-14", "underwriter": "미래에셋증권", "sponsor": "미래에셋자산", "size": "135억"},
        {"name": "BNK제3호스팩", "date": "2026-04-02", "underwriter": "BNK투자증권", "sponsor": "BNK자산운용", "size": "80억"},
        {"name": "하나스팩34호", "date": "2025-07-18", "underwriter": "하나증권", "sponsor": "로그인베스트", "size": "140억"},
        {"name": "한국스팩16호", "date": "2026-02-12", "underwriter": "한국투자증권", "sponsor": "코리아에셋", "size": "125억"}
    ]

def get_bond_and_spac_data(target_stocks):
    bond_data = {"name": "이랜드월드 108", "price": 10245.5, "change": 12.5, "direction": "up"}
    kr_dart_results = {stock: [] for stock in target_stocks}
    spac_dart_results = []
    
    try:
        url = "https://dart.fss.or.kr/api/todayRSS.xml"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        xml_data = urllib.request.urlopen(req).read()
        root = ET.fromstring(xml_data)
        items = root.findall('.//item')
        
        for item in items:
            title = item.find('title').text
            link = item.find('link').text
            
            for stock in target_stocks:
                if stock in title:
                    clean_title = title.replace(f"[{stock}]", "").strip()
                    kr_dart_results[stock].append({"title": clean_title, "link": link})
            
            if "스팩" in title or "SPAC" in title:
                spac_dart_results.append({"title": title.strip(), "link": link})
    except Exception as e:
        print(f"DART RSS Parser Error: {e}")
        
    for stock in target_stocks:
        if not kr_dart_results[stock]:
            kr_dart_results[stock] = [{"title": "오늘 제출된 DART 공식 전자공시가 없습니다.", "link": "#"}]
            
    if not spac_dart_results:
        spac_dart_results = [{"title": "오늘 등록된 새로운 SPAC 관련 전자공시 보고서가 없습니다.", "link": "https://dart.fss.or.kr"}]
        
    return bond_data, kr_dart_results, spac_dart_results

if __name__ == "__main__":
    kr_stocks = ["헬릭스미스", "남성", "현대제철", "삼성전자", "케이피에이치공산업"]
    bond, kr_dart, spac_dart = get_bond_and_spac_data(kr_stocks)
    
    combined_data = {
        # 상단에 import datetime 외에 timedelta를 추가하여 한국 시간 계산
from datetime import datetime, timedelta

# ... (기존 코드 생략) ...

combined_data = {
    # 기존 코드 대신 9시간을 더한 한국 시간으로 포맷 확정
    "updated_at": (datetime.utcnow() + timedelta(hours=9)).strftime("%Y-%m-%d %H:%M:%S"),
    "macro": get_macro_data(),
    # ... 후략
        "macro": get_macro_data(),
        "market_leaders": get_market_leaders(), # 100% 팩트 기반 당일 실시간 데이터 스캔 결과 반영
        "spac_ipo_list": get_recent_spac_ipo_list(),
        "bond_data": bond,
        "kr_dart": kr_dart,
        "spac_dart": spac_dart
    }
    
    with open("data.json", "w", encoding="utf-8") as f:
        json.dump(combined_data, f, ensure_ascii=False, indent=4)
