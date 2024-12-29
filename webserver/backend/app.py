from flask import Flask, request, redirect, url_for, render_template, send_from_directory, make_response, jsonify, flash, session
from flask_cors import CORS
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import logging
from logging.handlers import RotatingFileHandler
import zipfile
import glob
import time
from threading import Timer

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'd2271438da7ed08956bafefc80a475fc4c37d6f0bbb3747e617e52d6acfd1c04')

# Set up logging
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(level=logging.DEBUG)
handler = RotatingFileHandler('logs/app.log', maxBytes=1024 * 1024 * 10, backupCount=3)
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
app.logger.addHandler(handler)

# Global variables to manage batching
last_upload_time = 0
batch_delay = 5  # seconds to wait for more uploads
processing_timer = None

#front end comm

@app.route('/api/data')
def get_data():
    data = {}
    for foldername in os.listdir(app.config['UPLOAD_FOLDER']):
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], foldername)
        if os.path.isdir(folder_path):
            station_data = []
            csv_files = glob.glob(os.path.join(folder_path, '*.csv'))
            
            for file_path in csv_files:
                try:
                    df = pd.read_csv(file_path)
                    df['Time'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M:%S').dt.strftime('%Y-%m-%d %H:%M:%S')
                    station_data.extend(df.to_dict('records'))
                except Exception as e:
                    app.logger.error(f"Error reading file {file_path}: {str(e)}")
                    continue
            
            if station_data:
                data[foldername] = sorted(station_data, key=lambda x: x['Time'])
    
    return jsonify(data)
    
def process_uploads(folder):
    global processing_timer
    processing_timer = None
    app.logger.info(f"Starting to process uploads for folder: {folder}")
    drawResults(folder)
    app.logger.info(f"Finished processing uploads for folder: {folder}")

# Define the base directory for uploaded files
UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
    app.logger.info(f"Created upload folder: {UPLOAD_FOLDER}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Allowed file extensions (optional, for basic filtering)
ALLOWED_EXTENSIONS = {'csv'}

@app.route('/station/<station_name>')
def station_detail(station_name):
    app.logger.info(f"Accessing detailed view for station: {station_name}")
    station_folder = os.path.join(app.config['UPLOAD_FOLDER'], station_name)
    
    if not os.path.exists(station_folder):
        app.logger.error(f"Station folder not found: {station_folder}")
        flash(f"Station '{station_name}' not found", "error")
        return redirect(url_for('list_files'))

    # Read all CSV files in the station folder
    csv_files = glob.glob(os.path.join(station_folder, '*.csv'))
    if not csv_files:
        app.logger.warning(f"No CSV files found in station folder: {station_folder}")
        flash(f"No data files found for station '{station_name}'", "warning")
        return redirect(url_for('list_files'))

    all_data = pd.DataFrame()
    for file in csv_files:
        try:
            df = pd.read_csv(file)
            all_data = pd.concat([all_data, df], ignore_index=True)
        except Exception as e:
            app.logger.error(f"Error reading CSV file {file}: {str(e)}")
            continue

    if all_data.empty:
        app.logger.error(f"No valid data found for station: {station_name}")
        flash(f"No valid data found for station '{station_name}'", "error")
        return redirect(url_for('list_files'))

    # Convert 'Time' column to datetime
    all_data['Time'] = pd.to_datetime(all_data['Time'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
    
    # Remove rows with invalid timestamps
    all_data = all_data.dropna(subset=['Time'])

    # Sort data by time
    all_data = all_data.sort_values('Time')

    # List of parameters to plot
    parameters = ['Probe_TempCal', 'Condraw', 'CondCal', 'SpCond', 'Salinity', 'TurbRaw', 'TurbCal', 'TurbManu', 
                  'ChlRaw', 'ChlVolts', 'ChlCal', 'CDOMRaw', 'CDOMVolts', 'CDOMCal', 'CDOMChlEQ', 'ChlAdj', 'TempRaw', 'TempCal']

    # Generate plots for each parameter
    plots = []
    for param in parameters:
        if param in all_data.columns:
            # Remove non-numeric values and convert to float
            all_data[param] = pd.to_numeric(all_data[param], errors='coerce')
            
            # Drop NaN values for this parameter
            param_data = all_data.dropna(subset=[param])
            
            if not param_data.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.plot(param_data['Time'], param_data[param])
                ax.set_title(f'{param} over Time')
                ax.set_xlabel('Time')
                ax.set_ylabel(param)
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
                ax.xaxis.set_major_locator(mdates.AutoDateLocator())
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                # Save plot to a file
                plot_filename = f'{station_name}_{param}_plot.png'
                plot_path = os.path.join(station_folder, plot_filename)
                plt.savefig(plot_path)
                plt.close(fig)
                
                plots.append(plot_filename)
            else:
                app.logger.warning(f"No valid data for parameter {param} in station {station_name}")
        else:
            app.logger.warning(f"Parameter {param} not found in the data for station {station_name}")

    if not plots:
        app.logger.error(f"No plots could be generated for station: {station_name}")
        flash(f"No valid data available to plot for station '{station_name}'", "error")
        return redirect(url_for('list_files'))

    return render_template('station_detail.html', station_name=station_name, plots=plots)
    
# Function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Function to get the prefix from the file name
def get_prefix(filename):
    return filename.split('_', 1)[0]

def drawResults(station_folder):
    app.logger.info(f"Starting drawResults for station folder: {station_folder}")
    
    # Get all CSV files in the station folder
    csv_files = glob.glob(os.path.join(station_folder, '*.csv'))
    app.logger.debug(f"Found {len(csv_files)} CSV files in {station_folder}")

    # Initialize an empty DataFrame to store all data
    all_data = pd.DataFrame()
    error_files = []

    # Read and combine all CSV files
    for file_path in csv_files:
        app.logger.debug(f"Reading file: {file_path}")
        try:
            df = pd.read_csv(file_path)
            if df.empty:
                error_files.append(file_path)
                app.logger.warning(f"File {file_path} is empty and will be skipped.")
                continue
            
            df['Time'] = pd.to_datetime(df['Time'], format='%d-%m-%Y %H:%M:%S', errors='coerce')
            
            # Check for NaN values in this file
            chl_adj_col = next((col for col in df.columns if 'ChlAdj' in col), None)
            if chl_adj_col:
                nan_count = df[chl_adj_col].isna().sum()
                if nan_count > 0:
                    app.logger.warning(f"File {file_path} contains {nan_count} NaN values in the {chl_adj_col} column")
            
            all_data = pd.concat([all_data, df], ignore_index=True)
        except pd.errors.EmptyDataError:
            error_files.append(file_path)
            app.logger.warning(f"File {file_path} is empty and will be skipped.")
        except Exception as e:
            error_files.append(file_path)
            app.logger.error(f"Error reading file {file_path}: {str(e)}")

    if error_files:
        app.logger.warning(f"The following files were skipped due to errors: {', '.join(error_files)}")

    if all_data.empty:
        app.logger.error(f"No valid data found in any of the CSV files for station {os.path.basename(station_folder)}.")
        return

    app.logger.info(f"Combined data shape: {all_data.shape}")

    # Sort data by time
    all_data = all_data.sort_values('Time')

    # Check if 'ChlAdj' column exists
    chl_adj_col = next((col for col in all_data.columns if 'ChlAdj' in col), None)
    if not chl_adj_col:
        app.logger.error(f"'ChlAdj' column not found in the CSV files for station {os.path.basename(station_folder)}.")
        app.logger.error(f"Available columns: {all_data.columns.tolist()}")
        return

    # Log total NaN and Inf values before removal
    nan_count = all_data[chl_adj_col].isna().sum()
    inf_count = np.isinf(all_data[chl_adj_col]).sum()
    app.logger.info(f"Total NaN values in {chl_adj_col} column: {nan_count}")
    app.logger.info(f"Total Inf values in {chl_adj_col} column: {inf_count}")

    # Remove NaN and Inf values from the ChlAdj column
    all_data_clean = all_data[np.isfinite(all_data[chl_adj_col])]
    
    removed_count = len(all_data) - len(all_data_clean)
    app.logger.info(f"Removed {removed_count} rows with NaN or Inf values")

    if all_data_clean.empty:
        app.logger.error(f"No valid data found in the {chl_adj_col} column for station {os.path.basename(station_folder)}.")
        return

    all_data = all_data_clean  # Replace the original dataframe with the cleaned one

    app.logger.info("Calculating moving average and standard deviation")
    # Calculate moving average and standard deviation
    window = 4*12  # 24 hours, 4 data points per hour
    all_data['MA'] = all_data[chl_adj_col].rolling(window=window, center=True).mean()
    all_data['STD'] = all_data[chl_adj_col].rolling(window=window, center=True).std()

    # Calculate percentile bands
    all_data['Lower_Percentile'] = all_data[chl_adj_col].rolling(window=window, center=True).quantile(0.25)
    all_data['Upper_Percentile'] = all_data[chl_adj_col].rolling(window=window, center=True).quantile(0.75)

    app.logger.info("Creating plot")
    # Create the plot
    fig, ax = plt.subplots(figsize=(16, 10))

    # Plot raw data
    ax.scatter(all_data['Time'], all_data[chl_adj_col], alpha=0.3, s=10, color='#1f77b4', label='Raw Data', marker='x', linewidth=0.5)

    # Plot moving average
    ax.plot(all_data['Time'], all_data['MA'], color='#d62728', linewidth=2, label='12-hour Moving Average')

    # Plot standard deviation bands
    ax.fill_between(all_data['Time'], all_data['MA'] - all_data['STD'], 
                    all_data['MA'] + all_data['STD'], alpha=0.2, color='#ff7f0e', 
                    label='±1 Std Dev')

    # Plot percentile bands
    ax.fill_between(all_data['Time'], all_data['Lower_Percentile'], 
                    all_data['Upper_Percentile'], alpha=0.2, color='#2ca02c', 
                    label='25th-75th Percentile')

    # Set title and labels
    station_name = os.path.basename(station_folder)
    ax.set_title(f'Chlorophyll Adjusted (ChlAdj) Time Series Analysis - Station {station_name}', fontsize=20, pad=20)
    ax.set_xlabel('Time', fontsize=14, labelpad=10)
    ax.set_ylabel('ChlAdj (µg/L)', fontsize=14, labelpad=10)

    # Format x-axis
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%Y'))
    ax.xaxis.set_major_locator(mdates.AutoDateLocator())

    # Rotate and align the tick labels so they look better
    plt.gcf().autofmt_xdate()

    # Set y-axis limits to focus on the main data range
    y_min, y_max = np.nanpercentile(all_data[chl_adj_col], [1, 99])
    if np.isfinite(y_min) and np.isfinite(y_max):
        ax.set_ylim(y_min, y_max)
    else:
        app.logger.warning(f"Unable to set y-axis limits due to invalid data: y_min={y_min}, y_max={y_max}")

    # Improve legend
    ax.legend(loc='upper right', fontsize=12, framealpha=0.9)

    # Remove top and right spines
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    # Adjust layout
    plt.tight_layout()

    # Save the plot as a PNG file in the station folder
    output_file = os.path.join(station_folder, f'{station_name}_chlorophyll_analysis.png')
    plt.savefig(output_file, dpi=300, bbox_inches='tight')
    plt.close(fig)

    app.logger.info(f"Analysis complete for station {station_name}. Graph saved as {output_file}")


# Cooldown period in seconds
COOLDOWN_PERIOD = 300  # 5 minutes

@app.route('/regenerate_graphs', methods=['POST'])
def regenerate_graphs():
    current_time = datetime.now()
    last_regeneration = session.get('last_graph_regeneration')
    
    if last_regeneration:
        last_regeneration = datetime.fromisoformat(last_regeneration)
        if current_time - last_regeneration < timedelta(seconds=COOLDOWN_PERIOD):
            remaining_time = (last_regeneration + timedelta(seconds=COOLDOWN_PERIOD) - current_time).seconds
            flash(f'Please wait {remaining_time} seconds before regenerating graphs again.', 'warning')
            return redirect(url_for('list_files'))

    try:
        app.logger.info("Starting to regenerate all graphs")
        for foldername in os.listdir(app.config['UPLOAD_FOLDER']):
            folder_path = os.path.join(app.config['UPLOAD_FOLDER'], foldername)
            if os.path.isdir(folder_path):
                app.logger.info(f"Regenerating graph for folder: {foldername}")
                drawResults(folder_path)
        
        session['last_graph_regeneration'] = current_time.isoformat()
        flash('All graphs have been regenerated successfully.', 'success')
    except Exception as e:
        app.logger.error(f"Error regenerating graphs: {str(e)}")
        flash('An error occurred while regenerating graphs.', 'error')

    return redirect(url_for('list_files'))

# Upload endpoint
@app.route('/upload', methods=['POST'])
def upload_file():
    global last_upload_time, processing_timer

    app.logger.info("File upload request received")
    if 'file' not in request.files:
        app.logger.warning("No file part in the request")
        return 'No file part', 400
    file = request.files['file']
    if file.filename == '':
        app.logger.warning("No selected file")
        return 'No selected file', 400
    if file and allowed_file(file.filename):
        prefix = get_prefix(file.filename)
        app.logger.info(f"Processing file: {file.filename} with prefix: {prefix}")
        # Create a subdirectory for the prefix if it doesn't exist
        prefix_folder = os.path.join(app.config['UPLOAD_FOLDER'], prefix)
        if not os.path.exists(prefix_folder):
            os.makedirs(prefix_folder)
            app.logger.info(f"Created new folder: {prefix_folder}")
        
        # Save the file in the appropriate subdirectory
        file_path = os.path.join(prefix_folder, file.filename)
        file.save(file_path)
        app.logger.info(f"File saved: {file_path}")
        
        # Update the last upload time
        last_upload_time = time.time()
        
        # Cancel any existing timer
        if processing_timer:
            processing_timer.cancel()
            app.logger.debug("Cancelled existing processing timer")
        
        # Set a new timer to process uploads after the batch delay
        processing_timer = Timer(batch_delay, process_uploads, args=[prefix_folder])
        processing_timer.start()
        app.logger.info(f"Set new processing timer for {batch_delay} seconds")
        
        return 'File uploaded successfully. Analysis will be performed shortly.', 200
    app.logger.warning(f"Invalid file type: {file.filename}")
    return 'Invalid file type', 400

@app.route('/processing_status')
def processing_status():
    global processing_timer
    if processing_timer and processing_timer.is_alive():
        time_remaining = round(batch_delay - (time.time() - last_upload_time), 1)
        app.logger.debug(f"Processing in progress. Time remaining: {time_remaining} seconds")
        return jsonify({"status": "processing", "time_remaining": time_remaining})
    else:
        app.logger.debug("No active processing")
        return jsonify({"status": "idle"})

# Route to show all uploaded files with download links
@app.route('/')
def list_files():
    app.logger.info("Listing all files")
    folders = []
    current_time = time.time()
    archived_time_seconds = 21 * 24 * 60 * 60  # 21 days in seconds
    
    for foldername in os.listdir(app.config['UPLOAD_FOLDER']):
        folder_path = os.path.join(app.config['UPLOAD_FOLDER'], foldername)
        if os.path.isdir(folder_path):
            # Get all files
            files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
            
            # Find the graph file
            graph_file = next((f for f in files if f.endswith('_chlorophyll_analysis.png')), None)
            
            # Remove graph file from the list if it exists
            if graph_file:
                files.remove(graph_file)
            
            # Sort the remaining files alphabetically
            files.sort()
            
            # If graph file exists, put it at the top of the list
            if graph_file:
                files.insert(0, graph_file)
            
            # Get the latest update time from either the graph file or the most recent data file
            last_updated = None
            last_updated_timestamp = None
            
            if files:
                # Check all files to find the most recent update
                file_timestamps = []
                for file in files:
                    file_path = os.path.join(folder_path, file)
                    file_timestamps.append(os.path.getmtime(file_path))
                
                if file_timestamps:
                    last_updated_timestamp = max(file_timestamps)
                    last_updated = datetime.fromtimestamp(last_updated_timestamp).strftime('%Y-%m-%d %H:%M:%S')
            
            # Calculate age in seconds
            age_in_seconds = current_time - (last_updated_timestamp or 0)
            is_old = age_in_seconds > archived_time_seconds
            
            folders.append({
                'folder': foldername, 
                'files': files,
                'last_updated': last_updated,
                'last_updated_timestamp': last_updated_timestamp or 0,
                'is_old': is_old
            })
    
    # Sort folders by last_updated_timestamp, putting most recent first
    folders.sort(key=lambda x: (-(x['last_updated_timestamp'] or 0), x['folder']))
    
    app.logger.debug(f"Found {len(folders)} folders")
    return render_template('list_files.html', folders=folders)

# Route to download files
@app.route('/download/<folder>/<filename>')
def download_file(folder, filename):
    app.logger.info(f"Download request for file: {filename} in folder: {folder}")
    return send_from_directory(os.path.join(app.config['UPLOAD_FOLDER'], folder), filename)

# Route to download all files in a folder as a ZIP
@app.route('/download_folder/<folder>')
def download_folder(folder):
    app.logger.info(f"Download request for entire folder: {folder}")
    folder_path = os.path.join(app.config['UPLOAD_FOLDER'], folder)
    if not os.path.isdir(folder_path):
        app.logger.error(f"Folder not found: {folder}")
        return 'Folder not found', 404

    zip_filename = f"{folder}.zip"
    zip_path = os.path.join(app.config['UPLOAD_FOLDER'], zip_filename)

    app.logger.info(f"Creating ZIP file: {zip_path}")
    # Create a ZIP file
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))
                app.logger.debug(f"Added file to ZIP: {file}")

    app.logger.info("Sending ZIP file as response")
    # Send the ZIP file as a response
    response = make_response(send_from_directory(app.config['UPLOAD_FOLDER'], zip_filename))
    response.headers["Content-Disposition"] = f"attachment; filename={zip_filename}"
    os.remove(zip_path)  # Optionally remove the ZIP file after sending
    app.logger.info(f"ZIP file sent and removed: {zip_path}")
    return response

if __name__ == '__main__':
    app.logger.info("Starting Flask application")
    app.run(host='0.0.0.0', port=5000, debug=True)
