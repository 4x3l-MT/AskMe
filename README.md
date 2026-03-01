# AskMe - Asistente de Voz Offline

Asistente de voz para Windows que se activa con la palabra **"AskMe"** seguida de una accion. Funciona **100% offline** para el reconocimiento de voz gracias a [Vosk](https://alphacephei.com/vosk/). Controla el sistema, abre aplicaciones, busca en Google y controla Spotify.

---

## Funciones

| Categoria | Comandos |
|---|---|
| Volumen | Subir, bajar, silenciar |
| Sistema | Apagar, reiniciar, suspender, cancelar apagado |
| Spotify | Reproducir cancion, pausar, reanudar, siguiente, anterior, ver que suena |
| Google | Abrir busquedas en el navegador |
| Aplicaciones | Chrome, Firefox, Word, Excel, Spotify, Discord, VS Code y mas |
| Utilidades | Ver hora y fecha, cerrar el asistente con la voz |

Cada accion envia una notificacion de escritorio confirmando que se completo.

---

## Requisitos

- Windows 10/11
- Python 3.8 o superior
- Microfono
- Conexion a internet (solo para Spotify y Google)

---

## Instalacion

### 1. Python

Descargalo desde **https://python.org**. Durante la instalacion activa la casilla **"Add Python to PATH"**.

Si olvidaste marcarlo, ve a Variables de entorno del sistema, abre la variable Path y agrega estas dos rutas (ajusta el numero de version segun el tuyo):

```
C:\Users\TuNombre\AppData\Local\Programs\Python\Python312\
C:\Users\TuNombre\AppData\Local\Programs\Python\Python312\Scripts\
```

Despues cierra y vuelve a abrir CMD. Verifica con:

```bash
python --version
```

### 2. Dependencias

Abre CMD y ejecuta:

```bash
pip install vosk sounddevice plyer pycaw comtypes spotipy
```

Si sounddevice da error, instala asi:

```bash
pip install pipwin
pipwin install pyaudio
```

### 3. Modelo de voz Vosk

1. Ve a **https://alphacephei.com/vosk/models**
2. Descarga **vosk-model-es-0.42** (~50 MB)
3. Descomprimelo y renombra la carpeta a `model`
4. Coloca la carpeta junto al script:

```
tu_carpeta/
    askme.py
    model/
        am/
        conf/
        ...
```

### 4. Configurar Spotify (opcional)

Si no usas Spotify puedes saltarte este paso, el asistente funciona igual sin el.

1. Ve a **https://developer.spotify.com/dashboard**
2. Inicia sesion y crea una app (nombre cualquiera)
3. En Settings, dentro de Redirect URIs agrega: `http://localhost:8888/callback`
4. Copia tu Client ID y Client Secret
5. Pegajos en el script donde dice:

```python
SPOTIFY_CLIENT_ID     = "TU_CLIENT_ID_AQUI"
SPOTIFY_CLIENT_SECRET = "TU_CLIENT_SECRET_AQUI"
```

La primera vez que ejecutes el script se abrira el navegador para autorizar el acceso. Despues queda guardado y no lo vuelve a pedir.

---

## Uso

```bash
python askme.py
```

Di en voz alta **"AskMe"** seguido de la accion que quieres realizar.

---

## Comandos disponibles

### Volumen
```
AskMe sube el volumen
AskMe baja el volumen
AskMe silencia
```

### Sistema
```
AskMe apaga
AskMe reinicia
AskMe suspende
AskMe cancela el apagado
```

### Spotify
```
AskMe pon Bohemian Rhapsody
AskMe pausa
AskMe reanuda
AskMe siguiente
AskMe anterior
AskMe que suena
```

### Google
```
AskMe busca recetas de pasta
AskMe busca el clima de hoy
```

### Aplicaciones
```
AskMe abre Chrome
AskMe abre Spotify
AskMe abre la calculadora
AskMe abre el explorador de archivos
AskMe abre VS Code
```

### Utilidades
```
AskMe que hora es
AskMe detente        <- cierra el asistente
```

---

## Notas importantes

- El reconocimiento de voz es 100% offline (Vosk).
- El control de Spotify y las busquedas en Google requieren internet.
- El control de Spotify via API siempre necesita conexion, incluso si la cancion esta descargada en la app.
- El apagado y reinicio tienen 10 segundos de gracia. Puedes cancelarlos diciendo `AskMe cancela el apagado`.
- Para agregar mas aplicaciones, edita el diccionario `APPS` en el script.

---

## Solucion de problemas

**"python" no se reconoce en CMD**
Agrega Python al PATH como se indica en el paso 1.

**sounddevice da error al instalar**
```bash
pip install pipwin
pipwin install pyaudio
```

**Vosk no entiende bien lo que digo**
Habla despacio y claro. Asegurate de que el microfono este bien configurado en Windows y sin mucho ruido ambiente.

**Spotify da error de autenticacion**
Borra el archivo `.spotify_cache` que se genera junto al script y vuelve a ejecutarlo para reautorizar.
