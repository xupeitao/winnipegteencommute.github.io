# -*- coding: utf-8 -*-

import dash
import dash_bootstrap_components as dbc
from dash import Dash, html, dcc, Input, Output, callback, State
import plotly.express as px
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import osmnx as ox

# Function for creating Scatter Maps
def create_scatter_mapbox(df, lat, lon, color, hover_name, hover_data, title, zoom_level, center_lat, center_lon, mapbox_style, admin):
    fig = px.scatter_mapbox(
        df,
        lat=lat,
        lon=lon,
        color=color,
        hover_name=hover_name,
        hover_data=hover_data,
        title=title,
        zoom=zoom_level,
        center=dict(lat=center_lat, lon=center_lon),
        mapbox_style=mapbox_style,
        color_discrete_sequence=px.colors.qualitative.Light24,
    )

    # Just use the Winnipeg's boundary (lines)
    for _, row in admin.iterrows():
        fig.add_trace(
            px.line_mapbox(
                gpd.GeoDataFrame(geometry=[row.geometry.exterior], crs=admin.crs),
                lat=row.geometry.exterior.coords.xy[1].tolist(),
                lon=row.geometry.exterior.coords.xy[0].tolist(),
            ).data[0]
        )

    # update the margin to fit the screen
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )

    return fig

# Function for creating Heat Maps
def create_density_mapbox(df, lat, lon, z_col, radius, opacity, title, zoom_level, center_lat, center_lon, mapbox_style, color_continuous_scale, admin):
    fig = px.density_mapbox(
        df,
        lat=lat,
        lon=lon,
        z=z_col,
        radius=radius,
        opacity=opacity,
        title=title,
        zoom=zoom_level,
        center=dict(lat=center_lat, lon=center_lon),
        mapbox_style=mapbox_style,
        color_continuous_scale=color_continuous_scale,
    )

    # Add Winnipeg administrative boundaries
    for _, row in admin.iterrows():
        fig.add_trace(
            px.line_mapbox(
                gpd.GeoDataFrame(geometry=[row.geometry.exterior], crs=admin.crs),
                lat=row.geometry.exterior.coords.xy[1].tolist(),
                lon=row.geometry.exterior.coords.xy[0].tolist(),
            ).data[0]
        )

    # update the margin to fit the screen
    fig.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
    )

    return fig

# Step 1: Read the data
# Use the url of the csv I uploaded to github
df_stops = pd.read_csv('https://raw.githubusercontent.com/xupeitao/winnipegteencommute.github.io/eed46f305bef43e3238668591bda862e8e899799/data/stops.txt')

# Step 2: Convert stop locations into a GeoDataFrame
geometry = [Point(xy) for xy in zip(df_stops['Long'], df_stops['Lat'])]
gdf_stops = gpd.GeoDataFrame(df_stops, geometry=geometry)
gdf_stops.crs = 'EPSG:4326'

# Get the administrative boundary of Winnipeg using OSMnx
city = 'Winnipeg, Canada'
admin = ox.geocode_to_gdf(city)
admin.crs = 4326

# Step 3: Spatial Join to identify stops within the city boundary
stops_within = gpd.sjoin(gdf_stops, admin, how="inner", predicate="within")

# Step 4: Layout pre-setting, to show all the city boundary
center_lat = stops_within['Lat'].mean() - 0.025
center_lon = stops_within['Long'].mean()
zoom_level = 9

