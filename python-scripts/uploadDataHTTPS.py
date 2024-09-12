import requests
import os
import configparser
import logging

# Set up logging
logging.basicConfig(
    filename='upload.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

config = configparser.ConfigParser()
current_dir = os.path.dirname(os.path.abspath(__file__))
config_file = 'Upconfig.cfg'
configfilewithpath = os.path.join(current_dir, config_file)
config.read(configfilewithpath)

SERVER_URL = config.get('Section1', 'server_url')
data_dir = os.path.join(current_dir, config.get('Section1', 'data_dir'))
tracker_file = os.path.join(current_dir, 'uploaded_files.txt')

# Load the list of uploaded files from the tracker file
def load_uploaded_files():
    if os.path.exists(tracker_file):
        with open(tracker_file, 'r') as f:
            return set(f.read().splitlines())
    return set()

# Save the name of the uploaded file to the tracker file
def save_uploaded_file(filename):
    with open(tracker_file, 'a') as f:
        f.write(f"{filename}\n")

uploaded_files = load_uploaded_files()
files_uploaded = False

for filename in os.listdir(data_dir):
    if filename.endswith(".csv") and filename not in uploaded_files:
        file_path = os.path.join(data_dir, filename)
        
        with open(file_path, 'rb') as file:
            files = {'file': (filename, file, 'text/csv')}
            try:
                response = requests.post(SERVER_URL, files=files)
                logging.info(f"File {filename} sent. Response: {response.status_code}")
                if response.status_code == 200:
                    # Add the file to the tracker after successful upload
                    save_uploaded_file(filename)
                    files_uploaded = True
                    logging.info(f"File {filename} uploaded and recorded in tracker.")
                else:
                    logging.error(f"File {filename} failed to upload. Status code: {response.status_code}")
            except Exception as e:
                logging.error(f"Error sending file {filename}: {e}")

if files_uploaded == False:
    logging.info("No files were uploaded during this run.")
