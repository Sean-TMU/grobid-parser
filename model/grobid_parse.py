import warnings
warnings.filterwarnings("ignore")
import os, re, html
from dotenv import load_dotenv
load_dotenv()

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
import logging

class GrobidParser:
    """Class to handle parsing of PDF documents using Grobid"""
    
    def __init__(self):
        self.grobid_url = os.environ.get('GROBID_URL')
        # Set up logging
        log_level = 'INFO'
        logger = logging.getLogger()
        logger.setLevel(log_level)

        console_handler = logging.StreamHandler()
        console_handler.setLevel(log_level)
        logger.addHandler(console_handler)
        self.logger = logger
    
    def parse_pdf(self, root_folder:str, pdf_file: str) -> dict:
        """Main method to parse PDF and return structured data"""
        try:
            xml_path = self._process_pdf(root_folder, pdf_file)
            if xml_path and os.path.exists(xml_path):
                return self._parse_xml(xml_path)
            return None
        except Exception as e:
            self.logger.error(f"Error parsing PDF {pdf_file}: {str(e)}")
            return None

    def _process_pdf(self, root_folder: str, pdf_file: str) -> str:
        """Process PDF through Grobid service"""
        pdf_content = []
        filename = os.path.splitext(os.path.basename(pdf_file))[0]
        xml_path = os.path.join(root_folder, f'{filename}.grobid.tei.xml')
        
        # If the XML file already exists, return the path
        if os.path.exists(xml_path):
            return xml_path
        
        try:
            # Official python api client failed, so use request instead
            url = self.grobid_url + "/api/processFulltextDocument"
            pdf_content += [("input", (open(f"{root_folder}/{pdf_file}", "rb")))]
            response = requests.post(url, files=pdf_content).text
            if response is not None:
                # Export xml content to the disk
                with open(xml_path, 'w') as fp:
                    fp.write(response)

            return xml_path
        except Exception as e:
            self.logger.error(f"Grobid processing failed: {str(e)}")
            return None

    def _parse_xml(self, xml_file: str) -> dict:
        """Parse XML output from Grobid"""
        try:
            with open(xml_file, 'r', encoding='utf-8') as f:
                article = BeautifulSoup(f.read(), "lxml")
            
            publisher, journal = parse_publisher(article)
            referencecount, text = parse_text(article)
            return {
                "title": [parse_title(article)],
                "language": [parse_language(article)],
                "publisher": [publisher],
                "journal": [journal], 
                "release_year": [parse_year(article)],
                "doi": [parse_doi(article)],
                "referencecount": [referencecount],
                "text": [text]
            }
        except Exception as e:
            self.logger.error(f"XML parsing failed: {str(e)}")
            return None

def parse_title(article):
    title_tag = article.find("titlestmt")
    if not title_tag:
        return ""
    title = title_tag.find("title", attrs={"type": "main"})
    title = title.text.strip() if title is not None else ""
    # Convert Entities to Symbols
    decode_title = html.unescape(title)
    # Strip html tag, only keep plain text
    title_text = BeautifulSoup(decode_title, "html.parser").get_text()
    return title_text

def parse_language(article):
    header_tag = article.find("teiheader")
    language = header_tag.get('xml:lang') if header_tag is not None else ""
    return language

def parse_publisher(article):
    monogr_tag = article.find("monogr")
    if not monogr_tag:
        return "", ""
        
    journal = monogr_tag.find("title", attrs={"type": "main"})
    journal = journal.text.strip() if journal else ""
    
    imprint = monogr_tag.find("imprint")
    if not imprint:
        return "", journal
        
    publisher = imprint.find("publisher")
    publisher = publisher.text.strip() if publisher else ""
    
    return publisher, journal

def parse_year(article):
    pub_date = article.find("publicationstmt")
    if not pub_date:
        return ""
    year = pub_date.find("date")
    return year.attrs.get("when", "") if year else ""

def parse_doi(article):
    doi = article.find("idno", attrs={"type": "DOI"})
    return doi.text.strip() if doi else ""

def parse_references(article):
    """Extract reference title and author name then store as dictionary type"""
    reference_list = {}
    references = article.find("text")
    if not references:
        return reference_list
        
    references = references.find("div", attrs={"type": "references"})
    if not references:
        return reference_list
        
    for elem in references.find_all("biblstruct"):
        ref_id = elem.get('xml:id', "")
        title = elem.find("title", attrs={"level": "a"})
        if not title:
            title = elem.find("title", attrs={"level": "m"})
        title = title.text if title else ""
        
        authors = elem.find_all("author")
        if (not authors) or (not title):
            # Only keep the reference that contains both title and author info
            continue
            
        author = authors[0]
        firstname = author.find("forename", {"type": "first"})
        firstname = firstname.text.strip() if firstname else ""
        
        middlename = author.find("forename", {"type": "middle"})
        middlename = middlename.text.strip() if middlename else ""
        
        lastname = author.find("surname")
        lastname = lastname.text.strip() if lastname else ""
        
        reference_list[ref_id] = {
            "title": title,
            "author": f"{lastname} {firstname}{middlename}".strip()
        }
        
    return reference_list