fig = create_scatter_mapbox(
    df=stops_within,
    lat='Lat',
    lon='Long',
    color=None,
    hover_name='stop_name',
    hover_data='stop_url',
    title='<br>Winnipeg Public Transport Stops',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Heat Map
fig_heat = create_density_mapbox(
    df=stops_within,
    lat='Lat',
    lon='Long',
    z_col=None,
    radius=2,
    opacity=0.5,
    title='<br>Winnipeg Public Transport Stops Density',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style='carto-positron',
    color_continuous_scale="Plasma",
    admin=admin
)

# Step 1: Read the data
# Use the url of the csv I uploaded to github
df_passup = pd.read_csv('https://raw.githubusercontent.com/xupeitao/winnipegteencommute.github.io/eed46f305bef43e3238668591bda862e8e899799/data/Transit_Pass_ups.csv')

# Step 2: Data Cleaning
print("Number of Rows before deleting:", len(df_passup))

# convert Long and Lat to numeric format
df_passup['Long'] = pd.to_numeric(df_passup['Long'], errors='coerce')
df_passup['Lat'] = pd.to_numeric(df_passup['Lat'], errors='coerce')

# Replace '#VALUE!' with NaN
df_passup.replace('#VALUE!', pd.NA, inplace=True)

# Replace any '0' value in Long and Lat with NaN
df_passup["Lat"] = df_passup["Lat"].replace(0, pd.NA)
df_passup["Long"] = df_passup["Long"].replace(0, pd.NA)

# Drop rows with NaN in 'Long' or 'Lat'
df_passup.dropna(subset=['Long', 'Lat'], inplace=True)

print("Number of Rows after deleting:", len(df_passup))

# Step 3: Time data pre-processing
# Convert 'Time' column to datetime type
df_passup['Time'] = pd.to_datetime(df_passup['Time'], errors='coerce')

# Extraction year, date, and hour
df_passup['Year'] = df_passup['Time'].dt.year
df_passup['Date'] = df_passup['Time'].dt.date
df_passup['Hour'] = df_passup['Time'].dt.hour

# Define Time Period ()
def time_period(hour):
    """
    Distinguish time periods:
    6-9am: Represents the time students go to school in the morning.
    3-6pm: Represents the time students leave school in the afternoon.
    Others: Covers times out of peak hours.
    """
    if 0 <= hour < 6:
        return '0-6am'
    elif 6 <= hour < 9:
        return '6-9am'
    elif 9 <= hour < 12:
        return '9-12am'
    elif 12 <= hour < 15:
        return '12-3pm'
    elif 15 <= hour < 18:
        return '3-6pm'
    else:
        return '6-12pm'

df_passup['Time_Period'] = df_passup['Hour'].apply(time_period)

# Step 4: Convert stop locations into a GeoDataFrame
geometry = [Point(xy) for xy in zip(df_passup['Long'], df_passup['Lat'])]
gdf_passup = gpd.GeoDataFrame(df_passup, geometry=geometry)
gdf_passup.crs = 'EPSG:4326'

# Get the administrative boundary of Winnipeg using OSMnx
city = 'Winnipeg, Canada'
admin = ox.geocode_to_gdf(city)
admin.crs = 4326

# Spatial Join to identify stops within the city boundary
passup_within = gpd.sjoin(gdf_passup, admin, how="inner", predicate="within")

# Step 5: Route data pre-processing
# Count the occurrences of each Route Number
route_counts = passup_within['Route Number'].value_counts()

# Replace Route Numbers with counts less than 1000 with 'Other'
def update_route_number(route_number):
    if pd.notna(route_number) and route_counts[route_number] < 1000:
        return 'Other'
    else:
        return route_number

passup_within['Route Number'] = passup_within['Route Number'].apply(update_route_number)

# Step 6: Number Counted by different parameters
# Calculate Route Number counts after replacement
route_counts = passup_within['Route Number'].value_counts().reset_index()
route_counts.columns = ['Route Number', 'Count']

# Calculate number by Year
year_counts = passup_within['Year'].value_counts().reset_index()
year_counts.columns = ['Year', 'Count']

# Calculate number by hour
hour_counts = passup_within['Hour'].value_counts().reset_index()
hour_counts.columns = ['Hour', 'Count']
hour_counts['Hour'] = hour_counts['Hour'].astype(int)
hour_counts = hour_counts.sort_values(by='Hour')

# Calculate number by Time Period
time_counts = passup_within['Time_Period'].value_counts().reset_index()
time_counts.columns = ['Time_Period', 'Count']

# Calculate number by Pass-Up Type
type_counts = passup_within['Pass-Up Type'].value_counts().reset_index()
type_counts.columns = ['Pass-Up Type', 'Count']

# Step 7: Layout pre-setting, to show all the city boundary
center_lat = passup_within['Lat'].mean() - 0.025
center_lon = passup_within['Long'].mean()
zoom_level = 9

# Scatter Map
fig_pass = create_scatter_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    color=None,
    hover_name='Pass-Up ID',
    hover_data=['Route Name','Route Number','Pass-Up Type','Time'],
    title='<br>Winnipeg Public Transport Pass-up Data',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Heat Map
fig_passheat = create_density_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    z_col=None,
    radius=2,
    opacity=0.5,
    title='<br>Winnipeg Public Transport Pass-up Data',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style='carto-positron',
    color_continuous_scale="Plasma",
    admin=admin
)

