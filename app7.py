from dash import Dash, dcc, html
from dash.dependencies import Input, Output
import pandas as pd
import plotly.express as px
import datetime
import numpy as np
from oauth2client.service_account import ServiceAccountCredentials
import gsheets
import requests
from dash.dash import no_update

pdkey = "Sheets.json"
xlsx_file = 'data.xlsx'
Sheet_List = []

spreadsheet_id = "1bZZe4WqYr1nV-y80IPq5GTiRK2jHf6DS-lQb6vJXV3I"

SCOPE = ["https://spreadsheets.google.com/feeds", 'https://www.googleapis.com/auth/spreadsheets',
         "https://www.googleapis.com/auth/drive.file", "https://www.googleapis.com/auth/drive"]

CREDS = ServiceAccountCredentials.from_json_keyfile_name(pdkey, SCOPE)

access_token = CREDS.create_delegated(CREDS._service_account_email).get_access_token().access_token
url = "https://www.googleapis.com/drive/v3/files/" + spreadsheet_id + "/export?mimeType=application%2Fvnd.openxmlformats-officedocument.spreadsheetml.sheet"


def refresh_data_from_sheets():
    global xlsx_data
    global sheet_names
    global Sheet_List
    res = requests.get(url, headers={"Authorization": "Bearer " + access_token})

    # If you want to create the XLSX data as a file, you can use the following script.
    with open(xlsx_file, 'wb') as f:
        f.write(res.content)

    # Load the XLSX file
    xlsx_data = pd.ExcelFile(xlsx_file)

    # Get sheet names from the XLSX file
    sheet_names = xlsx_data.sheet_names
    
    Sheet_List = [{'label': sheet, 'value': sheet} for sheet in sheet_names]
    return sheet_names
    
refresh_data_from_sheets()

app = Dash(__name__, external_stylesheets=['/assets/style.css'])

app.title = "Autonomous Drone Based Water Quality Monitoring"
    
df = pd.read_excel(xlsx_file, sheet_name=0)
df['DateTime:'] = pd.to_datetime(df['DateTime:'], format='%d/%m/%Y', errors='coerce')

#transform every unique date to a number
numdate= [x for x in range(len(df['DateTime:'].unique()))]

# Update the CSS class names for the header
app.layout = html.Div(
    children=(
        html.Div(
            children=(
                html.H1(
                    children="Autonomous Drone Water Quality Monitoring", className="header-title"
                ),
                html.P(
                    children=(
                        "By Lochlan Sharkey"
                    ),
                    className="header-description",
                ),
                html.Button(
                    id="refresh-button",
                    children=html.Span("Refresh Data", className="rotate-text"),
                    n_clicks=0,
                ),
            ),
            className="header",
        ),
        html.Div(
            children=(
                html.Div(
                    children=(
                        html.H1(
                            children="Select a Site:", className="title"
                        ),
                        dcc.Dropdown(
                            id='dropdown',
                            className='dropclass',
                            options=Sheet_List,
                            value=sheet_names[0],
                            style={'width': '550px', 'display': 'inline-block'}
                        ),
                        html.Img(src="/assets/searchlogo3.png", className="searchlogo",
                            style={'display': 'inline-block', 'height': '31px', 'width': '34px',
                                    'margin-left': '10px'}
                        ),
                    ),
                    className="card",
                ),
                html.Div(
                    children=(
                        dcc.Graph(
                            id='scatter-maxbox',
                            config={"displayModeBar": False},
                        ),
                        html.Div(
                            children=(
                                html.H2("Depth", className="title"),
                                dcc.Slider(
                                    id='depth-slider',
                                    min=df['Depth (m):'].min(),
                                    max=df['Depth (m):'].max(),
                                    value=df['Depth (m):'].min(),
                                    marks={str(depth): str(depth) for depth in df['Depth (m):'].unique()},
                                    step=None
                                ),
                            ),
                            className="slider-container",
                        ),
                        html.Div(
                            children=(
                                html.H2("Date", className="title"),
                                dcc.Slider(
                                    id='date-slider',
                                    min=numdate[0],
                                    max=numdate[-1],
                                    value=numdate[0],
                                    marks={numd: date.strftime('%d/%m') for numd, date in
                                           zip(numdate, df['DateTime:'].dt.date.unique())},
                                    step=None
                                ),
                            ),
                            className="slider-container",
                        ),
                    ),
                    className="card",
                ),
            ),
            className="wrapper",
        ),
    ),
)
    
# Define the callback
@app.callback(
    [Output('dropdown', 'options'),
    Output('scatter-maxbox', 'figure')],
    [Input('dropdown', 'value'),
    Input('depth-slider', 'value'),
    Input('date-slider', 'value'),
    Input('refresh-button', 'n_clicks'),
    Input('dropdown', 'options'),]
)


