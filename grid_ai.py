from google import genai
from google.genai import types
import tvDatafeed as tvDatafeed, pandas as pd, json, requests, time

# =============================================================================
# CONFIGURACIÓN Y CONSTANTES
# =============================================================================

# Instrucciones detalladas para la IA. Define su rol y el formato de salida esperado.
INSTRUCCIONES_IA = """
Eres un gestor senior de fondos de inversiones, analista tecnico profesional, genio en estrategias de scalping y grid trading.
A partir de datos de velas OHLC que te voy a suminstrar eres capaz de detrminar:
- El ultimo rango consolidado
- La separacion porcentualmas eficiente entre niveles del grid para que el precio fluctue con gran probabilidad en al menos en un par de niveles claves (compra y venta), ojo con colocar muchos niveles o una separacion muy pequeña, no se deben abrir muchas posiciones dentro del rango, solo las necesarias para garantizar la eficiencia del grid.
- El nivel mas concurrido del rango consolidado.
La distancia entre niveles del grid debe ser en porcentaje sin el simbolo "%", de al menos 3 decimales donde la suma de todos los digitos del porcentaje debe ser 9. Debe tener al menos 3 numeros distintos de 0.
La separacion minima debe ser mayor o igual a 0.0999.
Dentro del rango detectado no pueden haber mas de 3 niveles y como minimo 1 nivel.
Si no hay un rango consolidado, devuelve una separacion olgada para evitar quedar muy cargados si el precio se viene en contra.
Debes devolver un JSON con la siguiente estructura:
{
    "symbol": "string",
    "separacion": "string",
    "nivel_clave: "string, nivel mas concurrido del rango consolidado",
    "mensaje": "Cualquiero cosa, mensaje u observaciones qie quieras decirme"
}
"""

# Lista de modelos de IA a probar en orden de preferencia.
MODELOS_IA = [
    "gemini-3-flash-preview", 
    "gemini-2.5-flash", 
    "gemini-2.5-flash-lite"
]

# Claves de API de Google GenAI para manejar límites de cuota (Rate Limiting).
GENAI_API_KEY = [
    "AIzaSyDxtM2-NpHG9PAd9bWGwCAascCYVT2wYCA", 
    "AIzaSyCbrcm3NLjc1Qo3By7bGt2mJ8zu_Kw5swo", 
    "AIzaSyAIWNvwgdCbMl08geCLa1iwona04s2Ri74"
]

# URL del Web App de Google Apps Script para registrar los análisis en una hoja de cálculo.
URL_GSHEETS = "https://script.google.com/macros/s/AKfycbyJyyN7WFPtao1u_y8jgwsaKVYf2j8TL4vtg-Xe3kAotmBsUAEyFFjt2K-NgHauYxJjHw/exec"

# Parámetros de mercado por defecto.
symbol:str = "GOLD"
exchange:str = "TVC"
intervalo:tvDatafeed.Interval = tvDatafeed.Interval.in_1_minute
n_bars:int = 60

def obtener_datos_velas_ohlc(symbol:str, exchange:str, intervalo:tvDatafeed.Interval, n_bars:int):
    """
    Obtiene el historial de precios (Open, High, Low, Close) desde TradingView.
    
    Args:
        symbol (str): Símbolo del activo (ej. "GOLD").
        exchange (str): Exchange de procedencia (ej. "TVC").
        intervalo (tvDatafeed.Interval): Temporalidad de las velas.
        n_bars (int): Cantidad de velas hacia atrás a recuperar.
    
    Returns:
        pd.DataFrame: Datos de las velas o None si falla.
    """
    # Inicializar la conexión con TradingView (acceso público por defecto)
    tv = tvDatafeed.TvDatafeed()

    # Descargar el historial de precios solicitado
    data = tv.get_hist(symbol, exchange, intervalo, n_bars=n_bars)
    return data

