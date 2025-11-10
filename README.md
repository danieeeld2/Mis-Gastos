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
| `/ayuda` | `/ayuda` | Muestra tus objetivos de gasto actuales. |

---

## ☁️ Despliegue en Railway (Configuración)

Para poner tu bot en funcionamiento y accesible desde Telegram, la manera más rápida y recomendable es usar **Railway**.

### 1. Requisitos Previos

Necesitas obtener tu **Token de Bot** y gestionar la persistencia del archivo de base de datos (`gastos.db`):

1.  **Token de Telegram:** Crea un nuevo bot en Telegram usando **@BotFather** y guarda el `TOKEN`.
2.  **Base de Datos (`gastos.db`):** El bot utiliza una base de datos SQLite llamada `gastos.db`. Esta base de datos se **creará automáticamente** la primera vez que el bot se ejecute si no existe.

### 2. Pasos en Railway

Sigue estos pasos para conectar tu código a Railway:

1.  **Conexión a GitHub:**
    * Crea un nuevo proyecto en Railway y selecciona **"Deploy from GitHub Repo"**.
    * Conecta el repositorio donde tienes el código del bot.

2.  **Configuración de Variables de Entorno (¡Obligatorio!):**
    * Una vez que Railway detecte el repositorio, navega a la pestaña **`Variables`**.
    * Debes añadir una única variable de entorno:
        * **Clave:** `TELEGRAM_BOT_TOKEN`
        * **Valor:** Pega el Token que obtuviste de @BotFather.

3.  **Configuración de Persistencia (Volúmenes):**
    * Como el bot usa el archivo de base de datos local (`gastos.db`) para guardar la información, necesitamos que Railway lo mantenga incluso si el bot se reinicia.
    * Navega a la pestaña **`Settings`** (Ajustes) del servicio.
    * Busca la sección **`Files`** o **`Storage`** y configura un volumen de persistencia para que el archivo `gastos.db` se guarde de forma permanente. **Es crucial que este archivo persista** para que tus gastos no se pierdan.

4.  **Despliegue:**
    * Vuelve a la pestaña **`Deployments`** y revisa el log. Railway debería instalar las dependencias (listadas en `requirements.txt`) y ejecutar el bot.
    * Cuando veas el mensaje `🤖 Bot iniciado correctamente` en los logs, el bot estará en línea.

### 3. ¡Listo!

Busca tu bot en Telegram, comienza con el comando `/start` para configurar tus objetivos y, luego, usa `/gasto` para registrar tu primera transacción.