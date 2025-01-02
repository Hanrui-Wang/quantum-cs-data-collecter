import requests
import xml.etree.ElementTree as ET
import time
import random
import json
import os


# ---------------------------- Utility Functions ----------------------------

def ensure_directory(path):
    """Ensure a directory exists."""
    if not os.path.exists(path):
        os.makedirs(path)


def load_cache(file_path):
    """Load cache from a file."""
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return {}


def save_cache(data, file_path):
    """Save cache to a file."""
    with open(file_path, 'w') as f:
        json.dump(data, f, indent=4)


# Initialize Cache Directories
ensure_directory('cache/conferences')
ensure_directory('cache/authors')


# ---------------------------- Stage 1: Fetch Conference Data ----------------------------

def query_dblp(keyword, venue, year, max_results=50):
    """Fetch papers from DBLP and cache results."""
    cache_path = f"cache/conferences/{venue}{year}.json"
    conference_cache = load_cache(cache_path)
    
    if conference_cache:
        print(f"Loading cached data for {venue} {year}...")
        return False, conference_cache

    base_url = "https://dblp.org/search/publ/api"
    params = {"q": f"title:{keyword} venue:{venue} year:{year}", "format": "xml", "h": max_results}

    try:
        response = requests.get(base_url, params=params)
        if response.status_code == 429:
            print("Rate limited. Sleeping before retry...")
            time.sleep(random.uniform(60, 120))
            return query_dblp(keyword, venue, year, max_results)
        if response.status_code != 200:
            raise Exception(f"Failed to fetch data: {response.status_code}")
        
        root = ET.fromstring(response.content)
        papers = [{"title": info.find("title").text, "authors": [a.text for a in info.findall(".//author")]} 
                  for info in root.findall(".//info")]
        
        save_cache(papers, cache_path)
        return True, papers
    except Exception as e:
        print(f"Error querying DBLP: {e}")
    return False, []


def fetch_all_conference_papers():
    """Fetch papers from multiple conferences and years."""
    keyword = "quantum"
    venues = ["NeurIPS", "DAC", "AAAI", "ICCAD"]
    years = range(2020, 2025)
    all_papers = []

    for venue in venues:
        for year in years:
            print(f"Querying {venue} {year}...")
            is_sleep, papers = query_dblp(keyword, venue, year)
            all_papers.extend(papers)
            if is_sleep:
                time.sleep(random.uniform(2, 5))
    
    save_cache(all_papers, 'cache/all_papers.json')
    return all_papers


# ---------------------------- Stage 2: Process and Cache Author Profiles ----------------------------

def get_dblp_author_profile(author_name):
    """Fetch DBLP profile URL for an author."""
    author_cache_path = f"cache/authors/{author_name.replace(' ', '_')}.json"
    author_cache = load_cache(author_cache_path)
    
    if 'profile_url' in author_cache:
        return author_cache['profile_url']
    
    search_url = "https://dblp.org/search/author/api"
    params = {"q": author_name, "format": "xml", "h": 1}

    try:
        response = requests.get(search_url)
        if response.status_code == 429:
            print("Rate limited. Sleeping before retry...")
            time.sleep(random.uniform(60, 120))
            return get_dblp_author_profile(author_name)
        if response.status_code != 200:
            raise Exception(f"Failed to query DBLP: Status Code {response.status_code}")
        
        root = ET.fromstring(response.content)
        author_entry = root.find(".//hits/hit/info/url")
        profile_url = author_entry.text if author_entry is not None else None
        author_cache['profile_url'] = profile_url
        save_cache(author_cache, author_cache_path)
        return profile_url
    except Exception as e:
        print(f"Error fetching DBLP author profile: {e}")
    return None


def get_dblp_publication_count(author_url):
    """Fetch publication count from DBLP author profile."""
    try:
        response = requests.get(author_url + ".xml")
        root = ET.fromstring(response.content)
        return len(root.findall(".//r"))
    except Exception as e:
        print(f"Error fetching publication count: {e}")
    return None


def get_latest_affiliation(author_url):
    """Fetch latest affiliation from DBLP author profile."""
    try:
        response = requests.get(author_url + ".xml")
        root = ET.fromstring(response.content)
        affiliation = root.find(".//note[@type='affiliation']")
        return affiliation.text.strip() if affiliation is not None else "Unknown Affiliation"
    except Exception as e:
        print(f"Error fetching affiliation: {e}")
    return "Unknown Affiliation"


def process_all_authors(papers):
    """Process unique authors and cache their publication count and affiliation."""
    authors = set(author for paper in papers for author in paper['authors'])
    print(f"Found {len(authors)} unique authors.")
    
    for idx, author in enumerate(authors, start=1):
        print(f"Processing author {author} ({idx}/{len(authors)})")
        author_cache_path = f"cache/authors/{author.replace(' ', '_')}.json"
        author_cache = load_cache(author_cache_path)
        
        if 'is_professor' in author_cache:
            print(" → Author already cached.")
            continue
        
        profile_url = get_dblp_author_profile(author)
        if not profile_url:
            continue

        pub_count = get_dblp_publication_count(profile_url)
        if pub_count is None:
            continue
        
        affiliation = "Unknown"
        if pub_count >= 20:
            affiliation = get_latest_affiliation(profile_url)
        
        author_cache.update({
            'profile_url': profile_url,
            'pub_count': pub_count,
            'affiliation': affiliation,
            'is_professor': pub_count >= 20
        })
        save_cache(author_cache, author_cache_path)
        time.sleep(random.uniform(2, 5))


# ---------------------------- Stage 3: Build the Final Dictionary ----------------------------

def build_professor_paper_dict(papers):
    professor_dict = {}
    for paper in papers:
        for author in paper['authors']:
            author_cache = load_cache(f"cache/authors/{author.replace(' ', '_')}.json")
            if author_cache.get('is_professor'):
                key = f"{author}, {author_cache.get('affiliation', 'Unknown')}"
                if key not in professor_dict:
                    professor_dict[key] = []
                professor_dict[key].append((paper.get('conference', 'Unknown'), paper.get('title', 'Unknown')))
    save_cache(professor_dict, 'professor_papers.json')
    return professor_dict


# ---------------------------- Main Program ----------------------------

def main():
    papers = fetch_all_conference_papers()
    process_all_authors(papers)
    professor_dict = build_professor_paper_dict(papers)
    print(json.dumps(professor_dict, indent=4))


if __name__ == "__main__":
    main()
