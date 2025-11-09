# 💰 Gestor de Gastos en Telegram

Un bot de Telegram simple y eficiente para registrar y analizar tus gastos mensuales en tiempo real, utilizando **Python** y **Railway** para su despliegue.

---

## 🎯 ¿Qué hace este Bot?

Este bot actúa como tu **asistente personal de finanzas**. Su objetivo principal es simplificar el registro diario de gastos, permitiéndote:

* **Registro Rápido:** Añadir gastos a categorías predefinidas con un simple comando.
* **Visibilidad:** Generar resúmenes y **gráficas** detalladas de tus patrones de consumo.
* **Referencia Objetiva:** Usar objetivos de gasto (no límites estrictos) para guiarte en tus finanzas.
* **Flexibilidad:** Deshacer el último gasto y redefinir objetivos sobre la marcha.

## ⚙️ Comandos del Bot

El bot utiliza comandos sencillos para interactuar con tus datos:

| Comando | Uso | Descripción |
| :--- | :--- | :--- |
| `/gasto <cat> <imp> [desc]` | `/gasto ocio 15.65 Cervezas` | Registra un nuevo gasto. |
| `/deshacer` | `/deshacer` | **Elimina el último gasto** registrado (ideal para errores). |
| `/resumen` | `/resumen` | Muestra el total gastado por categoría en el mes actual. |
| `/grafica` | `/grafica` / `/grafica semanal` | Genera una visualización (gráfico de barras y tarta) de tus gastos. |
| `/redefinir <cat> <obj>` | `/redefinir ocio 400` | Cambia el valor objetivo de una categoría específica. |
| `/detalle <cat>` | `/detalle vivienda` | Muestra una lista de los últimos gastos de una categoría. |

---

## ☁️ Despliegue en Railway (Configuración)

Para poner tu bot en funcionamiento y accesible desde Telegram, la manera más rápida y recomendable es usar **Railway**.

### 1. Requisitos Previos

Necesitas obtener tu **Token de Bot** y un **archivo de datos** para persistencia:

1.  **Token de Telegram:** Crea un nuevo bot en Telegram usando **@BotFather** y guarda el `TOKEN`.
2.  **Archivo de Gastos (`gastos.json`):** El bot guarda todos los datos de gasto en un archivo llamado `gastos.json` que necesita ser creado o gestionado.
    * *Opción simple:* Sube el código a tu repositorio de GitHub y asegúrate de que el archivo `gastos.json` (aunque esté vacío, con `{}`) esté presente.

### 2. Pasos en Railway

Sigue estos pasos para conectar tu código a Railway:

1.  **Conexión a GitHub:**
    * Crea un nuevo proyecto en Railway y selecciona **"Deploy from GitHub Repo"**.
    * Conecta el repositorio donde tienes el código del bot.

2.  **Configuración de Variables de Entorno:**
    * Una vez que Railway detecte el repositorio, navega a la pestaña **`Variables`**.
    * Debes añadir una única variable de entorno:
        * **Clave:** `TELEGRAM_BOT_TOKEN`
        * **Valor:** Pega el Token que obtuviste de @BotFather.

3.  **Configuración de Persistencia (Volúmenes):**
    * Como el bot usa un archivo local (`gastos.json`) para guardar la información, necesitamos que Railway lo mantenga incluso si el bot se reinicia.
    * Navega a la pestaña **`Settings`** (Ajustes) del servicio.
    * Busca la sección **`Files`** o **`Storage`** y configura un volumen de persistencia para el directorio raíz del proyecto o directamente para el archivo `gastos.json`.
        * *En Railway, la forma más sencilla es que el bot escriba en el disco y Railway mantenga ese disco.* Si el `gastos.json` está en la raíz, suele funcionar por defecto, pero asegúrate de que el log de Railway no muestre errores de permisos de escritura.

4.  **Despliegue:**
    * Vuelve a la pestaña **`Deployments`** y revisa el log. Railway debería instalar las dependencias (como `python-telegram-bot` y `matplotlib`) y ejecutar `main.py`.
    * Cuando veas el mensaje `🤖 Bot iniciado correctamente` en los logs, el bot estará en línea.

### 3. ¡Listo!

Busca tu bot en Telegram y comienza a usar el comando `/start` o `/gasto` para registrar tu primera transacción.