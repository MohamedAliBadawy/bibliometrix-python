from .utils import *


#### WEB OF SCIENCE PARSER ####
def parse_wos_data(datapath):  # PARSER FOR WEB OF SCIENCE TXT and CIW
    elem_data = []
    data = {}
    current_key = None

    with open(datapath, 'r', encoding='utf-8') as file:
        lines = file.readlines()

    for i, line in enumerate(lines[2:], start=2):
        # line = line.decode('utf-8')
        line = line.rstrip()
        if line.strip() != " " and line.strip() != "EF":
            if line.startswith("ER"):
                elem_data.append(data.copy())
                current_key = None
                data = {}
            elif line.startswith("  "):
                if current_key:
                    if current_key in data:
                        if current_key in {"DE", "C3", "EM", "FU", "FX", "WC"}:
                            current_value = " ".join(data[current_key]) + " " + line.strip()
                            data[current_key] = [current_value]
                        else:
                            data[current_key].append(line.strip())
                    else:
                        data[current_key] = [line.strip()]
            else:
                line = line.strip()
                key_value = line.split(" ", 1)
                if len(key_value) == 2:
                    key, value = key_value
                    data[key] = [value]
                    current_key = key

    return elem_data


#### PUBMED PARSER ####
def parse_pubmed_data(datapath):  # PARSER FOR PUBMED TXT
    data = []
    current_record = {}
    
    with open(datapath, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    for line in lines:
        # line = line.decode('utf-8')  # Decode the line from bytes to string
        if line.strip() == '':
            # If the line is empty, add the current record to the data
            if current_record:
                data.append(current_record)
                current_record = {}
            continue

        key_match = re.match(r'^([A-Z]+)\s*-\s*(.+)', line)
        if key_match:
            key = key_match.group(1)
            value = key_match.group(2)

            if key in current_record:
                current_record[key] += ';' + value
            else:
                current_record[key] = value
        else:
            # Add the content to the previous key
            current_record[key] += ' ' + line.strip()

    # Add the last record if present
    if current_record:
        data.append(current_record)

    return data


#### COCHRANE PARSER ####
def parse_cochrane_data(datapath):
    data = []
    current_record = {}
    
    with open(datapath, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    for line in lines:
        line = line.strip()
        if not line:
            # If the line is empty, add the current record to the data
            if current_record:
                if 'Record' in current_record:
                    del current_record['Record']
                if 'AB' in current_record and current_record['AB'].startswith('Abstract - Background'):
                    current_record['AB'] = current_record['AB'][22:].strip()
                data.append(current_record)
                current_record = {}
            continue
        
        if line.startswith('Record #'):
            # If the line starts with 'Record #', it is the beginning of a new record
            if current_record:
                if b'Record' in current_record:
                    del current_record[b'Record']
                if b'AB' in current_record and current_record[b'AB'].startswith(b'Abstract - Background'):
                    current_record[b'AB'] = current_record[b'AB'][22:].strip()
                data.append(current_record)
                current_record = {}
            continue

        # Find columns with the format 'KEY: value'
        key_match = re.match(r'^([A-Z]{2,})\s*:\s*(.+)', line)
        if key_match:
            key = key_match.group(1)
            value = key_match.group(2)
            
            if key in current_record:
                current_record[key] += '; ' + value
            else:
                current_record[key] = value
        else:
            # If the line does not match the format 'KEY: value', add the content to the previous key
            if current_record:
                current_record[key] += ' ' + line.strip()

    # Add the last record if present
    if current_record:
        if 'Record' in current_record:
            del current_record['Record']
        if 'AB' in current_record and current_record['AB'].startswith('Abstract - Background'):
            current_record['AB'] = current_record['AB'][20:].strip()
        data.append(current_record)

    return data


#### PUBMED XML PARSER ####
def parse_pubmed_xml(datapath):
    """
    Parse PubMed XML data (MedLine XML format).
    
    Args:
        datapath: Path to the XML file
        
    Returns:
        List of dictionaries with bibliographic data
    """
    import xml.etree.ElementTree as ET
    
    data = []
    
    try:
        tree = ET.parse(datapath)
        root = tree.getroot()
    except ET.ParseError as e:
        print(f"Error parsing XML: {e}")
        return data
    
    # Handle different XML root structures
    articles = []
    if root.tag == 'PubmedArticle':
        articles = [root]
    else:
        articles = root.findall('.//PubmedArticle')
    
    for article in articles:
        record = {}
        
        # Extract PMID
        pmid = article.find('.//PMID')
        if pmid is not None:
            record['PMID'] = pmid.text.strip() if pmid.text else ""
        
        # Extract Article metadata
        article_elem = article.find('Article')
        if article_elem is not None:
            # Title
            title = article_elem.find('ArticleTitle')
            if title is not None:
                record['TI'] = title.text.strip() if title.text else ""
            
            # Abstract
            abstract_elem = article_elem.find('Abstract')
            if abstract_elem is not None:
                abstract_texts = []
                for abstract_text in abstract_elem.findall('AbstractText'):
                    if abstract_text.text:
                        abstract_texts.append(abstract_text.text.strip())
                record['AB'] = " ".join(abstract_texts) if abstract_texts else ""
            
            # Language
            lang = article_elem.find('Language')
            if lang is not None:
                record['LA'] = lang.text.strip() if lang.text else "eng"
            
            # Publication Types
            pub_types = article_elem.find('PublicationTypeList')
            if pub_types is not None:
                pub_type_list = [pt.text for pt in pub_types.findall('PublicationType') if pt.text]
                record['DT'] = ";".join(pub_type_list) if pub_type_list else ""
            
            # Authors
            author_list = article_elem.find('AuthorList')
            if author_list is not None:
                authors = []
                for author in author_list.findall('Author'):
                    last_name = author.find('LastName')
                    initials = author.find('Initials')
                    if last_name is not None and last_name.text:
                        author_name = last_name.text.strip()
                        if initials is not None and initials.text:
                            author_name += " " + initials.text.strip()
                        authors.append(author_name)
                record['AU'] = ";".join(authors) if authors else ""
            
            # Journal Title
            journal = article_elem.find('Journal')
            if journal is not None:
                journal_title = journal.find('Title')
                if journal_title is not None:
                    record['SO'] = journal_title.text.strip() if journal_title.text else ""
                
                # Journal Info - look for JournalIssue
                journal_issues = journal.findall('JournalIssue')
                if journal_issues:
                    journal_info = journal_issues[0]
                    volume = journal_info.find('Volume')
                    if volume is not None:
                        record['VL'] = volume.text.strip() if volume.text else ""
                    
                    issue = journal_info.find('Issue')
                    if issue is not None:
                        record['IS'] = issue.text.strip() if issue.text else ""
                    
                    # Publication Date - first try PubDate
                    pub_date = journal_info.find('PubDate')
                    if pub_date is not None:
                        year = pub_date.find('Year')
                        if year is not None:
                            try:
                                record['PY'] = int(year.text)
                            except (ValueError, TypeError):
                                record['PY'] = ""
            
            # Pagination
            pagination = article_elem.find('Pagination')
            if pagination is not None:
                start_page = pagination.find('MedlinePgn')
                if start_page is not None and start_page.text:
                    pages = start_page.text.strip().split('-')
                    if len(pages) >= 1:
                        record['BP'] = pages[0]
                    if len(pages) >= 2:
                        record['EP'] = pages[-1]
            
            # Keywords
            keywords_list = article_elem.find('KeywordList')
            if keywords_list is not None:
                keywords = []
                for keyword in keywords_list.findall('Keyword'):
                    if keyword.text:
                        keywords.append(keyword.text.strip())
                record['DE'] = ";".join(keywords) if keywords else ""
            
            # MeSH Terms
            mesh_list = article_elem.find('MeshHeadingList')
            if mesh_list is not None:
                mesh_terms = []
                for mesh_heading in mesh_list.findall('MeshHeading'):
                    descriptor = mesh_heading.find('DescriptorName')
                    if descriptor is not None and descriptor.text:
                        mesh_terms.append(descriptor.text.strip())
                if mesh_terms:
                    record['ID'] = ";".join(mesh_terms)
        
        # Extract publication types and additional info
        media_elem = article.find('Article/MediaList')
        if media_elem is not None:
            media_items = media_elem.findall('Medium')
            if media_items:
                record['UT'] = media_items[0].text if media_items[0].text else ""
        
        # Citation counts (if available)
        record['TC'] = 0  # Initialize to 0 since not typically in PubMed XML
        
        # Database
        record['DB'] = 'PUBMED'
        
        # Add record if it has at least PMID and Title
        if 'PMID' in record or 'TI' in record:
            data.append(record)
    
    return data
