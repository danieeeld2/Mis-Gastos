import os
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import json
from pathlib import Path
import io
from collections import Counter
import re

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PRESUPUESTO = {
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
    def __init__(self, data_file='gastos.json'):
        self.data_file = data_file
        self.gastos = self._cargar_datos()
    
    def _cargar_datos(self):
        if Path(self.data_file).exists():
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}
    
    def _guardar_datos(self):
        with open(self.data_file, 'w', encoding='utf-8') as f:
            json.dump(self.gastos, f, ensure_ascii=False, indent=2)
    
    def agregar_gasto(self, categoria, importe, descripcion=""):
        mes_actual = datetime.now().strftime("%Y-%m")
        
        if mes_actual not in self.gastos:
            self.gastos[mes_actual] = {}
        
        if categoria not in self.gastos[mes_actual]:
            self.gastos[mes_actual][categoria] = []
        
        gasto = {
            "fecha": datetime.now().isoformat(),
            "importe": importe,
            "descripcion": descripcion
        }
        
        self.gastos[mes_actual][categoria].append(gasto)
        self._guardar_datos()
        return True
    
    def obtener_gastos_rango(self, fecha_inicio, fecha_fin):
        """Obtiene todos los gastos en un rango de fechas"""
        gastos_filtrados = []
        
        for mes, categorias in self.gastos.items():
            for categoria, gastos in categorias.items():
                for gasto in gastos:
                    fecha_gasto = datetime.fromisoformat(gasto["fecha"])
                    if fecha_inicio <= fecha_gasto <= fecha_fin:
                        gastos_filtrados.append({
                            **gasto,
                            "categoria": categoria,
                            "mes": mes
                        })
        
        return sorted(gastos_filtrados, key=lambda x: x["fecha"])
    
    def obtener_resumen_mes(self, mes=None):
        if mes is None:
            mes = datetime.now().strftime("%Y-%m")
        
        if mes not in self.gastos:
            return {}
        
        resumen = {}
        for categoria, gastos in self.gastos[mes].items():
            total = sum(g["importe"] for g in gastos)
            resumen[categoria] = {
                "total": total,
                "cantidad": len(gastos),
                "limite": PRESUPUESTO.get(categoria, {}).get("limite", 0)
            }
        
        return resumen
    
    def buscar_gastos(self, termino):
        """Busca gastos por descripción"""
        resultados = []
        termino_lower = termino.lower()
        
        for mes, categorias in self.gastos.items():
            for categoria, gastos in categorias.items():
                for gasto in gastos:
                    if termino_lower in gasto.get("descripcion", "").lower():
                        resultados.append({
                            **gasto,
                            "categoria": categoria,
                            "mes": mes
                        })
        
        return sorted(resultados, key=lambda x: x["fecha"], reverse=True)
    
    def analizar_descripciones(self, fecha_inicio=None, fecha_fin=None):
        """Analiza las palabras más frecuentes en las descripciones"""
        if fecha_inicio is None:
            fecha_inicio = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if fecha_fin is None:
            fecha_fin = datetime.now()
        
        gastos = self.obtener_gastos_rango(fecha_inicio, fecha_fin)
        
        # Extraer palabras significativas
        palabras = []
        stop_words = {'de', 'del', 'la', 'el', 'en', 'con', 'por', 'para', 'a', 'y', 'o', 'un', 'una'}
        
        for gasto in gastos:
            desc = gasto.get("descripcion", "").lower()
            # Extraer palabras de 3+ caracteres
            palabras_desc = re.findall(r'\b\w{3,}\b', desc)
            palabras.extend([p for p in palabras_desc if p not in stop_words])
        
        return Counter(palabras).most_common(10)

gestor = GestorGastos()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = """
🏦 *Bot de Gestión de Gastos*

¡Hola! Te ayudaré a controlar tus gastos mensuales.

*📝 Registrar gastos:*
`/gasto <categoría> <importe> [descripción]`

Ejemplo: `/gasto ocio 15.65 Cervezas con amigos`

*Categorías disponibles:*
• `vivienda` - Alquiler y gastos de casa
• `ocio` - Suscripciones, fiestas, etc.
• `inversiones` - SP500 y otras inversiones
• `ahorro` - Ahorro
• `transporte` - Uber, metro...
• `viajes` - Escapadas y vacaciones
• `comida` - Comidas
• `otros` - Otros gastos

*📊 Consultar:*
• `/resumen` - Resumen del mes actual
• `/grafica [filtro]` - Gráficas de gastos
  · `/grafica` - Mes actual
  · `/grafica semanal` - Última semana
  · `/grafica mensual` - Comparativa mensual
  · `/grafica 2025-01-01 2025-03-31` - Rango personalizado
• `/detalle <categoría>` - Lista de gastos de una categoría
• `/buscar <término>` - Buscar gastos por descripción
• `/estadisticas` - Análisis de tus gastos

*💡 Otros:*
• `/ayuda` - Info de presupuesto
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = f"""
📋 *Tu Presupuesto Mensual:*

