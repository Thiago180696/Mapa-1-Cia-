
import folium
from folium.plugins import LocateControl
from shapely import wkt
import pandas as pd
from itertools import cycle

# Carregar dados
df_km = pd.read_excel("coordenadas_com_extremos_corrigidos.xlsx")
df_km_full = pd.read_excel("coordenadas.xlsx")
df_bases = pd.read_excel("bases.xlsx")
df_municipios = pd.read_excel("municipios_selecionados.xlsx")
df_malha = pd.read_excel("Malha.xlsx", header=None, skiprows=1)
df_linhas_conc = pd.read_json("linhas_concessionarias.json")

# Preparar dados
df_malha.columns = [
    "Tipo", "SP", "KM INICIAL", "KM FINAL", "EXTENSÃO", "MUNICÍPIO", "RODOVIA", "JURISDIÇÃO",
    "ADMINISTRAÇÃO", "CONSERVAÇÃO", "SUPERFÍCIE", "PELOTÃO", "Sentido", "CPI", "BTLH", "CIA", "PEL/GP"
]
df_malha = df_malha.dropna(subset=["Tipo", "SP"])
df_malha["Codificação"] = df_malha["Tipo"].astype(str).str.strip() + " " + df_malha["SP"].astype(str).str.strip()
df_malha["NOME DA RODOVIA"] = df_malha["Codificação"] + " " + df_malha["RODOVIA"].astype(str).str.strip()
df_malha["CONCESSIONÁRIA"] = df_malha["ADMINISTRAÇÃO"].astype(str).str.strip() + " " + df_malha["CONSERVAÇÃO"].astype(str).str.strip()

# Municípios
df_municipios["geometry"] = df_municipios["geometry"].apply(wkt.loads)
info = df_malha[["MUNICÍPIO", "PELOTÃO", "BTLH", "CPI"]].dropna().drop_duplicates("MUNICÍPIO")
info["PELOTÃO"] = info["PELOTÃO"].astype(int).map({1: "1º Pel", 2: "2º Pel", 3: "3º Pel"})
map_info = info.set_index("MUNICÍPIO").to_dict(orient="index")
df_municipios["PELOTÃO"] = df_municipios["name_muni"].map(lambda x: map_info.get(x, {}).get("PELOTÃO"))
df_municipios["BTLH"] = df_municipios["name_muni"].map(lambda x: map_info.get(x, {}).get("BTLH"))
df_municipios["CPI"] = df_municipios["name_muni"].map(lambda x: map_info.get(x, {}).get("CPI"))

# Criar mapa
mapa = folium.Map(location=[-21.5, -48.5], zoom_start=8, control_scale=True)
LocateControl(auto_start=True).add_to(mapa)

# Pelotões
cores_pel = {"1º Pel": "#3B82F6", "2º Pel": "#D1D5DB", "3º Pel": "#10B981"}
grupo_municipios = folium.FeatureGroup(name="Pelotões", show=True).add_to(mapa)
for _, row in df_municipios.iterrows():
    cor = cores_pel.get(row["PELOTÃO"], "#CCCCCC")
    folium.GeoJson(
        data=row["geometry"].__geo_interface__,
        style_function=lambda feature, cor=cor: {"fillColor": cor, "color": "black", "weight": 1, "fillOpacity": 0.4},
        tooltip=row["name_muni"],
        popup=folium.Popup(f"{row['name_muni']}<br>{row['PELOTÃO']}<br>{row['BTLH']}<br>{row['CPI']}")
    ).add_to(grupo_municipios)

# Bases
grupo_bases = folium.FeatureGroup(name="Bases Policiais", show=True).add_to(mapa)
for _, row in df_bases.iterrows():
    folium.Marker(
        location=[row["lat"], row["lon"]],
        icon=folium.Icon(color="blue", icon="shield", prefix="fa"),
        popup=f"Base: {row['nome']}<br>Fone: {row['telefone']}<br>Status: {row['status']}"
    ).add_to(grupo_bases)

# Marcos KM (pretos)
grupo_km = folium.FeatureGroup(name="Marcos Quilométricos", show=True).add_to(mapa)
df_km["rodovia"] = df_km["rodovia"].str.strip().str.upper()
for _, row in df_km.iterrows():
    folium.Marker(
        location=[row["y"], row["x"]],
        icon=folium.DivIcon(html=f'<div style="font-size:9pt;color:black;">{int(row["km"])}</div>'),
        popup=f"Rodovia: {row['rodovia']}<br>KM: {row['km']}"
    ).add_to(grupo_km)

