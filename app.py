import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime
import time
import os
import functools

# Set page configuration
st.set_page_config(
    page_title="PetMatch - Find Your Perfect Pet",
    page_icon="🐾",
    layout="centered"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #ff6b6c;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #4a4a4a;
        text-align: center;
        margin-bottom: 2rem;
    }
    .pet-card {
        border-radius: 10px;
        border: 1px solid #e0e0e0;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    .pet-name {
        font-size: 1.3rem;
        font-weight: bold;
        color: #ff6b6b;
    }
    .pet-details {
        margin-top: 0.5rem;
    }
    .pet-description {
        margin-top: 1rem;
        font-style: italic;
    }
    .tag {
        background-color: #808080;
        border-radius: 20px;
        padding: 0.2rem 0.6rem;
        margin-right: 0.3rem;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state variables
if 'access_token' not in st.session_state:
    st.session_state.access_token = None
if 'token_expires' not in st.session_state:
    st.session_state.token_expires = 0
if 'search_results' not in st.session_state:
    st.session_state.search_results = None
if 'selected_pet' not in st.session_state:
    st.session_state.selected_pet = None
if 'page' not in st.session_state:
    st.session_state.page = 1
if 'favorites' not in st.session_state:
    st.session_state.favorites = []

# Function to get access token
def get_access_token():
    # Check if token is still valid
    if st.session_state.access_token and time.time() < st.session_state.token_expires:
        return st.session_state.access_token
    
    # Get API credentials from environment variables or secrets
    api_key = os.environ.get('PETFINDER_API_KEY') or st.secrets.get('PETFINDER_API_KEY')
    api_secret = os.environ.get('PETFINDER_API_SECRET') or st.secrets.get('PETFINDER_API_SECRET')
    
    if not api_key or not api_secret:
        st.error("⚠️ Petfinder API credentials are missing. Please set them in your environment variables or Streamlit secrets.")
        return None
    
    # Get new token
    url = "https://api.petfinder.com/v2/oauth2/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": api_key,
        "client_secret": api_secret
    }
    
    try:
        response = requests.post(url, data=data)
        response.raise_for_status()
        token_data = response.json()
        st.session_state.access_token = token_data['access_token']
        st.session_state.token_expires = time.time() + token_data['expires_in'] - 60  # Buffer of 60 seconds
        return st.session_state.access_token
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Error getting access token: {str(e)}")
        return None

# Function to search pets
def search_pets(params):
    token = get_access_token()
    if not token:
        return None
    
    url = "https://api.petfinder.com/v2/animals"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Error searching pets: {str(e)}")
        return None



# Function to get breeds
def get_breeds(animal_type):
    token = get_access_token()
    if not token:
        return []
    
    url = f"https://api.petfinder.com/v2/types/{animal_type}/breeds"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return [breed['name'] for breed in response.json()['breeds']]
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Error getting breeds: {str(e)}")
        return []

# Function to get organizations
def get_organizations(location):
    token = get_access_token()
    if not token:
        return []
    
    url = "https://api.petfinder.com/v2/organizations"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"location": location, "distance": 100, "limit": 100}
    
    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return [(org['id'], org['name']) for org in response.json()['organizations']]
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Error getting organizations: {str(e)}")
        return []

# Function to get pet details
def get_pet_details(pet_id):
    token = get_access_token()
    if not token:
        return None
    
    url = f"https://api.petfinder.com/v2/animals/{pet_id}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.json()['animal']
    except requests.exceptions.RequestException as e:
        st.error(f"⚠️ Error getting pet details: {str(e)}")
        return None

