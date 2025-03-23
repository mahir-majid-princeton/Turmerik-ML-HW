import json
import glob
from helperFunctions import get_patient_info, get_patient_diagnosis, get_patient_medication

patientPath = './synthea_patient_data/*.json'
json_files = glob.glob(patientPath)

columns = ['patientId', 'gender', 'age', 'condition']
patients = []

# Parsing through JSON files of each patient as well as obtaining key attributes
# including gender, age, diagnosis, and medication
for file in json_files:
    with open(file, "r", encoding="utf-8") as f:
        data = json.load(f)

    attributes = data['entry'][0]['resource']
    patientId, gender, age = get_patient_info(attributes)
    if not patientId or not gender or not age: continue

    condition, finding = get_patient_diagnosis(data)

    medication = get_patient_medication(data)

    patient = ({
        "patientId": patientId,
        "gender": gender,
        "age": age,
        "condition": condition,  
        "finding": finding,
        "medication": medication
    })

    patients.append(patient)

    
    
    


    

