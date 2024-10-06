import ast
import fuzzywuzzy
import pandas as pd
import re
import streamlit as st
from fuzzywuzzy import process

st.title("Data Preprocessing Tool for Clinic Names and Isolated Organisms")

uploaded_file = st.file_uploader("Upload CSV file")
if uploaded_file is not None:
    try:
        data0 = pd.read_csv(uploaded_file)
    except Exception as e:
        st.error(f"Error loading CSV file: {e}")
        st.stop()

    data0_columns = data0.columns.tolist()
    selected_column = st.selectbox("Select a column to process", data0_columns)

    if selected_column in ["Clinic Name", "Isolated Organisms"]:
        has_mapping_file = st.radio("Do you have a mapping file (TXT) for this column?", ("Yes", "No"))
        mapping = None

        if has_mapping_file == "Yes":
            mapping_file = st.file_uploader("Upload mapping file", type="txt")
            if mapping_file is not None:
                mapping_raw = mapping_file.getvalue().decode("utf-8")
                try:
                    mapping = ast.literal_eval(mapping_raw)
                    st.write("Mapping file uploaded!")
                except (ValueError, SyntaxError) as e:
                    st.error(f"Error reading mapping file: {e}")
                    st.stop()
            else:
                st.info("Please upload a mapping file.")
                st.stop()
        else:
            mapping = {}
            st.write("Proceeding without a mapping file.")

        def remove_clinic_dept(text):
            """Remove department from clinic name."""
            words = text.split()
            return ' '.join(words[:-1])

        def get_clinic_dept(text):
            """Extract department from clinic name."""
            words = text.split()
            return words[-1]

        def get_clinic_names_matches(data, selected_column, mapping):
            """Get possible clinic name matches using fuzzy matching."""
            clinic_names = sorted(data[selected_column].unique().tolist())
            clinic_names_no_dept = [remove_clinic_dept(name) for name in clinic_names]
            clinic_names_unique = sorted(set(clinic_names_no_dept))
            matches_dict = {}

            for ind in range(len(clinic_names_unique)):
                matches = process.extract(clinic_names_unique[ind], clinic_names_unique, limit=10)
                highest_score = matches[1][1]  # Exclude the string itself which has the highest score
                for m in matches[1:]:
                    if m[1] == highest_score:
                        key = clinic_names_unique[ind]
                        if key in matches_dict:
                            matches_dict[key].append(m[0])
                        else:
                            matches_dict[key] = [m[0]]

            # Exclude keys already in mapping
            matches_dict = {key: value for key, value in matches_dict.items() if key not in mapping}
            return matches_dict

        def clean_org_name(text):
            """Clean organism name by applying regex patterns."""
            patterns_iso_org = {
                "spaces_hyphens": re.compile(r'[\s\-]+'),
                "duplicate_words": re.compile(r'\b(complex|species)\s+\1\b', re.I),
                "possible_suspected_parenthesis": re.compile(r'\((suspected|possible)\)$'),
                "possible_suspected": re.compile(r'\ba?\s*(possible|suspected)\b', re.I)
            }

            org_name = patterns_iso_org['spaces_hyphens'].sub(' ', text.strip().lower())
            org_name = patterns_iso_org['duplicate_words'].sub(r'\1', org_name)

            if patterns_iso_org['possible_suspected_parenthesis'].search(org_name):
                words = org_name.split()
                return words[0].capitalize() + " " + " ".join(words[1:]) if words else org_name

            match = patterns_iso_org['possible_suspected'].search(org_name)
            if match:
                clean_name = patterns_iso_org['possible_suspected'].sub('', org_name).strip()
                words = clean_name.split()
                clean_name = words[0].capitalize() + ' ' + ' '.join(words[1:])
                clean_name = ' '.join(clean_name.split())
                return f"{clean_name} ({match.group(1)})".strip()
            else:
                words = org_name.split()
                return (words[0].capitalize() + ' ' + ' '.join(words[1:])).strip()

        def get_isolated_org_matches(data, selected_column, mapping):
            """Get grouped isolated organisms for matching."""
            unique_iso_org = set()
            clean_name_cache = {}

            for entry in data[selected_column].dropna().unique():
                iso_org_list = entry.split('&')
                for iso_org in iso_org_list:
                    iso_org = iso_org.strip()
                    if iso_org in clean_name_cache:
                        clean_iso_org = clean_name_cache[iso_org]
                    else:
                        clean_iso_org = clean_org_name(iso_org)
                        clean_name_cache[iso_org] = clean_iso_org
                    unique_iso_org.add(clean_iso_org)

            unique_iso_org = sorted(unique_iso_org)
            organism_groups = {}
            for org in unique_iso_org:
                genus_letter = org[0].upper() if org else '#'
                organism_groups.setdefault(genus_letter, []).append(org)

            return organism_groups

        if mapping is not None:
            if selected_column == "Clinic Name":
                clinic_names_matches = get_clinic_names_matches(data0, selected_column, mapping)

                if not clinic_names_matches:
                    st.success("All clinic names are already mapped.")
                    if st.button("Apply mappings"):
                        st.session_state['confirm_replacements'] = True
                else:
                    df = pd.DataFrame(clinic_names_matches.items(), columns=["Location", "Possible Replacement"])
                    df.index = range(1, len(df) + 1)
                    st.write("Here are the clinic locations and possible replacements:")
                    st.dataframe(df)

                    if 'confirm_replacements' not in st.session_state:
                        st.session_state['confirm_replacements'] = False

                    keys = list(clinic_names_matches.keys())

                    for i, key in enumerate(keys):
                        st.markdown(f"**Location {i+1}:** {key}")
                        options = clinic_names_matches[key] + ['Keep as is', 'Type in replacement..']
                        value = st.selectbox(f"Select replacement:", options=options, key=f"replace_{i}")

                        if value == 'Type in replacement..':
                                otherRep = st.text_input('Type in replacement..', key=f"other_{i}")
                        else:
                            otherRep = ''

                        if value == 'Keep as is':
                            mapping[key] = key
                        elif value == 'Type in replacement..':
                            if otherRep.strip():
                                mapping[key] = otherRep.strip()
                            else:
                                st.warning(f"Please enter a replacement for '{key}'.")
                        else:
                            mapping[key] = value

                    if st.button("Review replacements"):
                        st.session_state['review_replacements'] = True

                    if st.session_state.get('review_replacements', False):
                        df_rep = pd.DataFrame({
                            "Before": list(mapping.keys()),
                            "After": list(mapping.values())
                        })
                        df_rep.index = range(1, len(df_rep) + 1)
                        st.write("Review your replacements:")
                        st.dataframe(df_rep)

                        if st.button("Confirm replacements"):
                            st.session_state['confirm_replacements'] = True

                if st.session_state.get('confirm_replacements', False):
                    clinic_names_no_dept = data0[selected_column].apply(remove_clinic_dept)
                    dept_names = data0[selected_column].apply(get_clinic_dept)

                    clinic_loc = clinic_names_no_dept.replace(mapping)
                    dept_replacements = {'Onc.': 'Oncology'}
                    clinic_dept = dept_names.replace(dept_replacements)

                    data1 = data0.copy()
                    data1[selected_column] = clinic_loc + ' ' + clinic_dept

                    @st.cache_data
                    def convert_df(df):
                        return df.to_csv(index=False).encode("utf-8")

                    csv = convert_df(data1)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.download_button("Download mapping file", str(mapping), file_name='clin_names_mapping.txt')
                    with col2:
                        st.download_button(
                            label="Download processed data as CSV",
                            data=csv,
                            file_name="standardized_clin_names.csv",
                            mime="text/csv"
                        )

            elif selected_column == "Isolated Organisms":
                organism_groups = get_isolated_org_matches(data0, selected_column, mapping)
                group_letters = sorted(organism_groups.keys())

                selected_group = st.selectbox("Select a batch to process (by first letter of genus):", group_letters, index=None)
                if selected_group is not None:
                    batch_organisms = organism_groups[selected_group]
                    isolated_org_names_matches = {}
                    for org in batch_organisms:
                        matches = process.extract(org, batch_organisms, limit=10)
                        matches = [m for m in matches if m[0] != org]
                        if matches:
                            highest_score = matches[0][1]
                            highest_matches = [m[0] for m in matches if m[1] == highest_score]
                            if org not in mapping:
                                isolated_org_names_matches[org] = highest_matches

                    if not isolated_org_names_matches:
                        st.success(f"All isolated organisms in batch '{selected_group}' are already mapped.")
                        if st.button("Apply mappings"):
                            st.session_state['confirm_replacements'] = True
                    else:
                        df = pd.DataFrame({
                            "Isolated Organism": isolated_org_names_matches.keys(),
                            "Possible Replacement": isolated_org_names_matches.values()
                        })
                        df.index = range(1, len(df) + 1)
                        st.write("Here are the isolated organisms and possible replacements:")
                        st.dataframe(df)

                        if 'user_mappings' not in st.session_state:
                            st.session_state['user_mappings'] = {}

                        keys = list(isolated_org_names_matches.keys())

                        for i, key in enumerate(keys):
                            st.markdown(f"**Isolated Organism {i+1}:** {key}")
                            options = isolated_org_names_matches[key] + ['Keep as is', 'Type in replacement..']
                            value = st.selectbox(f"Select replacement:", options=options, key=f"iso_rep_{i}")

                            if value == 'Type in replacement..':
                                otherRep = st.text_input("Type in your replacement:", key=f"iso_other_{i}")
                            else:
                                otherRep = ''

                            if value == 'Keep as is':
                                st.session_state['user_mappings'][key] = key
                            elif value == 'Type in replacement..':
                                if otherRep.strip():
                                    st.session_state['user_mappings'][key] = otherRep.strip()
                                else:
                                    st.warning(f"Please enter a replacement for '{key}'.")
                            else:
                                st.session_state['user_mappings'][key] = value

                        if st.button("Review replacements"):
                            st.session_state['review_replacements'] = True

                        if st.session_state.get('review_replacements', False):
                            mapping.update(st.session_state['user_mappings'])

                            df_rep = pd.DataFrame({
                                "Before": list(st.session_state['user_mappings'].keys()),
                                "After": list(st.session_state['user_mappings'].values())
                            })
                            df_rep.index = range(1, len(df_rep) + 1)
                            st.write("Review your replacements:")
                            st.dataframe(df_rep)

                            if st.button("Confirm replacements"):
                                st.session_state['confirm_replacements'] = True

                    if st.session_state.get('confirm_replacements', False):
                        replaced_entry_list = []
                        clean_name_cache = {}

                        for entry in data0[selected_column]:
                            if pd.isnull(entry):
                                replaced_entry_list.append('')
                                continue

                            replaced = []
                            orgs = entry.split("&")

                            for org in orgs:
                                org = org.strip()
                                if org in clean_name_cache:
                                    cleaned_org = clean_name_cache[org]
                                else:
                                    cleaned_org = clean_org_name(org)
                                    clean_name_cache[org] = cleaned_org
                                std_org = mapping.get(cleaned_org, cleaned_org)
                                replaced.append(std_org)

                            replaced_entry = ' & '.join(replaced)
                            replaced_entry_list.append(replaced_entry)

                        data1 = data0.copy()
                        data1[selected_column] = replaced_entry_list

                        @st.cache_data
                        def convert_df(df):
                            return df.to_csv(index=False).encode("utf-8")

                        csv = convert_df(data1)

                        col1, col2 = st.columns(2)
                        with col1:
                            st.download_button("Download mapping file", str(mapping), file_name='isolated_organisms_mapping.txt')
                        with col2:
                            st.download_button(
                                label="Download processed data as CSV",
                                data=csv,
                                file_name="standardized_isolated_organisms.csv",
                                mime="text/csv"
                            )
                else:
                    st.write(" ")
            else:
                st.write(" ")
    elif selected_column is None:
        st.write(" ")
    else:
        st.write(f"Column {selected_column} is not supported.")
else:
    st.write(" ")
