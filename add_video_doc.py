import os
import re
import json
import yaml
import requests
from git import Repo
from collections import OrderedDict

# Global variables for video documentation details
VIDEO_DETAILS = {
    "short_summary": "Learn to get started with Cloudinary in a Node.js app. This tutorial covers setting up, configuring, and optimizing images using the Cloudinary Node.js SDK.",
    "file_name": "getting_started_with_cloudinary_node_tutorial",
    "title": "Getting started with Cloudinary in Node.js (video tutorial)",
    "meta_title": "Getting Started With Cloudinary in Node.js (Video Tutorial)",
    "description": "A step-by-step guide to getting started with Cloudinary in a Node.js application, including setup, configuration, and image optimization techniques.",
    "menu_title": "Getting started with Cloudinary in Node.js",
    "partial_card_file_name": "partial_card_getting_started_with_cloudinary_node",
    "partial_card_title": "Cloudinary in Node.js",
    "partial_card_description": "Learn to get started with Cloudinary in Node.js, including setup and image optimization.",
    "public_id": "Getting_Started_in_Node_-_v3_lma5vk",
    "github_url": "https://github.com/cloudinary-community/cloudinary-examples/tree/main/examples/node-image-upload"
}

JIRA_USERNAME = os.getenv("JIRA_USERNAME")
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN")

if not JIRA_USERNAME or not JIRA_API_TOKEN:
    raise ValueError("JIRA credentials are not set in environment variables.")

