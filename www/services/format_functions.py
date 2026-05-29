from .utils import *
from .parsers import *
import zipfile
import tempfile
import os


def format_ab_column(entry, source, file_type):         # Function for AB Column (format--> "Abstract")
    abstract = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            abstract = entry.get('abstract', '').replace('\n', ' ')
        elif file_type == '.txt' or file_type == '.ciw':
            abstract = entry.get('AB', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            abstract = entry.get('AB', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            abstract = entry.get('abstract', '')
        elif file_type == '.csv':
            abstract = entry['Abstract']
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            abstract = entry['Abstract']
    elif source == 'The_Lens':
        if file_type == '.csv':
            abstract = entry['Abstract']
    elif source == 'Cochrane':
        if file_type == '.txt':
            abstract = entry.get('AB', '')

    return abstract


def format_af_column(entry, source, file_type):         # Function for AF Column (format--> "[Surname, Name]")
    authors = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            authors_str = entry.get('author', '').replace('\n', ' ')
            authors_list = authors_str.split(" and ")

            for person in authors_list:
                parts = person.split(", ")
                if len(parts) == 2:
                    surname, first_names = parts
                else:
                    # Se ci sono più parti, la prima è il cognome, il resto sono nomi propri
                    surname = parts[0]
                    first_names = ' '.join(parts[1:])

                # author_dict = {'Surname': surname, 'Name': first_names}
                author_dict = surname + ' ' + first_names
                authors.append(author_dict)
        elif file_type == '.txt' or file_type == '.ciw':
            authors_list = entry.get('AF', '')
            for person in authors_list:
                parts = person.split(", ")
                if len(parts) == 2:
                    surname, first_names = parts
                else:
                    # Se ci sono più parti, la prima è il cognome, il resto sono nomi propri
                    surname = parts[0]
                    first_names = ' '.join(parts[1:])

                # author_dict = {'Surname': surname, 'Name': first_names}
                author_dict = surname + ' ' + first_names
                authors.append(author_dict)
    elif source == 'PubMed':
        if file_type == '.txt':
            for author in entry.get('FAU', '').split(";"):
                if ', ' in author:
                    surname, first_names = author.split(", ")
                    #author_dict = {'Surname': surname, 'Name': first_names}
                    author_dict = surname + ' ' + first_names
                    authors.append(author_dict)
                else:
                    # Handle cases where the author string does not contain a comma and space
                    surname = author
                    first_names = ''
                    #author_dict = {'Surname': surname, 'Name': first_names}
                    author_dict = surname + ' ' + first_names
                    authors.append(author_dict)
    elif source == 'Scopus':
        if file_type == '.bib':
            for person in entry.get('author', []).split(" and "):
                parts = person.split(", ")
                if len(parts) == 2:
                    surname, first_names = parts
                else:
                    # Se ci sono più parti, la prima è il cognome, il resto sono nomi propri
                    surname = parts[0]
                    first_names = ' '.join(parts[1:])
                author_dict = surname + ' ' + first_names
                authors.append(author_dict)
        elif file_type == '.csv':
            persons = str(entry['Author full names']).split("; ")
            for person in persons:
                if person.strip() and len(person.split(", ")) == 2:
                    surname, name_oid = person.split(", ")
                    name = name_oid.split(" (")[0]
                    author_dict = surname + ' ' + name
                    authors.append(author_dict)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            persons = entry['Authors'].split("; ")
            for person in persons:
                if person.strip() and len(person.split(", ")) == 2:
                    surname, name = person.split(", ")
                    # author_dict = {'Surname': surname, 'Name': name}
                    author_dict = surname + ' ' + name
                    authors.append(author_dict)
    elif source == 'The_Lens':
        if file_type == '.csv':
            persons = str(entry['Author/s']).split("; ")
            for person in persons:
                if person.strip() and len(person.strip().split(" ")) > 1:
                    parts = person.split(" ")
                    name = " ".join(parts[:-1])
                    surname = parts[-1]
                    # author_dict = {'Surname': surname, 'Name': name}
                    author_dict = surname + ' ' + name
                    authors.append(author_dict)
    elif source == 'Cochrane':
        if file_type == '.txt':
            authors = ''
    return authors


def format_au_column(entry, source, file_type):         # Function for AU Column (format--> "[Surname, N.]")
    authors = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            authors_str = entry.get('author', '').replace('\n', ' ')
            authors_list = authors_str.split(" and ")

            for person in authors_list:
                parts = person.split(", ")
                if len(parts) == 2:
                    surname, names = parts
                else:
                    surname = parts[0]
                    names = ' '.join(parts[1:])

                initials = ''.join([name[0] for name in names.split() if name])
                # author_dict = {'Surname': surname, 'Name Initials': initials}
                author_dict = surname + ' ' + initials
                authors.append(author_dict)
        elif file_type == '.txt' or file_type == '.ciw':
            authors_list = entry.get('AU', '')
            for author in authors_list:
                parts = author.split(", ")
                if len(parts) == 2:
                    surname, names = parts
                else:
                    surname = parts[0]
                    names = ' '.join(parts[1:])

                # initials = ''.join([name[0] + '.' for name in re.split(r'[ -]', names) if name])
                # author_dict = {'Surname': surname, 'Name Initials': initials}
                author_dict = surname + ' ' + names
                authors.append(author_dict)
    elif source == 'PubMed':
        if file_type == '.txt':
            authors_list = entry.get('AU', '').split(";")
            for author in authors_list:
                if author:
                    surname, *initials = author.split(" ")
                    initials = ' '.join(initials)
                    #author_dict = {'Surname': surname, 'Name Initials': initials}
                    author_dict = surname + ' ' + initials
                    authors.append(author_dict)
    elif source == 'Scopus':
        if file_type == '.bib':
            for person in entry.get('author', []).split(" and "):
                surname, names = person.split(", ")
                initials = ''
                for name in names.split(" "):
                    initials += name[0] + '.'
                author_dict = surname + ' ' + initials
                authors.append(author_dict)
        elif file_type == '.csv':
            persons = str(entry['Authors']).split("; ")
            for person in persons:
                if person.strip() and len(person.strip().split(" ")) > 1:
                    parts = person.split(" ")
                    surname = " ".join(parts[:-1])
                    initials = parts[-1]
                    author_dict = surname + ' ' + initials
                    authors.append(author_dict)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            # Pulizia preliminare dei dati
            authors_raw = re.sub(r"\s+", " ", entry['Authors'])  # Rimuove spazi multipli
            authors_raw = re.sub(r"[()]", "", authors_raw)       # Rimuove parentesi
            
            # Suddivisione degli autori
            persons = authors_raw.split("; ")
            for person in persons:
                if person.strip() and len(person.split(", ")) == 2:
                    surname, name = person.split(", ")
                    initials = ''.join([part[0] for part in name.split()])
                    author_dict = surname + ' ' + initials 
                    authors.append(author_dict)
                elif person.strip() and len(person.split(" ")) > 1:
                    parts = person.split(" ")
                    surname = parts[-1]
                    initials = ''.join([part[0] + '.' for part in parts[:-1]])
                    author_dict = surname + ' ' + initials
                    authors.append(author_dict)
    elif source == 'The_Lens':
        if file_type == '.csv':
            persons = str(entry['Author/s']).split("; ")
            for person in persons:
                if person != "null null":
                    if person.strip():
                        person = person.strip()
                        surname = re.sub(r".*\s", "", person)
                        name = re.sub(r"\s+[^ ]+$", "", person)
                        name = re.sub(r"[^A-Z]", "", name)
                        author_dict = f"{surname.upper()} {name}"
                        authors.append(author_dict)
    elif source == 'Cochrane':
        if file_type == '.txt':
            for author in entry.get('AU', '').split("; "):
                if author:
                    surname, *initials = author.split(" ")
                    if len(initials) >= 2:
                        #author_dict = {'Surname': initials[0], 'Name Initials': initials[1]}
                        author_dict = initials[0] + ' ' + initials[1]
                    else:
                        #author_dict = {'Surname': surname, 'Name Initials': initials[0]}
                        author_dict = surname + ' ' + initials[0]
                    authors.append(author_dict)

    return authors


def format_au1_un_column(entry, source, file_type):     # Function for AU1_UN Column (format--> "University of the First Author")
    university = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            university = entry.get('affiliations', '').replace('\n', ' ').split("; ")[0]
        elif file_type == '.txt' or file_type == '.ciw':
            university = str(entry.get('C3', '')).split("; ")[0].replace('[', '').replace(']', '').replace("'", '')
    elif source == 'PubMed':
        if file_type == '.txt':
            istituti = entry.get('AD', '').split(";")
            risultato = []

            if isinstance(istituti[0], str):
                parti = istituti[0].split(",")
            if len(parti) > 1 and any(
                    keyword in parti[1] for keyword in ["University", "National", "Medical", "Centre", "Electronic"]):
                seconda_parte = parti[1].strip().rstrip('.')
                risultato.append(seconda_parte)
            elif len(parti) > 2 and any(
                    keyword in parti[2] for keyword in ["University", "National", "Medical", "Centre", "Electronic"]):
                terza_parte = parti[2].strip().rstrip('.')
                risultato.append(terza_parte)

            university = ';'.join(risultato)
    elif source == 'Scopus':
        if file_type == '.bib':
            affiliation = entry.get('affiliations', []).split("; ")[0]
            university = affiliation.split(", ")[0]
        elif file_type == '.csv':
            affiliation = str(entry['Affiliations']).split("; ")[0]
            university = affiliation.split(", ")[0]
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            persons = re.findall(r'\((.*?)\)', entry['Authors Affiliations'])
            if len(persons) > 0:
                university = persons[0]
    elif source == 'The_Lens':
        if file_type == '.csv':
            university = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            university = ''
        
    return university


def format_au_un_column(entry, source, file_type):      # Function for AU_UN Column (format--> [Universities])
    universities = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            universities = entry.get('affiliations', '').replace('\n', ' ').split("; ")
        elif file_type == '.txt' or file_type == '.ciw':
            author_universities = str(entry.get('C3', '')).split("; ")
            for university in author_universities:
                universities.append(university.replace('[', '').replace(']', '').replace("'", ''))
    elif source == 'PubMed':
        if file_type == '.txt':
            for text in entry.get('AD', '').split(";"):
                if isinstance(text, str):
                    istituti = text.split(";")
                    risultato = []

                    for istituto in istituti:
                        if any(keyword in istituto for keyword in ["University", "National", "Medical", "Centre", "Electronic"]):
                            # Dividi la sottostringa usando il delimitatore ','
                            parti = istituto.split(",")
                            if len(parti) > 1 and any(keyword in parti[1] for keyword in ["University", "National", "Medical", "Centre", "Electronic"]):
                                # Prendi la seconda parte (dopo la prima virgola) e rimuovi eventuali punti alla fine
                                seconda_parte = parti[1].strip().rstrip('.')
                                risultato.append(seconda_parte)
                            elif len(parti) > 2 and any(keyword in parti[2] for keyword in ["University", "National", "Medical", "Centre", "Electronic"]):
                                # Prendi la terza parte (dopo la seconda virgola) e rimuovi eventuali punti alla fine
                                terza_parte = parti[2].strip().rstrip('.')
                                risultato.append(terza_parte)

                    # Unisci le stringhe risultanti in un'unica stringa con ';' come separatore
                    universities.extend(risultato)
    elif source == 'Scopus':
        if file_type == '.bib':
            for affiliation in entry.get('affiliations', []).split("; "):
                universities.append(affiliation.split(", ")[0])
        elif file_type == '.csv':
            for affiliation in str(entry['Affiliations']).split("; "):
                universities.append(affiliation.split(", ")[0])
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            persons = re.findall(r'\((.*?)\)', entry['Authors Affiliations'])
            for person in persons:
                universities.append(person)
    elif source == 'The_Lens':
        if file_type == '.csv':
            universities = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            university = ''
            universities.append(university)

    return universities


def format_bp_column(entry, source, file_type):         # Function for BP Column (format--> Begin Page)
    begin_page = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            begin_page = entry.get('pages', '').split("-")[0]
        elif file_type == '.txt' or file_type == '.ciw':
            begin_page = entry.get('BP', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            try:
                begin_page = entry.get('PG', '').split("-")
                if begin_page[0] < begin_page[1]:
                    begin_page = begin_page[0]
            except:
                begin_page = ''
    elif source == 'Scopus':
        if file_type == '.bib':
            begin_page = entry.get('pages', '').split(" - ")[0]
        elif file_type == '.csv':
            if str(entry.get('Page start', '')) != "nan":
                begin_page = str(entry.get('Page start', ''))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            if len(str(entry['Pagination']).split("-")) == 2:
                begin_page, end_page = entry['Pagination'].split("-")
    elif source == 'The_Lens':
        if file_type == '.csv':
            begin_page = entry['Start Page']
    elif source == 'Cochrane':
        if file_type == '.txt':
            begin_page = ''

    return begin_page


def format_c1_column(entry, source, file_type):         # Function for C1 Column (format--> [Affiliations])
    affiliations = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            affiliation_text = entry.get('affiliation', '')
            if affiliation_text:
                affiliation_lines = affiliation_text.strip().split("\n")  # Remove leading and trailing whitespaces from the 'affiliation' field and split it into lines.

                for line in affiliation_lines:
                    if "(Corresponding Author)" not in line:
                        num_authors = len(line.split("; "))
                        if num_authors == 0:  # If there is just one author, the affiliation is the string formed by joining the parts from the third part onwards.
                            parts = line.split(",")
                            affiliation = ", ".join(parts[2:])
                        else:  # If there are multiple authors, split the last part into subparts using ',' as the separator. The affiliation is the string formed by joining the subparts from the third subpart onwards.
                            parts = line.split(";")
                            last_parts = parts[-1]
                            last_part = last_parts.split(",")
                            affiliation = ", ".join(last_part[2:])
                        affiliation = affiliation.strip().rstrip('.')  # Remove leading and trailing whitespaces from the affiliation and remove any trailing '.'
                        affiliations.append(affiliation)
        elif file_type == '.txt' or file_type == '.ciw':
            author_affiliations = entry.get('C1', '')
            if len(author_affiliations) > 0:
                for affiliation in author_affiliations:
                    if ']' in affiliation:
                        affiliations.append(affiliation.split("] ")[1].replace('.', ''))
                    else:
                        affiliations.append(affiliation.replace('.', ''))
            else:
                affiliations = []
    elif source == 'PubMed':
        if file_type == '.txt':
            affiliations = entry.get('AD', '').split(".;")
    elif source == 'Scopus':
        if file_type == '.bib':
            for affiliation in entry.get('affiliations', []).split("; "):
                affiliations.append(affiliation)
        elif file_type == '.csv':
            for affiliation in str(entry['Affiliations']).split("; "):
                affiliations.append(affiliation)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            persons = re.findall(r'\((.*?)\)', entry['Authors (Raw Affiliation)']) 
            for person in persons:
                affiliations.append(person)
    elif source == 'The_Lens':
        if file_type == '.csv':
            affiliations = []
    elif source == 'Cochrane':
        if file_type == '.txt':
            affiliations = []

    return affiliations


def format_cr_column(entry, source, file_type):         # Function for CR Column (format--> "[References]")
    cited_references = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            references = entry.get('cited-references', '')
            if references:
                cited_references = references.split("\n")
            else:
                cited_references = []
        elif file_type == '.txt' or file_type == '.ciw':
            cited_references = entry.get('CR', '') if entry.get('CR', '') else []
    elif source == 'PubMed':
        if file_type == '.txt':
            cited_references = []
    elif source == 'Scopus':
        if file_type == '.csv':
            for reference in str(entry.get('References', '')).split("; "):
                cited_references.append(reference)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            cited_references = []
    elif source == 'The_Lens':
        if file_type == '.csv':
            cited_references = str(entry['References']).split("; ")
    elif source == 'Cochrane':
        if file_type == '.txt':
            cited_references = []

    return cited_references


def format_de_column(entry, source, file_type):         # Function for DE Column (format--> "[Keywords]")
    author_keywords = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            keywords = entry.get('keywords', '').replace('\n', ' ').strip().split("; ")
            author_keywords.extend(keywords)
        elif file_type == '.txt' or file_type == '.ciw':
            for keyword in entry.get('DE', ''):
                author_keywords.extend(keyword.split("; "))
    elif source == 'PubMed':
        if file_type == '.txt':
            for keyword in entry.get('MH', '').split(";"):
                keyword = keyword.replace('*', '').strip()
                author_keywords.append(keyword)
    elif source == 'Scopus':
        if file_type == '.bib':
            try:
                for keyword in entry.get('author_keywords', []).split("; "):
                    if keyword != "nan":
                        author_keywords.append(keyword)
                    else:
                        author_keywords = []
            except:
                author_keywords = []
        elif file_type == '.csv':
            for keyword in str(entry['Author Keywords']).split("; "):
                if keyword != "nan":
                    author_keywords.append(keyword)
                else:
                    author_keywords = []
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            if str(entry['MeSH terms']) == 'nan':
                author_keywords = []
            else:
                keywords = str(entry['MeSH terms']).split("; ")
                for keyword in keywords:
                    # keyword_dict = {'Terms': keyword}
                    author_keywords.append(keyword)
    elif source == 'The_Lens':
        if file_type == '.csv':
            if str(entry['Keywords']) == 'null' or str(entry['Keywords']) == 'nan':
                author_keywords = []
            else:
                keywords = str(entry['Keywords']).split("; ")
                for keyword in keywords:
                    # keyword_dict = {'Terms': keyword}
                    author_keywords.append(keyword)
    elif source == 'Cochrane':
        if file_type == '.txt':
            for keyword in entry.get('KY', '').split(";"):
                author_keywords.append(keyword)

    return author_keywords


def format_di_column(entry, source, file_type):         # Function for DI Column (format--> "DOI")
    doi = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            doi = entry.get('doi', '')
        elif file_type == '.txt' or file_type == '.ciw':
            doi = entry.get('DI', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            doi = entry.get('LID', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            doi = entry.get('doi', '')
        elif file_type == '.csv':
            doi = entry.get('DOI', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            doi = entry['DOI']
    elif source == 'The_Lens':
        if file_type == '.csv':
            doi = entry['DOI']
    elif source == 'Cochrane':
        if file_type == '.txt':
            doi = entry.get('DOI', '')

    return doi


def format_dt_column(entry, source, file_type):         # Function for DT Column ("Document Type")
    document_type = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            document_type = entry.get('type', '')
        elif file_type == '.txt' or file_type == '.ciw':
            document_type = entry.get('DT', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            document_type = entry.get('PT', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            document_type = entry.get('type', '')
        elif file_type == '.csv':
            document_type = entry.get('Document Type', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            document_type = entry['Publication Type']
    elif source == 'The_Lens':
        if file_type == '.csv':
            document_type = entry['Publication Type']
    elif source == 'Cochrane':
        if file_type == '.txt':
            document_type = ''

    return document_type


def format_em_column(entry, source, file_type):         # Function for EM Column (format--> "[Authors E-mail]")
    emails = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            for email in entry.get('author-email', '').split("\n"):
                emails.append(email)
        elif file_type == '.txt' or file_type == '.ciw':
            for email in entry.get('EM', ''):
                emails.extend(email.split("; "))
    elif source == 'PubMed':
        if file_type == '.txt':
            for email_info in entry.get('AD', '').split(";"):
                if 'Electronic address:' in email_info:
                    email = email_info.split("Electronic address:")[1].strip().rstrip('.')
                    emails.append(email)
    elif source == 'Scopus':
        if file_type == '.bib':
            for email_info in entry.get('correspondence_address', '').split("; "):
                if 'email:' in email_info:
                    email = email_info.split("email:")[1].strip()
                    emails.append(email)
        elif file_type == '.csv':
            for email_info in str(entry.get('Correspondence Address', '')).split("; "):
                if 'email:' in email_info:
                    email = email_info.split("email:")[1].strip()
                    emails.append(email)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            emails = ''
    elif source == 'The_Lens':
        if file_type == '.csv' or file_type == '.xlsx':
            emails = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            emails = ''

    return emails


def format_ep_column(entry, source, file_type):         # Function for EP Column ("End Page")
    end_page = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            try:
                end_page = entry.get('pages', '').split("-")
                if end_page[0] < end_page[1]:
                    end_page = end_page[1]
            except:
                end_page = ''
        elif file_type == '.txt' or file_type == '.ciw':
            end_page = entry.get('EP', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            try:
                end_page = entry.get('PG', '').split("-")
                if end_page[0] < end_page[1]:
                    end_page = end_page[1]
            except:
                end_page = ''
    elif source == 'Scopus':
        if file_type == '.bib':
            try:
                end_page = entry.get('pages', '').split(" - ")[1]
            except:
                end_page = ''
        elif file_type == '.csv':
            if str(entry.get('Page end', '')) != "nan":
                end_page = str(entry.get('Page end', ''))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            if len(str(entry['Pagination']).split("-")) == 2:
                begin_page, end_page = entry['Pagination'].split("-")
    elif source == 'The_Lens':
        if file_type == '.csv':
            end_page = entry['End Page']
    elif source == 'Cochrane':
        if file_type == '.txt':
            end_page = ''

    return end_page


def format_fu_column(entry, source, file_type):         # Function for FU Column ("Funding Details")
    funding = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            funding = entry.get('funding-acknowledgement', '')
        elif file_type == '.txt' or file_type == '.ciw':
            funding = entry.get('FU', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            for funding_info in entry.get('GR', '').split(";"):
                if funding_info:
                    funding.append(funding_info)
    elif source == 'Scopus':
        if file_type == '.csv':
            for funding_info in str(entry.get('Funding Details', '')).split("; "):
                if funding_info != "nan":
                    funding.append(funding_info)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            funding = entry["Funding"] if str(entry["Funding"]) != "nan" else ''
    elif source == 'The_Lens':
        if file_type == '.csv':
            funding = entry["Funding"] if str(entry["Funding"]) != "nan" else ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            funding = ''

    return funding


def format_fx_column(entry, source, file_type):         # Function for FX Column (format--> "Funding Text")
    fx = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            fx = entry.get('funding-text', '')
        elif file_type == '.txt' or file_type == '.ciw':
            fx = entry.get('FX', [''])[0]
    elif source == 'PubMed':
        fx = ''
    elif source == 'Scopus':
        if file_type == '.csv':
            funding_texts = str(entry.get('Funding Texts', ''))
            if funding_texts != "nan":
                fx = funding_texts
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            fx = entry["Acknowledgements"]
    elif source == 'The_Lens':
        if file_type == '.csv':
            fx = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            fx = ''

    return fx


def format_id_column(entry, source, file_type):         # Function for ID Column (format--> [Index Keywords])
    index_keywords = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            keywords = entry.get('keywords-plus', '').replace('\n', ' ').strip().split("; ")
            index_keywords.extend(keywords)
        elif file_type == '.txt' or file_type == '.ciw':
            for keyword in entry.get('ID', ''):
                index_keywords.extend(keyword.split("; "))
    elif source == 'PubMed':
        if file_type == '.txt':
            for keyword in entry.get('MH', '').split(";"):
                keyword = keyword.strip('*')
                index_keywords.append(keyword)
    elif source == 'Scopus':
        if file_type == '.bib':
            try:
                for keyword in entry.get('keywords', []).split("; "):
                    index_keywords.append(keyword)
            except:
                index_keywords = []
        elif file_type == '.csv':
            for keyword in str(entry['Index Keywords']).split("; "):
                index_keywords.append(keyword)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            if str(entry['MeSH terms']) == 'nan':
                index_keywords = []
            else:
                keywords = str(entry['MeSH terms']).split("; ")
                for keyword in keywords:
                    # keyword_dict = {'Terms': keyword}
                    index_keywords.append(keyword)
    elif source == 'The_Lens':
        if file_type == '.csv':
            if str(entry['Keywords']) == 'null' or str(entry['Keywords']) == 'nan':
                index_keywords = []
            else:
                keywords = str(entry['Keywords']).split("; ")
                for keyword in keywords:
                    # keyword_dict = {'Terms': keyword}
                    index_keywords.append(keyword)
    elif source == 'Cochrane':
        if file_type == '.txt':
            for keyword in entry.get('KY', '').split(";"):
                index_keywords.append(keyword)

    return index_keywords


def format_is_column(entry, source, file_type):         # Function for IS Column (format--> "Issue")
    issue = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            issue = entry.get('Number', '')
        elif file_type == '.txt' or file_type == '.ciw':
            issue = entry.get('IS', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            issue = entry.get('IP', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            issue = entry.get('number', '')
        elif file_type == '.csv':
            if str(entry.get('Issue', '')) != "nan":
                issue = str(int(entry.get('Issue', '')))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            issue = entry['Issue'] if str(entry['Issue']) != "nan" else ''
    elif source == 'The_Lens':
        if file_type == '.csv':
            issue = entry['Issue Number'] if str(entry['Issue Number']) != "nan" else ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            issue = ''

    return issue


def format_ji_column(entry, source, file_type):         # Function for JI Column (format--> "Abbrev. Journal Name")
    abbrev_source_title = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            abbrev_source_title = entry.get('journal-iso', '')
        elif file_type == '.txt' or file_type == '.ciw':
            abbrev_source_title = entry.get('JI', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            abbrev_source_title = entry.get('TA', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            abbrev_source_title = entry.get('abbrev_source_title', '')
        elif file_type == '.csv':
            abbrev_source_title = entry.get('Abbreviated Source Title', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            abbrev_source_title = entry['Source title']
    elif source == 'The_Lens':
        if file_type == '.csv':
            abbrev_source_title = entry['Source Title']
    elif source == 'Cochrane':
        if file_type == '.txt':
            abbrev_source_title = entry.get('SO', '')
    
    return abbrev_source_title


def format_la_column(entry, source, file_type):         # Function for LA Column (format--> "Language")
    language = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            language = entry.get('language', '')
        elif file_type == '.txt' or file_type == '.ciw':
            language = entry.get('LA', [''])[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            language = entry.get('LA', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            language = entry.get('language', '')
        elif file_type == '.csv':
            language = entry.get('Language of Original Document', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            language = ''
    elif source == 'The_Lens':
        if file_type == '.csv':
            language = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            language = ''

    return language


def format_oa_column(entry, source, file_type):         # Function for OA Column (format--> [Open Access])
    open_access = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            for oa in entry.get('oa', '').strip().split(", "):
                open_access.append(oa)
        elif file_type == '.txt' or file_type == '.ciw':
            for oa in entry.get('OA', ''):
                open_access.extend(oa.split(", "))
    elif source == 'PubMed':
        if file_type == '.txt':
            open_access = ''
    elif source == 'Scopus':
        if file_type == '.bib':
            try:
                open_access = entry.get('note', '').split("; ")[1]
            except:
                open_access = ''
        elif file_type == '.csv':
            open_access = entry.get('Open Access', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            open_access = entry['Open Access']
    elif source == 'The_Lens':
        if file_type == '.csv':
            open_access = entry['Open Access Colour']
    elif source == 'Cochrane':
        if file_type == '.txt':
            open_access = ''

    return open_access


def format_oi_column(entry, source, file_type):         # Function for OI Column ([Orcid Number]")
    oi = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            for orcid_numbers in entry.get('orcid-numbers', '').split("\n"):
                parts = orcid_numbers.split("/")
                if len(parts[-1].strip()) == 19:
                    oi.append(parts[-1].strip())
        elif file_type == '.txt' or file_type == '.ciw':
            orcid_ids = list(entry.get('OI', ''))
            if orcid_ids:  # If the 'OI' field is not empty, split the string into parts using the delimiter '; ' and extract the ORCID number from each part.
                for orcid in orcid_ids:
                    orcid_parts = orcid.split("; ")
                    for part in orcid_parts:
                        orcid_split = part.split("/")
                        orcid_number = orcid_split[-1].strip()
                        if len(orcid_number) == 19:
                            oi.append(orcid_number)
            else:
                oi.append('')
    elif source == 'PubMed':
        if file_type == '.txt':
            oi = []
            for orcid in entry.get('AUID', '').split(";"):
                if orcid:
                    oi.append(orcid)
    elif source == 'Scopus':
        if file_type == '.csv':
            for orcid in str(entry.get('Author(s) ID', '')).split("; "):
                oi.append(orcid)
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            oi = ''
    elif source == 'The_Lens':
        if file_type == '.csv':
            oi = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            oi = ''

    return oi


def format_pmid_column(entry, source, file_type):       # Function for PMID Column (format--> "PubMed ID")
    pmid = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            pmid = ''
        elif file_type == '.txt' or file_type == '.ciw':
            pmid = entry.get('PM', '')
    elif source == 'PubMed':
        if file_type == '.txt':
            pmid = entry.get('PMID', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            try:
                pmid = entry.get('pmid', '')
            except:
                pmid = ''
        elif file_type == '.csv':
            if str(entry.get('PubMed ID', '')) != "nan":
                pmid = str(int(entry.get('PubMed ID', '')))
            else:
                pmid = ''
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            pmid = entry['PMID'] if str(entry['PMID']) != "nan" else ''
    elif source == 'The_Lens':
        if file_type == '.csv':
            pmid = entry['PMID'] if str(entry['PMID']) != "nan" else ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            pmid = ''

    return pmid


def format_pu_column(entry, source, file_type):         # Function for PU Column (format--> "Publisher")
    publisher = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            publisher = entry.get('publisher', '')
        elif file_type == '.txt' or file_type == '.ciw':
            publisher = entry.get('PU', '')
    elif source == 'PubMed':
        if file_type == '.txt':
            publisher = ''
    elif source == 'Scopus':
        if file_type == '.bib':
            publisher = entry.get('publisher', '')
        elif file_type == '.csv':
            publisher = entry.get('Publisher', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            publisher = ''
    elif source == 'The_Lens':
        if file_type == '.csv' or file_type == '.xlsx':
            publisher = entry['Publisher']
    elif source == 'Cochrane':
        if file_type == '.txt':
            publisher = ''

    return publisher


def format_py_column(entry, source, file_type):         # Function for PY Column (format--> "Publication Year")
    publication_year = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            publication_year = entry.get('year', '')
        elif file_type == '.txt' or file_type == '.ciw':
            publication_year = entry.get('PY', '')[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            publication_year = entry.get('DP', '')
            publication_year = re.findall(r'\d{4}', publication_year)[0] if publication_year else ''
    elif source == 'Scopus':
        if file_type == '.bib':
            publication_year = str(entry.get('year', ''))
        elif file_type == '.csv':
            publication_year = str(entry.get('Year', ''))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            publication_year = entry['PubYear']
    elif source == 'The_Lens':
        if file_type == '.csv':
            publication_year = entry['Publication Year']
    elif source == 'Cochrane':
        if file_type == '.txt':
            publication_year = entry.get('YR', '')

    return publication_year


def format_rp_column(entry, source, file_type):         # Function for RP Column (format--> "Correspondence Address")
    correspondence_address = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            correspondence_author = ''
            first_email = ''
            affiliation_text = entry.get('affiliation', '')
            if affiliation_text:
                affiliation_lines = affiliation_text.strip().split("\n")  # Remove leading and trailing whitespaces from the 'affiliation' field and split it into lines.

                for line in affiliation_lines:
                    if "(Corresponding Author)" in line:
                        correspondence_author = line
                        break

            emails = entry.get('author-email', '').split("\n")
            if emails:
                first_email = emails[0]

            correspondence_address = correspondence_author + '; email: ' + first_email
        elif file_type == '.txt' or file_type == '.ciw':
            correspondence_author = entry.get('RP', '')
            if correspondence_author:
                correspondence_author = correspondence_author[0]

            first_email = ''
            for email in entry.get('EM', ''):
                emails = email.split("; ")
                if emails:
                    first_email = emails[0]
            correspondence_address = correspondence_author + '; email: ' + first_email
    elif source == 'PubMed':
        if file_type == '.txt':
            correspondence_address = ''
    elif source == 'Scopus':
        if file_type == '.bib':
            correspondence_address = entry.get('correspondence_address', '')
        elif file_type == '.csv':
            correspondence_address = entry.get('Correspondence Address', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            correspondence_address = entry['Corresponding Authors']
    elif source == 'The_Lens':
        if file_type == '.csv':
            correspondence_address = ''
    elif source == 'Cochrane':
        if file_type == '.txt':
            correspondence_address = ''

    return correspondence_address


def format_sc_column(entry, source, file_type):         # Function for SC Column (format--> [Fields of Research])
    fields = []
    if source == 'Web_of_Science':
        if file_type == '.bib':
            fields = entry.get('research-areas', '').split("; ")
        elif file_type == '.txt' or file_type == '.ciw':
            original_fields = entry.get('SC', '')
            if original_fields:  # If the 'SC' field is not empty, split the string into parts using the delimiter '; ' and extract the field of research from each part.
                for field in original_fields:
                    field_parts = field.split(";")
                    for part in field_parts:
                        if part.strip():  # This ensures we skip empty parts
                            fields.append(part.strip())
            else:
                fields.append('')
    elif source == 'PubMed':
        if file_type == '.txt':
            fields = ''
    elif source == 'Scopus':
        fields = ''
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            fields = entry['Fields of Research (ANZSRC 2020)']
    elif source == 'The_Lens':
        if file_type == '.csv':
            fields = entry['Fields of Study']
    elif source == 'Cochrane':
        if file_type == '.txt':
            fields = ''

    return fields


def format_sn_column(entry, source, file_type):         # Function for SN Column (format--> "ISSN")
    issn = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            issn = entry.get('issn', '')
        elif file_type == '.txt' or file_type == '.ciw':
            issn = entry.get('SN', '')
    elif source == 'PubMed':
        if file_type == '.txt':
            issn = entry.get('IS', '').replace(';', ' ')
    elif source == 'Scopus':
        if file_type == '.bib':
            issn = entry.get('issn', '')
        elif file_type == '.csv':
            issn = entry.get('ISSN', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            issn = ''
    elif source == 'The_Lens':
        if file_type == '.csv':
            issn = entry['ISSNs']
    elif source == 'Cochrane':
        if file_type == '.txt':
            issn = entry.get('SN', '')

    return issn


def format_so_column(entry, source, file_type):         # Function for SO Column (format--> "Journal")
    journal = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            journal = entry.get('journal', '').replace('\n', ' ')
            if journal == '':
                journal = entry.get('booktitle', '').replace('\n', ' ')
        elif file_type == '.txt' or file_type == '.ciw':
            journal_entries = entry.get('SO', '')
            if journal_entries:
                for journal_entry in journal_entries:
                    journal += journal_entry + ' '
                journal = journal.rstrip()
    elif source == 'PubMed':
        if file_type == '.txt':
            journal = entry.get('JT', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            journal = entry.get('journal', '')
        elif file_type == '.csv':
            journal = entry.get('Source title', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            journal = entry['Source title']
    elif source == 'The_Lens':
        if file_type == '.csv':
            journal = entry['Source Title']
    elif source == 'Cochrane':
        if file_type == '.txt':
            journal = entry.get('SO', '')
            
    return journal


def format_sr_column(entry, source, file_type):  # Function for SR Column (format--> "Author, Publication Year, Journal")
    sr = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            author_dict = {}
            authors_str = entry.get('author', '').replace('\n', ' ')
            authors_list = authors_str.split(" and ")

            for person in authors_list:
                parts = person.split(", ")
                if len(parts) == 2:
                    surname, names = parts
                else:
                    surname = parts[0]
                    names = ' '.join(parts[1:])

                initials = ''.join([name[0] + '.' for name in names.split() if name])
                author_dict = {'Surname': surname, 'Name Initials': initials}

            publication_year = entry.get('year', '')
            journal = entry.get('journal', '').replace('\n', ' ')
            if journal == '':
                journal = entry.get('booktitle', '').replace('\n', ' ')
            sr = author_dict['Surname'] + ' ' + author_dict['Name Initials'] + ', ' + publication_year + ', ' + journal
        elif file_type == '.txt' or file_type == '.ciw':
            authors_list = entry.get('AU', '')
            parts = authors_list[0].split(", ")
            if len(parts) == 2:
                surname, names = parts
            else:
                surname = parts[0]
                names = ' '.join(parts[1:])

            publication_year = entry.get('PY', '')

            journal = ''
            journal_entries = entry.get('SO', '')
            if journal_entries:
                for journal_entry in journal_entries:
                    journal += journal_entry + ' '
                journal = journal.rstrip()

            sr = surname + ' ' + names + ', ' + publication_year[0] + ', ' + journal
    elif source == 'PubMed':
        if file_type == '.txt':
            author = entry.get('AU', '').split(";")[0]
            publication_year = entry.get('DP', '')
            publication_year = re.findall(r'\d{4}', publication_year)[0] if publication_year else ''
            ta = entry.get('TA', '')
            sr = author + ', ' + publication_year + ', ' + ta
    elif source == 'Scopus':
        if file_type == '.bib':
            author = entry.get('author', '').split(" and ")[0]
            surname, names = author.split(", ")
            initials = ''
            for name in names.split(" "):
                initials += name[0] + '.'
            publication_year = entry.get('year', '')
            ta = entry.get('journal', '')
            sr = surname + ' ' + initials + ', ' + publication_year + ', ' + ta
        elif file_type == '.csv':
            author = str(entry['Authors']).split("; ")[0]
            parts = author.split(" ")
            surname = " ".join(parts[:-1])
            initials = parts[-1]
            publication_year = str(entry.get('Year', ''))
            ta = entry.get('Source title', '')
            sr = surname + ' ' + initials + ', ' + publication_year + ', ' + ta
    elif source == 'Dimensions':
        persons = entry['Authors'].split("; ")
        if len(persons) > 0 and len(persons[0].split(", ")) == 2:
            surname, name = persons[0].split(", ")
            publication_year = str(entry['PubYear'])
            journal = str(entry['Source title'])
            sr = surname + ' ' + name[0] + ', ' + publication_year + ', ' + journal
    elif source == 'The_Lens':
        persons = str(entry['Author/s']).split("; ")
        if len(persons) > 0 and len(persons[0].split(" ")) == 2:
            parts = persons[0].split(" ")
            name = " ".join(parts[:-1])
            if len(name) == 0:
                name = ''
            else:
                name = name[0]
            surname = parts[-1]
            publication_year = str(entry['Publication Year'])
            journal = str(entry['Source Title'])
            sr = surname + ' ' + name + ', ' + publication_year + ', ' + journal
    elif source == 'Cochrane':
        if file_type == '.txt':
            author = entry.get('AU', '').split(";")[0]
            publication_year = entry.get('YR', '')
            ta = entry.get('SO', '')
            sr = author + ', ' + publication_year + ', ' + ta

    return sr


def format_tc_column(entry, source, file_type):  # Function for TC Column (format--> "Times Cited")
    times_cited = 0
    if source == 'Web_of_Science':
        if file_type == '.bib':
            times_cited = entry.get('times-cited', '')
        elif file_type == '.txt' or file_type == '.ciw':
            tc = entry.get('TC', '')
            if tc:
                times_cited = tc[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            times_cited = 0
    elif source == 'Scopus':
        if file_type == '.bib':
            try:
                cited_by = entry.get('note', '').split("; ")[0]
                times_cited = cited_by.split(": ")[1]
            except:
                times_cited = 0
        elif file_type == '.csv':
            times_cited = str(entry.get('Cited by', ''))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            times_cited = entry['Times cited']
    elif source == 'The_Lens':
        if file_type == '.csv':
            times_cited = entry['Citing Works Count']
    elif source == 'Cochrane':
        if file_type == '.txt':
            times_cited = 0

    return times_cited


def format_ti_column(entry, source, file_type):  # Function for TI Column (format--> "Title")
    title = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            title = entry.get('title', '')
        elif file_type == '.txt' or file_type == '.ciw':
            title_entries = entry.get('TI', '')
            if title_entries:
                for title_entry in title_entries:
                    title += title_entry + ' '
                title = title.rstrip()
    elif source == 'PubMed':
        if file_type == '.txt':
            title = entry.get('TI', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            title = entry.get('title', '')
        elif file_type == '.csv':
            title = entry.get('Title', '')
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            title = entry['Title']
    elif source == 'The_Lens':
        if file_type == '.csv':
            title = entry['Title']
    elif source == 'Cochrane':
        if file_type == '.txt':
            title = entry.get('TI', '')

    return title


def format_ut_column(entry, source, file_type):  # Function for UT Column (format--> "Publication ID")
    publication_id = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            publication_id = entry.get('unique-id', '')
        elif file_type == '.txt' or file_type == '.ciw':
            pub_id = entry.get('UT', '')
            if pub_id:
                publication_id = pub_id[0]
    elif source == 'PubMed':
        if file_type == '.txt':
            publication_id = entry.get('PMID', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            url = entry.get('url', '')
            match = re.search(r'eid=(.*?)&', url)
            if match:
                publication_id = match.group(1)
            else:
                publication_id = ''
        elif file_type == '.csv':
            publication_id = str(entry.get('EID', ''))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            publication_id = entry['Publication ID']
    elif source == 'The_Lens':
        if file_type == '.csv':
            publication_id = entry['Lens ID']
    elif source == 'Cochrane':
        if file_type == '.txt':
            publication_id = entry.get('ID', '')

    return publication_id


def format_vl_column(entry, source, file_type):  # Function for VL Column (format--> "VL: Volume")
    volume = ''
    if source == 'Web_of_Science':
        if file_type == '.bib':
            volume = entry.get('volume', '')
        elif file_type == '.txt' or file_type == '.ciw':
            volume = entry.get('VL', '')
    elif source == 'PubMed':
        if file_type == '.txt':
            volume = entry.get('VI', '')
    elif source == 'Scopus':
        if file_type == '.bib':
            volume = entry.get('volume', '')
        elif file_type == '.csv':
            volume = str(entry.get('Volume', ''))
    elif source == 'Dimensions':
        if file_type == '.csv' or file_type == '.xlsx':
            volume = entry['Volume']
    elif source == 'The_Lens':
        if file_type == '.csv':
            volume = entry['Volume']
    elif source == 'Cochrane':
        if file_type == '.txt':
            volume = ''
            
    return volume


def process_zip_file(zip_path, source, author):
    """
    Extract and process multiple files from a ZIP archive
    
    Args:
        zip_path: Path to the ZIP file
        source: The source of the data
        author: The author format preference
    
    Returns:
        Combined JSON data from all files in the ZIP
    """
    all_entries = []
    processed_files = 0
    failed_files = []
    max_files = 50  # Limite massimo di file per evitare sovraccarico
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            # Validate ZIP file size and content
            file_list = zip_ref.namelist()
            valid_files = [f for f in file_list if not f.startswith('.') and not f.endswith('/')]
            
            if len(valid_files) > max_files:
                raise ValueError(f"ZIP archive contains too many files ({len(valid_files)}). Maximum allowed: {max_files}")
            
            # Create a temporary directory to extract files
            with tempfile.TemporaryDirectory() as temp_dir:
                zip_ref.extractall(temp_dir)
                
                # Get list of extracted files
                extracted_files = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if not file.startswith('.'):  # Skip hidden files
                            extracted_files.append(os.path.join(root, file))
                
                # Process each extracted file
                for file_path in extracted_files:
                    try:
                        # Determine file type from extension
                        file_ext = os.path.splitext(file_path)[1].lower()
                        if file_ext in ['.txt', '.ciw', '.bib', '.csv', '.xlsx']:
                            # Process the file using the same logic as single files
                            file_entries = process_single_file(file_path, source, file_ext, author)
                            all_entries.extend(file_entries)
                            processed_files += 1
                        else:
                            print(f"Unsupported file type: {file_ext} for file {os.path.basename(file_path)}")
                    except Exception as e:
                        # Log error but continue processing other files
                        failed_files.append(os.path.basename(file_path))
                        print(f"Error processing file {os.path.basename(file_path)}: {str(e)}")
                        continue
        
        print(f"Successfully processed {processed_files} files from ZIP archive.")
        if failed_files:
            print(f"Failed to process {len(failed_files)} files: {', '.join(failed_files)}")
            
    except zipfile.BadZipFile:
        raise ValueError("The uploaded file is not a valid ZIP archive.")
    except Exception as e:
        raise ValueError(f"Error extracting ZIP file: {str(e)}")
    
    if not all_entries:
        raise ValueError("No valid bibliographic data found in the ZIP archive. Please ensure it contains supported file formats (.txt, .csv, .bib, .xlsx).")
    
    # Convert combined entries to JSON
    return json.dumps(all_entries, ensure_ascii=False, indent=4)


def process_multiple_files(file_list, source, author):
    """
    Process multiple files selected by the user
    
    Args:
        file_list: List of file information dictionaries
        source: The source of the data
        author: The author format preference
    
    Returns:
        Combined JSON data from all files
    """
    all_entries = []
    processed_files = 0
    failed_files = []
    
    for file_info in file_list:
        try:
            file_path = file_info["datapath"]
            file_name = file_info["name"]
            
            # Determine if it's a ZIP file or regular file
            if file_name.endswith(".zip"):
                # Process ZIP file
                zip_json = process_zip_file(file_path, source, author)
                zip_entries = json.loads(zip_json)
                all_entries.extend(zip_entries)
            else:
                # Process regular file
                file_entries = process_single_file(file_path, source, file_name, author)
                all_entries.extend(file_entries)
            
            processed_files += 1
            print(f"Successfully processed: {file_name}")
            
        except Exception as e:
            failed_files.append(file_info["name"])
            print(f"Error processing file {file_info['name']}: {str(e)}")
            continue
    
    print(f"Successfully processed {processed_files} files.")
    if failed_files:
        print(f"Failed to process {len(failed_files)} files: {', '.join(failed_files)}")
    
    if not all_entries:
        raise ValueError("No valid bibliographic data found in the selected files.")
    
    return json.dumps(all_entries, ensure_ascii=False, indent=4)


def process_single_file(data, source, file_type, author):
    """
    Process a single file and return the list of entries
    
    Args:
        data: The path to the input file
        source: The source of the data  
        file_type: The file extension/type
        author: The author format preference
    
    Returns:
        A list of dictionaries containing the formatted data
    """
    list_bib_data = []
    
    if source == "wos":
        source = "Web_of_Science"
        if file_type.endswith("bib"):
            file_type = ".bib"
            bib_parser = BibTexParser()
            with open(data, 'r', encoding='utf-8') as file:
                bib_data = bib_parser.parse_file(file)
            json_data = json.dumps(bib_data.entries, indent=4)
            list_bib_data = json.loads(json_data)
        elif file_type.endswith("txt"):
            file_type = ".txt"
            bib_data = parse_wos_data(data)
            list_bib_data = bib_data
        elif file_type.endswith("ciw"):
            file_type = ".ciw"
            bib_data = parse_wos_data(data)
            list_bib_data = bib_data

    elif source == "scopus":
        source = "Scopus"
        if file_type.endswith("bib"):
            file_type = ".bib"
            bib_parser = BibTexParser()
            with open(data, 'r', encoding='utf-8') as file:
                bib_data = bib_parser.parse_file(file)
            list_bib_data = bib_data.entries
        elif file_type.endswith("csv"):
            file_type = ".csv"
            bib_data = pd.read_csv(data)
            list_bib_data = bib_data.to_dict(orient='records')
    
    elif source == "dimensions":
        source = "Dimensions"
        if file_type.endswith("xlsx"):
            file_type = ".xlsx"
            bib_data = pd.read_excel(data, skiprows=1)
            list_bib_data = bib_data.to_dict(orient='records')
        elif file_type.endswith("csv"):
            file_type = ".csv"
            bib_data = pd.read_csv(data, skiprows=1)
            list_bib_data = bib_data.to_dict(orient='records')

    elif source == "lens":
        source = "The_Lens"
        if file_type.endswith("csv"):
            file_type = ".csv"
            bib_data = pd.read_csv(data)
            list_bib_data = bib_data.to_dict(orient='records')
    
    elif source == "pubmed":
        source = "PubMed"
        if file_type.endswith("txt"):
            file_type = ".txt"
            list_bib_data = parse_pubmed_data(data)
    
    elif source == "cochrane":
        source = "Cochrane"
        if file_type.endswith("txt"):
            file_type = ".txt"
            list_bib_data = parse_cochrane_data(data)

    # Extract relevant data and store it in a list of dictionaries
    entries = []
    for entry in list_bib_data:
        entry_data = {
            'AB': format_ab_column(entry, source, file_type),           # Abstract
            'AF': format_af_column(entry, source, file_type),           # Authors Full Name
            'AU': format_au_column(entry, source, file_type),           # Author/s
            'AU_UN': format_au_un_column(entry, source, file_type),     # Authors University
            'AU1_UN': format_au1_un_column(entry, source, file_type),   # Authors First University
            'BP': format_bp_column(entry, source, file_type),           # Beginning Page
            'EP': format_ep_column(entry, source, file_type),           # Ending Page
            'CR': format_cr_column(entry, source, file_type),           # Cited References
            'C1': format_c1_column(entry, source, file_type),           # Authors Affiliation
            'DB': source,                                               # Database
            'DE': format_de_column(entry, source, file_type),           # Author Keywords
            'DI': format_di_column(entry, source, file_type),           # DOI
            'DT': format_dt_column(entry, source, file_type),           # Document Type
            'EM': format_em_column(entry, source, file_type),           # Email
            'FU': format_fu_column(entry, source, file_type),           # Funding Details
            'FX': format_fx_column(entry, source, file_type),           # Funding Text
            'IS': format_is_column(entry, source, file_type),           # Issue
            'JI': format_ji_column(entry, source, file_type),           # Abbreviated Journal Name
            'ID': format_id_column(entry, source, file_type),           # Index Keywords
            'LA': format_la_column(entry, source, file_type),           # Language
            'OA': format_oa_column(entry, source, file_type),           # Open Access
            'OI': format_oi_column(entry, source, file_type),           # Orcid ID
            'PMID': format_pmid_column(entry, source, file_type),       # PubMed ID
            'PU': format_pu_column(entry, source, file_type),           # Publisher
            'PY': format_py_column(entry, source, file_type),           # Publication Year
            'RP': format_rp_column(entry, source, file_type),           # Correspondence Address
            'SC': format_sc_column(entry, source, file_type),           # Fields of Research
            'SN': format_sn_column(entry, source, file_type),           # ISSN
            'SO': format_so_column(entry, source, file_type),           # Journal
            'SR': format_sr_column(entry, source, file_type),           # Author, Publication Year, Journal
            'TC': format_tc_column(entry, source, file_type),           # Times Cited
            'TI': format_ti_column(entry, source, file_type),           # Title
            'UT': format_ut_column(entry, source, file_type),           # Publication ID
            'VL': format_vl_column(entry, source, file_type),           # Volume
        }

        # Add any remaining columns from the raw entry that aren't yet mapped
        for column in entry.keys():
            if column not in entry_data:  # Avoid overwriting existing keys
                entry_data[column] = entry.get(column, None)
        
        # Remove the column based on the value of the 'author' field
        if author == "surname":
            entry_data.pop('AF', None)  # Remove 'AF' if it exists
        elif author == "fullname":
            entry_data.pop('AU', None)  # Remove 'AU' if it exists

        entries.append(entry_data)

    return entries


def biblio_json(data, source, type, author):
    """
    Function to format the data from the input file into a JSON format
    
    Args:
        data: The path to the input file
        source: The source of the data
        type: The type of the input file
        author: The author of the data
    
    Returns:
        A JSON string containing the formatted data
    """
    # Handle ZIP files - extract and process multiple files
    if type.endswith("zip"):
        return process_zip_file(data, source, author)
    
    # Handle single files - use the new process_single_file function
    entries = process_single_file(data, source, type, author)
    
    # Convert the list of dictionaries to JSON
    json_data = json.dumps(entries, ensure_ascii=False, indent=4)
    
    return json_data