# Concessionárias
mapa_concess = df_malha.dropna(subset=["Codificação", "CONCESSIONÁRIA"]).drop_duplicates("Codificação").set_index("Codificação")["CONCESSIONÁRIA"].to_dict()
concess_rodovia = df_malha[["Codificação", "CONCESSIONÁRIA"]].drop_duplicates()
lista_concessionarias = sorted(concess_rodovia["CONCESSIONÁRIA"].unique())
cores_fixas = cycle(["#E6194B", "#3CB44B", "#FFE119", "#0082C8", "#F58231", "#911EB4", "#46F0F0"])
mapa_cores_concess = dict(zip(lista_concessionarias, cores_fixas))

for _, linha in df_linhas_conc.iterrows():
    cod_rodovia = str(linha["rodovia"]).replace("SP", "SP ").strip().upper()
    nome_concess = mapa_concess.get(cod_rodovia, "Desconhecida")
    cor = mapa_cores_concess.get(nome_concess, "#888888")
    folium.PolyLine(
        locations=linha["coords"],
        color=cor,
        weight=6,
        opacity=0.9,
        popup=folium.Popup(f"{nome_concess} - {cod_rodovia}")
    ).add_to(folium.FeatureGroup(name=nome_concess, show=True).add_to(mapa))

# Extremos calculados
df_km_full["rodovia"] = df_km_full["rodovia"].str.strip().str.upper()
extremos = df_malha.groupby("Codificação")[["KM INICIAL", "KM FINAL"]].agg({"KM INICIAL": "min", "KM FINAL": "max"}).reset_index()
def localizar_extremos(row):
    rod = row["Codificação"].strip().upper()
    sub = df_km_full[df_km_full["rodovia"] == rod]
    if sub.empty: return pd.Series([None]*4, index=["lat_ini", "lon_ini", "lat_fim", "lon_fim"])
    ini = sub.iloc[(sub["km"] - row["KM INICIAL"]).abs().argsort().iloc[0]]
    fim = sub.iloc[(sub["km"] - row["KM FINAL"]).abs().argsort().iloc[0]]
    return pd.Series([ini["y"], ini["x"], fim["y"], fim["x"]], index=["lat_ini", "lon_ini", "lat_fim", "lon_fim"])
extremos_coords = extremos.apply(localizar_extremos, axis=1)
df_extremos = pd.concat([extremos, extremos_coords], axis=1)
grupo_extremos = folium.FeatureGroup(name="Extremos de Rodovias", show=True).add_to(mapa)
for _, row in df_extremos.iterrows():
    if pd.notna(row["lat_ini"]):
        folium.Marker([row["lat_ini"], row["lon_ini"]], icon=folium.Icon(color="green", icon="flag", prefix="fa"), popup=f"{row['Codificação']}<br>KM Inicial: {row['KM INICIAL']}").add_to(grupo_extremos)
    if pd.notna(row["lat_fim"]):
        folium.Marker([row["lat_fim"], row["lon_fim"]], icon=folium.Icon(color="red", icon="flag", prefix="fa"), popup=f"{row['Codificação']}<br>KM Final: {row['KM FINAL']}").add_to(grupo_extremos)

# Legendas
folium.Element('''
<div style="position: fixed; bottom: 50px; left: 50px; width: 220px; background-color: white; z-index:9999; font-size:14px;
 border:2px solid grey; border-radius:6px; padding: 10px;">
 <b>Legenda - Pelotões</b><br>
 <i style="background:#3B82F6;width:12px;height:12px;display:inline-block;"></i> 1º Pel<br>
 <i style="background:#D1D5DB;width:12px;height:12px;display:inline-block;"></i> 2º Pel<br>
 <i style="background:#10B981;width:12px;height:12px;display:inline-block;"></i> 3º Pel<br>
 <i class="fa fa-shield" style="color:blue;"></i> Bases Policiais
</div>''').add_to(mapa.get_root())

# Legenda Concessionárias
leg_conc = "<b>Legenda - Concessionárias</b><br>" + "".join(
    f'<i style="background:{cor};width:12px;height:12px;display:inline-block;"></i> {nome}<br>'
    for nome, cor in mapa_cores_concess.items())
folium.Element(f'<div style="position: fixed; bottom: 50px; right: 50px; width: 300px; background-color: white; z-index:9999; font-size:14px; border:2px solid grey; border-radius:6px; padding: 10px;">{leg_conc}</div>').add_to(mapa.get_root())

folium.LayerControl(collapsed=False).add_to(mapa)
mapa.save("mapa_final_completo.html")
print("✅ Mapa final salvo como 'mapa_final_completo.html'")
