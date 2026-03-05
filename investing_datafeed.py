import logging
import time
import re
import pandas as pd
from datetime import datetime
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import sync_playwright

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
        self._init_session()

    def _init_session(self):
        url = "https://www.investing.com/commodities/gold-streaming-chart"
        logger.info("Iniciando Playwright para evadir Cloudflare y extraer tokens UDF...")
        
        try:
            with sync_playwright() as p:
                # --no-sandbox es vital en entornos de servidor como Render/Docker
                browser = p.chromium.launch(
                    headless=True, 
                    args=["--disable-blink-features=AutomationControlled", "--no-sandbox", "--disable-setuid-sandbox"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                page.goto(url, wait_until="domcontentloaded")
                time.sleep(3) # Damos margen para que Cloudflare termine su validación
                
                html = page.content()
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
                    logger.info("InvestingDatafeed sesión UDF iniciada exitosamente con Playwright (sincrono).")
                else:
                    logger.warning("No se pudo extraer el token UDF. Posible bloqueo o Captcha visible.")
                
                browser.close()
        except Exception as e:
            logger.error(f"Excepción en _init_session: {e}")

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
        
    def get_hist(self, symbol="8830", exchange="COMEX", interval=Interval.in_daily, n_bars=100):
        # Si la sesión no inicializó bien al principio (común en Render por arranques frios), reintentamos en caliente.
        if not self.tvc_host or not self.carrier:
            logger.info("La sesión UDF no estaba lista. Intentando reinicializar en la peticion de datos...")
            self._init_session()
            
        if not self.tvc_host or not self.carrier:
            logger.error("Error definitivo: La sesión UDF no pudo ser inicializada.")
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
        
        logger.info(f"Pidiendo datos (Playwright) a Investing.com de {exchange}:{symbol} (Int: {interval}, Barras: {n_bars})")
        
        try:
            with sync_playwright() as p:
                # --no-sandbox / --disable-setuid-sandbox es esencial en contenedores
                browser = p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                # Fetch as JSON directly using pure page navigation (Safe around CORS)
                page.goto(history_url, wait_until="domcontentloaded")
                json_text = page.locator("body").inner_text()
                browser.close()
                
                import json
                try:
                    data = json.loads(json_text)
                except:
                    logger.error(f"Error parseando JSON de UDF: {str(json_text)[:200]}")
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

if __name__ == "__main__":
    tv = InvestingDatafeed()
    print("\n--- TEST: ORO 1 MINUTO ---")
    df_1m = tv.get_hist(symbol="8830", exchange="COMEX", interval=Interval.in_1_minute, n_bars=10)
    print(df_1m)
    
    print("\n--- TEST: ORO 1 DIA ---")
    df_1d = tv.get_hist(symbol="8830", exchange="COMEX", interval=Interval.in_daily, n_bars=10)
    print(df_1d)

