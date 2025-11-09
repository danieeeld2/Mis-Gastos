import os
import logging
from datetime import datetime, timedelta
from telegram import Update, BotCommand 
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
import asyncio

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
    
    def eliminar_ultimo_gasto(self):
        ultimo_gasto = None
        mes_ultimo = None
        categoria_ultima = None
        indice_ultimo = -1

        for mes, categorias in self.gastos.items():
            for categoria, gastos in categorias.items():
                for i, gasto in enumerate(gastos):
                    fecha_actual = gasto["fecha"]
                    if ultimo_gasto is None or fecha_actual > ultimo_gasto["fecha"]:
                        ultimo_gasto = gasto
                        mes_ultimo = mes
                        categoria_ultima = categoria
                        indice_ultimo = i
        
        if ultimo_gasto:
            del self.gastos[mes_ultimo][categoria_ultima][indice_ultimo]
            
            if not self.gastos[mes_ultimo][categoria_ultima]:
                 del self.gastos[mes_ultimo][categoria_ultima]
            if not self.gastos[mes_ultimo]:
                del self.gastos[mes_ultimo]
                
            self._guardar_datos()
            
            return {
                "exito": True,
                "importe": ultimo_gasto["importe"],
                "categoria": categoria_ultima
            }
            
        return {"exito": False}
    
    def obtener_gastos_rango(self, fecha_inicio, fecha_fin):
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
                "objetivo": PRESUPUESTO.get(categoria, {}).get("objetivo", 0) 
            }
        
        return resumen
    
    def buscar_gastos(self, termino):
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
        if fecha_inicio is None:
            fecha_inicio = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if fecha_fin is None:
            fecha_fin = datetime.now()
        
        gastos = self.obtener_gastos_rango(fecha_inicio, fecha_fin)
        
        palabras = []
        stop_words = {'de', 'del', 'la', 'el', 'en', 'con', 'por', 'para', 'a', 'y', 'o', 'un', 'una'}
        
        for gasto in gastos:
            desc = gasto.get("descripcion", "").lower()
            palabras_desc = re.findall(r'\b\w{3,}\b', desc)
            palabras.extend([p for p in palabras_desc if p not in stop_words])
        
        return Counter(palabras).most_common(10)

gestor = GestorGastos()

