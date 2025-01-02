import requests
import xml.etree.ElementTree as ET

def query_dblp(keyword, venue, year, max_results=50):
    """
    Query DBLP for papers containing a keyword in the title from a specific conference and year.

    Args:
        keyword (str): The keyword to search for in the title.
        venue (str): The conference name (e.g., "DAC").
        year (str): The year of the conference (e.g., "2024").
        max_results (int): The maximum number of results to fetch.

    Returns:
        List[Dict]: A list of dictionaries with 'title' and 'authors'.
    """
    base_url = "https://dblp.org/search/publ/api"
    # Build a specific query to filter by title, venue, and year
    query = f"title:{keyword} venue:{venue} year:{year}"
    
    params = {
        "q": query,
        "format": "xml",
        "h": max_results
    }
    
    response = requests.get(base_url, params=params)
    
    if response.status_code != 200:
        raise Exception(f"Failed to fetch data: {response.status_code}")
    
    root = ET.fromstring(response.content)
    papers = []
    
    for hit in root.findall(".//hit"):
        info = hit.find(".//info")
        if info is not None:
            title = info.find("title").text if info.find("title") is not None else "N/A"
            authors = []
            authors_element = info.find("authors")
            if authors_element is not None:
                authors = [author.text for author in authors_element.findall("author") if author.text]
            
            papers.append({
                "title": title,
                "authors": authors
            })
    
    return papers

def main():
    keyword = "quantum"
    venue = "NeurIPS"
    year = "2020"
    max_results = 50  # Adjust the number of results as needed
    
    try:
        papers = query_dblp(keyword, venue, year, max_results)
        print(f"Found {len(papers)} papers with '{keyword}' in the title from {venue} {year}:\n")
        for i, paper in enumerate(papers, 1):
            print(f"{i}. Title: {paper['title']}")
            print(f"   Authors: {', '.join(paper['authors']) if paper['authors'] else 'N/A'}\n")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()

