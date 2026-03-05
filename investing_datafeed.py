import logging
import time
import re
import pandas as pd
from urllib.parse import urlparse, parse_qs
from curl_cffi import requests

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
        self.session = requests.Session(impersonate="chrome110")
        self._init_session()

    def _init_session(self):
        url = "https://www.investing.com/commodities/gold-streaming-chart"
        logger.info("Iniciando Sesion con curl_cffi (Impersonate Chrome)...")
        
        try:
            # Headers realistas para evitar 403 inmediatos
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/110.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.google.com/",
            }
            
            resp = self.session.get(url, headers=headers, timeout=30)
            
            if resp.status_code == 403:
                logger.error("Cloudflare bloqueo curl_cffi (403).")
                return

            html = resp.text
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
                logger.info("InvestingDatafeedCffi: Tokens UDF extraidos correctamente.")
            else:
                logger.warning("No se encontraron tokens UDF con curl_cffi.")
        except Exception as e:
            logger.error(f"Error en _init_session (cffi): {e}")

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
        if not self.tvc_host or not self.carrier:
            self._init_session()
            
        if not self.tvc_host or not self.carrier:
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
        
        try:
            resp = self.session.get(history_url, timeout=20)
            
            if resp.status_code != 200:
                logger.warning(f"Error {resp.status_code} al pedir datos. Re-intentando...")
                self._init_session()
                resp = self.session.get(history_url, timeout=20)

            data = resp.json()
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
                return df.tail(n_bars)
            return pd.DataFrame()
        except Exception as e:
            logger.error(f"Error en get_hist (cffi): {e}")
            return pd.DataFrame()

    def close(self):
        pass

if __name__ == "__main__":
    tv = InvestingDatafeedCffi()
    print("\n--- TEST CFFI: ORO 1 MINUTO ---")
    df_1m = tv.get_hist(symbol="8830", exchange="COMEX", interval=Interval.in_1_minute, n_bars=10)
    print(df_1m)

    print("\n--- TEST CFFI: ORO 1 DIA ---")
    df_1d = tv.get_hist(symbol="8830", exchange="COMEX", interval=Interval.in_daily, n_bars=10)
    print(df_1d)

