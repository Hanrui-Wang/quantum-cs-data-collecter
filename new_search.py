import requests
import xml.etree.ElementTree as ET
import time
import random
import json
import os
import csv

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
    """
    Fetch papers from multiple conferences and years, adding venue and year to each paper entry.
    
    Returns:
        List[Dict]: A list of paper dictionaries with 'title', 'authors', 'conference', 'venue', and 'year'.
    """
    keyword = "quantum"
    venues = ["NeurIPS", "DAC", "AAAI", "ICCAD"]
    years = range(2020, 2025)
    all_papers = []

    for venue in venues:
        for year in years:
            print(f"Querying {venue} {year}...")
            is_sleep, papers = query_dblp(keyword, venue, year)
            
            # Add venue and year to each paper
            for paper in papers:
                paper['venue'] = venue
                paper['year'] = year
                paper['conference'] = f"{venue}{year}"
            
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
    
    # Return cached profile URL if available
    if 'profile_url' in author_cache:
        return author_cache['profile_url']
    
    search_url = "https://dblp.org/search/author/api"
    params = {"q": author_name, "format": "xml", "h": 1}

    try:
        response = requests.get(search_url, params=params)  # Pass params here
        if response.status_code == 429:
            print("Rate limited. Sleeping before retry...")
            time.sleep(random.uniform(60, 120))
            return get_dblp_author_profile(author_name)
        if response.status_code != 200:
            raise Exception(f"Failed to query DBLP: Status Code {response.status_code}")
        
        # Parse the XML response
        root = ET.fromstring(response.content)
        author_entry = root.find(".//hits/hit/info/url")
        profile_url = author_entry.text if author_entry is not None else None
        
        # Cache the profile URL
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


def build_professor_paper_count_dict(papers):
    """
    Build a dictionary of professors with their paper counts per conference.

    Args:
        papers (List[Dict]): List of paper dictionaries with 'title', 'authors', and 'conference'.

    Returns:
        Dict[str, List[str]]: Dictionary with professor name+affiliation as key,
                              and a list of paper counts per conference as values.
    """
    professor_count_dict = {}
    conference_author_paper_count = {}

    # Step 1: Count papers per author per conference
    for paper in papers:
        conference = paper.get('conference', 'Unknown Conference')
        authors = paper.get('authors', [])
        
        for author in authors:
            author_cache_path = f"cache/authors/{author.replace(' ', '_')}.json"
            author_data = load_cache(author_cache_path)
            
            # Check if the author is a professor
            if author_data.get('is_professor'):
                affiliation = author_data.get('affiliation', 'Unknown Affiliation')
                key = f"{author}, {affiliation}"
                
                # Initialize entry if not exists
                if key not in conference_author_paper_count:
                    conference_author_paper_count[key] = {}
                
                # Increment count for the conference
                if conference not in conference_author_paper_count[key]:
                    conference_author_paper_count[key][conference] = 0
                conference_author_paper_count[key][conference] += 1

    # Step 2: Format the dictionary
    for professor, conf_counts in conference_author_paper_count.items():
        professor_count_dict[professor] = [
            f"{conf}, {count}" for conf, count in conf_counts.items()
        ]
    
    # Save to JSON cache
    save_cache(professor_count_dict, 'professor_paper_counts.json')
    
    return professor_count_dict


def generate_professor_paper_count_csv(professor_paper_count_dict, output_file='professor_paper_counts.csv'):
    """
    Generate a CSV file summarizing professor paper counts per conference with two-digit year format,
    handling multiple commas in affiliation, and including the author URL.

    Args:
        professor_paper_count_dict (Dict): Dictionary with professor name+affiliation as keys,
                                           and a list of paper counts per conference as values.
        output_file (str): Path to the output CSV file.
    """
    with open(output_file, mode='w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        
        # Write header row
        csv_writer.writerow(['Professor Name', 'Affiliation', 'Paper Counts', 'Author URL'])
        
        # Process each professor entry
        for key, counts in professor_paper_count_dict.items():
            # Split the key into name and affiliation (split only on the first comma)
            parts = key.split(',', 1)
            professor_name = parts[0].strip()
            affiliation = parts[1].strip() if len(parts) > 1 else 'Unknown Affiliation'
            
            # Format the counts into the desired format with two-digit year
            formatted_counts = "; ".join([
                f"{entry.split(',')[0][:-4]}({entry.split(',')[0][-2:]}):{entry.split(',')[1]}"
                for entry in counts
            ])
            
            # Fetch author URL from the cache
            author_cache_path = f"cache/authors/{professor_name.replace(' ', '_')}.json"
            author_data = load_cache(author_cache_path)
            author_url = author_data.get('profile_url', 'Unknown URL')
            
            # Write the row to CSV
            csv_writer.writerow([professor_name, affiliation, formatted_counts, author_url])
    
    print(f"CSV file successfully generated: {output_file}")



# ---------------------------- Main Program ----------------------------

def main():
    papers = fetch_all_conference_papers()
    process_all_authors(papers) # Uncomment for first time run
    professor_paper_count_dict = build_professor_paper_count_dict(papers)    
    print(json.dumps(professor_paper_count_dict, indent=4))

    generate_professor_paper_count_csv(professor_paper_count_dict)

    # professor_dict = build_professor_paper_dict(papers)
    # print(json.dumps(professor_dict, indent=4))


if __name__ == "__main__":
    main()
