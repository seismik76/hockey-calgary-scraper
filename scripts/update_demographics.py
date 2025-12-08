import json
import os

# Define the new data
new_data = {
    "Alpine Park": {
        "name": "Alpine Park",
        "population": 0,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development, negligible population in 2021."
    },
    "Alyth/Bonnybrook": {
        "name": "Alyth/Bonnybrook",
        "population": 0,
        "median_income": None,
        "census_year": 2019,
        "notes": "Predominantly industrial area."
    },
    "Ambleton": {
        "name": "Ambleton",
        "population": 0,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development, negligible population in 2021."
    },
    "Beltline": {
        "name": "Beltline",
        "population": 25880,
        "median_income": 43087,
        "census_year": 2019,
        "notes": "Income data is from 2005 (outdated)."
    },
    "Cornerstone": {
        "name": "Cornerstone",
        "population": 6190,
        "median_income": 99000,
        "census_year": 2021,
        "notes": "Data from 2021 Calgary municipal census."
    },
    "Elbow Valley": {
        "name": "Elbow Valley",
        "population": 380,
        "median_income": 74500,
        "census_year": 2020,
        "notes": "Data provided by user."
    },
    "Glacier Ridge": {
        "name": "Glacier Ridge",
        "population": 0,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development, negligible population in 2021."
    },
    "Harmony": {
        "name": "Harmony",
        "population": None,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development in Springbank (Rocky View County)."
    },
    "Hotchkiss": {
        "name": "Hotchkiss",
        "population": 0,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development, negligible population in 2021."
    },
    "Legacy": {
        "name": "Legacy",
        "population": 8000,
        "median_income": None,
        "census_year": 2019,
        "notes": "Rapidly growing new community."
    },
    "Medicine Hill": {
        "name": "Medicine Hill",
        "population": 0,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development (Trinity Hills)."
    },
    "Quarry Park": {
        "name": "Quarry Park",
        "population": None,
        "median_income": None,
        "census_year": 2019,
        "notes": "Included in Douglasdale/Glen census data."
    },
    "Redstone": {
        "name": "Redstone",
        "population": 9050,
        "median_income": None,
        "census_year": 2019,
        "notes": "Rapidly growing new community."
    },
    "South Calgary": {
        "name": "South Calgary",
        "population": 4540,
        "median_income": 38012,
        "census_year": 2019,
        "notes": "Income data is from 2000 (outdated)."
    },
    "Springbank": {
        "name": "Springbank",
        "population": None,
        "median_income": None,
        "census_year": 2021,
        "notes": "Rural residential area in Rocky View County."
    },
    "Vermilion Hill": {
        "name": "Vermilion Hill",
        "population": 0,
        "median_income": None,
        "census_year": 2021,
        "notes": "New development, negligible population in 2021."
    },
    "Wolf Willow": {
        "name": "Wolf Willow",
        "population": 525,
        "median_income": None,
        "census_year": 2019,
        "notes": "New development."
    }
}

file_path = r'c:\Users\pmair\Hockey Calgary Scraper\data\reference\neighborhood_demographics.json'

# Load existing data
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
except FileNotFoundError:
    print(f"File not found: {file_path}")
    data = {}
except json.JSONDecodeError:
    print(f"Error decoding JSON from {file_path}")
    data = {}

# Update data
for community, info in new_data.items():
    if community in data:
        print(f"Updating {community}...")
        # Update specific fields, preserving others if they exist
        data[community].update(info)
    else:
        print(f"Adding {community}...")
        data[community] = info

# Save back to file
with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=4)

print("Demographics updated successfully.")
