# Importar librerias
#  -----------------------------------------------
try:
    import pandas_ta as talib, sys, requests, datetime, asyncio, time, requests
    from tvDatafeed import TvDatafeed, Interval
except Exception as e:
    print(f"ERROR IMPORTANDO LIBRERIAS: {e}")
    sys.exit()
#  -----------------------------------------------

# Función EMAs 954
#  -----------------------------------------------
async def emas954(tv:TvDatafeed=TvDatafeed(), symbol:str="GC1!", exchange:str="COMEX", intervalo:Interval=Interval.in_1_minute, vela:int=1) -> str:
    try:
        print(f"Obteniendo historial en {intervalo}")
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
        print(f"ERROR EN emas954({intervalo}) - {e}")
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
                "emas954_1d": emas954_d,
                "emas954_w": emas954_w}
        r = requests.post(url=url, params=params)
        if r.status_code == 200:
            print(r.text)
            #logger.info(f"EMA954_1m: {emas954_1m}, EMA954_5m: {emas954_5m}, EMA954_15m: {emas954_15m}, EMA954_1h: {emas954_1h}, EMA954_4h: {emas954_4h}, EMA954_D: {emas954_d}, EMA954_w: {emas954_w}")
        else:
            print(f"ERROR ENVIANDO DATOS DE {symbol} AL GSHEETS. STATUS CODE: {r.status_code}" )
    except Exception as e:
        print("ERROR EN enviar_datos()")
#  -----------------------------------------------

# Enviar datos de EMAs 954 al GSheets
#  -----------------------------------------------
async def main():

    # Definir una sesion para la API de Trading View
    tv = TvDatafeed()

    # Variables iniciales
    symbol = "GC1!"
    exchange = "COMEX"
    emas954_1m = ""
    emas954_5m = ""
    emas954_15m = ""
    emas954_1h = ""
    emas954_4h = ""
    emas954_d = ""
    emas954_w = ""
    ciclo = 0
    ciclo_final = 63
    url_enviar_datos="https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec"
    url_disparar_github_actions = "https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec"
    
    while True:
        try:
            # Obtener velas y EMAs 954 cada vez que el segundero marca 0
            if datetime.datetime.now().second != 0 and emas954_1m != "" and emas954_5m != "" and emas954_15m != "":
                time.sleep(0.999)
                continue
            
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
                enviar_datos(symbol, url_enviar_datos, emas954_1m, emas954_5m, emas954_15m, emas954_1h, emas954_4h, emas954_d, emas954_w)
            
            ciclo += 1
            print(f"Ciclo {ciclo} completado.")
            if ciclo >= ciclo_final:
                print(f"Ciclo final {ciclo} alcanzado. Fin del programa.")
                await asyncio.sleep(3.6)
                r = requests.get(url_disparar_github_actions, params={"disparar": symbol})
                if r.status_code == 200:
                    print(r.text)
                else:
                    print(f"ERROR DISPARANDO GITHUB ACTIONS DE {symbol}. STATUS CODE: {r.status_code}" )
                break

        except Exception as e:
            print(f"ERROR EN EL CICLO main() - {e}")
            ciclo += 1
            print(f"Ciclo {ciclo} completado con errores.")
#  -----------------------------------------------


if __name__ == "__main__":
    
    # Ejecutar el programa principal
    # -----------------------------------------------
    asyncio.run(main())
    # -----------------------------------------------