def update_figure(selected_sheet, depth, selected_date, refresh_clicks, Sheet_List):
    # Global Variables
    
    # Check if the refresh button was clicked
    if refresh_clicks > 0:
        # Refresh the data from Google Sheets
        refresh_data_from_sheets()
        Sheet_List=[{'label': sheet, 'value': sheet} for sheet in sheet_names]
        print(sheet_names)
        
        
    df = pd.read_excel(xlsx_file, sheet_name=selected_sheet)
    df['DateTime:'] = pd.to_datetime(df['DateTime:'], format='%d/%m/%Y', errors='coerce')
    
    Map_Zoom, Map_Center = Get_Map_Zoom_And_Center(df['Drone Longatude:'], df['Drone Latatude:'])
    
    date_to_filter = df['DateTime:'].dt.date.unique()[selected_date]
    filtered_df = df[(df['DateTime:'].dt.date == date_to_filter)]
    
    if filtered_df.empty:
        # Return a message or a placeholder figure to indicate no data
        error_msg = "No data available for the selected date."
        fig = px.scatter()
        fig.update_layout(annotations=[
            dict(
                text=error_msg,
                xref="paper",
                yref="paper",
                showarrow=False,
                font=dict(size=20)
            )
        ])
        
    else:
        # Set the smallest depth for the selected date
        min_depth = filtered_df['Depth (m):'].min()
        
        # Filter the data based on the selected date and depth
        filtered_df = filtered_df[(filtered_df['Depth (m):'] >= depth - 1) & (filtered_df['Depth (m):'] <= depth + 1)]

        if filtered_df.empty:
            # Return a message or a placeholder figure to indicate no data for the selected depth
            error_msg = f"No data available for depth {depth} on the selected date."
            fig = px.scatter()
            fig.update_layout(annotations=[
                dict(
                    text=error_msg,
                    xref="paper",
                    yref="paper",
                    showarrow=False,
                    font=dict(size=20)
                )
            ])
            
        else:
            
            # Filter the data based on the selected date
            fig = px.scatter_mapbox(filtered_df, lat = 'Drone Latatude:', lon = 'Drone Longatude:', color = 'Temperature (c):',
                hover_data={'Depth (m):': ':.2f', 'Temperature (c):': ':.2f'},
                center = {'lat': Map_Center[0], 'lon': Map_Center[1]},  # Use Map_Center values,
                zoom = int(Map_Zoom),
                range_color=(15, 25),
                mapbox_style = 'open-street-map',
            )
            
            fig.update_layout(transition_duration=500)
        
    return Sheet_List, fig


@app.callback(
    [Output('depth-slider', 'min'),
     Output('depth-slider', 'max'),
     Output('depth-slider', 'value'),
     Output('depth-slider', 'marks')],
    [Input('dropdown', 'value'),
     Input('date-slider', 'value')]
)
def update_depth_slider(selected_sheet, selected_date):
    df = pd.read_excel(xlsx_file, sheet_name=selected_sheet)

    # Filter the data based on the selected date
    date_to_filter = df['DateTime:'].dt.date.unique()[selected_date]
    filtered_df = df[df['DateTime:'].dt.date == date_to_filter]

    min_value = filtered_df['Depth (m):'].min()
    max_value = filtered_df['Depth (m):'].max()

    # Get the unique depth values in the dataset
    unique_depths = filtered_df['Depth (m):'].unique()

    # Initialize the marks dictionary
    marks = {}
    
    # Round the min_value down to the nearest integer
    min_value = np.floor(min_value).astype(int)

    # Round the max_value up to the nearest integer
    max_value = np.ceil(max_value).astype(int)
    
    value = min_value
    
    # Iterate over the unique depth values
    for depth in unique_depths:
        marks[int(depth)] = str(int(depth))
            
    return min_value, max_value, value, marks


@app.callback(
    [Output('date-slider', 'min'),
     Output('date-slider', 'max'),
     Output('date-slider', 'marks')],
    [Input('dropdown', 'value')]
)
def update_date_slider(selected_sheet):
    df = pd.read_excel(xlsx_file, sheet_name=selected_sheet)
    numdate = [x for x in range(len(df['DateTime:'].unique()))]
    min_value = numdate[0]
    max_value = numdate[-1]
    marks = {numd: date.strftime('%d/%m') for numd, date in zip(numdate, df['DateTime:'].dt.date.unique())}

    return min_value, max_value, marks


def Get_Map_Zoom_And_Center(longitudes=None, latitudes=None):
    """Function documentation:\n
    Basic framework adopted from Krichardson under the following thread:
    https://community.plotly.com/t/dynamic-zoom-for-mapbox/32658/7

    # NOTE:
    # THIS IS A TEMPORARY SOLUTION UNTIL THE DASH TEAM IMPLEMENTS DYNAMIC ZOOM
    # in their plotly-functions associated with mapbox, such as go.Densitymapbox() etc.

    Returns the appropriate zoom-level for these plotly-mapbox-graphics along with
    the center coordinate tuple of all provided coordinate tuples.
    """

    # Check whether both latitudes and longitudes have been passed,
    # or if the list lenghts don't match
    if ((latitudes is None or longitudes is None)
            or (len(latitudes) != len(longitudes))):
        # Otherwise, return the default values of 0 zoom and the coordinate origin as center point
        return 0, (0, 0)

    # Get the boundary-box 
    b_box = {} 
    b_box['height'] = latitudes.max()-latitudes.min()
    b_box['width'] = longitudes.max()-longitudes.min()
    b_box['center']= (np.mean(latitudes), np.mean(longitudes))

    # get the area of the bounding box in order to calculate a zoom-level
    area = b_box['height'] * b_box['width']

    # * 1D-linear interpolation with numpy:
    # - Pass the area as the only x-value and not as a list, in order to return a scalar as well
    # - The x-points "xp" should be in parts in comparable order of magnitude of the given area
    # - The zpom-levels are adapted to the areas, i.e. start with the smallest area possible of 0
    # which leads to the highest possible zoom value 20, and so forth decreasing with increasing areas
    # as these variables are antiproportional
    zoom = np.interp(x=area,
                     xp=[0, 5**-10, 4**-10, 3**-10, 2**-10, 1**-10, 1**-5],
                     fp=[20, 15,    14,     13,     12,     7,      5])

    # Finally, return the zoom level and the associated boundary-box center coordinates
    return zoom, b_box['center']

    
# Run the app
if __name__ == '__main__':
    app.run_server(debug=True)
