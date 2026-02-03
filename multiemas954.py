# Importar librerias
#  -----------------------------------------------
try:
    import pandas_ta as talib, sys, requests, datetime, asyncio, time
    from tvDatafeed import TvDatafeed, Interval
except Exception as e:
    print(f"ERROR IMPORTANDO LIBRERIAS: {e}")
    sys.exit()
#  -----------------------------------------------

# Función EMAs 954
#  -----------------------------------------------
async def emas954(tv:TvDatafeed=TvDatafeed(), symbol:str="GC1!", exchange:str="COMEX", intervalo:Interval=Interval.in_1_minute, vela:int=1) -> str:
    try:
        print(f"Obteniendo historial de {symbol} en {intervalo}")
        await asyncio.sleep(0.099)
        ohlc_df_1m = tv.get_hist(symbol=symbol, exchange=exchange, interval=intervalo, n_bars=5000)
        #print(ohlc_df_1m)

        ema9 = talib.ema(ohlc_df_1m["close"], 9).iloc[-1]
        ema9_anterior = talib.ema(ohlc_df_1m["close"], 9).iloc[-2]
        ema54 = talib.ema(ohlc_df_1m["close"], 54).iloc[-1]
        ema54_anterior = talib.ema(ohlc_df_1m["close"], 54).iloc[-2]
        if ema9 > ema54 and ema9_anterior > ema54_anterior:
            return "BUY"
        if ema9 < ema54 and ema9_anterior < ema54_anterior:
            return "SELL"
        return ""
    except Exception as e:
        print(f"ERROR EN emas954({intervalo}) de {symbol} - {e}")
        return ""
#  -----------------------------------------------

# Función para enviar info a una GSheets
#  -----------------------------------------------
def enviar_datos(symbol, url, emas954_1m, emas954_5m, emas954_15m, emas954_1h, emas954_4h, emas954_d, emas954_w):
    try:
        params = {"symbol": symbol, 
                "emas954_1m": emas954_1m, 
                "emas954_5m": emas954_5m, 
                "emas954_15m": emas954_15m, 
                "emas954_1h": emas954_1h,
                "emas954_4h": emas954_4h,
                "emas954_d": emas954_d,
                "emas954_w": emas954_w}
        print(params)
        r = requests.post(url=url, params=params)
        if r.status_code == 200:
            print(r.text)
        else:
            print(f"ERROR ENVIANDO DATOS DE {symbol} AL GSHEETS. STATUS CODE: {r.status_code}" )
    except Exception as e:
        print(f"ERROR EN enviar_datos() - {e}")
#  -----------------------------------------------

# Enviar datos de EMAs 954 al GSheets
#  -----------------------------------------------
async def main954(symbol: str, exchange: str, urls: list[str], ciclo_final: int=0):

    # Definir una sesion para la API de Trading View
    tv = TvDatafeed()

    # Variables iniciales
    emas954_1m = ""
    emas954_5m = ""
    emas954_15m = ""
    emas954_1h = ""
    emas954_4h = ""
    emas954_d = ""
    emas954_w = ""
    ciclo = 0
    
    while True:
        try:
            ti = datetime.datetime.now()
            resultados = await asyncio.gather(emas954(tv, symbol, exchange, Interval.in_1_minute, 1), 
                                            emas954(tv, symbol, exchange, Interval.in_5_minute, 1), 
                                            emas954(tv, symbol, exchange, Interval.in_15_minute, 1), 
                                            emas954(tv, symbol, exchange, Interval.in_1_hour, 1), 
                                            emas954(tv, symbol, exchange, Interval.in_4_hour, 1), 
                                            emas954(tv, symbol, exchange, Interval.in_daily, 1), 
                                            emas954(tv, symbol, exchange, Interval.in_weekly, 1))

            emas954_1m_actual, emas954_5m_actual, emas954_15m_actual, \
            emas954_1h_actual, emas954_4h_actual, emas954_d_actual, \
            emas954_w_actual = resultados
            print(datetime.datetime.now()-ti, f"- ({datetime.datetime.now()})")
            
            # Enviar solo si hay cambios
            if (emas954_1m != emas954_1m_actual and emas954_1m_actual != "" or 
                emas954_5m != emas954_5m_actual and emas954_5m_actual != "" or 
                emas954_15m != emas954_15m_actual and emas954_15m_actual != "" or 
                emas954_1h != emas954_1h_actual and emas954_1h_actual != "" or 
                emas954_4h != emas954_4h_actual and emas954_4h_actual != "" or 
                emas954_d != emas954_d_actual and emas954_d_actual != "" or 
                emas954_w != emas954_w_actual and emas954_w_actual != ""):

                emas954_1m = emas954_1m_actual if emas954_1m_actual != "" else emas954_1m
                emas954_5m = emas954_5m_actual if emas954_5m_actual != "" else emas954_5m
                emas954_15m = emas954_15m_actual if emas954_15m_actual != "" else emas954_15m
                emas954_1h = emas954_1h_actual if emas954_1h_actual != "" else emas954_1h
                emas954_4h = emas954_4h_actual if emas954_4h_actual != "" else emas954_4h
                emas954_d = emas954_d_actual if emas954_d_actual != "" else emas954_d
                emas954_w = emas954_w_actual if emas954_w_actual != "" else emas954_w
                for url in urls:
                    enviar_datos(symbol, url, emas954_1m, emas954_5m, emas954_15m, emas954_1h, emas954_4h, emas954_d, emas954_w)
            
            ciclo += 1
            print(f"Ciclo {ciclo} del {symbol} completado.")
            if ciclo >= ciclo_final:
                print(f"Ciclo final {ciclo} del {symbol} alcanzado. Fin del ciclo {symbol}.")
                break

        except Exception as e:
            print(f"ERROR EN EL CICLO main() - {e}")
            ciclo += 1
            print(f"Ciclo {ciclo} del {symbol} completado con errores.")
#  -----------------------------------------------

# Funcion main para multiples symbols
#  -----------------------------------------------
async def main():
    tareas = []
    for symbol in SYMBOLS:
        tareas.append(main954(symbol["symbol"], symbol["exchange"], [URL_ENVIAR_DATOS], CICLO_FINAL))
    await asyncio.gather(*tareas)
#  -----------------------------------------------

if __name__ == "__main__":

    # Variables iniciales
    # -------------------
    SYMBOLS: list[dict[str, str]] = [
        {"symbol": "DXY", "exchange": "TVC"}, 
        {"symbol": "SP500FT", "exchange": "VANTAGE"}, 
        {"symbol": "VIX", "exchange": "TVC"}, 
        {"symbol": "ZT1!", "exchange": "CBOT"}, 
        {"symbol": "ZN1!", "exchange": "CBOT"}, 
        {"symbol": "US02Y", "exchange": "TVC"}, 
        {"symbol": "US10Y", "exchange": "TVC"}]
    URL_ENVIAR_DATOS: str = "https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec"
    URL_DISPARAR_GITHUB_ACTIONS: str = "https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec"
    CICLO_FINAL: int = 36
    # -------------------
    
    # Ejecutar el programa principal
    # -----------------------------------------------
    ti = datetime.datetime.now()
    asyncio.run(main())
    print(f"Tiempo total: {datetime.datetime.now()-ti}")
    # -----------------------------------------------
    
