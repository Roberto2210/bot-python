import requests
import pandas as pd
import logging
import matplotlib.pyplot as plt
import seaborn as sns
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackContext

# 🔹 TOKEN del bot (reemplázalo con tu token de BotFather)
TOKEN = "7867484589:AAEisHzEFECBi0CIM-Irw5fwkcAZQT_fHbk"

# 🔹 URL de la API de partidos
API_URL = "https://api-ligamx-production.up.railway.app/partidos"

# Configurar logs
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def obtener_estadisticas():
    """Obtiene y procesa los datos de la API para analizar equipos con más partidos donde ambos anotan y el promedio de goles."""
    response = requests.get(API_URL)
    if response.status_code != 200:
        return "Error al obtener datos de la API."

    # Convertir a DataFrame
    data = response.json()
    df = pd.DataFrame(data)

    # Verificar columnas necesarias
    if not {'equipo_local', 'equipo_visitante', 'goles_local', 'goles_visitante'}.issubset(df.columns):
        return "Error: La API no tiene los datos esperados."

    # Convertir goles a numéricos
    df[['goles_local', 'goles_visitante']] = df[['goles_local', 'goles_visitante']].apply(pd.to_numeric, errors='coerce')

    # Filtrar partidos donde ambos anotaron
    df_ambos_anotan = df[(df['goles_local'] > 0) & (df['goles_visitante'] > 0)]
    
    # Contar equipos con más partidos donde ambos anotan
    equipos_ambos_anotan = df_ambos_anotan['equipo_local'].value_counts() + df_ambos_anotan['equipo_visitante'].value_counts()
    equipos_ambos_anotan = equipos_ambos_anotan.fillna(0).astype(int).sort_values(ascending=False)

    # Promedio de goles por equipo
    goles_locales = df.groupby('equipo_local')['goles_local'].mean()
    goles_visitantes = df.groupby('equipo_visitante')['goles_visitante'].mean()
    goles_por_equipo = goles_locales.add(goles_visitantes, fill_value=0).sort_values(ascending=False)

    # 📊 Gráfica: Equipos con más partidos donde ambos anotan
    plt.figure(figsize=(12, 6))
    sns.barplot(x=equipos_ambos_anotan.index, y=equipos_ambos_anotan.values, palette="Purples_r")
    plt.xticks(rotation=90)
    plt.title("Equipos con más partidos donde ambos anotan")
    plt.xlabel("Equipo")
    plt.ylabel("Cantidad de Partidos")
    plt.tight_layout()
    plt.savefig('ambos_anotan.png')
    plt.close()

    # 📊 Gráfica: Promedio de goles por equipo
    plt.figure(figsize=(12, 6))
    sns.barplot(x=goles_por_equipo.index, y=goles_por_equipo.values, palette="Oranges_r")
    plt.xticks(rotation=90)
    plt.title("Promedio de goles por equipo")
    plt.xlabel("Equipo")
    plt.ylabel("Goles por partido")
    plt.tight_layout()
    plt.savefig('goles_por_equipo.png')
    plt.close()

    # Convertir resultados a texto
    texto_ambos_anotan = "\n".join([f"{equipo}: {int(cantidad)} partidos" for equipo, cantidad in equipos_ambos_anotan.head(5).items()])
    texto_goles = "\n".join([f"{equipo}: {round(promedio,2)} goles/partido" for equipo, promedio in goles_por_equipo.head(5).items()])

    return f"📊 *Estadísticas Liga MX*\n\n⚽ *Equipos con más partidos donde ambos anotan:*\n{texto_ambos_anotan}\n\n🔥 *Promedio de goles por equipo:*\n{texto_goles}"

async def obtener_ofensiva_defensiva():
    """Obtiene los datos de goles recibidos y anotados de los equipos."""
    response = requests.get(API_URL)
    if response.status_code != 200:
        return "Error al obtener datos de la API.", None

    # Convertir a DataFrame
    data = response.json()
    df = pd.DataFrame(data)

    # Normalizar nombres de equipos
    df['equipo_local'] = df['equipo_local'].str.strip().str.lower()
    df['equipo_visitante'] = df['equipo_visitante'].str.strip().str.lower()

    # Diccionarios para acumular goles recibidos y anotados
    goles_recibidos = {}
    goles_anotados = {}

    # Calcular los goles recibidos y anotados por cada equipo
    for _, row in df.iterrows():
        goles_recibidos[row['equipo_local']] = goles_recibidos.get(row['equipo_local'], 0) + row['goles_visitante']
        goles_anotados[row['equipo_local']] = goles_anotados.get(row['equipo_local'], 0) + row['goles_local']
        
        goles_recibidos[row['equipo_visitante']] = goles_recibidos.get(row['equipo_visitante'], 0) + row['goles_local']
        goles_anotados[row['equipo_visitante']] = goles_anotados.get(row['equipo_visitante'], 0) + row['goles_visitante']

    # Convertir los diccionarios a DataFrame
    df_defensa = pd.DataFrame(list(goles_recibidos.items()), columns=['Equipo', 'Goles Recibidos'])
    df_ofensiva = pd.DataFrame(list(goles_anotados.items()), columns=['Equipo', 'Goles Anotados'])

    # Guardar la gráfica
    plt.figure(figsize=(12,6))
    plt.bar(df_defensa['Equipo'], df_defensa['Goles Recibidos'], color='red', alpha=0.6, label='Goles Recibidos')
    plt.bar(df_ofensiva['Equipo'], df_ofensiva['Goles Anotados'], color='blue', alpha=0.6, label='Goles Anotados')
    plt.xlabel("Equipos")
    plt.ylabel("Goles")
    plt.title("Comparación de Defensa y Ofensiva de la Liga MX")
    plt.xticks(rotation=90)
    plt.legend()
    plt.tight_layout()
    plt.savefig("ofensiva_defensiva.png")
    plt.close()

    return "📊 Comparación de ofensiva y defensiva en la Liga MX:", "ofensiva_defensiva.png"

# 🔹 Comando /goles
async def goles(update: Update, context: CallbackContext):
    mensaje = await obtener_estadisticas()
    await update.message.reply_text(mensaje, parse_mode="Markdown")
    await update.message.reply_photo(photo=open('ambos_anotan.png', 'rb'))
    await update.message.reply_photo(photo=open('goles_por_equipo.png', 'rb'))

# 🔹 Comando /ofensiva_defensiva
async def ofensiva_defensiva(update: Update, context: CallbackContext):
    mensaje, imagen = await obtener_ofensiva_defensiva()
    await update.message.reply_text(mensaje, parse_mode="Markdown")
    await update.message.reply_photo(photo=open(imagen, 'rb'))

# 🔹 Configurar el bot
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("goles", goles))
    app.add_handler(CommandHandler("ofensiva_defensiva", ofensiva_defensiva))
    print("Bot en ejecución...")
    app.run_polling()

if __name__ == "__main__":
    main()
