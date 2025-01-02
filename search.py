import requests
import xml.etree.ElementTree as ET
import time
from bs4 import BeautifulSoup
import random


def get_dblp_author_profile(author_name):
    """
    Search DBLP for an author's profile and return the author ID.

    Args:
        author_name (str): The author's name.

    Returns:
        str: The author's DBLP profile URL or None if not found.
    """
    search_url = "https://dblp.org/search/author/api"
    params = {
        "q": author_name,
        "format": "xml",
        "h": 1  # Only return the top match
    }

    try:
        response = requests.get(search_url, params=params)
        if response.status_code != 200:
            raise Exception(f"Failed to query DBLP: Status Code {response.status_code}")
        
        root = ET.fromstring(response.content)
        author_entry = root.find(".//hits/hit/info/url")
        if author_entry is not None:
            return author_entry.text
    except Exception as e:
        print(f"Error fetching DBLP author profile: {e}")
    return None


def get_dblp_publication_count(author_url):
    """
    Count the number of publications listed on a DBLP author profile.

    Args:
        author_url (str): The URL of the author's DBLP profile.

    Returns:
        int: The number of publications or None if unable to fetch.
    """
    try:
        response = requests.get(author_url + ".xml")  # Fetch the XML version of the profile
        if response.status_code != 200:
            raise Exception(f"Failed to access DBLP author profile: Status Code {response.status_code}")
        
        root = ET.fromstring(response.content)
        publication_list = root.findall(".//r")
        return len(publication_list)
    except Exception as e:
        print(f"Error fetching publication count from DBLP: {e}")
    return None


def is_professor_by_publication_count(author_name, threshold=20):
    """
    Identify if an author is a professor based on their DBLP publication count.

    Args:
        author_name (str): The name of the author.
        threshold (int): The publication count threshold for identifying professors.

    Returns:
        bool: True if the author's publication count exceeds the threshold, False otherwise.
    """
    print(f"Searching DBLP profile for '{author_name}'...")
    author_url = get_dblp_author_profile(author_name)
    
    if not author_url:
        print("DBLP profile not found.")
        return False
    
    print(f"Found DBLP profile: {author_url}")
    print("Fetching publication count...")
    publication_count = get_dblp_publication_count(author_url)
    
    if publication_count is None:
        print("Could not retrieve publication count.")
        return False
    
    print(f"Publication count: {publication_count}")
    if publication_count >= threshold:
        print(f"{author_name} is identified as a professor (≥ {threshold} publications).")
        return True
    else:
        print(f"{author_name} is not identified as a professor (< {threshold} publications).")
        return False

def query_dblp(keyword, venue, year, max_results=50):
    """
    Query DBLP for papers containing a keyword in the title from a specific conference and year.

    Args:
        keyword (str): The keyword to search for in the title.
        venue (str): The conference name (e.g., "DAC").
        year (str): The year of the conference (e.g., "2024").
        max_results (int): The maximum number of results to fetch.

    Returns:
        List[Dict]: A list of dictionaries with 'title', 'authors', and 'conference'.
    """
    base_url = "https://dblp.org/search/publ/api"
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
                "authors": authors,
                "conference": f"{venue}{year}"
            })
    
    return papers


import requests
from bs4 import BeautifulSoup
import time
import random


def is_professor_on_google(author_name, max_retries=2):
    """
    Check if an author is a professor or faculty member by analyzing the top 20 Google Search result titles.
    Retries up to max_retries times if no results are returned.

    Args:
        author_name (str): The author's name.
        max_retries (int): Number of retry attempts if no results are found.

    Returns:
        bool: True if the author is identified as a professor or faculty member, False otherwise.
    """
    search_query = f"{author_name} site:.edu OR site:.ac.uk OR site:.edu.au"
    search_url = f"https://www.google.com/search?q={search_query.replace(' ', '+')}&num=20"
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
        ])
    }

    attempt = 0
    while attempt <= max_retries:
        try:
            print(f"Attempt {attempt + 1}: Querying Google for {author_name}...")
            response = requests.get(search_url, headers=headers)
            
            if response.status_code != 200:
                print(f"Failed to query Google (Status Code: {response.status_code})")
                return False

            soup = BeautifulSoup(response.content, 'html.parser')
            search_results = soup.find_all('h3')[:20]  # Extract the first 20 result titles
            
            if not search_results:
                print("No results found, retrying...")
                attempt += 1
                time.sleep(random.uniform(5, 10))  # Random delay before retrying
                continue
            
            # Check titles for keywords
            for result in search_results:
                title = result.text.lower()
                if 'professor' in title or 'faculty' in title:
                    print(f"Found keyword in title: '{title}'")
                    return True
            
            print("No relevant titles found in search results.")
            return False

        except Exception as e:
            print(f"Error on attempt {attempt + 1}: {e}")
            attempt += 1
            time.sleep(random.uniform(5, 10))  # Delay before retrying in case of an exception
    
    print("All retries failed. No valid results found.")
    return False