# Scatter Map
fig_RN = create_scatter_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    color='Route Number',
    hover_name='Pass-Up ID',
    hover_data=['Route Name','Route Number','Pass-Up Type','Time'],
    title='<br>Winnipeg Public Transport Pass-up Data by Route Number',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Create interactive bar chart
fig_RNbar = px.bar(
    route_counts,
    x='Route Number',
    y='Count',
    title='Pass-ups per Route Number in the past decade',
    labels={'Count': 'Pass-up Times'},
    text='Count',
    color='Route Number',
    # orientation='h',
)
fig_RNbar.update_traces(textposition='outside')

# Scatter Map
fig_YR = create_scatter_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    color='Year',
    hover_name='Pass-Up ID',
    hover_data=['Route Name','Route Number','Pass-Up Type','Time'],
    title='<br>Pass-ups data in Winnipeg by year',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Bar chart
fig_YRbar = px.bar(
    year_counts,
    x='Year',
    y='Count',
    title='<br>Pass-up times in Winnipeg by Year',
    labels={'Count': 'Pass-up Times'},
    text='Count',
    color='Year'
)
fig_YRbar.update_traces(textposition='outside')

# Scatter Map
fig_TR = create_scatter_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    color='Time_Period',
    hover_name='Pass-Up ID',
    hover_data=['Route Name','Route Number','Pass-Up Type','Time'],
    title='<br>Pass-ups data in Winnipeg by Time Period',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Scatter Map
fig_HR = create_scatter_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    color='Hour',
    hover_name='Pass-Up ID',
    hover_data=['Route Name','Route Number','Pass-Up Type','Time'],
    title='<br>Pass-ups data in Winnipeg by Hour',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Bar chart by Hour
fig_HRbar = px.bar(
    hour_counts,
    x='Hour',
    y='Count',
    title='<br>Pass-up times in Winnipeg by Hour',
    labels={'Count': 'Pass-up Times'},
    text='Count',
    color='Hour',
)
fig_HRbar.update_traces(textposition='outside')

# Bar chart by Time Period
fig_TRbar = px.bar(
    time_counts,
    y='Time_Period',
    x='Count',
    title='Pass-up times in Winnipeg by Time Period',
    labels={'Count': 'Pass-up Times'},
    text='Count',
    color='Time_Period',
    color_discrete_sequence=px.colors.qualitative.Light24,
    orientation='h'
)
fig_TRbar.update_traces(textposition='outside')

