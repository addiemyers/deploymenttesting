#!/usr/bin/env python3
import cgi
import cgitb
import urllib.request
import urllib.parse
import json

# Enable backend browser error logging for easier debugging
cgitb.enable()

# Your OMDb API Key
API_KEY = "73400291"

# --- HEADERS ---
# We tell the browser to expect application/json instead of text/html
print("Content-Type: application/json; charset=utf-8\n")

# Parse incoming query parameters
form = cgi.FieldStorage()
search_query = form.getvalue("movie_title", "")

if not search_query:
    # Send custom JSON error if no movie title parameter was passed
    print(json.dumps({"Response": "False", "Error": "No movie title provided."}))
    exit()

# Safely encode the movie title for the URL string
encoded_title = urllib.parse.quote(search_query.strip())
url = f"https://www.omdbapi.com/?apikey={API_KEY}&t={encoded_title}"

try:
    with urllib.request.urlopen(url) as response:
        if response.status == 200:
            # Load the data from OMDb and parse it directly
            raw_data = response.read().decode('utf-8')
            # Stream the raw JSON back to the browser's JavaScript fetch caller
            print(raw_data)
        else:
            print(json.dumps({"Response": "False", "Error": f"OMDb responded with status code {response.status}."}))
except Exception as e:
    print(json.dumps({"Response": "False", "Error": f"Could not connect to database: {str(e)}"}))