def build_professor_paper_dict(papers):
    """
    Build a dictionary of professors and their papers.

    Args:
        papers (List[Dict]): List of paper dictionaries with 'title', 'authors', 'conference'.

    Returns:
        Dict[str, List[Tuple[str, str]]]: Professor name as key, list of (conference, paper title) as value.
    """
    professor_dict = {}
    checked_authors = set()
    
    for paper in papers:
        conference = paper['conference']
        title = paper['title']
        for author in paper['authors']:
            if author in checked_authors:
                continue  # Skip if already checked
            
            print(f"Checking if {author} is a professor via Google Search...")
            if is_professor_by_publication_count(author, 15):
                print(f"{author} is identified as a professor.")
                if author not in professor_dict:
                    professor_dict[author] = []
                professor_dict[author].append((conference, title))
            else:
                print(f"{author} is not identified as a professor.")
            
            checked_authors.add(author)
            time.sleep(random.uniform(5, 10))  # Sleep to avoid detection as a bot
    
    return professor_dict


def main():
    keyword = "quantum"
    venue = "DAC"
    year = "2020"
    max_results = 50
    
    try:
        print("Querying DBLP...")
        papers = query_dblp(keyword, venue, year, max_results)
        print(f"Found {len(papers)} papers.\n")
        
        print("Building professor-paper dictionary...")
        professor_paper_dict = build_professor_paper_dict(papers)
        
        print("\n=== Professors and Their Papers ===")
        for professor, entries in professor_paper_dict.items():
            print(f"{professor}:")
            for conf, title in entries:
                print(f"   - ({conf}) {title}")
    except Exception as e:
        print(f"Error: {e}")


def get_google_search_results(query, max_results=10):
    """
    Fetch the top search results from Google for a given query, including titles, links, and snippets.

    Args:
        query (str): Search query string.
        max_results (int): Number of search results to return.

    Returns:
        List[Dict]: A list of dictionaries with 'title', 'link', and 'snippet'.
    """
    search_url = f"https://www.google.com/search?q={query.replace(' ', '+')}&num={max_results}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: Status code {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        results = []
        
        for g in soup.find_all('div', class_='tF2Cxc')[:max_results]:
            title_element = g.find('h3')
            link_element = g.find('a', href=True)
            snippet_element = g.find('div', {'class': 'IsZvec'})
            
            title = title_element.text if title_element else "No title"
            link = link_element['href'] if link_element else "No link"
            snippet = snippet_element.text if snippet_element else "No snippet"
            
            results.append({
                'title': title,
                'link': link,
                'snippet': snippet
            })
        
        return results
    
    except Exception as e:
        print(f"Error: {e}")
        return []

def get_google_scholar_profile(author_name):
    """
    Search for the author's Google Scholar profile and return the profile URL if found.

    Args:
        author_name (str): The name of the author.

    Returns:
        str: The Google Scholar profile URL or None if not found.
    """
    search_url = f"https://scholar.google.com/scholar?q={author_name.replace(' ', '+')}"
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
        ])
    }

    try:
        response = requests.get(search_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to query Google Scholar: Status Code {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        profile_link = soup.find('h4', text='Profiles')
        if profile_link:
            first_profile = profile_link.find_next('a', href=True)
            if first_profile:
                return f"https://scholar.google.com{first_profile['href']}"
    except Exception as e:
        print(f"Error fetching Google Scholar profile: {e}")
    return None


def get_h_index(profile_url):
    """
    Fetch the h-index from a Google Scholar profile.

    Args:
        profile_url (str): The URL of the Google Scholar profile.

    Returns:
        int: The h-index value or None if not found.
    """
    headers = {
        "User-Agent": random.choice([
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/89.0.4389.82 Safari/537.36"
        ])
    }
    
    try:
        response = requests.get(profile_url, headers=headers)
        if response.status_code != 200:
            raise Exception(f"Failed to access profile: Status Code {response.status_code}")
        
        soup = BeautifulSoup(response.content, 'html.parser')
        index_row = soup.find('td', text='h-index')
        if index_row:
            h_index = index_row.find_next('td').text
            return int(h_index)
    except Exception as e:
        print(f"Error fetching h-index: {e}")
    return None


def is_professor_by_h_index(author_name, threshold=20):
    """
    Identify if an author is a professor based on their Google Scholar h-index.

    Args:
        author_name (str): The name of the author.
        threshold (int): The h-index threshold for identifying professors.

    Returns:
        bool: True if the author's h-index exceeds the threshold, False otherwise.
    """
    print(f"Searching Google Scholar profile for '{author_name}'...")
    profile_url = get_google_scholar_profile(author_name)
    
    if not profile_url:
        print("Google Scholar profile not found.")
        return False
    
    print(f"Found profile: {profile_url}")
    print("Fetching h-index...")
    h_index = get_h_index(profile_url)
    
    if h_index is None:
        print("Could not retrieve h-index.")
        return False
    
    print(f"h-index: {h_index}")
    if h_index >= threshold:
        print(f"{author_name} is identified as a professor (h-index ≥ {threshold}).")
        return True
    else:
        print(f"{author_name} is not identified as a professor (h-index < {threshold}).")
        return False


def main2():

    is_prof = get_google_search_results("Gushu Li", )
    print(is_prof)


if __name__ == "__main__":
    # main2()
    main()


