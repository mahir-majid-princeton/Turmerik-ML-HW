This github repository contains the matching algorithm for patients from the Synthea dataset and provides eligible trials from clinicaltrials.gov that the patients are 
eligible for. To use it, first make sure to have all the required libraries by running, pip install -r requirements.txt, and then simply execute the "output.py" file
to generate a json file called 'matchings.json' and a excel file, which can also be opened as a google spreadsheet, called 'Patient_Trial_Matchings.xlsx' 
containing all the patient and trial matches.
