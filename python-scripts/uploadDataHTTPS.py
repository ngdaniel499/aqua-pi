import requests
import os
import logging
import shutil
import configparser
from datetime import datetime

# Set up logging
logging.basicConfig(
    filename='upload.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def log_and_print(message, level=logging.INFO):
    print(message)
    if level == logging.INFO:
        logging.info(message)
    elif level == logging.ERROR:
        logging.error(message)

# Define relative paths
current_dir = os.path.dirname(os.path.abspath(__file__))
data_dir = os.path.join(current_dir, 'data')
uploaded_data_dir = os.path.join(data_dir, 'uploaded-data')

# Ensure directories exist
os.makedirs(data_dir, exist_ok=True)
os.makedirs(uploaded_data_dir, exist_ok=True)

# Read server URL from config file
config = configparser.ConfigParser()
config_file = os.path.join(current_dir, 'Upconfig.cfg')
config.read(config_file)

try:
    SERVER_URL = config.get('Section1', 'server_url')
except (configparser.NoSectionError, configparser.NoOptionError) as e:
    log_and_print(f"Error reading server_url from config file: {e}", logging.ERROR)
    raise

def upload_file(filename):
    file_path = os.path.join(data_dir, filename)
    with open(file_path, 'rb') as file:
        files = {'file': (filename, file, 'text/csv')}
        try:
            response = requests.post(SERVER_URL, files=files)
            log_and_print(f"File {filename} sent. Response: {response.status_code}")
            if response.status_code == 200:
                log_and_print(f"File {filename} uploaded successfully.")
                return True
            else:
                log_and_print(f"File {filename} failed to upload. Status code: {response.status_code}", logging.ERROR)
                return False
        except Exception as e:
            log_and_print(f"Error sending file {filename}: {e}", logging.ERROR)
            return False

def move_file_to_uploaded(filename):
    src = os.path.join(data_dir, filename)
    dst = os.path.join(uploaded_data_dir, filename)
    shutil.move(src, dst)
    log_and_print(f"Moved {filename} to uploaded directory.")

def get_files_to_upload():
    return [f for f in os.listdir(data_dir) if f.endswith(".csv") and f != "uploaded-data"]

def main():
    files_to_upload = get_files_to_upload()
    
    if not files_to_upload:
        log_and_print("No files to upload.")
        return

    # Sort files by modification time (newest first)
    files_to_upload.sort(key=lambda x: os.path.getmtime(os.path.join(data_dir, x)), reverse=True)
    
    newest_file = files_to_upload[0]
    files_uploaded = []

    for filename in files_to_upload:
        if upload_file(filename):
            files_uploaded.append(filename)

    if files_uploaded:
        # Move all uploaded files except the newest one to the 'uploaded-data' directory
        for filename in files_uploaded:
            if filename != newest_file:
                move_file_to_uploaded(filename)
        log_and_print(f"Uploaded {len(files_uploaded)} files. Kept {newest_file} in 'data' directory.")
    else:
        log_and_print("Failed to upload any files.", logging.ERROR)

if __name__ == "__main__":
    main()