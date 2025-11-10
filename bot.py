import os
import logging
from datetime import datetime, timedelta
from telegram import Update, BotCommand, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, ConversationHandler
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import sqlite3
from pathlib import Path
import io
from collections import Counter
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Estados para el ConversationHandler
CONFIGURANDO_CATEGORIA = range(1)

CATEGORIAS_DEFAULT = {
    "vivienda": {"objetivo": 800, "nombre": "Alquiler y gastos de casa"},
    "ocio": {"objetivo": 350, "nombre": "Suscripciones, fiestas, etc."},
    "inversiones": {"objetivo": 0, "nombre": "SP500 y otras inversiones"},
    "ahorro": {"objetivo": 700, "nombre": "Ahorro"},
    "transporte": {"objetivo": 10, "nombre": "Uber, metro..."},
    "viajes": {"objetivo": 300, "nombre": "Escapadas y vacaciones"},
    "comida": {"objetivo": 230, "nombre": "Comidas"},
    "otros": {"objetivo": 100, "nombre": "Otros gastos"}
}

class GestorGastos:
    def __init__(self, db_file='gastos.db'):
        self.db_file = db_file
        self._inicializar_db()
    
    def _inicializar_db(self):
        """Crea las tablas si no existen"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Tabla de categorías (objetivos personalizados por usuario)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categorias (
                user_id INTEGER,
                categoria TEXT,
                objetivo REAL,
                nombre TEXT,
                PRIMARY KEY (user_id, categoria)
            )
        ''')
        
        # Tabla de gastos
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS gastos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                fecha TIMESTAMP NOT NULL,
                categoria TEXT NOT NULL,
                importe REAL NOT NULL,
                descripcion TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Índices para mejorar rendimiento
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gastos_user_fecha ON gastos(user_id, fecha)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_gastos_categoria ON gastos(user_id, categoria)')
        
        conn.commit()
        conn.close()
    
    def usuario_configurado(self, user_id):
        """Verifica si el usuario ya configuró sus objetivos"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM categorias WHERE user_id = ?', (user_id,))
        count = cursor.fetchone()[0]
        conn.close()
        return count > 0
    
    def configurar_categorias_default(self, user_id):
        """Configura las categorías por defecto para un nuevo usuario"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        for cat, info in CATEGORIAS_DEFAULT.items():
            cursor.execute('''
                INSERT OR REPLACE INTO categorias (user_id, categoria, objetivo, nombre)
                VALUES (?, ?, ?, ?)
            ''', (user_id, cat, info['objetivo'], info['nombre']))
        
        conn.commit()
        conn.close()
    
    def obtener_categorias(self, user_id):
        """Obtiene las categorías configuradas del usuario"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            SELECT categoria, objetivo, nombre 
            FROM categorias 
            WHERE user_id = ?
            ORDER BY categoria
        ''', (user_id,))
        
        categorias = {}
        for row in cursor.fetchall():
            categorias[row[0]] = {"objetivo": row[1], "nombre": row[2]}
        
        conn.close()
        return categorias
    
    def actualizar_objetivo(self, user_id, categoria, nuevo_objetivo):
        """Actualiza el objetivo de una categoría"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE categorias 
            SET objetivo = ? 
            WHERE user_id = ? AND categoria = ?
        ''', (nuevo_objetivo, user_id, categoria))
        conn.commit()
        conn.close()
    
    def agregar_gasto(self, user_id, categoria, importe, descripcion=""):
        """Registra un nuevo gasto"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO gastos (user_id, fecha, categoria, importe, descripcion)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, datetime.now(), categoria, importe, descripcion))
        
        conn.commit()
        conn.close()
        return True
    
    def eliminar_ultimo_gasto(self, user_id):
        """Elimina el último gasto registrado"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Obtener el último gasto
        cursor.execute('''
            SELECT id, importe, categoria 
            FROM gastos 
            WHERE user_id = ?
            ORDER BY fecha DESC, id DESC
            LIMIT 1
        ''', (user_id,))
        
        resultado = cursor.fetchone()
        
        if resultado:
            gasto_id, importe, categoria = resultado
            cursor.execute('DELETE FROM gastos WHERE id = ?', (gasto_id,))
            conn.commit()
            conn.close()
            return {"exito": True, "importe": importe, "categoria": categoria}
        
        conn.close()
        return {"exito": False}
    
    def obtener_gastos_rango(self, user_id, fecha_inicio, fecha_fin):
        """Obtiene gastos en un rango de fechas"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fecha, categoria, importe, descripcion
            FROM gastos
            WHERE user_id = ? AND fecha BETWEEN ? AND ?
            ORDER BY fecha
        ''', (user_id, fecha_inicio, fecha_fin))
        
        gastos = []
        for row in cursor.fetchall():
            gastos.append({
                "fecha": row[0],
                "categoria": row[1],
                "importe": row[2],
                "descripcion": row[3]
            })
        
        conn.close()
        return gastos
    
    def obtener_resumen_mes(self, user_id, mes=None):
        """Obtiene el resumen de gastos de un mes"""
        if mes is None:
            mes = datetime.now().strftime("%Y-%m")
        
        fecha_inicio = datetime.strptime(mes + "-01", "%Y-%m-%d")
        if fecha_inicio.month == 12:
            fecha_fin = fecha_inicio.replace(year=fecha_inicio.year + 1, month=1, day=1)
        else:
            fecha_fin = fecha_inicio.replace(month=fecha_inicio.month + 1, day=1)
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT categoria, SUM(importe), COUNT(*)
            FROM gastos
            WHERE user_id = ? AND fecha >= ? AND fecha < ?
            GROUP BY categoria
        ''', (user_id, fecha_inicio, fecha_fin))
        
        resumen = {}
        categorias = self.obtener_categorias(user_id)
        
        for row in cursor.fetchall():
            categoria = row[0]
            resumen[categoria] = {
                "total": row[1],
                "cantidad": row[2],
                "objetivo": categorias.get(categoria, {}).get("objetivo", 0)
            }
        
        conn.close()
        return resumen
    
    def buscar_gastos(self, user_id, termino):
        """Busca gastos por descripción"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT fecha, categoria, importe, descripcion
            FROM gastos
            WHERE user_id = ? AND descripcion LIKE ?
            ORDER BY fecha DESC
        ''', (user_id, f'%{termino}%'))
        
        resultados = []
        for row in cursor.fetchall():
            resultados.append({
                "fecha": row[0],
                "categoria": row[1],
                "importe": row[2],
                "descripcion": row[3]
            })
        
        conn.close()
        return resultados
    
    def obtener_estadisticas(self, user_id, fecha_inicio, fecha_fin):
        """Obtiene estadísticas de gastos"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Palabras más frecuentes
        cursor.execute('''
            SELECT descripcion
            FROM gastos
            WHERE user_id = ? AND fecha BETWEEN ? AND ? AND descripcion != ''
        ''', (user_id, fecha_inicio, fecha_fin))
        
        palabras = []
        stop_words = {'de', 'del', 'la', 'el', 'en', 'con', 'por', 'para', 'a', 'y', 'o', 'un', 'una'}
        
        for row in cursor.fetchall():
            desc = row[0].lower()
            palabras_desc = re.findall(r'\b\w{3,}\b', desc)
            palabras.extend([p for p in palabras_desc if p not in stop_words])
        
        palabras_frecuentes = Counter(palabras).most_common(10)
        
        conn.close()
        return {"palabras_frecuentes": palabras_frecuentes}

gestor = GestorGastos()

async def configurar_comandos(application: Application):
    commands = [
        BotCommand("start", "Inicio y configuración"),
        BotCommand("gasto", "Registra un nuevo gasto"),
        BotCommand("resumen", "Resumen de gastos del mes"),
        BotCommand("grafica", "Genera gráficas de gastos"),
        BotCommand("detalle", "Detalle de una categoría"),
        BotCommand("buscar", "Busca gastos por descripción"),
        BotCommand("estadisticas", "Análisis de patrones de gasto"),
        BotCommand("redefinir", "Cambia el objetivo de gasto"),
        BotCommand("configurar", "Reconfigura tus objetivos"),
        BotCommand("deshacer", "Elimina el último gasto"),
        BotCommand("ayuda", "Información y ayuda")
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("✅ Comandos configurados")
    except Exception as e:
        logger.error(f"❌ Error al configurar comandos: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        # Primera vez - mostrar mensaje de bienvenida y pedir configuración
        mensaje = """
🏦 *¡Bienvenido al Bot de Gestión de Gastos!*

👋 Veo que es tu primera vez aquí. 

Antes de empezar, necesito que configures tus *objetivos mensuales* para cada categoría de gasto.

Puedes elegir entre:
"""
        keyboard = [
            [InlineKeyboardButton("✨ Usar objetivos recomendados", callback_data="config_default")],
            [InlineKeyboardButton("⚙️ Configurar manualmente", callback_data="config_manual")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=reply_markup)
        return
    
    # Usuario ya configurado
    mensaje = """
🏦 *Bot de Gestión de Gastos*

¡Hola de nuevo! Aquí están los comandos disponibles:

*📝 Registrar:*
• `/gasto <cat> <importe> [desc]` - Añadir gasto
• `/deshacer` - Eliminar último gasto

*📊 Consultar:*
• `/resumen` - Ver resumen del mes
• `/grafica` - Ver gráficas
• `/detalle <cat>` - Detalles de categoría
• `/buscar <término>` - Buscar gastos
• `/estadisticas` - Análisis de patrones

*⚙️ Configuración:*
• `/redefinir <cat> <objetivo>` - Cambiar un objetivo
• `/configurar` - Reconfigurar todo
• `/ayuda` - Ver tus objetivos actuales
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def boton_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "config_default":
        # Usar configuración por defecto
        gestor.configurar_categorias_default(user_id)
        
        mensaje = """
✅ *¡Configuración completada!*

He configurado tus objetivos con valores recomendados:

"""
        categorias = gestor.obtener_categorias(user_id)
        total = 0
        for cat, info in categorias.items():
            mensaje += f"• *{info['nombre']}*: {info['objetivo']}€\n"
            if cat not in ["ahorro", "inversiones"]:
                total += info['objetivo']
        
        mensaje += f"""
━━━━━━━━━━━━━━━━━
💰 *Total objetivos:* {total}€

Puedes cambiar cualquier objetivo con:
`/redefinir <categoría> <nuevo_importe>`

¡Ya puedes empezar a registrar gastos! 🎉
Usa `/gasto <categoría> <importe> [descripción]`
"""
        await query.edit_message_text(mensaje, parse_mode='Markdown')
    
    elif query.data == "config_manual":
        mensaje = """
⚙️ *Configuración Manual*

Para configurar cada categoría, usa el comando:
`/redefinir <categoría> <objetivo>`

*Categorías disponibles:*
"""
        # Primero configurar con defaults y luego el usuario modifica
        gestor.configurar_categorias_default(user_id)
        categorias = gestor.obtener_categorias(user_id)
        
        for cat, info in categorias.items():
            mensaje += f"• `{cat}` - {info['nombre']}\n"
        
        mensaje += f"""
━━━━━━━━━━━━━━━━━
*Ejemplo:*
`/redefinir ocio 400`
`/redefinir comida 300`

Cuando termines, usa `/ayuda` para ver tu configuración.
"""
        await query.edit_message_text(mensaje, parse_mode='Markdown')

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        await update.message.reply_text(
            "⚠️ Primero debes configurar tus objetivos con `/start`"
        )
        return
    
    categorias = gestor.obtener_categorias(user_id)
    
    mensaje = f"📋 *Tus Objetivos de Gasto Mensual:*\n\n"
    
    total_presupuesto = 0
    for cat, info in categorias.items():
        if cat not in ["ahorro", "inversiones"]:
            total_presupuesto += info['objetivo']
        mensaje += f"• *{info['nombre']}*: {info['objetivo']}€\n"
    
    mensaje += f"""
━━━━━━━━━━━━━━━━━
💰 *Suma de objetivos:* {total_presupuesto}€

*💡 Tips:*
• Usa `/redefinir <cat> <objetivo>` para ajustar
• Registra gastos al momento: `/gasto <cat> <imp>`
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def configurar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Permite reconfigurar todos los objetivos"""
    user_id = update.effective_user.id
    
    mensaje = """
⚙️ *Reconfigurar Objetivos*

Elige cómo quieres reconfigurar:
"""
    keyboard = [
        [InlineKeyboardButton("✨ Restaurar valores recomendados", callback_data="config_default")],
        [InlineKeyboardButton("⚙️ Configurar manualmente", callback_data="config_manual")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(mensaje, parse_mode='Markdown', reply_markup=reply_markup)

async def registrar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        await update.message.reply_text(
            "⚠️ Primero debes configurar tus objetivos con `/start`"
        )
        return
    
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Formato: `/gasto <categoría> <importe> [descripción]`\n"
                "Ejemplo: `/gasto ocio 25.50 Netflix`",
                parse_mode='Markdown'
            )
            return
        
        categoria = context.args[0].lower()
        categorias = gestor.obtener_categorias(user_id)
        
        if categoria not in categorias:
            cats = ", ".join(categorias.keys())
            await update.message.reply_text(
                f"❌ Categoría no válida.\nCategorías: `{cats}`",
                parse_mode='Markdown'
            )
            return
        
        try:
            importe = float(context.args[1].replace(',', '.'))
            if importe <= 0:
                await update.message.reply_text("❌ El importe debe ser mayor que 0")
                return
        except ValueError:
            await update.message.reply_text("❌ Importe no válido")
            return
        
        descripcion = " ".join(context.args[2:]) if len(context.args) > 2 else ""
        
        gestor.agregar_gasto(user_id, categoria, importe, descripcion)
        
        resumen = gestor.obtener_resumen_mes(user_id)
        cat_info = resumen.get(categoria, {})
        total = cat_info.get("total", importe)
        objetivo = categorias[categoria]["objetivo"]
        porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
        
        emoji = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
        
        mensaje = f"""
✅ *Gasto registrado*

📁 {categorias[categoria]['nombre']}
💶 {importe:.2f}€
"""
        if descripcion:
            mensaje += f"📝 {descripcion}\n"
        
        mensaje += f"""
━━━━━━━━━━━━━━━━━
📊 Total: {total:.2f}€ / {objetivo}€
{emoji} {porcentaje:.1f}% del objetivo
"""
        
        if porcentaje > 100:
            mensaje += f"\n⚠️ Exceso: {total-objetivo:.2f}€"
        elif porcentaje > 80:
            mensaje += f"\n💡 Quedan: {objetivo-total:.2f}€"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error al registrar gasto: {e}")
        await update.message.reply_text("❌ Error al registrar el gasto")

async def deshacer_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    try:
        resultado = gestor.eliminar_ultimo_gasto(user_id)
        
        if resultado["exito"]:
            categorias = gestor.obtener_categorias(user_id)
            nombre = categorias[resultado['categoria']]['nombre']
            
            await update.message.reply_text(
                f"🗑️ *Gasto eliminado*\n"
                f"Importe: {resultado['importe']:.2f}€\n"
                f"Categoría: {nombre}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ No hay gastos para eliminar")
            
    except Exception as e:
        logger.error(f"Error al deshacer: {e}")
        await update.message.reply_text("❌ Error al eliminar el gasto")

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        await update.message.reply_text("⚠️ Configura tus objetivos con `/start`")
        return
    
    resumen_mes = gestor.obtener_resumen_mes(user_id)
    categorias = gestor.obtener_categorias(user_id)
    
    if not resumen_mes:
        await update.message.reply_text("📭 No hay gastos este mes")
        return
    
    mes = datetime.now().strftime("%B %Y")
    mensaje = f"📊 *Resumen de {mes}*\n\n"
    
    total_gastado = 0
    
    for categoria in categorias.keys():
        if categoria in resumen_mes:
            info = resumen_mes[categoria]
            nombre = categorias[categoria]["nombre"]
            total = info["total"]
            objetivo = categorias[categoria]["objetivo"]
            
            porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
            total_gastado += total
            
            emoji = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
            
            mensaje += f"{emoji} *{nombre}*\n"
            mensaje += f"   {total:.2f}€ / {objetivo}€ ({porcentaje:.1f}%)\n\n"
    
    presupuesto_total = sum(v["objetivo"] for k, v in categorias.items() 
                           if k not in ["ahorro", "inversiones"])
    
    mensaje += f"━━━━━━━━━━━━━━━━━\n"
    mensaje += f"💰 *Total:* {total_gastado:.2f}€ / {presupuesto_total}€"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def redefinir_objetivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        await update.message.reply_text("⚠️ Configura tus objetivos con `/start`")
        return
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Uso: `/redefinir <categoría> <objetivo>`\n"
            "Ejemplo: `/redefinir ocio 400`",
            parse_mode='Markdown'
        )
        return
    
    categoria = context.args[0].lower()
    categorias = gestor.obtener_categorias(user_id)
    
    if categoria not in categorias:
        cats = ", ".join(categorias.keys())
        await update.message.reply_text(
            f"❌ Categoría no válida.\nCategorías: `{cats}`",
            parse_mode='Markdown'
        )
        return
    
    try:
        nuevo_objetivo = float(context.args[1].replace(',', '.'))
        if nuevo_objetivo < 0:
            await update.message.reply_text("❌ El objetivo debe ser positivo")
            return
    except ValueError:
        await update.message.reply_text("❌ Objetivo no válido")
        return
    
    gestor.actualizar_objetivo(user_id, categoria, nuevo_objetivo)
    
    await update.message.reply_text(
        f"✅ *Objetivo actualizado*\n"
        f"{categorias[categoria]['nombre']}: *{nuevo_objetivo:.2f}€*",
        parse_mode='Markdown'
    )

# Placeholders para los demás comandos (grafica, detalle, buscar, estadisticas)
# Los puedes adaptar fácilmente cambiando las llamadas a gestor

async def detalle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Uso: `/detalle <categoría>`",
            parse_mode='Markdown'
        )
        return
    
    categoria = context.args[0].lower()
    categorias = gestor.obtener_categorias(user_id)
    
    if categoria not in categorias:
        await update.message.reply_text("❌ Categoría no válida")
        return
    
    mes_actual = datetime.now()
    inicio_mes = mes_actual.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    gastos = gestor.obtener_gastos_rango(user_id, inicio_mes, mes_actual)
    gastos_cat = [g for g in gastos if g['categoria'] == categoria]
    
    if not gastos_cat:
        await update.message.reply_text(
            f"📭 No hay gastos en '{categorias[categoria]['nombre']}' este mes"
        )
        return
    
    mensaje = f"📋 *{categorias[categoria]['nombre']}*\n\n"
    total = 0
    
    for gasto in gastos_cat[:20]:
        fecha = datetime.fromisoformat(gasto["fecha"])
        fecha_str = fecha.strftime("%d/%m %H:%M")
        total += gasto["importe"]
        
        mensaje += f"• {fecha_str} - {gasto['importe']:.2f}€"
        if gasto.get("descripcion"):
            mensaje += f"\n  _{gasto['descripcion']}_"
        mensaje += "\n\n"
    
    objetivo = categorias[categoria]["objetivo"]
    porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
    
    mensaje += f"━━━━━━━━━━━━━━━━━\n"
    mensaje += f"Total: {total:.2f}€ / {objetivo}€"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Uso: `/buscar <término>`",
            parse_mode='Markdown'
        )
        return
    
    termino = " ".join(context.args)
    resultados = gestor.buscar_gastos(user_id, termino)
    categorias = gestor.obtener_categorias(user_id)
    
    if not resultados:
        await update.message.reply_text(f"🔍 No se encontraron gastos con '{termino}'")
        return
    
    total = sum(r["importe"] for r in resultados)
    mensaje = f"🔍 *'{termino}'*\n{len(resultados)} gastos · {total:.2f}€\n\n"
    
    for gasto in resultados[:15]:
        fecha = datetime.fromisoformat(gasto["fecha"])
        fecha_str = fecha.strftime("%d/%m/%Y")
        cat_nombre = categorias[gasto["categoria"]]["nombre"]
        
        mensaje += f"• {fecha_str} - {gasto['importe']:.2f}€\n"
        mensaje += f"  {cat_nombre}\n"
        if gasto.get("descripcion"):
            mensaje += f"  _{gasto['descripcion']}_\n"
        mensaje += "\n"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        await update.message.reply_text("⚠️ Configura tus objetivos con `/start`")
        return
    
    await update.message.reply_text("📊 Analizando tus gastos...")
    
    mes_actual = datetime.now()
    inicio_mes = mes_actual.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    gastos_mes = gestor.obtener_gastos_rango(user_id, inicio_mes, mes_actual)
    
    if not gastos_mes:
        await update.message.reply_text("📭 No hay suficientes datos")
        return
    
    stats = gestor.obtener_estadisticas(user_id, inicio_mes, mes_actual)
    
    # Análisis por día de la semana
    gastos_por_dia = {i: [] for i in range(7)}
    dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    for gasto in gastos_mes:
        fecha = datetime.fromisoformat(gasto["fecha"])
        dia = fecha.weekday()
        gastos_por_dia[dia].append(gasto["importe"])
    
    promedios = {dia: sum(g)/len(g) if g else 0 for dia, g in gastos_por_dia.items()}
    dia_mayor = max(promedios, key=promedios.get)
    
    dias_con_gastos = len(set(datetime.fromisoformat(g["fecha"]).date() for g in gastos_mes))
    promedio_diario = sum(g["importe"] for g in gastos_mes) / dias_con_gastos if dias_con_gastos > 0 else 0
    
    gasto_max = max(gastos_mes, key=lambda x: x["importe"])
    gasto_min = min(gastos_mes, key=lambda x: x["importe"])
    
    mensaje = f"📊 *Estadísticas del Mes*\n\n"
    mensaje += f"📈 *Resumen:*\n"
    mensaje += f"• Total gastos: {len(gastos_mes)}\n"
    mensaje += f"• Promedio diario: {promedio_diario:.2f}€\n"
    mensaje += f"• Día con más gasto: {dias[dia_mayor]}\n\n"
    
    mensaje += f"💰 *Extremos:*\n"
    mensaje += f"• Mayor: {gasto_max['importe']:.2f}€\n"
    if gasto_max.get('descripcion'):
        mensaje += f"  _{gasto_max['descripcion']}_\n"
    mensaje += f"• Menor: {gasto_min['importe']:.2f}€\n"
    if gasto_min.get('descripcion'):
        mensaje += f"  _{gasto_min['descripcion']}_\n"
    
    if stats["palabras_frecuentes"]:
        mensaje += f"\n🔤 *Palabras frecuentes:*\n"
        for palabra, freq in stats["palabras_frecuentes"][:5]:
            mensaje += f"• {palabra}: {freq}x\n"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def grafica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not gestor.usuario_configurado(user_id):
        await update.message.reply_text("⚠️ Configura tus objetivos con `/start`")
        return
    
    try:
        ahora = datetime.now()
        
        # Determinar rango de fechas
        if len(context.args) == 0 or context.args[0] == "mensual":
            fecha_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = ahora
            titulo = "Gastos del Mes Actual"
        elif context.args[0] == "semanal":
            fecha_inicio = ahora - timedelta(days=7)
            fecha_fin = ahora
            titulo = "Última Semana"
        else:
            await update.message.reply_text(
                "❌ Uso: `/grafica [mensual|semanal]`",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text("📊 Generando gráfica...")
        
        gastos = gestor.obtener_gastos_rango(user_id, fecha_inicio, fecha_fin)
        categorias = gestor.obtener_categorias(user_id)
        
        if not gastos:
            await update.message.reply_text("📭 No hay gastos en el período")
            return
        
        # Agrupar por categoría
        gastos_por_cat = {}
        for gasto in gastos:
            cat = gasto["categoria"]
            if cat not in gastos_por_cat:
                gastos_por_cat[cat] = []
            gastos_por_cat[cat].append(gasto)
        
        # Crear figura con 3 gráficas
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. Gráfica de barras: Gastado vs Objetivo
        ax1 = fig.add_subplot(gs[0, 0])
        cats = []
        totales = []
        objetivos_list = []
        colores = []
        
        for cat in categorias.keys():
            if cat in gastos_por_cat:
                nombre = categorias[cat]["nombre"]
                total = sum(g["importe"] for g in gastos_por_cat[cat])
                objetivo = categorias[cat]["objetivo"]
                
                cats.append(nombre[:20])
                totales.append(total)
                objetivos_list.append(objetivo)
                
                porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
                if porcentaje <= 80:
                    colores.append('#2ecc71')
                elif porcentaje <= 100:
                    colores.append('#f39c12')
                else:
                    colores.append('#e74c3c')
        
        x = range(len(cats))
        width = 0.35
        
        ax1.bar([i - width/2 for i in x], totales, width, label='Gastado', color=colores)
        ax1.bar([i + width/2 for i in x], objetivos_list, width, label='Objetivo', 
                color='#3498db', alpha=0.6)
        
        ax1.set_xlabel('Categoría', fontsize=10)
        ax1.set_ylabel('Importe (€)', fontsize=10)
        ax1.set_title('Gastos vs Objetivo', fontsize=12, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(cats, rotation=45, ha='right', fontsize=9)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. Gráfica de tarta: Distribución
        ax2 = fig.add_subplot(gs[0, 1])
        colores_tarta = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c', '#34495e', '#e67e22']
        
        if totales:
            ax2.pie(totales, labels=cats, autopct='%1.1f%%', colors=colores_tarta, startangle=90)
            ax2.set_title('Distribución de Gastos', fontsize=12, fontweight='bold')
        
        # 3. Evolución temporal
        ax3 = fig.add_subplot(gs[1, :])
        
        gastos_por_dia = {}
        for gasto in gastos:
            fecha = datetime.fromisoformat(gasto["fecha"]).date()
            if fecha not in gastos_por_dia:
                gastos_por_dia[fecha] = 0
            gastos_por_dia[fecha] += gasto["importe"]
        
        fechas = sorted(gastos_por_dia.keys())
        importes_diarios = [gastos_por_dia[f] for f in fechas]
        
        # Acumulado
        acumulado = []
        suma = 0
        for imp in importes_diarios:
            suma += imp
            acumulado.append(suma)
        
        ax3_2 = ax3.twinx()
        
        ax3.bar(fechas, importes_diarios, color='#3498db', alpha=0.6, label='Gasto diario')
        ax3_2.plot(fechas, acumulado, color='#e74c3c', linewidth=2, marker='o', label='Acumulado')
        
        ax3.set_xlabel('Fecha', fontsize=10)
        ax3.set_ylabel('Gasto diario (€)', fontsize=10, color='#3498db')
        ax3_2.set_ylabel('Gasto acumulado (€)', fontsize=10, color='#e74c3c')
        ax3.set_title('Evolución Temporal', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        ax3.tick_params(axis='x', rotation=45)
        
        if len(fechas) > 15:
            ax3.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        else:
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        lines1, labels1 = ax3.get_legend_handles_labels()
        lines2, labels2 = ax3_2.get_legend_handles_labels()
        ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.suptitle(titulo, fontsize=14, fontweight='bold', y=0.98)
        
        # Guardar y enviar
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        total_periodo = sum(g["importe"] for g in gastos)
        caption = f"💰 Total: {total_periodo:.2f}€ | 📊 {len(gastos)} gastos"
        
        await update.message.reply_photo(photo=buf, caption=caption)
        buf.close()
        
    except Exception as e:
        logger.error(f"Error al generar gráfica: {e}")
        await update.message.reply_text(f"❌ Error: {str(e)}")

def main():
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Error: TELEGRAM_BOT_TOKEN no encontrado")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    # Configurar comandos
    application.post_init = configurar_comandos
    
    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("configurar", configurar))
    application.add_handler(CommandHandler("gasto", registrar_gasto))
    application.add_handler(CommandHandler("deshacer", deshacer_gasto))
    application.add_handler(CommandHandler("resumen", resumen))
    application.add_handler(CommandHandler("detalle", detalle))
    application.add_handler(CommandHandler("buscar", buscar))
    application.add_handler(CommandHandler("estadisticas", estadisticas))
    application.add_handler(CommandHandler("grafica", grafica))
    application.add_handler(CommandHandler("redefinir", redefinir_objetivo))
    
    # Callback para botones
    application.add_handler(CallbackQueryHandler(boton_callback))
    
    print("🤖 Bot iniciado correctamente")
    print("📊 Usando SQLite para almacenamiento")
    print("Presiona Ctrl+C para detener")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()