# Scatter Map
fig_TP = create_scatter_mapbox(
    df=passup_within,
    lat='Lat',
    lon='Long',
    color='Pass-Up Type',
    hover_name='Pass-Up ID',
    hover_data=['Route Name','Route Number','Pass-Up Type','Time'],
    title='<br>Pass-ups data in Winnipeg by Pass-up Type',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Bar chart
fig_TPbar = px.bar(
    type_counts,
    y='Pass-Up Type',
    x='Count',
    title='<br>Pass-up times in Winnipeg per Pass-Up Type',
    labels={'Count': 'Pass-up Times'},
    text='Count',
    color='Pass-Up Type',
    color_discrete_sequence=px.colors.qualitative.Light24,
    orientation='h'
)
fig_TPbar.update_traces(textposition='outside')

# Step 1: Read the data
# Use the url of the csv I uploaded to github
df_census = pd.read_csv('https://raw.githubusercontent.com/xupeitao/winnipegteencommute.github.io/refs/heads/main/data/Winnipeg_Census_Point.csv')

# Step 4: Convert stop locations into a GeoDataFrame
geometry = [Point(xy) for xy in zip(df_census['Long'], df_census['Lat'])]
gdf_census = gpd.GeoDataFrame(df_census, geometry=geometry)
gdf_census.crs = 'EPSG:4326'

# Get the administrative boundary of Winnipeg using OSMnx
city = 'Winnipeg, Canada'
admin = ox.geocode_to_gdf(city)
admin.crs = 4326

# Spatial Join to identify stops within the city boundary
census_within = gpd.sjoin(gdf_census, admin, how="inner", predicate="within")

# Layout Pre-setting
center_lat = census_within['Lat'].mean() - 0.025
center_lon = census_within['Long'].mean()
zoom_level = 9

limits = [(0, 50), (50, 100), (100, 200), (200,500), (500,2000)]
colors = ["grey", "royalblue", "lightseagreen", "orange", "red"]
sizes = [1, 3, 5, 7, 20]

# Create a new column for color categories based on the limits
census_within['Color_Category'] = pd.cut(census_within['Total_15_Density'], bins=[limit[0] for limit in limits] + [limits[-1][1]],
                                            labels=colors, right=False)

# Scatter Map
fig_total = create_scatter_mapbox(
    df=df_census,
    lat='Lat',
    lon='Long',
    color='Total_15_Density',
    hover_name='OBJECTID',
    hover_data=['Total_15_to_19_years','Men_15_to_19_years','Women_15_to_19_years','Shape_Area(km^2)','Total_15_Density','Men_15_Density','Women_15_Density'],
    title='<br>Total Teenager Density in Winnipeg (2021)',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style="carto-positron",
    admin=admin
)

# Update marker sizes by limits group
size_map = {color: size for color, size in zip(colors, sizes)}
census_within['Marker_Size'] = census_within['Color_Category'].map(size_map)
census_within['Marker_Size'] = census_within['Marker_Size'].fillna(5)
fig_total.update_traces(marker={'size': census_within['Marker_Size']})

# Box chart
fig_csbox = px.box(df_census, x=['Total_15_to_19_years','Men_15_to_19_years','Women_15_to_19_years',"Total_15_Density", "Men_15_Density", "Women_15_Density"],
                    title="Teenager Density in Winnipeg (2021)", orientation='h')
fig_csbox.update_layout(xaxis_type="log")

# Heat Map
fig_totalheat = create_density_mapbox(
    df=census_within,
    lat='Lat',
    lon='Long',
    z_col='Total_15_Density',
    radius=20,
    opacity=1,
    title='<br>Total Teenager Density in Winnipeg (2021)',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style='carto-positron',
    color_continuous_scale="Plasma",
    admin=admin
)

# Heat Map
fig_men = create_density_mapbox(
    df=census_within,
    lat='Lat',
    lon='Long',
    z_col='Men_15_Density',
    radius=20,
    opacity=1,
    title='<br>Men Teenager Density in Winnipeg (2021)',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style='carto-positron',
    color_continuous_scale="Plasma",
    admin=admin
)

# Heat Map
fig_women = create_density_mapbox(
    df=census_within,
    lat='Lat',
    lon='Long',
    z_col='Women_15_Density',
    radius=20,
    opacity=1,
    title='<br>Women Teenager Density in Winnipeg (2021)',
    zoom_level=zoom_level,
    center_lat=center_lat,
    center_lon=center_lon,
    mapbox_style='carto-positron',
    color_continuous_scale="Plasma",
    admin=admin
)

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP], suppress_callback_exceptions=True)
server = app.server # for deployment