async def configurar_comandos(application: Application):
    commands = [
        BotCommand("start", "Inicio y comandos disponibles"),
        BotCommand("gasto", "Registra un nuevo gasto: /gasto <cat> <imp> [desc]"),
        BotCommand("resumen", "Resumen de gastos del mes actual"),
        BotCommand("grafica", "Genera gráficas de gastos (mensual, semanal, etc.)"),
        BotCommand("detalle", "Detalle de gastos de una categoría: /detalle <cat>"),
        BotCommand("buscar", "Busca gastos por descripción: /buscar <término>"),
        BotCommand("estadisticas", "Análisis de tus patrones de gasto"),
        BotCommand("redefinir", "Cambia el objetivo de gasto: /redefinir <cat> <obj>"),
        BotCommand("deshacer", "Elimina el último gasto registrado"),
        BotCommand("ayuda", "Información de presupuesto y categorías")
    ]
    try:
        await application.bot.set_my_commands(commands)
        logger.info("Comandos de Telegram actualizados.")
    except Exception as e:
        logger.error(f"Error al configurar comandos de Telegram: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = """
🏦 *Bot de Gestión de Gastos*

¡Hola! Te ayudaré a controlar tus gastos mensuales.

*📝 Registrar gastos:*
`/gasto <categoría> <importe> [descripción]`
`/deshacer` - Elimina el último gasto

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
• `/detalle <categoría>` - Lista de gastos de una categoría
• `/buscar <término>` - Buscar gastos por descripción
• `/estadisticas` - Análisis de tus gastos

*⚙️ Configuración:*
• `/redefinir <categoría> <objetivo>` - Cambia el objetivo mensual

*💡 Otros:*
• `/ayuda` - Info de presupuesto
"""
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def ayuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    mensaje = f"""
📋 *Tus Objetivos de Gasto Mensual:*

"""
    total_presupuesto = 0
    for cat, info in PRESUPUESTO.items():
        if cat not in ["ahorro", "restaurante"]:
            total_presupuesto += info['objetivo'] 
        mensaje += f"• *{info['nombre']}*: {info['objetivo']}€\n"
    
    mensaje += f"""
━━━━━━━━━━━━━━━━━
💰 *Suma de objetivos:* {total_presupuesto}€
💵 *Sueldo neto estimado:* ~2.050€
🍽️ *Ticket restaurante:* 11€/día (230€/mes)

*💡 Tips:*
• Registra gastos al momento para no olvidarlos
• Usa `/redefinir <cat> <obj>` para ajustar tus objetivos.
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
        objetivo = PRESUPUESTO[categoria]["objetivo"] 
        porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
        
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
📊 Total categoría: {total:.2f}€ / {objetivo}€ (Objetivo)
{emoji_estado} {porcentaje:.1f}% del objetivo
"""
        
        if porcentaje > 100:
            mensaje += f"\n⚠️ ¡Te has pasado {total-objetivo:.2f}€ de tu objetivo!"
        elif porcentaje > 80:
            mensaje += f"\n💡 Quedan {objetivo-total:.2f}€ para tu objetivo"
        
        await update.message.reply_text(mensaje, parse_mode='Markdown')
        
    except Exception as e:
        logger.error(f"Error al registrar gasto: {e}")
        await update.message.reply_text("❌ Error al registrar el gasto. Inténtalo de nuevo.")

async def deshacer_gasto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        resultado = gestor.eliminar_ultimo_gasto()

        if resultado["exito"]:
            nombre_categoria = PRESUPUESTO[resultado['categoria']]['nombre']
            
            mensaje = f"🗑️ *Gasto deshecho correctamente:*\n"
            mensaje += f"  - Importe: {resultado['importe']:.2f}€\n"
            mensaje += f"  - Categoría: {nombre_categoria}"
            await update.message.reply_text(mensaje, parse_mode='Markdown')
        else:
            await update.message.reply_text("❌ No se encontró ningún gasto para deshacer.")
            
    except Exception as e:
        logger.error(f"Error al deshacer gasto: {e}")
        await update.message.reply_text("❌ Error al intentar deshacer el gasto.")


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
            objetivo = PRESUPUESTO[categoria]["objetivo"] 
            
            porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
            
            total_gastado += total
            
            emoji = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
            
            mensaje += f"{emoji} *{nombre}*\n"
            mensaje += f"   {total:.2f}€ / {objetivo}€ ({porcentaje:.1f}%) · {info['cantidad']} gastos\n\n"
    
    presupuesto_total = sum(v["objetivo"] for k, v in PRESUPUESTO.items() 
                           if k not in ["ahorro", "restaurante"])
    
    mensaje += f"━━━━━━━━━━━━━━━━━\n"
    mensaje += f"💰 *Total gastado:* {total_gastado:.2f}€\n"
    mensaje += f"📦 *Objetivo total:* {presupuesto_total}€"
    
    if total_gastado > presupuesto_total:
        mensaje += f"\n🚨 Exceso del objetivo: {total_gastado - presupuesto_total:.2f}€"
    else:
        mensaje += f"\n✅ Queda para el objetivo: {presupuesto_total - total_gastado:.2f}€"
    
    await update.message.reply_text(mensaje, parse_mode='Markdown')

async def grafica(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        ahora = datetime.now()
        
        if len(context.args) == 0 or context.args[0] == "mensual":
            fecha_inicio = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            fecha_fin = ahora
            titulo = "Gastos del Mes Actual"
            tipo = "mensual"
        elif context.args[0] == "semanal":
            fecha_inicio = ahora - timedelta(days=7)
            fecha_fin = ahora
            titulo = "Gastos de la Última Semana"
            tipo = "semanal"
        elif context.args[0] == "diaria":
            fecha_inicio = ahora - timedelta(days=30)
            fecha_fin = ahora
            titulo = "Gastos Diarios (Últimos 30 días)"
            tipo = "diaria"
        elif len(context.args) == 2:
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
        
        gastos_por_categoria = {}
        for gasto in gastos:
            cat = gasto["categoria"]
            if cat not in gastos_por_categoria:
                gastos_por_categoria[cat] = []
            gastos_por_categoria[cat].append(gasto)
        
        fig = plt.figure(figsize=(16, 10))
        gs = fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)
        
        ax1 = fig.add_subplot(gs[0, 0])
        categorias = []
        totales = []
        objetivos = []
        colores = []
        
        for cat in PRESUPUESTO.keys():
            if cat in gastos_por_categoria:
                nombre = PRESUPUESTO[cat]["nombre"]
                total = sum(g["importe"] for g in gastos_por_categoria[cat])
                objetivo = PRESUPUESTO[cat]["objetivo"]
                
                categorias.append(nombre[:20])
                totales.append(total)
                objetivos.append(objetivo)
                
                porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
                if porcentaje <= 80:
                    colores.append('#2ecc71')
                elif porcentaje <= 100:
                    colores.append('#f39c12')
                else:
                    colores.append('#e74c3c')
        
        x = range(len(categorias))
        width = 0.35
        
        ax1.bar([i - width/2 for i in x], totales, width, label='Gastado', color=colores)
        ax1.bar([i + width/2 for i in x], objetivos, width, label='Objetivo', color='#3498db', alpha=0.6)
        
        ax1.set_xlabel('Categoría', fontsize=10)
        ax1.set_ylabel('Importe (€)', fontsize=10)
        ax1.set_title('Gastos vs Objetivo', fontsize=12, fontweight='bold')
        ax1.set_xticks(x)
        ax1.set_xticklabels(categorias, rotation=45, ha='right', fontsize=9)
        ax1.legend()
        ax1.grid(axis='y', alpha=0.3)
        
        ax2 = fig.add_subplot(gs[0, 1])
        colores_tarta = ['#e74c3c', '#3498db', '#2ecc71', '#f39c12', '#9b59b6', '#1abc9c']
        
        if totales:
            ax2.pie(totales, labels=categorias, autopct='%1.1f%%', colors=colores_tarta, startangle=90)
            ax2.set_title('Distribución de Gastos', fontsize=12, fontweight='bold')
        
        ax3 = fig.add_subplot(gs[1, :])
        
        gastos_por_dia = {}
        for gasto in gastos:
            fecha = datetime.fromisoformat(gasto["fecha"]).date()
            if fecha not in gastos_por_dia:
                gastos_por_dia[fecha] = 0
            gastos_por_dia[fecha] += gasto["importe"]
        
        fechas = sorted(gastos_por_dia.keys())
        importes_diarios = [gastos_por_dia[f] for f in fechas]
        
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
        
        if len(fechas) > 15:
            ax3.xaxis.set_major_locator(mdates.WeekdayLocator())
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        else:
            ax3.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
        
        lines1, labels1 = ax3.get_legend_handles_labels()
        lines2, labels2 = ax3_2.get_legend_handles_labels()
        ax3.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
        
        plt.suptitle(titulo, fontsize=14, fontweight='bold', y=0.98)
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close(fig)
        
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
    
    gastos_ordenados = sorted(gastos_mes, key=lambda x: x["fecha"], reverse=True)
    
    mensaje = f"📋 *Detalle: {PRESUPUESTO[categoria]['nombre']}*\n\n"
    total = 0
    
    for gasto in gastos_ordenados[:20]: 
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
    
    objetivo = PRESUPUESTO[categoria]["objetivo"]
    porcentaje = (total / objetivo * 100) if objetivo > 0 else 0
    emoji = "✅" if porcentaje <= 80 else "⚠️" if porcentaje <= 100 else "🚨"
    
    mensaje += f"━━━━━━━━━━━━━━━━━\n"
    mensaje += f"{emoji} Total: {total:.2f}€ / {objetivo}€ (Objetivo)"
    
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
    
    for gasto in resultados[:15]: 
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
    
    mes_actual = datetime.now()
    inicio_mes = mes_actual.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    gastos_mes = gestor.obtener_gastos_rango(inicio_mes, mes_actual)
    
    if not gastos_mes:
        await update.message.reply_text("📭 No hay suficientes datos para análisis.")
        return
    
    palabras_frecuentes = gestor.analizar_descripciones(inicio_mes, mes_actual)
    
    gastos_por_dia_semana = {i: [] for i in range(7)}
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    for gasto in gastos_mes:
        fecha = datetime.fromisoformat(gasto["fecha"])
        dia = fecha.weekday()
        gastos_por_dia_semana[dia].append(gasto["importe"])
    
    promedios_dia = {dia: sum(gastos)/len(gastos) if gastos else 0 
                     for dia, gastos in gastos_por_dia_semana.items()}
    dia_mas_gasto = max(promedios_dia, key=promedios_dia.get)
    
    dias_con_gastos = len(set(datetime.fromisoformat(g["fecha"]).date() for g in gastos_mes))
    promedio_diario = sum(g["importe"] for g in gastos_mes) / dias_con_gastos if dias_con_gastos > 0 else 0
    
    gasto_max = max(gastos_mes, key=lambda x: x["importe"])
    gasto_min = min(gastos_mes, key=lambda x: x["importe"])
    
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

async def redefinir_objetivo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PRESUPUESTO
    
    if len(context.args) != 2:
        await update.message.reply_text(
            "❌ Formato incorrecto.\n"
            "Uso: `/redefinir <categoría> <nuevo_objetivo>`\n"
            "Ejemplo: `/redefinir ocio 400`",
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
        nuevo_objetivo = float(context.args[1].replace(',', '.'))
        if nuevo_objetivo < 0:
            await update.message.reply_text("❌ El objetivo debe ser un número positivo o cero.")
            return
    except ValueError:
        await update.message.reply_text("❌ Objetivo no válido. Usa números (ej: 400 o 350.50)")
        return
        
    PRESUPUESTO[categoria]["objetivo"] = nuevo_objetivo
    
    await update.message.reply_text(
        f"✅ ¡Objetivo actualizado!\n"
        f"La categoría *{PRESUPUESTO[categoria]['nombre']}* tiene ahora un objetivo de *{nuevo_objetivo:.2f}€*.",
        parse_mode='Markdown'
    )

def main():
    TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    application = Application.builder().token(TOKEN).build()
    
    application.post_init = configurar_comandos
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("ayuda", ayuda))
    application.add_handler(CommandHandler("gasto", registrar_gasto))
    application.add_handler(CommandHandler("resumen", resumen))
    application.add_handler(CommandHandler("grafica", grafica))
    application.add_handler(CommandHandler("detalle", detalle))
    application.add_handler(CommandHandler("buscar", buscar))
    application.add_handler(CommandHandler("estadisticas", estadisticas))
    application.add_handler(CommandHandler("redefinir", redefinir_objetivo))
    application.add_handler(CommandHandler("deshacer", deshacer_gasto))
    
    print("🤖 Bot iniciado correctamente")
    print("Presiona Ctrl+C para detener")
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()