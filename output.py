import json
from trials import matchings
from helperFunctions import save_excel_sheet

# Uses list of matchings to produce output json file and excel file
with open('matchings.json', 'w') as json_file:
    json.dump(matchings, json_file, indent=4)

json_data = []

with open('matchings.json', 'r') as f:
    json_data = json.load(f)

save_excel_sheet(json_data)