"""
    total_presupuesto = 0
    for cat, info in PRESUPUESTO.items():
        if cat not in ["ahorro", "restaurante"]:
            total_presupuesto += info['limite']
        mensaje += f"• *{info['nombre']}*: {info['limite']}€\n"
    
    mensaje += f"""
━━━━━━━━━━━━━━━━━
💰 *Total presupuesto:* {total_presupuesto}€
💵 *Sueldo neto estimado:* ~2.050€
🍽️ *Ticket restaurante:* 11€/día (230€/mes)

*💡 Tips:*
• Registra gastos al momento para no olvidarlos
• Revisa el `/resumen` semanalmente
• Usa descripciones claras para analizar patrones
• Los gráficos te ayudan a ver tendencias
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def registrar_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if len(context.args) < 2:
            await update.message.reply_text(
                "❌ Formato incorrecto.\n"
                "Uso: `/gasto <categoría> <importe> [descripción]`\n"
                "Ejemplo: `/gasto ocio 25.50 Netflix mensual`",
                parse_mode='Markdown'
            )
            return
        
        categoria = context.args[0].lower()
        
        if categoria not in PRESUPUESTO:
            categorias = ", ".join(PRESUPUESTO.keys())
            await update.message.reply_text(
                f"❌ Categoría no válida.\n"
                f"Categorías: `{categorias}`",
                parse_mode='Markdown'
            )
            return
        
        try:
            importe = float(context.args[1].replace(',', '.'))
            if importe <= 0:
                await update.message.reply_text("❌ El importe debe ser mayor que 0")
                return
        except ValueError:
            await update.message.reply_text("❌ Importe no válido. Usa números (ej: 15.65)")
            return
        
        descripcion = " ".join(context.args[2:]) if len(context.args) > 2 else ""
        
        gestor.agregar_gasto(categoria, importe, descripcion)
        
        resumen = gestor.obtener_resumen_mes()
        cat_info = resumen.get(categoria, {})
        total = cat_info.get("total", importe)
        limite = PRESUPUESTO[categoria]["limite"]
        porcentaje = (total / limite * 100) if limite > 0 else 0
        
        emoji_estado = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
        
        mensaje = f"""
✅ *Gasto registrado*

📁 {PRESUPUESTO[categoria]['nombre']}
💶 Importe: {importe:.2f}€
"""
        if descripcion:
            mensaje += f"📝 {descripcion}\n"
        
        mensaje += f"""
━━━━━━━━━━━━━━━━━
📊 Total categoría: {total:.2f}€ / {limite}€
{emoji_estado} {porcentaje:.1f}% del presupuesto
"""
        
        if porcentaje > 100:
            mensaje += f"\n⚠️ ¡Te has pasado {total-limite:.2f}€!"
        elif porcentaje > 80:
            mensaje += f"\n💡 Quedan {limite-total:.2f}€ este mes"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error al registrar gasto: {e}")
        await update.message.reply_text("❌ Error al registrar el gasto. Inténtalo de nuevo.")

