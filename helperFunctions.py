import requests
from datetime import date
from openai import OpenAI
import pandas as pd

# Parses through a patient's information from the Synthea dataset to get
# a patient's id, gender, and age
def get_patient_info(attributes):
    patientId = attributes['id']
    gender = ""
    age = 0.0

    if 'gender' in attributes:
        gender = attributes['gender']

    # Using user's birth date to precisely determine their age
    if 'birthDate' in attributes:
        birthDate = attributes['birthDate']
        today = date.today()
        year = birthDate[:4]
        month = birthDate[5:7]
        if month[-1] == '-': 
            month = birthDate[5:6]
            day = birthDate[7:]
        else:
            day = birthDate[8:]
        
        year = int(year)
        month = int(month)
        day = int(day)

        birth_date = date(year, month, day)
        days_difference = (today - birth_date).days
        age = round(days_difference / 365, 2)
    
    return patientId, gender, age

# Parses through a patient's information from the Synthea dataset to get
# a patient's diagnosis including thier condition and relevant findings
def get_patient_diagnosis(data):
    condition = set()
    finding = set()

    for entry in data.get('entry', []):
        resource = entry.get('resource', {})
    
        if resource.get('resourceType') == "Condition" and 'code' in resource and 'text' in resource['code']:
            condRes = resource['code']['text']
            clinicalStatus = resource['clinicalStatus']['coding'][0]['code']
            verificationStatus = resource['verificationStatus']['coding'][0]['code']

            if clinicalStatus == "active" and verificationStatus == "confirmed":
                if condRes[len(condRes)-10:] == '(disorder)' and condRes not in condition:
                    condition.add(condRes[:len(condRes)-11])
                if condRes[len(condRes)-9:] == "(finding)" and condRes not in finding:
                    finding.add(condRes[:len(condRes)-10])
    
    return list(condition), list(finding)

# Parses through a patient's information from the Synthea dataset to get
# a patient's medication
def get_patient_medication(data):
    medication = set()

    for entry in data.get('entry', []):
        resource = entry.get('resource', {})
    
        if resource.get('resourceType') == "Medication" and 'code' in resource and 'text' in resource['code']:
            medRes = resource['code']['text']

            if medRes not in medication:
                medication.add(medRes)
        
    return list(medication)



# Determines the relevant clinical studies that a patient can participate
# in based on their attributes and condition
def find_matching_studies(patientAge, patientGender,
                            patientCond, patientFindings, patientMedication):
    matchedStudies = []

    for condition in patientCond:
        # Forming a get request to receive list of relevant studies based on patient's condition
        parameters = {
            "format": "json",
            "query.cond": condition,
            "filter.overallStatus": "RECRUITING",
            "countTotal": "true"
        }

        base_url = "https://clinicaltrials.gov/api/v2/studies"
        response = requests.get(base_url, params=parameters)
        data = response.json()
        studies = data.get("studies", [])

        # Determines studies from the response that the patient is actually eligilbe for based on
        # their inclusion and exclusion criteria
        for study in studies:
            studyId = study["protocolSection"]["identificationModule"]["nctId"]
            studyTitle = study["protocolSection"]["identificationModule"]["briefTitle"]
            studyGender = study["protocolSection"]["eligibilityModule"]["sex"]

            minAgeStr = study["protocolSection"]["eligibilityModule"].get("minimumAge", float('-inf'))
            minAge = parse_age(minAgeStr)
            maxAgeStr = study["protocolSection"]["eligibilityModule"].get("maximumAge", float('inf'))
            maxAge = parse_age(maxAgeStr)

            eligibilityCriteriaMeet = determine_inclusion_eligibility(study, patientAge, minAge, maxAge, 
                                                                      patientGender, studyGender, studyId)
            eligibilityCriteriaMeet = determine_exclusion_eligibility(study, eligibilityCriteriaMeet, patientCond, 
                                                                      patientFindings, patientMedication)

            if eligibilityCriteriaMeet: matchedStudies.append({"trialId": studyId, "trialName": studyTitle, 
                                   "eligibilityCriteriaMeet": eligibilityCriteriaMeet})
    
    return matchedStudies

# Takes in a string age with a time measurement at the end of it such as 'Years' or 'Months',
# and converts it to a numerical value
def parse_age(strAge):
    age = strAge

    if strAge != float('-inf') and strAge != float('inf'):
        if strAge[len(strAge)-5:] == 'Years':
            age = int(strAge[:len(strAge)-6])
        elif strAge[len(strAge)-6:] == 'Months':
            age = round(int(strAge[:len(strAge)-7]) / 12, 2)
        elif strAge[len(strAge)-4:] == 'Days':
            age = round(int(strAge[:len(strAge)-5]) / 365, 2)
        elif strAge[len(strAge)-5:] == 'Hours':
            age = round(int(strAge[:len(strAge)-6]) / (365*24), 2)
        elif strAge[len(strAge)-4:] == 'Year':
            age = int(strAge[:len(strAge)-5])
        elif strAge[len(strAge)-5:] == 'Month':
            age = round(int(strAge[:len(strAge)-6]) / 12, 2)
        elif strAge[len(strAge)-3:] == 'Day':
            age = round(int(strAge[:len(strAge)-4]) / 365, 2)
        elif strAge[len(strAge)-4:] == 'Hour':
            age = round(int(strAge[:len(strAge)-5]) / (365*24), 2)
        elif strAge[len(strAge)-7:] == 'Minutes':
            age = round(int(strAge[:len(strAge)-8]) / (365*24*60), 2)

    return age