def reconstruct_paragraph(paragraph, reference_dict):
    if not paragraph or not paragraph.contents:
        return ""
    
    switch = False # Determine the ')' or ' 'comes from figure/table or bib reference or not
    paragraph_content = ""
    for element in paragraph.contents:
        if (isinstance(element, Tag) and 
            element.get('type') == "bibr" and 
            element.get('target') and 
            reference_dict):
            try:
                target_id = str(element.get('target')[1:])
                ref = reference_dict.get(target_id, "Not Found")
                if ref == "Not Found":
                    # If the target id not exist in reference_dict
                    continue
                reference_string = f"[bib_ref] {ref['title']}, {ref['author']} [/bib_ref]"
                if paragraph_content.endswith("[/bib_ref]"):
                    paragraph_content += " "
                paragraph_content += reference_string
                switch = True
            except (ValueError, IndexError):
                print(f"Invalid reference target: {element.get('target')}")
                continue
                
        elif isinstance(element, Tag) and element.get('type'):
            # Handle figure/table references
            # You cannot remove the ')' because they does not appeared in the paragraph_content yet
            text_end = paragraph_content
            patterns_to_remove = r"\s*\(?[Ff]igure\s*|\s*\(?[Ff]ig\.?\s*|\s*\(?[Tt]able\s*"
            text_end = re.sub(patterns_to_remove, '', text_end, flags=re.IGNORECASE)
            paragraph_content = text_end
            switch = True
                
        elif isinstance(element, NavigableString):
            if switch and (element.text.startswith(')') or element.text.startswith(' ')):
                text_end = element.text[1:]
            else:
                text_end = element.text
            
            switch = False
            patterns_to_remove = r"\s*\(?\s*[,]*\s*[Ss]upplementary\s*\)?|\s*\(?\s*[,]*\s*[A-Za-z]+\s*[Ss]upplementary\s*\)?"
            paragraph_content += re.sub(patterns_to_remove, '', text_end, flags=re.IGNORECASE)
            
    return paragraph_content

def parse_text(article):
    """Parse and structure the main text content"""
    common_titles = ["abstract", "introduction", "materialandmethods", "methods", "results", "discussion", "conclusion"]
    reference_dict = parse_references(article)
    sections = []

    # Handle abstract section
    abstract = article.find("abstract")
    abstract_text = abstract.find_all("div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"})
    if abstract_text:
        sections.append({
            "heading": "# Abstract\n\n",
            "text": ""
        })
    
    for abstract_div in abstract_text:
        abstract_list = list(abstract_div.children)
        if not abstract_list:
            continue
        if len(abstract_list) == 1:
            sections.append({
                "heading": "",
                "text": reconstruct_paragraph(abstract_list[0], reference_dict)+"\n\n"
            })
            continue
        
        heading = ""
        text_parts = []
        if isinstance(abstract_list[0], NavigableString):
            heading_text = abstract_list[0].text
            # Add \n to separate header-paragraph in same section
            heading = f"## {heading_text}\n"
            p_all = abstract_list[1:]
        else:
            p_all = abstract_list
            
        for p in p_all:
            if p is not None:
                text_parts.append(reconstruct_paragraph(p, reference_dict))
            if p == p_all[-1]:
                # Add \n\n between last paragraph and the following section
                text_parts[-1] += "\n\n"
            else:
                # Add \n to separate paragraph-paragraph in same section
                text_parts[-1] += "\n"
                
        if heading or text_parts:
            # If you change to 'and' not 'or', some sections that does not have heading will be skipped
            sections.append({
                "heading": heading,
                "text": text_parts
            })

    # Handle body section (Cannot change to body tag, else abstract section will process twice)
    article_text = article.find("text")
    divs = article_text.find_all("div", attrs={"xmlns": "http://www.tei-c.org/ns/1.0"})
    for div in divs:
        div_list = list(div.children)
        
        if not div_list:
            continue
            
        if len(div_list) == 1:
            if isinstance(div_list[0], NavigableString):
                sections.append({
                    "heading": f"# {div_list[0]}\n\n",
                    "text": ""
                })
            else:
                sections.append({
                    "heading": "",
                    "text": reconstruct_paragraph(div_list[0], reference_dict)
                })
            continue
            
        # Handle multi-element divs
        heading = ""
        text_parts = []
        
        if isinstance(div_list[0], NavigableString):
            heading_text = div_list[0].text
            # Add \n to separate header-paragraph in same section
            heading = f"# {heading_text}\n" if heading_text.strip().lower() in common_titles else f"## {heading_text}\n"
            p_all = div_list[1:]
        else:
            p_all = div_list
            
        for p in p_all:
            if p is not None:
                text_parts.append(reconstruct_paragraph(p, reference_dict))
            if p == p_all[-1]:
                # Add \n\n between last paragraph and the following section
                text_parts[-1] += "\n\n"
            else:
                # Add \n to separate paragraph-paragraph in same section
                text_parts[-1] += "\n"
                
        if heading or text_parts:
            # If you change to 'and' not 'or', some sections that does not have heading will be skipped
            sections.append({
                "heading": heading,
                "text": text_parts
            })
            
    # Concatenate all sections into a single string
    article_text = ""
    # Filter out irrelevant sections
    irrelevant_sections = ["acknowledgement", "conflict of interest", "funding", "author contribution", 
                            "competing interests", "supplementary material", "additional information", 
                            "supplementary information", "data availability", "appendix"]
    for section in sections:
        if any(x.strip() in section["heading"].strip().lower() for x in irrelevant_sections):
            continue
        article_text += section["heading"]
        for text_part in section["text"]:
            article_text += text_part
    
    return len(reference_dict), article_text