# Custom representer for OrderedDict
def represent_ordereddict(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

# Custom Dumper that inherits from SafeDumper
class OrderedDumper(yaml.SafeDumper):
    def represent_str(self, data):
        if "\n" in data:  # Ensure that \n is preserved as a literal "\n" rather than an actual line break
            return self.represent_scalar("tag:yaml.org,2002:str", data, style='"')  # Force double quotes
        return self.represent_scalar("tag:yaml.org,2002:str", data)

OrderedDumper.add_representer(str, OrderedDumper.represent_str)

# Register the custom representer
OrderedDumper.add_representer(OrderedDict, represent_ordereddict)

# Register the custom representer
yaml.add_representer(OrderedDict, represent_ordereddict)

def suggest_placement(video_title, menu_json_path):
    """
    Suggest the best place to add the new video tutorial in the menu.
    Returns both the selected tutorial ID and its path.
    """
    with open(menu_json_path, 'r') as file:
        menu_data = json.load(file)

    tutorial_sections = []

    def find_tutorials(node, path):
        if 'children' in node:
            for child in node['children']:
                find_tutorials(child, path + [node['id']])
        elif 'id' in node:
            tutorial_sections.append((node['id'], path))

    for item in menu_data:
        find_tutorials(item, [])

    print("Available tutorial sections:")
    for idx, (tutorial_id, path) in enumerate(tutorial_sections):
        print(f"{idx + 1}. {tutorial_id} (Path: {' > '.join(path)})")

    print("\nSelect the index after which you want to add the tutorial:")
    selected_index = int(input("Index: ")) - 1
    
    selected_tutorial = tutorial_sections[selected_index]
    return selected_tutorial[0], selected_tutorial[1]  # Return both ID and path

def update_yaml_with_new_entry(yaml_data, selected_tutorial_id, new_yaml_entry):
    """
    Insert the new YAML entry after the specified tutorial ID in the docs section.
    
    :param yaml_data: The entire YAML data dictionary
    :param selected_tutorial_id: The ID of the tutorial after which the new entry should be added
    :param new_yaml_entry: The new YAML entry to be added
    :return: Updated YAML data
    """
    # Ensure the documentation section exists
    if 'en' not in yaml_data or 'docs' not in yaml_data['en']:
        yaml_data['en']['docs'] = OrderedDict()
    
    # Create a new OrderedDict to maintain the original order
    new_documentation = OrderedDict()
    
    # Iterate through existing entries
    for key, value in yaml_data['en']['docs'].items():
        # Add existing entries
        new_documentation[key] = value
        
        # If we find the selected tutorial ID, add the new entry right after it
        if key == selected_tutorial_id:
            # Add the new entry
            new_entry_key = list(new_yaml_entry.keys())[0]
            new_documentation[new_entry_key] = new_yaml_entry[new_entry_key]
    
    # Replace the old documentation section with the new one
    yaml_data['en']['docs'] = new_documentation
    
    return yaml_data

def add_partial_doc_to_parent_pages(docs_dir, partial_card_file_name, parent_path):
    """
    Add partial doc reference to parent pages derived from the selected path.
    """
    # Convert section IDs to filenames and create full paths
    # We want the last two parent directories before the final selection
    parent_sections = parent_path[-2:]  # Take the two parents before the final selection
    parent_pages = [
        os.path.join(docs_dir, f'app/views/documentation/{section}.html.md')
        for section in parent_sections
    ]
    
    for parent_page in parent_pages:
        if os.path.exists(parent_page):
            with open(parent_page, 'r') as file:
                content = file.read()
            
            # Find the last {partialdoc} and add the new one after it
            last_partial = content.rindex('{partialdoc}')
            insert_pos = content.index('\n', last_partial) + 1
            new_partial = f'{{partialdoc}}{partial_card_file_name}{{partialdoc}}\n'
            
            updated_content = content[:insert_pos] + new_partial + content[insert_pos:]
            
            with open(parent_page, 'w') as file:
                file.write(updated_content)

def create_partial_card(docs_dir):
    """Create and update the partial card file."""
    source_partial = os.path.join(
        docs_dir,
        'app/views/documentation/partials/_partial_card_upload_assets_in_react.html.md'
    )
    dest_partial = os.path.join(
        docs_dir,
        f'app/views/documentation/partials/_{VIDEO_DETAILS["partial_card_file_name"]}.html.md'
    )
    
    # Copy the file
    with open(source_partial, 'r') as file:
        content = file.read()
    
    # Update the content
    content = content.replace('upload_assets_in_react_tutorial', VIDEO_DETAILS['file_name'])
    content = re.sub(r'vidId =\s*["\'].*?["\']', f'vidId = "{VIDEO_DETAILS["public_id"]}"', content)
    content = re.sub(r'<h6 class="tut_header">.*?</h6>', f'<h6 class="tut_header">{VIDEO_DETAILS["partial_card_title"]}</h6>', content)
    content = re.sub(r'<small>.*?</small>', f'<small>{VIDEO_DETAILS["partial_card_description"]}</small>', content)
    
    # Write the new file
    with open(dest_partial, 'w') as file:
        file.write(content)

def create_new_documentation_page(jira_ticket):
    """Main function to create new documentation page with all required updates."""
    # Parse the JIRA ticket for the video link
    ticket_id = jira_ticket.split('/')[-1]
    print("ticket_id: ", ticket_id)

    response = requests.get(
        f"https://cloudinary.atlassian.net/rest/api/3/issue/{ticket_id}?fields=description",
        auth=(JIRA_USERNAME, JIRA_API_TOKEN)
    )
    if response.status_code != 200:
        raise ValueError(f"Failed to fetch JIRA issue. Status code: {response.status_code}")

    print("response: ", response.json())
    video_url = response.json().get('fields', {}).get('description', {}).get('content', [{}])[0].get('content', [{}])[0].get('text', '')
    print("video_url:", video_url)

    if not video_url:
        raise ValueError("No video URL found in the JIRA ticket description.")

    video_id = video_url.split('v=')[-1]

    # Git operations
    repo = Repo(os.path.join(os.getcwd(), 'cld_docs'))
    branch_name = f"{ticket_id}_{VIDEO_DETAILS['file_name']}"
    repo.git.checkout('master')
    repo.git.pull()
    repo.git.checkout('-b', branch_name)

    # Determine placement
    json_path = os.path.join(os.getcwd(), 'cld_docs/app/menus/submenus/programmable-media-menu.json')
    selected_tutorial_id, parent_path = suggest_placement(VIDEO_DETAILS['title'], json_path)

    # Update JSON menu
    with open(json_path, 'r') as file:
        menu_data = json.load(file)

    new_entry = {"id": f"{VIDEO_DETAILS['file_name']}"}

    def add_to_menu(data):
        def search_and_insert(menu_list):
            for i, item in enumerate(menu_list):
                if item.get('id') == selected_tutorial_id:
                    # Insert the new entry right after the found item
                    menu_list.insert(i + 1, new_entry)
                    return True
                
                # Recursively search through children if they exist
                if 'children' in item:
                    if search_and_insert(item['children']):
                        return True
            return False

        return search_and_insert(data)
    
    add_to_menu(menu_data)

    with open(json_path, 'w') as file:
        json.dump(menu_data, file, indent=2)

    # Update YAML
    yaml_path = os.path.join(os.getcwd(), 'cld_docs/config/locales/en.yml')
    
    # Use full_load to preserve order
    yaml.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
                         lambda loader, node: OrderedDict(loader.construct_pairs(node)))
    
    with open(yaml_path, 'r') as file:
        yaml_data = yaml.full_load(file)

    new_yaml_entry = {
        f"{VIDEO_DETAILS['file_name']}": {
            "title": VIDEO_DETAILS['title'],
            "meta_title": VIDEO_DETAILS['meta_title'],
            "description": VIDEO_DETAILS['description'],
            "menu_title": VIDEO_DETAILS['menu_title']
        }
    }

    # Update YAML with the new entry after the selected tutorial
    yaml_data = update_yaml_with_new_entry(yaml_data, selected_tutorial_id, new_yaml_entry)

    # Use safe_dump with default_flow_style=False to maintain readability
    # Add the custom representer to handle OrderedDict
    with open(yaml_path, 'w') as file:
        yaml.dump(yaml_data, file, default_flow_style=False, Dumper=OrderedDumper)

    # Create and modify new documentation file
    source_md = os.path.join(os.getcwd(), 'cld_docs/app/views/documentation/upload_assets_in_react_tutorial.html.md')
    dest_md = os.path.join(os.getcwd(), f'cld_docs/app/views/documentation/{VIDEO_DETAILS["file_name"]}.html.md')

    with open(source_md, 'r') as file:
        content = file.read()

    # Perform all content replacements at once
    content = re.sub(r'videoId:\s*["\'].*?["\']', f'videoId: "{video_id}"', content)
    content = re.sub(r'\[githublink\]:\s*https?://[^\s]+', f'[githublink]: {VIDEO_DETAILS["github_url"]}', content)
    content = re.sub(
        r'(## Overview\s*\n).*?(?=\n## |\Z)',
        r'\1\n' + VIDEO_DETAILS['short_summary'] + '\n',
        content,
        flags=re.DOTALL
    )

    with open(dest_md, 'w') as file:
        file.write(content)

    docs_dir = os.path.join(os.getcwd(), 'cld_docs')

    # Add partial doc references to parent pages
    add_partial_doc_to_parent_pages(docs_dir, VIDEO_DETAILS['partial_card_file_name'], parent_path)
    
    # Create and update the partial card
    create_partial_card(docs_dir)

    # Git operations (commented out for manual handling)
    # repo.git.add(all=True)
    # repo.git.commit('-m', f"Add new tutorial page for {video_title} ({ticket_id})")
    # repo.git.push('--set-upstream', 'origin', branch_name)

if __name__ == "__main__":
    jira_ticket_url = input("Enter the JIRA ticket URL: ")
    create_new_documentation_page(jira_ticket_url)