def consultar_ia(modelo:str, api_key:str, instrucciones:str, data:pd.DataFrame):
    """
    Envía los datos de las velas a la IA de Google para que realice el análisis de Grid.
    
    Args:
        modelo (str): Nombre del modelo de Gemini a utilizar.
        api_key (str): Clave de API de Google GenAI.
        instrucciones (str): El prompt del sistema con las reglas de trading.
        data (pd.DataFrame): Los datos OHLC convertidos a texto.
        
    Returns:
        str: Respuesta en formato JSON directamente desde la IA.
    """
    client = genai.Client(api_key=api_key)
    response = client.models.generate_content(
        model=modelo,
        contents=data.to_string(), # Convertimos el DataFrame a String para que la IA lo lea
        config=types.GenerateContentConfig(
            system_instruction=instrucciones,
            response_mime_type="application/json",
            # Se define el esquema esperado para asegurar que la IA devuelva los campos correctos
            response_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "separacion": {"type": "string"},
                    "nivel_clave": {"type": "string"},
                    "mensaje": {"type": "string"}
                },
                "required": ["symbol", "separacion", "nivel_clave", "mensaje"]
            }
        )
    )
    return response.text

def analizar_rango_con_ia(modelo:str, api_key:str, symbol:str, exchange:str, intervalo:tvDatafeed.Interval, n_bars:int):
    """
    Flujo intermedio: Obtiene datos y luego llama a la IA.
    """
    # 1. Obtener datos de TradingView
    data = obtener_datos_velas_ohlc(symbol, exchange, intervalo, n_bars)
    
    # 2. Si hay datos válidos, enviarlos a la IA
    analisis = consultar_ia(modelo=modelo, api_key=api_key, instrucciones=INSTRUCCIONES_IA, data=data) if isinstance(data, pd.DataFrame) else None
    return analisis

def enviar_analisis_a_gsheets(modelo:str, url:str, analisis:dict):
    """
    Envía el resultado del análisis a una Google Sheet para registro y monitoreo.
    
    Args:
        modelo (str): Nombre del modelo que generó el análisis.
        url (str): URL del Google Apps Script.
        analisis (dict): Diccionario con los resultados (soporte, resistencia, etc.).
    """
    try:
        # Preparamos los parámetros que espera el script de Google (GApps Script)
        params = {
            "analisisGrid": analisis,
            "symbol": analisis["symbol"], 
            "separacion": analisis["separacion"], 
            "nivelClave": analisis["nivel_clave"],
            "mensaje": analisis["mensaje"],
            "modelo": modelo
        }
        print(f"Enviando analisis...")
        
        # Realizamos la petición HTTP POST enviando la información
        r = requests.post(url=url, params=params)
        
        if r.status_code == 200:
            print(f"Respuesta GSheets: {r.text}")
        else:
            print(f"ERROR ENVIANDO ANALISIS AL GSHEETS. STATUS CODE: {r.status_code}")
            
    except Exception as e:
        print(f"ERROR EN enviar_analisis_a_gsheets() - ERROR: {e} ANALISIS: {analisis}")

def main():
    """
    Función principal que orquesta el proceso.
    Intenta usar diferentes API Keys y modelos si encuentra errores de límite de cuota (429).
    """
    # Doble bucle para agotar todas las llaves y modelos si es necesario
    for api_key in GENAI_API_KEY:
        for modelo in MODELOS_IA:
            try:
                print(f"Analizando con modelo: {modelo}...")
                
                analisis_raw = analizar_rango_con_ia(modelo=modelo, api_key=api_key, symbol=symbol, exchange=exchange, intervalo=intervalo, n_bars=n_bars)
                
                # Si el análisis falla o la API devuelve un error 429 (Resource Exhausted), probamos el siguiente modelo/llave
                if analisis_raw is None or "429" in analisis_raw:
                    print(f"Falla en el análisis o cuota excedida para {modelo}. Reintentando con otro...")
                    continue
                else :
                    # Si tenemos éxito, procesamos el JSON
                    analisis_data = json.loads(analisis_raw)
                    print("Análisis exitoso obtenido:")
                    print(json.dumps(analisis_data, indent=4))
                    
                    # Enviamos los datos a la hoja de cálculo
                    enviar_analisis_a_gsheets(modelo=modelo, url=URL_GSHEETS, analisis=analisis_data)
                    
                    # Terminamos el script tras el primer éxito exitoso
                    return
            except Exception as e:
                print(f"ERROR EN main() - ERROR: {e}")

    # Si llegamos aquí, significa que todos los modelos/llaves fallaron
    print("Todos los modelos/llaves fallaron. Terminando el script.")
    
# Punto de entrada del script
if __name__ == "__main__":
    main()
    
