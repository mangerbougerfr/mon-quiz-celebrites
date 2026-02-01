import streamlit as st
import requests
import random
import re

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Quiz Célébrités", page_icon="🎬", layout="centered")

# --- FONCTIONS ---
def is_latin(text):
    # Vérifie si le nom est écrit avec notre alphabet
    return bool(re.match(r'^[a-zA-Zà-üÀ-Ü\s\-\.\']+$', text))

def is_from_2000s(person):
    # Vérifie si la personne est connue pour des films après l'an 2000
    if 'known_for' in person:
        for work in person['known_for']:
            date = work.get('release_date') or work.get('first_air_date')
            if date:
                year = int(date[:4])
                if year >= 2000:
                    return True
    return False

def get_random_page():
    # MODIFICATION : On cherche maintenant dans les 20 premières pages
    return random.randint(1, 20)

def get_people_from_api():
    try:
        page = get_random_page()
        url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page}"
        response = requests.get(url)
        data = response.json()
        
        valid_people = []
        if "results" in data:
            for p in data["results"]:
                if p['profile_path'] and is_latin(p['name']) and is_from_2000s(p):
                    valid_people.append(p)
            return valid_people
        return []
    except:
        return []

# --- LOGIQUE DU JEU ---
if 'current_person' not in st.session_state:
    st.session_state.current_person = None
if 'choices' not in st.session_state:
    st.session_state.choices = []
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = "question"
if 'message' not in st.session_state:
    st.session_state.message = ""

def new_round():
    people_list = get_people_from_api()
    
    # Sécurité anti-bug
    if not people_list or len(people_list) < 4:
        new_round() 
        return

    correct_person = random.choice(people_list)
    correct_gender = correct_person['gender']
    
    # Filtrer par genre
    same_gender_people = [p for p in people_list if p['id'] != correct_person['id'] and p['gender'] == correct_gender]
    
    if len(same_gender_people) < 3:
        others = [p for p in people_list if p['id'] != correct_person['id']]
    else:
        others = same_gender_people

    if len(others) >= 3:
        wrong_answers = random.sample(others, 3)
        choices = wrong_answers + [correct_person]
        random.shuffle(choices)
        
        st.session_state.current_person = correct_person
        st.session_state.choices = choices
        st.session_state.game_phase = "question"
        st.session_state.message = ""
    else:
        new_round()

def check_answer(selected_person):
    if selected_person['id'] == st.session_state.current_person['id']:
        st.session_state.score += 1
        st.session_state.message = f"✅ BRAVO ! C'est bien {selected_person['name']}"
    else:
        st.session_state.message = f"❌ RATÉ... C'était {st.session_state.current_person['name']}"
    
    st.session_state.game_phase = "resultat"

# --- INTERFACE ---
st.title("🌟 Quiz Célébrités (Années 2000+)")
st.write(f"**Score : {st.session_state.score}**")

if st.session_state.current_person is None:
    new_round()

if st.session_state.current_person:
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        photo_path = st.session_state.current_person['profile_path']
        st.image(f"{IMAGE_URL}{photo_path}", use_container_width=True)

    if st.session_state.game_phase == "question":
        st.write("### Qui est cette personne ?")
        
        c1, c2 = st.columns(2)
        for i, person in enumerate(st.session_state.choices):
            if i < 2:
                with c1:
                    if st.button(person['name'], key=f"btn_{i}", use_container_width=True):
                        check_answer(person)
                        st.rerun()
            else:
                with c2:
                    if st.button(person['name'], key=f"btn_{i}", use_container_width=True):
                        check_answer(person)
                        st.rerun()

    else:
        if "✅" in st.session_state.message:
            st.success(st.session_state.message)
        else:
            st.error(st.session_state.message)
        
        if st.button("Question Suivante ➡️", type="primary"):
            new_round()
            st.rerun()
