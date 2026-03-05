import logging
import asyncio
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)
if not logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s]: %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)

class Interval:
    in_1_minute = "1"
    in_3_minute = "3"
    in_5_minute = "5"
    in_15_minute = "15"
    in_30_minute = "30"
    in_45_minute = "45"
    in_1_hour = "1H"
    in_2_hour = "2H"
    in_3_hour = "3H"
    in_4_hour = "4H"
    in_daily = "1D"
    in_weekly = "1W"
    in_monthly = "1M"

class InvestingDatafeed:
    def __init__(self):
        self.tvc_host = None
        self.carrier = None
        self.time_val = None
        self.domain_id = "1"
        self.lang_id = "1"
        self.timezone_id = "8"
        self._loop = asyncio.new_event_loop()
        self._loop.run_until_complete(self._init_session_async())

    async def _init_session_async(self):
        url = "https://www.investing.com/commodities/gold-streaming-chart"
        logger.info("Iniciando Playwright para evadir Cloudflare y extraer tokens UDF...")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(
                    headless=True, 
                    args=["--disable-blink-features=AutomationControlled"]
                )
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                await page.goto(url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                
                html = await page.content()
                tvc_matches = re.findall(r'https://tvc[^"\']*', html)
                
                if tvc_matches:
                    tvc_url = tvc_matches[0].replace('&amp;', '&')
                    parsed = urlparse(tvc_url)
                    qs = parse_qs(parsed.query)
                    
                    self.tvc_host = f"{parsed.scheme}://{parsed.netloc}"
                    self.carrier = qs.get("carrier", [""])[0]
                    self.time_val = qs.get("time", [""])[0]
                    self.domain_id = qs.get("domain_ID", ["1"])[0]
                    self.lang_id = qs.get("lang_ID", ["1"])[0]
                    self.timezone_id = qs.get("timezone_ID", ["8"])[0]
                    logger.info("InvestingDatafeed sesión UDF iniciada exitosamente con Playwright.")
                else:
                    logger.warning("No se pudo extraer el token UDF. Posible bloqueo o Captcha visible.")
                
                await browser.close()
        except Exception as e:
            logger.error(f"Excepción en _init_session_async: {e}")

    def _map_interval(self, interval):
        mapping = {
            Interval.in_1_minute: "1", Interval.in_3_minute: "3", Interval.in_5_minute: "5",
            Interval.in_15_minute: "15", Interval.in_30_minute: "30", Interval.in_45_minute: "45",
            Interval.in_1_hour: "60", Interval.in_2_hour: "120", Interval.in_3_hour: "180",
            Interval.in_4_hour: "240", Interval.in_daily: "D", Interval.in_weekly: "W", Interval.in_monthly: "M"
        }
        return mapping.get(interval, "D")

    def _get_multiplier_days(self, interval):
        mapping = {
            "1": 1, "3": 2, "5": 3, "15": 7, "30": 10, "45": 14,
            "60": 20, "120": 40, "180": 60, "240": 80,
            "D": 1.5, "W": 10, "M": 40
        }
        udf_res = self._map_interval(interval)
        return mapping.get(udf_res, 2)
        
    async def _fetch_history_async(self, symbol, exchange, interval, n_bars):
        if not self.tvc_host or not self.carrier:
            logger.error("La sesión UDF no está lista.")
            return pd.DataFrame()

        resolution = self._map_interval(interval)
        to_time = int(time.time())
        multiplier = self._get_multiplier_days(interval)
        
        if resolution in ["D", "W", "M"]:
            days_back = int(n_bars * multiplier) + 10
        else:
            minutes_per_bar = int(resolution)
            days_back = int((n_bars * minutes_per_bar) / 1440) * 2 + 5 

        from_time = to_time - (days_back * 86400)
        history_url = f"{self.tvc_host}/{self.carrier}/{self.time_val}/{self.domain_id}/{self.lang_id}/{self.timezone_id}/history?symbol={symbol}&resolution={resolution}&from={from_time}&to={to_time}"
        
        logger.info(f"Pidiendo datos (vía Playwright) a Investing.com de {exchange}:{symbol} (Int: {interval}, Barras: {n_bars})")
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                context = await browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = await context.new_page()
                
                # Fetch as JSON directly using page.evaluate to bypass cross-origin strictly inside context
                # OR we just navigate to it since it's a GET request
                await page.goto(history_url, wait_until="domcontentloaded")
                json_text = await page.locator("body").inner_text()
                await browser.close()
                
                import json
                try:
                    data = json.loads(json_text)
                except:
                    logger.error(f"Error parseando JSON de UDF: {json_text[:200]}")
                    return pd.DataFrame()
                    
                if data.get("s") == "ok":
                    df = pd.DataFrame({
                        "datetime": pd.to_datetime(data["t"], unit="s"),
                        "symbol": f"{exchange}:{symbol}",
                        "open": data["o"],
                        "high": data["h"],
                        "low": data["l"],
                        "close": data["c"],
                        "volume": data.get("v", [0]*len(data["t"]))
                    })
                    
                    df.set_index("datetime", inplace=True)
                    if len(df) > n_bars:
                        df = df.tail(n_bars)
                    return df
                elif data.get("s") == "no_data":
                    logger.warning("UDF retornó no_data.")
                    return pd.DataFrame()
                else:
                    logger.error(f"UDF error: {data}")
                    return pd.DataFrame()
        except Exception as e:
            logger.error(f"Excepción Playwright fetching UDF: {e}")
            return pd.DataFrame()

    def get_hist(self, symbol="8830", exchange="COMEX", interval=Interval.in_daily, n_bars=100):
        # Corre el loop asincrono para mantener la firma sincronica de get_hist()
        return self._loop.run_until_complete(self._fetch_history_async(symbol, exchange, interval, n_bars))

if __name__ == "__main__":
    tv = InvestingDatafeed()
    print("\n--- TEST: ORO 1 MINUTO ---")
    df_1m = tv.get_hist(symbol="8830", exchange="COMEX", interval=Interval.in_1_minute, n_bars=10)
    print(df_1m)
    
    print("\n--- TEST: ORO 1 DIA ---")
    df_1d = tv.get_hist(symbol="8830", exchange="COMEX", interval=Interval.in_daily, n_bars=10)
    print(df_1d)

