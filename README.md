# 💰 Gestor de Gastos en Telegram

Un bot de Telegram simple y eficiente para registrar y analizar tus gastos mensuales en tiempo real, utilizando **Python** y **Railway** para su despliegue.

---

## 🎯 ¿Qué hace este Bot?

Este bot actúa como tu **asistente personal de finanzas**. Su objetivo principal es simplificar el registro diario de gastos, permitiéndote:

* **Persistencia Robusta:** Utiliza **SQLite** (archivo `gastos.db`) para almacenar los datos de manera estructurada y segura.
* **Configuración Inicial:** Guía al usuario a través de la configuración inicial de **objetivos de gasto** con valores por defecto o manuales.
* **Registro Rápido:** Añadir gastos a categorías predefinidas con un simple comando.
* **Visibilidad:** Generar resúmenes y **gráficas** detalladas de tus patrones de consumo.
* **Referencia Objetiva:** Usar objetivos de gasto para guiarte en tus finanzas.
* **Flexibilidad:** Deshacer el último gasto y redefinir objetivos sobre la marcha.
* **🔐 Backup y Restore:** Sistema de copias de seguridad para proteger tus datos.

## ⚙️ Comandos del Bot

El bot utiliza comandos sencillos para interactuar con tus datos:

| Comando | Uso | Descripción |
| :--- | :--- | :--- |
| `/start` | `/start` | Inicia el bot y gestiona la **configuración inicial de objetivos**. |
| `/gasto <cat> <imp> [desc]` | `/gasto ocio 15.65 Cervezas` | Registra un nuevo gasto. |
| `/resumen` | `/resumen` | Muestra el total gastado por categoría en el mes actual. |
| `/grafica` | `/grafica` o `/grafica semanal` | Genera una visualización (gráfico de barras, tarta y evolución) de tus gastos. |
| `/estadisticas` | `/estadisticas` | Análisis de patrones de gasto (palabras frecuentes, día más caro, etc.). |
| `/redefinir <cat> <obj>` | `/redefinir ocio 400` | Cambia el valor objetivo de una categoría específica. |
| `/detalle <cat>` | `/detalle vivienda` | Muestra una lista de los últimos gastos de una categoría. |
| `/deshacer` | `/deshacer` | **Elimina el último gasto** registrado (ideal para errores). |
| `/backup` | `/backup` | 💾 **Descarga una copia de seguridad** de tu base de datos (solo admin). |
| `/restore` | `/restore` | 🔄 **Restaura la base de datos** desde un archivo .db (solo admin). |
| `/ayuda` | `/ayuda` | Muestra tus objetivos de gasto actuales. |

---

## 🔐 Sistema de Backup y Restore

### ¿Por qué es importante?

Railway usa almacenamiento efímero por defecto, lo que significa que **los datos pueden perderse** al redesplegar o si el contenedor se reinicia. El sistema de backup te protege contra la pérdida de datos.

### Comandos de Backup

#### `/backup` - Crear copia de seguridad
Descarga un archivo `.db` con toda tu información:
- 📊 Muestra estadísticas (total de gastos y usuarios)
- 📅 Incluye fecha y hora del backup
- 🔒 Solo accesible para el administrador configurado

#### `/restore` - Restaurar datos
Recupera tus datos desde un backup:
1. Envía el archivo `.db` al bot
2. Escribe `/restore` en el caption o como mensaje
3. El bot restaura automáticamente los datos
4. ✅ Crea un backup automático del estado actual antes de restaurar

### Recomendaciones

- 💾 Haz backup **antes** de cualquier actualización importante
- 📆 Realiza backups periódicos (semanal o mensual)
- ☁️ Guarda los backups en un lugar seguro (Google Drive, Dropbox, etc.)
- 🔄 Considera migrar a **Railway Volumes** para persistencia automática

---

## ☁️ Despliegue en Railway (Configuración)

Para poner tu bot en funcionamiento y accesible desde Telegram, la manera más rápida y recomendable es usar **Railway**.

### 1. Requisitos Previos

Necesitas obtener tu **Token de Bot** y tu **User ID** de Telegram:

1.  **Token de Telegram:** 
    * Crea un nuevo bot en Telegram usando **@BotFather** 
    * Guarda el `TOKEN` que te proporciona

