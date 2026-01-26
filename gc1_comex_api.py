# Importar librerias
#  -----------------------------------------------
try:
    import sys, logging, traceback, flask, pandas_ta as ta
    from tvDatafeed import TvDatafeed, Interval
except Exception as e:
    print(f"ERROR IMPORTANDO LIBRERIAS: {e}")
    sys.exit()
#  -----------------------------------------------

# Función para configurar_logging()
#  -----------------------------------------------
def configurar_logging(archivo: str = "app.log", debug: bool = False):
    try:
        # 1️⃣ Crea un logger
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG if debug else logging.INFO)
        logger.handlers.clear()


        # 2️⃣ Handler para escribir en archivo
        file_handler = logging.FileHandler(archivo, mode="w", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter("[%(levelname)s]: %(message)s (%(asctime)s)", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(file_handler)

        # 3️⃣ Handler para imprimir en consola
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter("\n[%(levelname)s]: %(message)s (%(asctime)s)", datefmt="%Y-%m-%d %H:%M:%S"))
        logger.addHandler(console_handler)

        logger.info("Logging configurado correctamente")

        return logger
    except:
        print(f"\nERROR CONFIGURANDO LOGGING: {traceback.format_exc()}")
#  -----------------------------------------------

# Función para capturar errores no controlados (tracebacks)
#  -----------------------------------------------
def registrar_excepciones(exc_type, exc_value, exc_traceback):
    try:
        tb = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        logger.error(tb)
    except:
        logger.error(f"Error en registrar_excepciones() {traceback.format_exc()}")
#  -----------------------------------------------

# Función para obtener el csv ohlcv de TvDatafeed
#  -----------------------------------------------
def ohlcv(symbol:str="GC1!", exchange:str="COMEX", interval:Interval=Interval.in_1_minute, n_bars:int=9) -> str:
    try:
        df = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
        csv = df.to_csv(index=True)
        #print(csv)
        return csv
    except Exception as e:
        logger.error(f"ERROR EN ohlcv({symbol},{exchange},{interval}) - {e}")
        return "ERROR"
#  -----------------------------------------------

# Función para obtener el csv de las EMAS 954 de TvDatafeed
# ------------------------------------------------
def emas954(symbol:str="GC1!", exchange:str="COMEX", interval:Interval=Interval.in_1_minute, n_bars:int=9) -> str:
    try:
        df = tv.get_hist(symbol=symbol, exchange=exchange, interval=interval, n_bars=n_bars)
        df_ema9 = ta.ema(df["close"], length=9)
        df_ema54 = ta.ema(df["close"], length=54)
        df["ema9"] = df_ema9
        df["ema54"] = df_ema54
        csv = df.to_csv(index=True)
        #print(csv)
        return csv
    except Exception as e:
        logger.error(f"ERROR EN emas954() - {e}")
        return "ERROR"
# -----------------------------------------------

# main()
# ---------------
def main():
    
    # Flask app
    app = flask.Flask(__name__)

    # Ruta principal
    @app.route("/")
    def home():
        try:
            return f"""API de datos OHLCV de {SYMBOL} en {EXCHANGE}.<br>
            Rutas disponibles:<br>
            => /ohlcv_1m<br>
            => /ohlcv_5m<br>
            => /ohlcv_15m<br>
            => /ohlcv_1h<br>
            => /ohlcv_4h<br>
            => /ohlcv_d<br>
            => /ohlcv_w<br>
            => /emas954_5m<br>
            => /emas954_15m<br>
            => /emas954_1h<br>
            => /emas954_4h<br>
            => /emas954_d<br>
            => /emas954_w"""
        except Exception as e:
            logger.error(f"ERROR EN home(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)

    # Rutas ohlcv
    @app.route("/ohlcv_1m")
    def ohlcv_1m():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_1_minute)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_1m(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
    
    @app.route("/ohlcv_5m")
    def ohlcv_5m():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_5_minute)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_5m(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
    
    @app.route("/ohlcv_15m")
    def ohlcv_15m():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_15_minute)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_15m(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    @app.route("/ohlcv_1h")
    def ohlcv_1h():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_1_hour, n_bars=99)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_1h(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    @app.route("/ohlcv_4h")
    def ohlcv_4h():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_4_hour, n_bars=99)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_4h(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    @app.route("/ohlcv_d")
    def ohlcv_d():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_daily, n_bars=99)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_d(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    @app.route("/ohlcv_w")
    def ohlcv_w():
        try:
            return ohlcv(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_weekly, n_bars=99)
        except Exception as e:
            logger.error(f"ERROR EN ohlcv_w(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    # Rutas emas
    @app.route("/emas954_w")
    def emas954_w():
        try:
            return emas954(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_weekly, n_bars=5000)
        except Exception as e:
            logger.error(f"ERROR EN emas954_w(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    @app.route("/emas954_d")
    def emas954_d():
        try:
            return emas954(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_daily, n_bars=5000)
        except Exception as e:
            logger.error(f"ERROR EN emas954_d(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)
        
    @app.route("/emas954_4h")
    def emas954_4h():
        try:
            return emas954(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_4_hour, n_bars=5000)
        except Exception as e:
            logger.error(f"ERROR EN emas954_4h(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)

    @app.route("/emas954_1h")
    def emas954_1h():
        try:
            return emas954(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_1_hour, n_bars=5000)
        except Exception as e:
            logger.error(f"ERROR EN emas954_1h(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)

    @app.route("/emas954_15m")
    def emas954_15m():
        try:
            return emas954(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_15_minute, n_bars=5000)
        except Exception as e:
            logger.error(f"ERROR EN emas954_15m(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)

    @app.route("/emas954_5m")
    def emas954_5m():
        try:
            return emas954(symbol=SYMBOL, exchange=EXCHANGE, interval=Interval.in_5_minute, n_bars=5000)
        except Exception as e:
            logger.error(f"ERROR EN emas954_5m(): {e}")
            return flask.Response("ERROR INTERNO DEL SERVIDOR", status=500)

    app.run(host="0.0.0.0", port=80, debug=True)
    # -------------------------------------------
# ---------------

if __name__ == "__main__":

    # Capturar errores no manejados y configurar logger
    # -------------------------------------------------
    try:
        logger = configurar_logging()
        sys.excepthook = registrar_excepciones # Ejecutar registrar_excepciones() cada vez que ocurre un error no manejado 
    except:
        print(f"ERROR INICIAMDO LOGGER: {traceback.format_exc()}")
        sys.exit()
    # -------------------------------------------------
    
    # Definir sesion de tvDatafeed
    # -------------------------------------------------
    try:
        tv = TvDatafeed()
        logger.info("Sesión de tvDatafeed iniciada correctamente")
    except Exception as e:
        logger.error(f"ERROR INICIANDO SESION DE TVDATAFEED: {e}")
        sys.exit()
    # -------------------------------------------------

    # Variables iniciales
    # -------------------
    SYMBOL: str = "GC1!"
    EXCHANGE: str = "COMEX"
    # -------------------
    
    # Correr main()
    # -------------------------------------------------
    main()
    # -------------------------------------------------
