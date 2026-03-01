"""
+----------------------------------------------------------+
|           ASKME - ASISTENTE DE VOZ OFFLINE               |
|  Motor: Vosk (offline) | Spotify API | Google Search     |
|  Activacion: "AskMe + [accion]"                          |
+----------------------------------------------------------+

INSTALACION:
  pip install vosk sounddevice plyer pycaw comtypes spotipy

CONFIGURACION DE SPOTIFY:
  1. Ve a https://developer.spotify.com/dashboard
  2. Crea una app (nombre y descripcion cualquiera)
  3. En "Redirect URIs" agrega: http://localhost:8888/callback
  4. Copia tu Client ID y Client Secret
  5. Pegajos abajo en SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET

MODELO VOSK:
  Descarga vosk-model-es-0.42 en https://alphacephei.com/vosk/models
  Descomprime y renombra la carpeta a "model" junto a este script.

ESTRUCTURA:
  tu_carpeta/
  askme.py
  model/
"""

import json
import os
import subprocess
import sys
import time
import webbrowser
from datetime import datetime
from pathlib import Path
from urllib.parse import quote_plus

# ══════════════════════════════════════════════════════════
#  CONFIGURACION — EDITA ESTOS VALORES
# ══════════════════════════════════════════════════════════
SPOTIFY_CLIENT_ID     = "TU_CLIENT_ID_AQUI"
SPOTIFY_CLIENT_SECRET = "TU_CLIENT_SECRET_AQUI"
SPOTIFY_REDIRECT_URI  = "http://localhost:8888/callback"
# ══════════════════════════════════════════════════════════

MODEL_PATH  = Path(__file__).parent / "model"
SAMPLE_RATE = 16000
BLOCK_SIZE  = 8000

# ── Verificar dependencias ─────────────────────────────────
def verificar_deps():
    faltantes = []
    for mod in ["vosk", "sounddevice", "spotipy"]:
        try:
            __import__(mod)
        except ImportError:
            faltantes.append(mod)
    if faltantes:
        print(f"Error: faltan dependencias: {', '.join(faltantes)}")
        print(f"Ejecuta: pip install {' '.join(faltantes)}")
        sys.exit(1)
    if not MODEL_PATH.exists():
        print("Error: no se encontro la carpeta 'model' con el modelo Vosk.")
        print("Descargalo en: https://alphacephei.com/vosk/models")
        print(f"Coloca la carpeta aqui: {MODEL_PATH}")
        sys.exit(1)

verificar_deps()

import vosk
import sounddevice as sd
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# ── Inicializar Spotify ────────────────────────────────────
sp = None

def iniciar_spotify():
    global sp
    if SPOTIFY_CLIENT_ID == "TU_CLIENT_ID_AQUI":
        print("Aviso: Spotify no configurado. Edita SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en el script.")
        return False
    try:
        scope = "user-modify-playback-state user-read-playback-state user-read-currently-playing"
        auth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri=SPOTIFY_REDIRECT_URI,
            scope=scope,
            open_browser=True,
            cache_path=str(Path(__file__).parent / ".spotify_cache"),
        )
        sp = spotipy.Spotify(auth_manager=auth)
        sp.current_user()
        print("Spotify conectado correctamente.")
        return True
    except Exception as e:
        print(f"Aviso: no se pudo conectar Spotify: {e}")
        sp = None
        return False

def dispositivo_activo():
    if not sp:
        return None
    try:
        devices = sp.devices()
        for d in devices.get("devices", []):
            if d["is_active"]:
                return d["id"]
        devs = devices.get("devices", [])
        return devs[0]["id"] if devs else None
    except Exception:
        return None

# ── Notificaciones ─────────────────────────────────────────
def notificar(titulo: str, mensaje: str):
    try:
        from plyer import notification
        notification.notify(title=titulo, message=mensaje, app_name="AskMe", timeout=4)
    except Exception:
        pass
    print(f"  [{titulo}] {mensaje}")

