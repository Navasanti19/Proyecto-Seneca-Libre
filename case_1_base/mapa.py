import dash
from dash import dcc, html
from dash.dependencies import Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np

# Cargar los datos de depósitos y clientes
depots_df = pd.read_csv('data/Depots.csv')
clients_df = pd.read_csv('data/Clients.csv')
routes_df = pd.read_csv('results/reporte_rutas.csv')

# Crear los diccionarios de depósitos y clientes con coordenadas
deposits_dict = {
    f"D{int(row['DepotID'])}": [int(row['DepotID']), row['Longitude'], row['Latitude']]
    for _, row in depots_df.iterrows()
}
clients_dict = {
    f"C{int(row['ClientID'])}": [int(row['Product']), row['Longitude'], row['Latitude']]
    for _, row in clients_df.iterrows()
}

# Procesar las rutas para dividirlas en nodos y coordenadas
nodes_data = []
edges_data = []
for _, row in routes_df.iterrows():
    vehiculo = row['Vehículo']
    ruta = row['Ruta']
    if ruta != "Sin ruta":
        nodos = ruta.split(" -> ")
        for idx, nodo in enumerate(nodos):
            coordenadas = deposits_dict.get(nodo, clients_dict.get(nodo, [None, None, None]))
            if coordenadas[1] is None or coordenadas[2] is None:
                continue
            nodes_data.append({
                "Vehículo": vehiculo,
                "Nodo": nodo,
                "Latitud": float(coordenadas[2]),
                "Longitud": float(coordenadas[1]),
                "Orden": idx
            })
            # Crear aristas para las rutas
            if idx > 0:
                prev_nodo = nodos[idx - 1]
                prev_coords = deposits_dict.get(prev_nodo, clients_dict.get(prev_nodo, [None, None, None]))
                if prev_coords[1] is not None and prev_coords[2] is not None:
                    edges_data.append({
                        "Vehículo": vehiculo,
                        "Lat_inicio": float(prev_coords[2]),
                        "Lon_inicio": float(prev_coords[1]),
                        "Lat_fin": float(coordenadas[2]),
                        "Lon_fin": float(coordenadas[1])
                    })

nodes_df = pd.DataFrame(nodes_data)
edges_df = pd.DataFrame(edges_data)

# Colores únicos para cada vehículo
vehicle_colors = {
    vehicle: f"rgba({np.random.randint(0,255)}, {np.random.randint(0,255)}, {np.random.randint(0,255)}, 0.7)"
    for vehicle in routes_df['Vehículo'].unique()
}

# Inicializar la aplicación Dash
app = dash.Dash(__name__)
app.title = "Visualización de Rutas - Optimización"

# Layout de la aplicación
app.layout = html.Div([
    html.H1("Visualización de Rutas - Optimización de Vehículos", style={'textAlign': 'center'}),
    dcc.Dropdown(
        id='vehiculo-dropdown',
        options=[{'label': f'Vehículo {v}', 'value': v} for v in routes_df['Vehículo'].unique()],
        value=routes_df['Vehículo'].iloc[0],  # Seleccionar el primer vehículo por defecto
        placeholder="Selecciona un vehículo",
        style={'width': '50%', 'margin': '0 auto'}
    ),
    dcc.Graph(id='mapa-rutas', style={'height': '80vh'}),
])

# Callback para actualizar el mapa con líneas y nodos animados
@app.callback(
    Output('mapa-rutas', 'figure'),
    [Input('vehiculo-dropdown', 'value')]
)
def actualizar_mapa(vehiculo_seleccionado):
    # Filtrar datos para el vehículo seleccionado
    nodos_filtrados = nodes_df[nodes_df['Vehículo'] == vehiculo_seleccionado]
    rutas_filtradas = edges_df[edges_df['Vehículo'] == vehiculo_seleccionado]
    color = vehicle_colors[vehiculo_seleccionado]

    # Crear el mapa base
    fig = go.Figure()

    # Agregar las líneas para las rutas
    for _, edge in rutas_filtradas.iterrows():
        fig.add_trace(go.Scattermapbox(
            mode="lines",
            lon=[edge['Lon_inicio'], edge['Lon_fin']],
            lat=[edge['Lat_inicio'], edge['Lat_fin']],
            line=dict(width=3, color=color),
            hoverinfo="none",
            name="Ruta"
        ))

    # Agregar nodos iniciales
    fig.add_trace(go.Scattermapbox(
        mode="markers+text",
        lon=nodos_filtrados['Longitud'],
        lat=nodos_filtrados['Latitud'],
        text=nodos_filtrados['Nodo'],
        marker=dict(size=10, color="black"),
        hoverinfo="text",
        name="Nodos"
    ))

    # Crear animación: nodos en movimiento
    frames = []
    for orden in sorted(nodos_filtrados['Orden'].unique()):
        frame_data = nodos_filtrados[nodos_filtrados['Orden'] == orden]
        frames.append(
            go.Frame(
                data=[
                    go.Scattermapbox(
                        lon=frame_data['Longitud'],
                        lat=frame_data['Latitud'],
                        marker=dict(size=12, color=color),
                        name=f"Paso {orden}"
                    )
                ],
                name=str(orden)
            )
        )

    fig.frames = frames

    # Configurar el layout del mapa
    fig.update_layout(
        mapbox=dict(
            style="carto-positron",
            zoom=12,
            center={"lat": nodos_filtrados['Latitud'].mean(), "lon": nodos_filtrados['Longitud'].mean()},
        ),
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        updatemenus=[{
            "buttons": [
                {
                    "args": [None, {"frame": {"duration": 500, "redraw": True}, "fromcurrent": True}],
                    "label": "Iniciar",
                    "method": "animate",
                },
                {
                    "args": [[None], {"frame": {"duration": 0, "redraw": True}, "mode": "immediate", "transition": {"duration": 0}}],
                    "label": "Pausar",
                    "method": "animate",
                },
            ],
            "direction": "left",
            "pad": {"r": 10, "t": 87},
            "showactive": False,
            "type": "buttons",
            "x": 0.1,
            "xanchor": "right",
            "y": 0,
            "yanchor": "top",
        }]
    )
    return fig

# Ejecutar la aplicación
if __name__ == '__main__':
    app.run_server(debug=True)
