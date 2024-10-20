#### Data Preprocessing Tool for Clinic Names and Isolated Organisms

**Request Details:**

1. Standardize Clinic Name Column: Resolve inconsistencies (e.g., *SG Clinic* vs. *Singapore Clinic*) through user input.
2. Reuse a Mapping Dictionary: Utilize a previously created/downloaded mapping dictionary.
3. Standardize Isolated Organisms Column: Extend the standardization process to the *Isolated Organisms* column.



**Proposed App Features:**

1. Utilize the library `fuzzywuzzy` to provide the top-matching names, obtained from the uploaded dataset, in a dropdown menu for the user to choose from.

2. Include a free-text input field for cases where the desired replacement is not in the dropdown menu.

3. Allow users to review the selected replacements for each entry.

4. Prompt users to confirm the selected replacements to initiate the generation of the mapping file and processing of the dataset.

5. Allow users to download the mapping dictionary as a TXT file.

6. Allow users to download the processed data as a CSV file.

7. Allow users to upload the previously created/downloaded mapping TXT file to reuse mappings, thereby minimizing rework.

   - Partial: Prompts user to select replacements only for entries not included in the mapping file.
   - Complete: Recognizes that all entries are contained in the mapping file; only action required from the user is to apply the mappings.

8. Implement batch processing for isolated organisms (i.e., alphabetically by genus name) to address processing time issues.

   

**Assumptions:**

1. Column names are assumed to be *Clinic Name* and *Isolated Organisms*.
2. Clinic names are assumed to be in the format *Clinic Location + Department* (e.g., *BRI Neurology*, *Bristol Neurology*).
3. Isolated organisms are assumed to be listed in one cell, separated by *&*.

**Installations:**

- pip install fuzzywuzzy==0.18.0
- pip install pandas==2.2.2
- pip install python-Levenshtein==0.26.0
- pip install streamlit==1.38.0

**Run:**
- streamlit run app.py