# Function to format pet card
def display_pet_card(pet, is_favorite=False, context="search"):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if pet['photos'] and len(pet['photos']) > 0:
            st.image(pet['photos'][0]['medium'], use_container_width=True)
        else:
            st.image("https://via.placeholder.com/300x300?text=No+Image", use_container_width=True)
    
    with col2:
        st.markdown(f"<div class='pet-name'>{pet['name']}</div>", unsafe_allow_html=True)
        
        # Tags
        tags_html = ""
        if pet['status'] == 'adoptable':
            tags_html += "<span class='tag' style='background-color: #808080;'>Adoptable</span> "
        else:
            tags_html += f"<span class='tag' style='background-color: #808080;'>{pet['status'].title()}</span> "
        
        if pet['age']:
            tags_html += f"<span class='tag'>{pet['age']}</span> "
        if pet['gender']:
            tags_html += f"<span class='tag'>{pet['gender']}</span> "
        if pet['size']:
            tags_html += f"<span class='tag'>{pet['size']}</span> "
        
        st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='pet-details'>", unsafe_allow_html=True)
        if pet['breeds']['primary']:
            breed_text = pet['breeds']['primary']
            if pet['breeds']['secondary']:
                breed_text += f" & {pet['breeds']['secondary']}"
            if pet['breeds']['mixed']:
                breed_text += " (Mixed)"
            st.markdown(f"<strong>Breed:</strong> {breed_text}", unsafe_allow_html=True)
        
        if pet['colors']['primary'] or pet['colors']['secondary'] or pet['colors']['tertiary']:
            colors = [c for c in [pet['colors']['primary'], pet['colors']['secondary'], pet['colors']['tertiary']] if c]
            st.markdown(f"<strong>Colors:</strong> {', '.join(colors)}", unsafe_allow_html=True)
        
        if 'location' in pet and pet['contact']['address']['city'] and pet['contact']['address']['state']:
            st.markdown(f"<strong>Location:</strong> {pet['contact']['address']['city']}, {pet['contact']['address']['state']}", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        if pet['description']:
            st.markdown(f"<div class='pet-description'>{pet['description'][:500]}{'...' if len(pet['description']) > 500 else ''}</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Details", key=f"details_{context}_{pet['id']}"):
                st.session_state.selected_pet = pet['id']
                st.rerun()
        with col2:
            if not is_favorite:
                if st.button("Add to Favorites", key=f"fav_{context}_{pet['id']}"):
                    if pet['id'] not in [p['id'] for p in st.session_state.favorites]:
                        st.session_state.favorites.append(pet)
                        st.success(f"Added {pet['name']} to favorites!")
                        st.rerun()
            else:
                if st.button("Remove from Favorites", key=f"unfav_{context}_{pet['id']}"):
                    st.session_state.favorites = [p for p in st.session_state.favorites if p['id'] != pet['id']]
                    st.success(f"Removed {pet['name']} from favorites!")
                    st.rerun()

# Function to generate pet compatibility message
def get_compatibility_message(pet):
    messages = []
    
    # Check for kids
    if 'children' in pet['environment'] and pet['environment']['children'] is not None:
        if pet['environment']['children']:
            messages.append("✅ Good with children")
        else:
            messages.append("❌ Not recommended for homes with children")
    
    # Check for dogs
    if 'dogs' in pet['environment'] and pet['environment']['dogs'] is not None:
        if pet['environment']['dogs']:
            messages.append("✅ Good with dogs")
        else:
            messages.append("❌ Not recommended for homes with dogs")
    
    # Check for cats
    if 'cats' in pet['environment'] and pet['environment']['cats'] is not None:
        if pet['environment']['cats']:
            messages.append("✅ Good with cats")
        else:
            messages.append("❌ Not recommended for homes with cats")
    
    # Handling care needs
    if pet['attributes']:
        if 'special_needs' in pet['attributes'] and pet['attributes']['special_needs']:
            messages.append("⚠️ Has special needs")
        
        if 'house_trained' in pet['attributes'] and pet['attributes']['house_trained']:
            messages.append("✅ House-trained")
        elif 'house_trained' in pet['attributes']:
            messages.append("❌ Not house-trained")
        
        if 'shots_current' in pet['attributes'] and pet['attributes']['shots_current']:
            messages.append("✅ Vaccinations up to date")
        
        if 'spayed_neutered' in pet['attributes'] and pet['attributes']['spayed_neutered']:
            messages.append("✅ Spayed/neutered")
    
    return messages

# Function to display pet details page
# Changes to make keys unique across different tabs

# Function to display pet details page with unique tab identifier
def display_pet_details(pet_id, context="search", tab_id="tab1"):
    pet = get_pet_details(pet_id)
    if not pet:
        st.error("Unable to retrieve pet details. Please try again.")
        return
    
    # Back button with unique key that includes tab identifier
    if st.button("← Back to Search Results", key=f"back_{tab_id}_{context}_{pet_id}"):
        st.session_state.selected_pet = None
        st.rerun()  # Force immediate rerun
    
    # Pet name and status
    st.markdown(f"<h1 class='main-header'>{pet['name']}</h1>", unsafe_allow_html=True)
    
    status_color = "#c8e6c9" if pet['status'] == 'adoptable' else "#ffcdd2"
    st.markdown(f"<div style='text-align: center;'><span class='tag' style='background-color: {status_color}; font-size: 1rem;'>{pet['status'].title()}</span></div>", unsafe_allow_html=True)
    
    # Pet photos
    if pet['photos'] and len(pet['photos']) > 0:
        photo_cols = st.columns(min(3, len(pet['photos'])))
        for i, col in enumerate(photo_cols):
            if i < len(pet['photos']):
                col.image(pet['photos'][i]['large'], use_container_width=True)
    else:
        st.image("https://via.placeholder.com/500x300?text=No+Image", use_container_width=True)
    
    # Pet details
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Details")
        # Fix the breed line
        breed_text = pet['breeds']['primary']
        if pet['breeds']['secondary']:
            breed_text += f" & {pet['breeds']['secondary']}"
        if pet['breeds']['mixed']:
            breed_text += " (Mixed)"
    
        details = [
            f"**Type:** {pet['type']}",
            f"**Breed:** {breed_text}",
            f"**Age:** {pet['age']}",
            f"**Gender:** {pet['gender']}",
            f"**Size:** {pet['size']}"
        ]
    
        # Fix the colors line as well, to be safe
        colors = [c for c in [pet['colors']['primary'], pet['colors']['secondary'], pet['colors']['tertiary']] if c]
        if colors:
            details.append(f"**Colors:** {', '.join(colors)}")
    
        for detail in details:
            st.markdown(detail)
    
    with col2:
        st.markdown("### Compatibility")
        compatibility = get_compatibility_message(pet)
        for msg in compatibility:
            st.markdown(msg)
    
    # Description
    if pet['description']:
        if pet['description']:
            st.markdown("### About")
            #st.markdown(pet['description'])
            st.markdown(f"<div class='pet-description'>{pet['description'][:500]}{'...' if len(pet['description']) > 500 else ''}</div>", unsafe_allow_html=True)
    
    # Contact information
    st.markdown("### Adoption Information")
    
    # Organization info
    if pet['organization_id']:
        st.markdown(f"**Organization:** {pet['organization_id']}")
    
    # Contact details
    contact_info = []
    if pet['contact']['email']:
        contact_info.append(f"**Email:** {pet['contact']['email']}")
    if pet['contact']['phone']:
        contact_info.append(f"**Phone:** {pet['contact']['phone']}")
    if pet['contact']['address']['city'] and pet['contact']['address']['state']:
        contact_info.append(f"**Location:** {pet['contact']['address']['city']}, {pet['contact']['address']['state']} {pet['contact']['address']['postcode'] or ''}")
    
    for info in contact_info:
        st.markdown(info)
    
    # URL to pet on Petfinder
    if pet['url']:
        st.markdown(f"[View on Petfinder]({pet['url']})")
    
    # Add to favorites with unique key
    is_favorite = pet['id'] in [p['id'] for p in st.session_state.favorites]
    if not is_favorite:
        if st.button("Add to Favorites", key=f"add_fav_{tab_id}_{context}_{pet_id}"):
            st.session_state.favorites.append(pet)
            st.success(f"Added {pet['name']} to favorites!")
            st.rerun()
    else:
        if st.button("Remove from Favorites", key=f"rem_fav_{tab_id}_{context}_{pet_id}"):
            st.session_state.favorites = [p for p in st.session_state.favorites if p['id'] != pet['id']]
            st.success(f"Removed {pet['name']} from favorites!")
            st.rerun()

# Function to format pet card with unique tab identifier
def display_pet_card(pet, is_favorite=False, context="search", tab_id="tab1"):
    col1, col2 = st.columns([1, 2])
    
    with col1:
        if pet['photos'] and len(pet['photos']) > 0:
            st.image(pet['photos'][0]['medium'], use_container_width=True)
        else:
            st.image("https://via.placeholder.com/300x300?text=No+Image", use_container_width=True)
    
    with col2:
        st.markdown(f"<div class='pet-name'>{pet['name']}</div>", unsafe_allow_html=True)
        
        # Tags
        tags_html = ""
        if pet['status'] == 'adoptable':
            tags_html += "<span class='tag' style='background-color: #808080;'>Adoptable</span> "
        else:
            tags_html += f"<span class='tag' style='background-color: #808080;'>{pet['status'].title()}</span> "
        
        if pet['age']:
            tags_html += f"<span class='tag'>{pet['age']}</span> "
        if pet['gender']:
            tags_html += f"<span class='tag'>{pet['gender']}</span> "
        if pet['size']:
            tags_html += f"<span class='tag'>{pet['size']}</span> "
        
        st.markdown(f"<div>{tags_html}</div>", unsafe_allow_html=True)
        
        st.markdown("<div class='pet-details'>", unsafe_allow_html=True)
        if pet['breeds']['primary']:
            breed_text = pet['breeds']['primary']
            if pet['breeds']['secondary']:
                breed_text += f" & {pet['breeds']['secondary']}"
            if pet['breeds']['mixed']:
                breed_text += " (Mixed)"
            st.markdown(f"<strong>Breed:</strong> {breed_text}", unsafe_allow_html=True)
        
        if pet['colors']['primary'] or pet['colors']['secondary'] or pet['colors']['tertiary']:
            colors = [c for c in [pet['colors']['primary'], pet['colors']['secondary'], pet['colors']['tertiary']] if c]
            st.markdown(f"<strong>Colors:</strong> {', '.join(colors)}", unsafe_allow_html=True)
        
        if 'location' in pet and pet['contact']['address']['city'] and pet['contact']['address']['state']:
            st.markdown(f"<strong>Location:</strong> {pet['contact']['address']['city']}, {pet['contact']['address']['state']}", unsafe_allow_html=True)
        
        st.markdown("</div>", unsafe_allow_html=True)
        
        if pet['description']:
            st.markdown(f"<div class='pet-description'>{pet['description'][:300]}{'...' if len(pet['description']) > 300 else ''}</div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Details", key=f"details_{tab_id}_{context}_{pet['id']}"):
                st.session_state.selected_pet = pet['id']
                st.rerun()
        with col2:
            if not is_favorite:
                if st.button("Add to Favorites", key=f"fav_{tab_id}_{context}_{pet['id']}"):
                    if pet['id'] not in [p['id'] for p in st.session_state.favorites]:
                        st.session_state.favorites.append(pet)
                        st.success(f"Added {pet['name']} to favorites!")
                        st.rerun()
            else:
                if st.button("Remove from Favorites", key=f"unfav_{tab_id}_{context}_{pet['id']}"):
                    st.session_state.favorites = [p for p in st.session_state.favorites if p['id'] != pet['id']]
                    st.success(f"Removed {pet['name']} from favorites!")
                    st.rerun()

# Main app with updated function calls
def main():
    # Title
    st.markdown("<h1 class='main-header'>🐾 PetMatch</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>Find your perfect pet companion</p>", unsafe_allow_html=True)
    
    # Create tabs
    tab1, tab2, tab3 = st.tabs(["Search", "Favorites", "About"])
    
    with tab1:
        # If a pet is selected, show details
        if st.session_state.selected_pet:
            display_pet_details(st.session_state.selected_pet, context="search", tab_id="tab1")
        else:
            # Search form
            with st.expander("Search Options", expanded=True):
                with st.form("pet_search_form"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        animal_type = st.selectbox(
                            "Animal Type",
                            ["Dog", "Cat", "Rabbit", "Small & Furry", "Horse", "Bird", "Scales, Fins & Other", "Barnyard"]
                        )
                        
                        location = st.text_input("Location (ZIP code or City, State)", "")
                        
                        distance = st.slider("Distance (miles)", min_value=10, max_value=500, value=50, step=10)
                    
                    with col2:
                        age_options = ["Doesn't Matter", "Baby", "Young", "Adult", "Senior"]
                        age = st.selectbox("Age", age_options)

                        size_options = ["Doesn't Matter", "Small", "Medium", "Large", "XLarge"]
                        size = st.selectbox("Size", size_options)

                        gender_options = ["Doesn't Matter", "Male", "Female"]
                        gender = st.selectbox("Gender", gender_options)

                        good_with_children = st.checkbox("Good with children")
                        good_with_dogs = st.checkbox("Good with dogs")
                        good_with_cats = st.checkbox("Good with cats")
                        house_trained = st.checkbox("House-trained")
                        special_needs = st.checkbox("Special needs")
        
                    submitted = st.form_submit_button("Search")
                    
                    if submitted:
                        # Build search parameters
                        params = {
                            "type": animal_type.split(" ")[0],  # Take first word for types like "Small & Furry"
                            "location": location,
                            "distance": distance,
                            "status": "adoptable",
                            "sort": "distance",
                            "limit": 100
                        }
                        
                        if age != "Doesn't Matter":
                            params["age"] = age
                        if size != "Doesn't Matter":
                            params["size"] = size
                        if gender != "Doesn't Matter":
                            params["gender"] = gender

                        
                        # Add advanced filters
                        if good_with_children:
                            params["good_with_children"] = 1
                        if good_with_dogs:
                            params["good_with_dogs"] = 1
                        if good_with_cats:
                            params["good_with_cats"] = 1
                        if house_trained:
                            params["house_trained"] = 1
                        if special_needs:
                            params["special_needs"] = 1
                        
                        # Perform search
                        results = search_pets(params)
                        if results and 'animals' in results:
                            st.session_state.search_results = results
                            st.session_state.page = 1
                            st.success(f"Found {len(results['animals'])} pets!")
                        else:
                            st.error("No pets found with those criteria. Try expanding your search.")
            
            # Display search results
            if st.session_state.search_results and 'animals' in st.session_state.search_results:
                st.markdown("### Search Results")
                
                # Pagination
                results = st.session_state.search_results['animals']
                total_pages = (len(results) + 9) // 10  # 10 items per page
                
                # Display page selector
                if total_pages > 1:
                    col1, col2, col3 = st.columns([1, 3, 1])
                    with col2:
                        page = st.slider("Page", 1, total_pages, st.session_state.page)
                        if page != st.session_state.page:
                            st.session_state.page = page
                
                # Display pets for current page
                start_idx = (st.session_state.page - 1) * 10
                end_idx = min(start_idx + 10, len(results))
                
                for pet in results[start_idx:end_idx]:
                    st.markdown("---")
                    display_pet_card(pet, tab_id="tab1")
    
    with tab2:
        st.markdown("### Your Favorite Pets")
        
        if not st.session_state.favorites:
            st.info("You haven't added any pets to your favorites yet. Start searching to find your perfect match!")
        else:
            # Check if a pet is selected from favorites
            if st.session_state.selected_pet:
                display_pet_details(st.session_state.selected_pet, context="favorites", tab_id="tab2")
            else:
                for pet in st.session_state.favorites:
                    st.markdown("---")
                    display_pet_card(pet, is_favorite=True, context="favorites", tab_id="tab2")
    
    with tab3:
        st.markdown("### About PetMatch")
        st.markdown("""
        PetMatch helps you find your perfect pet companion from thousands of adoptable animals across the country.
        
        **How to use PetMatch:**
        1. Search for pets based on your preferences and location
        2. Browse through the results and click "View Details" to learn more about each pet
        3. Add pets to your favorites to keep track of the ones you're interested in
        4. Contact the shelter or rescue organization directly using the provided information
        
        **Data Source:**
        PetMatch uses the Petfinder API to provide up-to-date information on adoptable pets. Petfinder is North America's largest adoption website with hundreds of thousands of adoptable pets listed by more than 11,500 animal shelters and rescue organizations.
        
        **Privacy:**
        PetMatch does not store any personal information or search history. Your favorites are stored locally in your browser and are not shared with any third parties.
        """)


if __name__ == "__main__":
    main()