2.  **User ID de Telegram:**
    * Envía `/start` a [@userinfobot](https://t.me/userinfobot)
    * Guarda tu `User ID` (ejemplo: `914546055`)
    * Este ID se usará para los comandos de backup/restore

3.  **Base de Datos (`gastos.db`):** 
    * El bot utiliza SQLite (`gastos.db`)
    * Se **crea automáticamente** la primera vez que se ejecuta

### 2. Pasos en Railway

Sigue estos pasos para conectar tu código a Railway:

1.  **Conexión a GitHub:**
    * Crea un nuevo proyecto en Railway
    * Selecciona **"Deploy from GitHub Repo"**
    * Conecta el repositorio donde tienes el código del bot

2.  **Configuración de Variables de Entorno (¡Obligatorio!):**
    * Una vez que Railway detecte el repositorio, navega a **`Variables`**
    * Añade las siguientes variables de entorno:
        
        | Variable | Valor | Descripción |
        |----------|-------|-------------|
        | `TELEGRAM_BOT_TOKEN` | Tu token de @BotFather | Token del bot de Telegram |
        | `ADMIN_USER_ID` | Tu User ID numérico | ID para comandos de backup/restore |

3.  **Configuración de Persistencia (Volúmenes) - Opcional pero Recomendado:**
    * Como el bot usa SQLite local, te recomendamos configurar un **volumen persistente**
    * Navega a **`Variables`** → **`Add Volume`**
    * **Mount Path:** `/data`
    * **Tamaño:** 1GB (más que suficiente)
    * **⚠️ Importante:** Si configuras un volumen, debes modificar la línea 37 de `bot.py`:
      ```python
      # Cambiar de:
      def __init__(self, db_file='gastos.db'):
      
      # A:
      def __init__(self, db_file='/data/gastos.db'):
      ```

4.  **Despliegue:**
    * Vuelve a **`Deployments`** y revisa el log
    * Railway instalará las dependencias (`requirements.txt`) automáticamente
    * Cuando veas `🤖 Bot iniciado correctamente`, el bot estará en línea

### 3. ¡Listo!

Busca tu bot en Telegram:
1. Envía `/start` para configurar tus objetivos
2. Usa `/gasto` para registrar tu primera transacción
3. **¡Importante!** Haz tu primer backup con `/backup` para proteger tus datos

---

## 📊 Estructura del Proyecto

```
📁 proyecto/
├── bot.py              # Código principal del bot
├── requirements.txt    # Dependencias de Python
├── .env.example        # Plantilla de variables de entorno
├── .gitignore         # Archivos a ignorar en Git
└── README.md          # Este archivo
```

---

## 🔧 Desarrollo Local (Opcional)

Si quieres probar el bot en tu computadora:

1. **Clona el repositorio:**
   ```bash
   git clone <tu-repo>
   cd <tu-repo>
   ```

2. **Crea un archivo `.env`:**
   ```bash
   cp .env.example .env
   ```
   
   Edita `.env` y añade tus credenciales:
   ```
   TELEGRAM_BOT_TOKEN=tu_token_aqui
   ADMIN_USER_ID=tu_user_id_aqui
   ```

3. **Instala dependencias:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Ejecuta el bot:**
   ```bash
   python bot.py
   ```

**⚠️ Nota:** Nunca subas el archivo `.env` a Git (ya está protegido por `.gitignore`)

---

## 🛠️ Tecnologías Utilizadas

* **Python 3.x** - Lenguaje principal
* **python-telegram-bot** - Librería para interactuar con la API de Telegram
* **SQLite** - Base de datos ligera y embebida
* **Matplotlib** - Generación de gráficas
* **Railway** - Plataforma de despliegue en la nube

---

## 📝 Notas Importantes

### Seguridad
* ✅ Las credenciales están en variables de entorno (no en el código)
* ✅ El `.env` está protegido por `.gitignore`
* ✅ Los comandos de backup/restore solo funcionan para el admin configurado

### Persistencia de Datos
* ⚠️ **Sin volumen:** Los datos se pierden al redesplegar
* ✅ **Con volumen:** Los datos persisten automáticamente
* 💾 **Con backups:** Puedes recuperar datos manualmente

### Recomendaciones
1. Haz backups regulares con `/backup`
2. Guarda los archivos `.db` en un lugar seguro
3. Considera usar Railway Volumes para mayor tranquilidad
4. Mantén actualizado el `ADMIN_USER_ID` en Railway

---

## 🆘 Troubleshooting

### El bot no responde
* Verifica que las variables de entorno estén configuradas en Railway
* Revisa los logs en Railway para ver errores
* Asegúrate de que el bot esté iniciado (@BotFather)

### `/backup` dice "Solo el administrador..."
* Verifica que `ADMIN_USER_ID` esté configurado en Railway
* Confirma que el valor sea tu User ID correcto (número sin comillas)

### Se perdieron los datos
* Si no tienes backup: los datos se han perdido definitivamente
* Si tienes backup: usa `/restore` para recuperarlos
* Considera configurar Railway Volumes para evitar esto en el futuro

---

## 📄 Licencia

Este proyecto es de código abierto. Siéntete libre de usarlo, modificarlo y adaptarlo a tus necesidades.

---

**¿Preguntas o sugerencias?** Abre un issue en GitHub o contacta al desarrollador.