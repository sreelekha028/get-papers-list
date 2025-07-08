# fetch.py
import requests
from typing import List

BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

def search_pubmed(query: str) -> List[str]:
    url = f"{BASE_URL}/esearch.fcgi"
    params = {
        "db": "pubmed",
        "term": query,
        "retmode": "json",
        "retmax": 100
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.json().get("esearchresult", {}).get("idlist", [])

def fetch_pubmed_details(id_list: List[str]) -> str:
    url = f"{BASE_URL}/efetch.fcgi"
    params = {
        "db": "pubmed",
        "id": ",".join(id_list),
        "retmode": "xml"
    }
    response = requests.get(url, params=params)
    response.raise_for_status()
    return response.text

# parser.py
import xml.etree.ElementTree as ET
from typing import List, Dict
import re
import csv

# Embedded utility function to avoid import errors
def is_company_affiliation(affiliation: str) -> bool:
    academic_keywords = ["university", "institute", "college", "school", "hospital", "clinic"]
    company_keywords = ["inc", "corp", "ltd", "gmbh", "biotech", "pharma", "therapeutics", "biosciences"]
    affiliation_lower = affiliation.lower()

    return any(kw in affiliation_lower for kw in company_keywords) and not any(kw in affiliation_lower for kw in academic_keywords)

def parse_papers(xml_data: str) -> List[Dict]:
    root = ET.fromstring(xml_data)
    papers = []
    for article in root.findall(".//PubmedArticle"):
        try:
            pmid = article.findtext(".//PMID")
            title = article.findtext(".//ArticleTitle")
            pub_date = article.findtext(".//PubDate/Year") or "Unknown"

            affiliations = article.findall(".//AffiliationInfo")
            non_academic_authors = []
            company_affiliations = set()
            corresponding_email = ""

            for aff in affiliations:
                aff_text = aff.findtext("Affiliation") or ""
                if is_company_affiliation(aff_text):
                    company_affiliations.add(aff_text)
                    author = aff.get("AuthorName") or "Unknown"
                    non_academic_authors.append(author)

                if "@" in aff_text and not corresponding_email:
                    corresponding_email = extract_email(aff_text)

            if company_affiliations:
                papers.append({
                    "PubmedID": pmid,
                    "Title": title,
                    "Publication Date": pub_date,
                    "Non-academic Author(s)": ", ".join(non_academic_authors),
                    "Company Affiliation(s)": ", ".join(company_affiliations),
                    "Corresponding Author Email": corresponding_email
                })
        except Exception:
            continue

    return papers

def extract_email(text: str) -> str:
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else ""

def save_to_csv(papers: List[Dict], filename: str) -> None:
    if not papers:
        print("No papers to write.")
        return

    with open(filename, mode="w", newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=papers[0].keys())
        writer.writeheader()
        writer.writerows(papers)

    print(f"Results saved to {filename}")
