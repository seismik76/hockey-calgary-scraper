import json
import csv
import os

def generate_income_template():
    # Load the association mapping
    json_path = 'association_neighborhoods.json'
    if not os.path.exists(json_path):
        print(f"Error: {json_path} not found.")
        return

    with open(json_path, 'r') as f:
        data = json.load(f)

    # Prepare CSV data
    csv_rows = []
    for association, neighborhoods in data.items():
        for neighborhood in neighborhoods:
            csv_rows.append({
                'Association': association,
                'Neighborhood': neighborhood,
                'Average_Household_Income_2021': '', # Placeholder for user to fill
                'Source': ''
            })

    # Write to CSV
    csv_path = 'association_income_template.csv'
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        fieldnames = ['Association', 'Neighborhood', 'Average_Household_Income_2021', 'Source']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        
        writer.writeheader()
        writer.writerows(csv_rows)

    print(f"Successfully created {csv_path}")
    print("Please fill in the 'Average_Household_Income_2021' and 'Source' columns.")
    print("Best Source: Statistics Canada Census Profile (Search for 'Calgary' as Census Subdivision).")

if __name__ == "__main__":
    generate_income_template()
