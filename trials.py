from patient import patients
from helperFunctions import find_matching_studies

matchings = []

# Finding matching studies for each patient and storing results into matchings array
for patient in patients:
    patientId = patient['patientId']
    patientAge = patient['age']
    patientGender = patient['gender']
    patientCond = patient['condition']
    patientFindings = patient['finding']
    patientMedication = patient['medication']

    matchedStudies = find_matching_studies(patientAge, patientGender,
                                patientCond, patientFindings, patientMedication)
            
    matchings.append({"patientId": patientId, "eligibleTrials": matchedStudies})
