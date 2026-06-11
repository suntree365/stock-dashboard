import os
import json
import xml.etree.ElementTree as ET
import urllib.request
import re
from datetime import datetime, timedelta  # 9시간 시차 보정을 위한 timedelta 수식 추가 완료
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
    leaders = []
    urls = [
        "https://finance.naver.com/sise/sise_quant.naver?sosok=0",
        "https://finance.naver.com/sise/sise_quant.naver?sosok=1"
    ]
    
    for url in urls:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            html = urllib.request.urlopen(req).read().decode('cp949', errors='ignore')
            rows = re.findall(r'<tr.*?>.*?</tr>', html, re.DOTALL)
            
            for row in rows:
                if 'tltle' not in row:
                    continue
                try:
                    name = re.search(r'class="tltle">(.*?)</a>', row).group(1)
                    tds = re.findall(r'<td class="number".*?>(.*?)</td>', row, re.DOTALL)
                    if len(tds) >= 4:
                        ratio_str = re.sub(r'<.*?>', '', tds[2]).strip().replace('%', '')
                        ratio = float(ratio_str)
                        
                        amount_str = re.sub(r'<.*?>', '', tds[4]).strip().replace(',', '')
                        amount_val = float(amount_str)
                        
                        # 상승률 15% 이상 AND 거래대금 2,000억 이상 엄격 필터링
                        if ratio >= 15.0 and amount_val >= 200000:
                            leaders.append({
                                "name": name,
                                "ratio": round(ratio, 2),
                                "amount": f"{int