# Determines whether a patient meets the requirements of a study based on study's inclusion criteria
def determine_inclusion_eligibility(study, patientAge, minAge, maxAge, patientGender, studyGender, id):
    eligibilityCriteriaMeet = []
    eligibilityCriteria = study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    idx = eligibilityCriteria.find('Exclusion Criteria')
    inclusionCriteria = ""
    if idx != -1: inclusionCriteria = eligibilityCriteria[:idx]
    elif eligibilityCriteria[:18] == 'Inclusion Criteria':
        inclusionCriteria = eligibilityCriteria

    if minAge == float('-inf') and maxAge == float('inf'):
        eligibilityCriteriaMeet.append(f"Study accepts all ages")
    elif "age" in inclusionCriteria:
        if minAge != float('-inf') and maxAge != float('inf') and patientAge >= minAge and patientAge <= maxAge and patientAge > 1:
            eligibilityCriteriaMeet.append(
                f"Patient's age of {int(patientAge)} years old is within the study's age range of {minAge} years and {maxAge} years")
        elif minAge != float('-inf') and maxAge != float('inf') and patientAge >= minAge and patientAge <= maxAge and patientAge <= 1:
            eligibilityCriteriaMeet.append(
                f"Patient's age is at or below 1 year but is within the study's age range")
        elif minAge == float('-inf') and patientAge <= maxAge and patientAge > 1:
            eligibilityCriteriaMeet.append(
                f"Patient's age of {int(patientAge)} years is below study's maximum age requirement of {maxAge} years.")
        elif maxAge == float('inf') and patientAge >= minAge and patientAge > 1:
            eligibilityCriteriaMeet.append(
                f"Patient's age of {int(patientAge)} years is above study's minimum age requirement of {minAge} years.")
        else:
            return []

    if studyGender == "ALL":
        eligibilityCriteriaMeet.append(
            f"Study accepts all genders")
    elif patientGender == studyGender:
        eligibilityCriteriaMeet.append(
            f"Patient's gender matches the study's gender")
    else:
        return []

    return eligibilityCriteriaMeet

# Determines whether a patient meets the requirements of a study based on study's exclusion criteria
def determine_exclusion_eligibility(study, eligibilityCriteriaMeet, patientCond, patientFindings, patientMedication):
    eligibilityCriteria = study["protocolSection"]["eligibilityModule"]["eligibilityCriteria"]
    idx = eligibilityCriteria.find('Exclusion Criteria')
    exclusionCriteria = ""

    if idx != -1: exclusionCriteria = eligibilityCriteria[idx:]
    else: return eligibilityCriteriaMeet

    exclusionCriteriaArr = []

    for line in exclusionCriteria.split("\n"):
        if line.startswith("*"):
            exclusionCriteriaArr.append(line[2:])

    # Iterates through each bullet in the exclusion criteria and uses OpenAI's API to determine patient's
    # eligibility based on the given eclusion criteria bullet
    for i in range(len(exclusionCriteriaArr)):
        response = check_patient_exclusive_eligibility(exclusionCriteriaArr[i], patientCond, patientFindings,
                                                       patientMedication)
        if response == "FAIL": return []
        elif response: eligibilityCriteriaMeet.append(response)

    return eligibilityCriteriaMeet

# Helper method for checking a patient's eligibility based on exclusive criteria using OpenAI's API  
def check_patient_exclusive_eligibility(exclusionCriterion, patientCond, patientFindings, patientMedication):    
    prompt = f"""
    A patient is being evaluated for eligibility in a clinical trial. 
    The exclusion criterion being checked is: "{exclusionCriterion}".

    Patient details:
    - Conditions: {patientCond}
    - Findings: {patientFindings}
    - Medications: {patientMedication}

    If the patient meets the exclusion criterion, respond with only "FAIL".
    Otherwise, provide a sentence of why the patient is eligible.
    """
    
    # NOTE: I am leaving out the proper logic to check for exclusion criteria because 
    # I don't want to process a significant amount of data through my API token but if I had
    # a budget, I would be able to do this processing through a valid OPEN API key

    response = ""

    # client = OpenAI(
    #     api_key = "",
    # )

    # response = client.chat.completions.create(
    #     model="gpt-4-0613",
    #     messages=[
    #         {"role": "system", "content": "You are a medical eligibility evaluator."},
    #         {"role": "user", "content": prompt}
    #     ],
    #     temperature=0.3
    # )

    if response: return response["choices"][0]["message"]["content"].strip()
    else: return response

# Taking in matchings json data and saving a google spreadsheet containing the matchings
def save_excel_sheet(json_data):
    rows = []

    for patient in json_data: 
        patient_id = patient.get('patientId', '')
        for trial in patient.get('eligibleTrials', []):
            rows.append({
                'Patient ID': patient_id,
                'Trial ID': trial.get('trialId', ''),
                'Trial Name': trial.get('trialName', ''),
            })

    df = pd.DataFrame(rows)

    df.to_excel('Patient_Trial_Matchings.xlsx', index=False)