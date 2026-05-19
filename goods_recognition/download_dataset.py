import os
import urllib.request
import zipfile

url = "https://github.com/marcusklasson/GroceryStoreDataset/archive/refs/heads/master.zip"
zip_path = "dataset.zip"

print("Downloading dataset...")
urllib.request.urlretrieve(url, zip_path)

print("Extracting...")
with zipfile.ZipFile(zip_path, 'r') as zip_ref:
    zip_ref.extractall(".")

print("Done")