# ── Control de volumen ─────────────────────────────────────
def _vol():
    from ctypes import cast, POINTER
    from comtypes import CLSCTX_ALL
    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    devices = AudioUtilities.GetSpeakers()
    iface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
    return cast(iface, POINTER(IAudioEndpointVolume))

def subir_volumen(cantidad: int = 10):
    """Sube el volumen la cantidad de puntos indicada (default 10%)."""
    try:
        v = _vol(); n = min(1.0, v.GetMasterVolumeLevelScalar() + cantidad / 100)
        v.SetMasterVolumeLevelScalar(n, None)
        notificar("AskMe", f"Volumen subido a {int(n*100)}%")
    except Exception:
        import ctypes
        for _ in range(cantidad // 2):
            ctypes.windll.user32.keybd_event(0xAF, 0, 0, 0)
        notificar("AskMe", f"Volumen subido {cantidad}%")

def bajar_volumen(cantidad: int = 10):
    """Baja el volumen la cantidad de puntos indicada (default 10%)."""
    try:
        v = _vol(); n = max(0.0, v.GetMasterVolumeLevelScalar() - cantidad / 100)
        v.SetMasterVolumeLevelScalar(n, None)
        notificar("AskMe", f"Volumen bajado a {int(n*100)}%")
    except Exception:
        import ctypes
        for _ in range(cantidad // 2):
            ctypes.windll.user32.keybd_event(0xAE, 0, 0, 0)
        notificar("AskMe", f"Volumen bajado {cantidad}%")

def establecer_volumen(valor: int):
    """Establece el volumen en un valor exacto entre 0 y 100."""
    valor = max(0, min(100, valor))
    try:
        v = _vol()
        v.SetMasterVolumeLevelScalar(valor / 100, None)
        notificar("AskMe", f"Volumen establecido en {valor}%")
    except Exception:
        notificar("AskMe", "No se pudo establecer el volumen exacto")

def silenciar():
    try:
        v = _vol(); m = v.GetMute(); v.SetMute(not m, None)
        notificar("AskMe", f"Audio {'silenciado' if not m else 'activado'}")
    except Exception:
        import ctypes; ctypes.windll.user32.keybd_event(0xAD, 0, 0, 0)
        notificar("AskMe", "Audio silenciado/activado")

def extraer_numero(texto: str) -> int | None:
    """Extrae el primer numero entero encontrado en un texto."""
    import re
    # Soporte para palabras numericas comunes
    palabras = {
        "cero": 0, "diez": 10, "veinte": 20, "treinta": 30,
        "cuarenta": 40, "cincuenta": 50, "sesenta": 60,
        "setenta": 70, "ochenta": 80, "noventa": 90, "cien": 100,
    }
    for palabra, valor in palabras.items():
        if palabra in texto:
            return valor
    match = re.search(r'\d+', texto)
    return int(match.group()) if match else None

# ── Control del sistema ────────────────────────────────────
def apagar():
    notificar("AskMe", "Apagando en 10 segundos... Di 'AskMe cancela el apagado' para detenerlo")
    time.sleep(2); os.system("shutdown /s /t 10")

def reiniciar():
    notificar("AskMe", "Reiniciando en 10 segundos... Di 'AskMe cancela el apagado' para detenerlo")
    time.sleep(2); os.system("shutdown /r /t 10")

def suspender():
    notificar("AskMe", "Suspendiendo el equipo")
    time.sleep(2); os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")

def cancelar_apagado():
    os.system("shutdown /a")
    notificar("AskMe", "Apagado cancelado")

# ── Abrir aplicaciones ─────────────────────────────────────
APPS = {
    "chrome":        (["chrome", "google chrome", "navegador"],             "chrome"),
    "firefox":       (["firefox", "mozilla"],                               "firefox"),
    "edge":          (["edge", "microsoft edge"],                           "msedge"),
    "notepad":       (["notepad", "bloc de notas", "notas"],                "notepad.exe"),
    "calculadora":   (["calculadora", "calculator"],                        "calc.exe"),
    "explorador":    (["explorador", "explorador de archivos"],             "explorer.exe"),
    "word":          (["word", "microsoft word"],                           "winword"),
    "excel":         (["excel", "microsoft excel"],                         "excel"),
    "powerpoint":    (["powerpoint", "power point"],                        "powerpnt"),
    "spotify":       (["spotify"],                                          "spotify"),
    "discord":       (["discord"],                                          "discord"),
    "teams":         (["teams", "microsoft teams"],                         "teams"),
    "zoom":          (["zoom"],                                             "zoom"),
    "vscode":        (["visual studio code", "vs code", "codigo", "vscode"],"code"),
    "paint":         (["paint"],                                            "mspaint.exe"),
    "cmd":           (["cmd", "consola", "simbolo del sistema"],            "cmd.exe"),
    "powershell":    (["powershell"],                                       "powershell.exe"),
    "task manager":  (["administrador de tareas", "task manager"],          "taskmgr.exe"),
    "configuracion": (["configuracion", "ajustes", "settings"],             "ms-settings:"),
}

def abrir_aplicacion(nombre: str):
    nombre = nombre.lower()
    for app_key, (aliases, cmd) in APPS.items():
        if any(alias in nombre for alias in aliases):
            try:
                subprocess.Popen([cmd], shell=cmd.endswith(":"))
            except Exception:
                os.system(f"start {cmd}")
            notificar("AskMe", f"Abriendo {app_key}")
            return
    try:
        subprocess.Popen([nombre])
    except Exception:
        os.system(f"start {nombre}")
    notificar("AskMe", f"Intentando abrir '{nombre}'...")

# ── Google Search ──────────────────────────────────────────
def buscar_en_google(query: str):
    if not query:
        notificar("AskMe", "Que quieres buscar?"); return
    url = f"https://www.google.com/search?q={quote_plus(query)}"
    webbrowser.open(url)
    notificar("AskMe", f"Buscando '{query}' en Google")

# ── Spotify ────────────────────────────────────────────────
def spotify_play():
    if not sp:
        notificar("AskMe", "Spotify no esta configurado"); return
    try:
        sp.start_playback(device_id=dispositivo_activo())
        notificar("AskMe", "Reproduciendo musica")
    except Exception as e:
        notificar("AskMe", f"Error Spotify: {e}")

def spotify_pause():
    if not sp:
        notificar("AskMe", "Spotify no esta configurado"); return
    try:
        sp.pause_playback()
        notificar("AskMe", "Musica pausada")
    except Exception as e:
        notificar("AskMe", f"Error Spotify: {e}")

def spotify_siguiente():
    if not sp:
        notificar("AskMe", "Spotify no esta configurado"); return
    try:
        sp.next_track()
        time.sleep(0.5)
        info = sp.current_playback()
        if info and info.get("item"):
            notificar("AskMe", f"Siguiente: {info['item']['name']} - {info['item']['artists'][0]['name']}")
        else:
            notificar("AskMe", "Siguiente cancion")
    except Exception as e:
        notificar("AskMe", f"Error Spotify: {e}")

def spotify_anterior():
    if not sp:
        notificar("AskMe", "Spotify no esta configurado"); return
    try:
        sp.previous_track()
        time.sleep(0.5)
        info = sp.current_playback()
        if info and info.get("item"):
            notificar("AskMe", f"Anterior: {info['item']['name']} - {info['item']['artists'][0]['name']}")
        else:
            notificar("AskMe", "Cancion anterior")
    except Exception as e:
        notificar("AskMe", f"Error Spotify: {e}")

def spotify_buscar_y_reproducir(query: str):
    if not sp:
        notificar("AskMe", "Spotify no esta configurado"); return
    if not query:
        notificar("AskMe", "Que cancion quieres escuchar?"); return
    try:
        resultados = sp.search(q=query, limit=1, type="track")
        tracks = resultados["tracks"]["items"]
        if not tracks:
            notificar("AskMe", f"No encontre '{query}' en Spotify"); return
        track   = tracks[0]
        nombre  = track["name"]
        artista = track["artists"][0]["name"]
        sp.start_playback(device_id=dispositivo_activo(), uris=[track["uri"]])
        notificar("AskMe", f"Reproduciendo: {nombre} - {artista}")
    except Exception as e:
        notificar("AskMe", f"Error Spotify: {e}")

def spotify_cancion_actual():
    if not sp:
        notificar("AskMe", "Spotify no esta configurado"); return
    try:
        info = sp.current_playback()
        if info and info.get("item"):
            nombre  = info["item"]["name"]
            artista = info["item"]["artists"][0]["name"]
            estado  = "Reproduciendo" if info["is_playing"] else "Pausado"
            notificar("AskMe", f"{estado}: {nombre} - {artista}")
        else:
            notificar("AskMe", "No hay nada reproduciendose en Spotify")
    except Exception as e:
        notificar("AskMe", f"Error Spotify: {e}")

# ── Hora ───────────────────────────────────────────────────
def decir_hora():
    ahora = datetime.now()
    notificar("AskMe", f"{ahora.strftime('%H:%M')}  |  {ahora.strftime('%d/%m/%Y')}")

# ── Procesador de comandos ─────────────────────────────────
def procesar_comando(texto: str) -> bool:
    texto = texto.lower().strip()
    if "askme" not in texto and "ask me" not in texto:
        return False

    # Extraer accion
    for kw in ["ask me", "askme"]:
        if kw in texto:
            idx = texto.index(kw) + len(kw)
            break
    accion = texto[idx:].strip().lstrip(",").strip()
    print(f"  Accion: '{accion}'")

    # Detener asistente
    if any(p in accion for p in ["detente", "para", "cierra", "termina", "sal", "adios", "chao"]):
        notificar("AskMe", "Hasta luego!")
        return True

    # Volumen
    if any(p in accion for p in ["pon el volumen", "establece el volumen", "volumen al", "volumen a ", "sube el volumen a", "baja el volumen a"]):
        num = extraer_numero(accion)
        if num is not None:
            establecer_volumen(num)
        else:
            notificar("AskMe", "No entendi el valor. Di por ejemplo: 'pon el volumen al 60'")
    elif any(p in accion for p in ["sube", "subir", "aumenta", "mas volumen", "más volumen"]):
        num = extraer_numero(accion)
        subir_volumen(num if num else 10)
    elif any(p in accion for p in ["baja", "bajar", "disminuye", "menos volumen"]):
        num = extraer_numero(accion)
        bajar_volumen(num if num else 10)
    elif any(p in accion for p in ["silencia", "silencio", "mute", "sin sonido", "quita el sonido"]):
        silenciar()

    # Sistema
    elif any(p in accion for p in ["apaga", "apagar"]):
        apagar()
    elif any(p in accion for p in ["reinicia", "reiniciar", "restart"]):
        reiniciar()
    elif any(p in accion for p in ["suspende", "suspender", "duerme"]):
        suspender()
    elif any(p in accion for p in ["cancela el apagado", "cancela apagado", "cancela reinicio"]):
        cancelar_apagado()

    # Google
    elif any(accion.startswith(p) for p in ["busca", "buscar", "googlea"]):
        for prefijo in ["busca en google ", "buscar en google ", "googlea ", "busca ", "buscar "]:
            if accion.startswith(prefijo):
                query = accion[len(prefijo):]
                break
        else:
            query = accion
        buscar_en_google(query)

    # Spotify: reproducir cancion especifica
    elif any(accion.startswith(p) for p in ["pon ", "poner ", "reproduce ", "reproducir ", "escucha ", "escuchar "]):
        for prefijo in ["reproduce en spotify ", "pon la cancion ", "pon la canción ",
                        "reproduce ", "reproducir ", "escucha ", "escuchar ", "poner ", "pon "]:
            if accion.startswith(prefijo):
                query = accion[len(prefijo):]
                break
        else:
            query = accion
        spotify_buscar_y_reproducir(query)

    # Spotify: controles
    elif any(p in accion for p in ["pausa", "pausar", "pausa la musica"]):
        spotify_pause()
    elif any(p in accion for p in ["reanuda", "reanudar", "continua", "continúa", "resume", "play"]):
        spotify_play()
    elif any(p in accion for p in ["siguiente", "skip", "pasa la cancion"]):
        spotify_siguiente()
    elif any(p in accion for p in ["anterior", "regresa la cancion", "cancion anterior"]):
        spotify_anterior()
    elif any(p in accion for p in ["que suena", "qué suena", "que cancion suena", "cancion actual"]):
        spotify_cancion_actual()

    # Hora
    elif any(p in accion for p in ["que hora", "qué hora", "hora actual", "que fecha", "qué fecha"]):
        decir_hora()

    # Abrir app
    elif any(accion.startswith(p) for p in ["abre", "abrir", "lanza", "ejecuta", "inicia"]):
        for prefijo in ["abre el ", "abre la ", "abre los ", "abrir el ", "abrir la ",
                        "abre ", "abrir ", "lanza ", "ejecuta ", "inicia "]:
            if accion.startswith(prefijo):
                app_nombre = accion[len(prefijo):]
                break
        else:
            app_nombre = accion
        abrir_aplicacion(app_nombre)

    else:
        notificar("AskMe", f"No entendi: '{accion}'")

    return False

# ── Loop principal ─────────────────────────────────────────
def main():
    print("+----------------------------------------------------------+")
    print("|           ASKME - ASISTENTE DE VOZ OFFLINE               |")
    print("+----------------------------------------------------------+")
    print("|  Di: 'AskMe [accion]'                                   |")
    print("|                                                          |")
    print("|  VOLUMEN:   sube / baja / silencia el volumen           |")
    print("|  SISTEMA:   apaga / reinicia / suspende                 |")
    print("|  GOOGLE:    busca [lo que sea]                          |")
    print("|  SPOTIFY:   pon [cancion] / pausa / reanuda             |")
    print("|             siguiente / anterior / que suena            |")
    print("|  APPS:      abre [Chrome / Spotify / Word / ...]        |")
    print("|  HORA:      que hora es                                 |")
    print("|  SALIR:     detente                                      |")
    print("+----------------------------------------------------------+\n")

    print("Conectando con Spotify...")
    spotify_ok = iniciar_spotify()
    if not spotify_ok:
        print("(Continuando sin Spotify — configuralo en el script)\n")

    print("Cargando modelo Vosk...")
    vosk.SetLogLevel(-1)
    model = vosk.Model(str(MODEL_PATH))
    rec   = vosk.KaldiRecognizer(model, SAMPLE_RATE)
    print("Listo! Escuchando sin internet.\n")

    notificar("AskMe", "Asistente iniciado. Di 'AskMe + accion'")

    detener = False

    def callback(indata, frames, time_info, status):
        nonlocal detener
        if detener:
            return
        if rec.AcceptWaveform(bytes(indata)):
            resultado = json.loads(rec.Result())
            texto = resultado.get("text", "").strip()
            if texto:
                print(f"\n  Escuche: '{texto}'")
                detener = procesar_comando(texto)

    try:
        with sd.RawInputStream(
            samplerate=SAMPLE_RATE,
            blocksize=BLOCK_SIZE,
            dtype="int16",
            channels=1,
            callback=callback,
        ):
            print("Escuchando... (Ctrl+C para salir)\n")
            while not detener:
                time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nAsistente detenido manualmente.")
        notificar("AskMe", "Asistente cerrado.")

    print("Hasta luego!")

if __name__ == "__main__":
    main()