async def resumen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    resumen_mes = gestor.obtener_resumen_mes()
    
    if not resumen_mes:
        await update.message.reply_text("📭 No hay gastos registrados este mes.")
        return
    
    mes_actual = datetime.now().strftime("%B %Y")
    mensaje = f"📊 *Resumen de {mes_actual}*\n\n"
    
    total_gastado = 0
    
    for categoria in PRESUPUESTO.keys():
        if categoria in resumen_mes:
            info = resumen_mes[categoria]
            nombre = PRESUPUESTO[categoria]["nombre"]
            total = info["total"]
            limite = info["limite"]
            porcentaje = (total / limite * 100) if limite > 0 else 0
            
            total_gastado += total
            
            emoji = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
            
            mensaje += f"{emoji} *{nombre}*\n"
            mensaje += f"   {total:.2f}€ / {limite}€ ({porcentaje:.1f}%) · {info['cantidad']} gastos\n\n"
    
    presupuesto_total = sum(v["limite"] for k, v in PRESUPUESTO.items() 
                           if k not in ["ahorro", "restaurante"])
    
    mensaje += f"━━━━━━━━━━━━━━━━━\n"
    mensaje += f"💰 *Total gastado:* {total_gastado:.2f}€\n"
    mensaje += f"📦 *Presupuesto:* {presupuesto_total}€"
    
    if total_gastado > presupuesto_total:
        mensaje += f"\n🚨 Exceso: {total_gastado - presupuesto_total:.2f}€"
    else:
        mensaje += f"\n✅ Disponible: {presupuesto_total - total_gastado:.2f}€"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def grafica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Determinar el rango de fechas según el filtro
        ahora = datetime.now()
        
        if len(context.args) == 0 or context.args[0] == "mensual":
            # Gráfica mensual (mes actual)
            fecha_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = ahora
            titulo = "Gastos del Mes Actual"
            tipo = "mensual"
        elif context.args[0] == "semanal":
            # Última semana
            fecha_inicio = ahora - timedelta(days=7)
            fecha_fin = ahora
            titulo = "Gastos de la Última Semana"
            tipo = "semanal"
        elif context.args[0] == "diaria":
            # Últimos 30 días
            fecha_inicio = ahora - timedelta(days=30)
            fecha_fin = ahora
            titulo = "Gastos Diarios (Últimos 30 días)"
            tipo = "diaria"
        elif len(context.args) == 2:
            # Rango personalizado
            try:
                fecha_inicio = datetime.fromisoformat(context.args[0])
                fecha_fin = datetime.fromisoformat(context.args[1])
                titulo = f"Gastos del {context.args[0]} al {context.args[1]}"
                tipo = "personalizado"
            except ValueError:
                await update.message.reply_text(
                    "❌ Formato de fecha incorrecto.\n"
                    "Uso: `/grafica YYYY-MM-DD YYYY-MM-DD`",
                    parse_mode='Markdown'
                )
                return
        else:
            await update.message.reply_text(
                "❌ Uso: `/grafica [semanal|diaria|mensual|FECHA_INICIO FECHA_FIN]`",
                parse_mode='Markdown'
            )
            return
        
        await update.message.reply_text("📊 Generando gráfica...")
        
        gastos = gestor.obtener_gastos_rango(fecha_inicio, fecha_fin)
        
        if not gastos:
            await update.message.reply_text("📭 No hay gastos en el período seleccionado.")
            return
        
        # Preparar datos por categoría
        gastos_por_categoria = {}
        for gasto in gastos:
            cat = gasto["categoria"]
            if cat not in gastos_por_categoria:
                gastos_por_categoria[cat] = []
            gastos_por_categoria[cat].append(gasto)
        
        # Crear figura
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        # 1. Gráfico de barras: Total por categoría
        ax1 = fig.add_subplot(gs[0, 0])
        categorias = []
        totales = []
        limites = []
        colores = []
        
        for cat in PRESUPUESTO.keys():
            if cat in gastos_por_categoria:
                nombre = PRESUPUESTO[cat]["nombre"]
                total = sum(g["importe"] for g in gastos_por_categoria[cat])
                limite = PRESUPUESTO[cat]["limite"]
                
                categorias.append(nombre[:20])
                totales.append(total)
                limites.append(limite)
                
                # Color según % del límite
                porcentaje = (total / limite * 100) if limite > 0 else 0
                if porcentaje <= 80:
                    colores.append('#2ecc71')
                elif porcentaje <= 100:
                    colores.append('#f39c12')
                else:
                    colores.append('#e74c3c')
        
        x = range(len(categorias))
        width = 0.35
        
        ax1.bar([i - width/2 for i in x], totales, width, label='Gastado', color=colores)
        ax1.bar([i + width/2 for i in x], limites, width, label='Límite', color='#3498db', alpha=0.6)
        
        ax1.set_xlabel('Categoría', fontsize=10)
        ax1.set_ylabel('Importe (€)', fontsize=10)
        ax1.set_title('Gastos vs Presupuesto', fontsize=12, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(categorias, rotation=45, ha='right', fontsize=9)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        # 2. Gráfico de tarta: Distribución
        ax2 = fig.add_subplot(gs[0, 1])
        colores_tarta = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
        
        if totales:
            ax2.pie(totales, labels=categorias, autopct='%1.1f%%', colors=colores_tarta, startangle=90)
            ax2.set_title('Distribución de Gastos', fontsize=12, fontweight='bold')
        
        # 3. Evolución temporal
        ax3 = fig.add_subplot(gs[1, :])
        
        # Agrupar gastos por día
        gastos_por_dia = {}
        for gasto in gastos:
            fecha = datetime.fromisoformat(gasto["fecha"]).date()
            if fecha not in gastos_por_dia:
                gastos_por_dia[fecha] = 0
            gastos_por_dia[fecha] += gasto["importe"]
        
        fechas = sorted(gastos_por_dia.keys())
        importes_diarios = [gastos_por_dia[f] for f in fechas]
        
        # Calcular acumulado
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
        ax3.set_title('Evolución Temporal de Gastos', fontsize=12, fontweight='bold')
        ax3.grid(axis='y', alpha=0.3)
        ax3.tick_params(axis='x', rotation=45)
        
        # Formato de fechas en el eje X
        if len(fechas) > 15:
            ax3.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        else:
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        # Leyendas
        lines1, labels1 = ax3.get_legend_handles_labels()
        lines2, labels2 = ax3_2.get_legend_handles_labels()
        ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.suptitle(titulo, fontsize=14, fontweight='bold', y=0.98)
        
        # Guardar en memoria
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
        # Enviar imagen con caption
        total_periodo = sum(g["importe"] for g in gastos)
        caption = f"💰 Total del período: {total_periodo:.2f}€\n📊 {len(gastos)} gastos registrados"
        
        await update.message.reply_photo(photo=buf, caption=caption)
        buf.close()
        
    except Exception as e:
        logger.error(f"Error al generar gráfica: {e}")
        await update.message.reply_text(f"❌ Error al generar la gráfica: {str(e)}")

async def detalle(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Especifica una categoría.\n"
            "Uso: `/detalle <categoría>`",
            parse_mode='Markdown'
        )
        return
    
    categoria = context.args[0].lower()
    
    if categoria not in PRESUPUESTO:
        categorias = ", ".join(PRESUPUESTO.keys())
        await update.message.reply_text(
            f"❌ Categoría no válida.\n"
            f"Categorías: `{categorias}`",
            parse_mode='Markdown'
        )
        return
    
    mes_actual = datetime.now().strftime("%Y-%m")
    gastos_mes = gestor.gastos.get(mes_actual, {}).get(categoria, [])
    
    if not gastos_mes:
        await update.message.reply_text(
            f"📭 No hay gastos en '{PRESUPUESTO[categoria]['nombre']}' este mes."
        )
        return
    
    # Ordenar por fecha descendente
    gastos_ordenados = sorted(gastos_mes, key=lambda x: x["fecha"], reverse=True)
    
    mensaje = f"📋 *Detalle: {PRESUPUESTO[categoria]['nombre']}*\n\n"
    total = 0
    
    for gasto in gastos_ordenados[:20]:  # Mostrar últimos 20
        fecha = datetime.fromisoformat(gasto["fecha"])
        fecha_str = fecha.strftime("%d/%m %H:%M")
        importe = gasto["importe"]
        desc = gasto.get("descripcion", "")
        total += importe
        
        mensaje += f"• {fecha_str} - {importe:.2f}€"
        if desc:
            mensaje += f"\n  _{desc}_"
        mensaje += "\n\n"
    
    if len(gastos_ordenados) > 20:
        mensaje += f"_... y {len(gastos_ordenados) - 20} gastos más_\n\n"
    
    limite = PRESUPUESTO[categoria]["limite"]
    porcentaje = (total / limite * 100) if limite > 0 else 0
    emoji = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
    
    mensaje += f"━━━━━━━━━━━━━━━━━\n"
    mensaje += f"{emoji} Total: {total:.2f}€ / {limite}€ ({porcentaje:.1f}%)"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def buscar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ Especifica un término de búsqueda.\n"
            "Uso: `/buscar <término>`\n"
            "Ejemplo: `/buscar cerveza`",
            parse_mode='Markdown'
        )
        return
    
    termino = " ".join(context.args)
    resultados = gestor.buscar_gastos(termino)
    
    if not resultados:
        await update.message.reply_text(f"🔍 No se encontraron gastos con '{termino}'")
        return
    
    total = sum(r["importe"] for r in resultados)
    mensaje = f"🔍 *Resultados para '{termino}'*\n"
    mensaje += f"Encontrados {len(resultados)} gastos · Total: {total:.2f}€\n\n"
    
    for gasto in resultados[:15]:  # Mostrar primeros 15
        fecha = datetime.fromisoformat(gasto["fecha"])
        fecha_str = fecha.strftime("%d/%m/%Y")
        cat_nombre = PRESUPUESTO[gasto["categoria"]]["nombre"]
        
        mensaje += f"• {fecha_str} - {gasto['importe']:.2f}€\n"
        mensaje += f"  {cat_nombre}\n"
        if gasto.get("descripcion"):
            mensaje += f"  _{gasto['descripcion']}_\n"
        mensaje += "\n"
    
    if len(resultados) > 15:
        mensaje += f"_... y {len(resultados) - 15} resultados más_"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def estadisticas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📊 Analizando tus gastos...")
    
    # Análisis del mes actual
    mes_actual = datetime.now()
    inicio_mes = mes_actual.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    gastos_mes = gestor.obtener_gastos_rango(inicio_mes, mes_actual)
    
    if not gastos_mes:
        await update.message.reply_text("📭 No hay suficientes datos para análisis.")
        return
    
    # Palabras más frecuentes
    palabras_frecuentes = gestor.analizar_descripciones(inicio_mes, mes_actual)
    
    # Día de la semana con más gastos
    gastos_por_dia_semana = {i: [] for i in range(7)}
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    for gasto in gastos_mes:
        fecha = datetime.fromisoformat(gasto["fecha"])
        dia = fecha.weekday()
        gastos_por_dia_semana[dia].append(gasto["importe"])
    
    promedios_dia = {dia: sum(gastos)/len(gastos) if gastos else 0 
                     for dia, gastos in gastos_por_dia_semana.items()}
    dia_mas_gasto = max(promedios_dia, key=promedios_dia.get)
    
    # Gasto promedio por día
    dias_con_gastos = len(set(datetime.fromisoformat(g["fecha"]).date() for g in gastos_mes))
    promedio_diario = sum(g["importe"] for g in gastos_mes) / dias_con_gastos if dias_con_gastos > 0 else 0
    
    # Gasto más alto y más bajo
    gasto_max = max(gastos_mes, key=lambda x: x["importe"])
    gasto_min = min(gastos_mes, key=lambda x: x["importe"])
    
    # Construir mensaje
    mensaje = f"📊 *Estadísticas del Mes*\n\n"
    
    mensaje += f"📈 *Resumen general:*\n"
    mensaje += f"• Total de gastos: {len(gastos_mes)}\n"
    mensaje += f"• Promedio diario: {promedio_diario:.2f}€\n"
    mensaje += f"• Día con más gasto: {dias_semana[dia_mas_gasto]}\n\n"
    
    mensaje += f"💰 *Extremos:*\n"
    mensaje += f"• Mayor gasto: {gasto_max['importe']:.2f}€\n"
    if gasto_max.get('descripcion'):
        mensaje += f"  _{gasto_max['descripcion']}_\n"
    mensaje += f"• Menor gasto: {gasto_min['importe']:.2f}€\n"
    if gasto_min.get('descripcion'):
        mensaje += f"  _{gasto_min['descripcion']}_\n"
    mensaje += "\n"
    
    if palabras_frecuentes:
        mensaje += f"🔤 *Palabras más frecuentes:*\n"
        for palabra, freq in palabras_frecuentes[:5]:
            mensaje += f"• {palabra}: {freq} veces\n"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

def main():
    # Token del bot (lo debes obtener de @BotFather)
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not TOKEN:
        print("❌ Error: No se encontró TELEGRAM_BOT_TOKEN en las variables de entorno")
        print("Configura tu token con: export TELEGRAM_BOT_TOKEN='tu_token_aqui'")
        return
    
    # Crear aplicación
    application = Application.builder().token(TOKEN).build()
    
    # Registrar comandos
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("gasto", registrar_gasto))
    application.add_handler(CommandHandler("resumen", resumen))
    application.add_handler(CommandHandler("grafica", grafica))
    application.add_handler(CommandHandler("detalle", detalle))
    application.add_handler(CommandHandler("buscar", buscar))
    application.add_handler(CommandHandler("estadisticas", estadisticas))
    
    # Iniciar bot
    print("🤖 Bot iniciado correctamente")
    print("Presiona Ctrl+C para detener")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()