# define the layout
app.layout = dbc.Container(
    [
        dbc.Row(
            [
                dbc.Col(
                    html.Div(
                        [
                            html.H2("Winnipeg Teens and Public Transit Unreliability", style={'textAlign': 'center'}),
                        ],
                        style={'backgroundColor': '#e6f2ff', 'padding': '10px','display': 'flex','justifyContent': 'center','alignItems': 'center','height': '100px'}
                    ),
                    md=6,
                ),
                dbc.Col(
                    html.Div(
                        [
                            html.H6("This project addressed 'What impact might public transit unreliability have on young riders?' by analyzing the gaps in transit reliability in neighbourhoods that host large population of young people.", style={'textAlign': 'center'}),
                        ],
                        style={'backgroundColor': '#e6f2ff', 'padding': '10px','display': 'flex','justifyContent': 'center','alignItems': 'center','height': '100px'}
                    ),
                    md=6,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H4("Public Transit Map", style={'textAlign': 'center'}),
                            ],
                            style={'backgroundColor': '#e6f2ff', 'padding': '10px','display': 'flex','justifyContent': 'center','alignItems': 'center','height': '100px'}
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Label(""), #Main Filtering:
                                dcc.Dropdown(
                                    id='main-filter-dropdown',
                                    options=[
                                        {'label': 'Bus Stops Scatter Map', 'value': 'stop_point'},
                                        {'label': 'Bus Stops Heat Map', 'value': 'stop_heat'},
                                        {'label': 'Passup Scatter Map', 'value': 'passup_point'},
                                        {'label': 'Passup Heat Map', 'value': 'passup_heat'},
                                        {'label': 'Passup by Year', 'value': 'passup_year'},
                                        {'label': 'Passup by Time Period', 'value': 'passup_timeperiod'},
                                        {'label': 'Passup by Hour', 'value': 'passup_hour'},
                                        {'label': 'Passup by Type', 'value': 'passup_type'},
                                        {'label': 'Passup by Route Number', 'value': 'passup_routenumber'},
                                    ],
                                    value='passup_routenumber',  # Default
                                )
                            ],
                            style={'backgroundColor': '#e6f2ff', 'padding': '10px','height': '100px'}
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H4("Teen Census Map", style={'textAlign': 'center'}),
                            ],
                            style={'backgroundColor': '#e6f2ff', 'padding': '10px','display': 'flex','justifyContent': 'center','alignItems': 'center','height': '100px'}
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.Label(""), #Census Filtering:
                                dcc.Dropdown(
                                    id='census-filter-dropdown',
                                    options=[
                                        {'label': 'Total Census Scatter Map', 'value': 'census_point'},
                                        {'label': 'Total Census Heat Map', 'value': 'census_heat'},
                                        {'label': 'Male Census Heat Map', 'value': 'census_male_heat'},
                                        {'label': 'Female Census Heat Map', 'value': 'census_female_heat'}
                                    ],
                                    value='census_point',  # Default
                                )
                            ],
                            style={'backgroundColor': '#e6f2ff', 'padding': '10px','height': '100px'}
                        ),
                    ],
                    md=3,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H4("", style={'textAlign': 'center'}), #Public Transit Map
                                dcc.Graph(id='passup_routenumber', figure=fig_RN)
                            ],
                            style={'padding': '20px', 'display': 'flex','justifyContent': 'center','alignItems': 'center'}
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H4("", style={'textAlign': 'center'}), #Teenager Census Map
                                dcc.Graph(id='census_total_scatter', figure=fig_total)
                            ],
                            style={'padding': '20px','display': 'flex','justifyContent': 'center','alignItems': 'center'}
                        ),
                    ],
                    md=6,
                ),
            ]
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H4("", style={'textAlign': 'center'}), #Pass-up Data Chart
                                dcc.Graph(id='passup_RNbar', figure=fig_RNbar)
                            ],
                            style={'padding': '20px','display': 'flex','justifyContent': 'center','alignItems': 'center'}
                        ),
                    ],
                    md=6,
                ),
                dbc.Col(
                    [
                        html.Div(
                            [
                                html.H4("", style={'textAlign': 'center'}), #Teenagers Census Box Chart
                                dcc.Graph(id='census_total_box', figure=fig_csbox)
                            ],
                            style={'padding': '20px','display': 'flex','justifyContent': 'center','alignItems': 'center'}
                        ),
                    ],
                    md=6,
                ),
            ]
        ),
    ],
    fluid=True,
)

@app.callback(
    Output('passup_routenumber', 'figure'),
    [Input('main-filter-dropdown', 'value')]
)
def update_map(main_filter):
    if main_filter == 'stop_point':
        return fig
    elif main_filter == 'stop_heat':
        return fig_heat
    elif main_filter == 'passup_point':
        return fig_pass
    elif main_filter == 'passup_heat':
        return fig_passheat
    elif main_filter == 'passup_year':
        return fig_YR
    elif main_filter == 'passup_timeperiod':
        return fig_TR
    elif main_filter == 'passup_hour':
        return fig_HR
    elif main_filter == 'passup_type':
        return fig_TP
    elif main_filter == 'passup_routenumber':
        return fig_RN

@app.callback(
    Output('passup_RNbar', 'figure'),
    [Input('main-filter-dropdown', 'value')]
)
def update_map(main_filter):
    if main_filter == 'stop_point':
        return fig_RNbar
    elif main_filter == 'stop_heat':
        return fig_RNbar
    elif main_filter == 'passup_point':
        return fig_RNbar
    elif main_filter == 'passup_heat':
        return fig_RNbar
    elif main_filter == 'passup_year':
        return fig_YRbar
    elif main_filter == 'passup_timeperiod':
        return fig_TRbar
    elif main_filter == 'passup_hour':
        return fig_HRbar
    elif main_filter == 'passup_type':
        return fig_TPbar
    elif main_filter == 'passup_routenumber':
        return fig_RNbar

@app.callback(
    Output('census_total_scatter', 'figure'),
    [Input('census-filter-dropdown', 'value')]
)
def update_map(census_filter):
    if census_filter == 'census_point':
        return fig_total
    elif census_filter == 'census_heat':
        return fig_totalheat
    elif census_filter == 'census_male_heat':
        return fig_men
    elif census_filter == 'census_female_heat':
        return fig_women

if __name__ == '__main__':
    app.run(debug=False, port=8050)