import streamlit as st
import requests
import random
import re
import time

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"
GAME_DURATION = 30  # Durée du timer en secondes

st.set_page_config(page_title="Quiz Célébrités", page_icon="🎬", layout="centered")

# --- CSS PERSONNALISÉ ---
st.markdown("""
<style>
    .stButton button {
        height: 80px;
        font-size: 20px;
    }
    div[data-testid="stImage"] {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    .timer-container {
        text-align: center;
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# --- FONCTIONS ---
def is_latin(text):
    # Vérifie si le nom est écrit avec notre alphabet
    return bool(re.match(r'^[a-zA-Zà-üÀ-Ü\s\-\.\']+$', text))

def get_random_page():
    # On ne cherche que dans les 5 premières pages pour avoir des stars TRES connues
    return random.randint(1, 5)

def get_people_from_api():
    try:
        page = get_random_page()
        url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page}"
        response = requests.get(url)
        data = response.json()
        
        valid_people = []
        if "results" in data:
            for p in data["results"]:
                # Filtres : Photo existe, Nom latin, Populaire, Pas de contenu adulte
                if (p['profile_path'] and 
                    is_latin(p['name']) and 
                    p.get('popularity', 0) > 10 and 
                    not p.get('adult', False)):
                    valid_people.append(p)
            return valid_people
        return []
    except:
        return []

def display_circular_timer(remaining_time, total_time):
    """Affiche une jauge circulaire colorée via HTML/SVG"""
    percent = (remaining_time / total_time) * 100
    
    # Choix de la couleur
    if remaining_time > 15:
        color = "#4CAF50" # Vert
    elif remaining_time > 5:
        color = "#FFC107" # Jaune/Orange
    else:
        color = "#F44336" # Rouge

    # Code SVG pour le cercle
    svg_code = f"""
    <div style="display: flex; justify-content: center; margin-bottom: 10px;">
        <svg width="100" height="100" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#ddd" stroke-width="10" />
            <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="10"
                    stroke-dasharray="{283 * (percent/100)} 283"
                    transform="rotate(-90 50 50)" stroke-linecap="round" />
            <text x="50" y="55" text-anchor="middle" font-size="25" font-weight="bold" fill="#333">{int(remaining_time)}</text>
        </svg>
    </div>
    """
    st.markdown(svg_code, unsafe_allow_html=True)

# --- INITIALISATION SESSION STATE ---
if 'current_person' not in st.session_state:
    st.session_state.current_person = None
if 'choices' not in st.session_state:
    st.session_state.choices = []
if 'score' not in st.session_state:
    st.session_state.score = 0
if 'game_phase' not in st.session_state:
    st.session_state.game_phase = "init"
if 'message' not in st.session_state:
    st.session_state.message = ""
if 'start_time' not in st.session_state:
    st.session_state.start_time = 0

# --- LOGIQUE DU JEU ---

def new_round():
    people_list = get_people_from_api()
    
    if not people_list or len(people_list) < 4:
        time.sleep(0.5)
        st.rerun() 
        return

    correct_person = random.choice(people_list)
    correct_gender = correct_person['gender']
    
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
        st.session_state.start_time = time.time()
        st.session_state.message = ""
    else:
        new_round()

def check_answer(selected_person=None, time_out=False):
    if time_out:
        st.session_state.message = f"⏰ TEMPS ÉCOULÉ ! C'était {st.session_state.current_person['name']}"
    elif selected_person['id'] == st.session_state.current_person['id']:
        st.session_state.score += 1
        st.session_state.message = f"✅ BRAVO ! C'est bien {selected_person['name']}"
    else:
        st.session_state.message = f"❌ RATÉ... C'était {st.session_state.current_person['name']}"
    
    st.session_state.game_phase = "resultat"

# --- INTERFACE ---
st.title("🌟 Quiz Célébrités")

st.metric(label="Score", value=st.session_state.score)

if st.session_state.current_person is None and st.session_state.game_phase == "init":
    if st.button("COMMENCER LE JEU", type="primary"):
        new_round()
        st.rerun()

elif st.session_state.game_phase == "question":
    
    # 1. Gestion du Timer
    elapsed_time = time.time() - st.session_state.start_time
    remaining_time = GAME_DURATION - elapsed_time
    
    display_circular_timer(max(0, remaining_time), GAME_DURATION)

    if remaining_time <= 0:
        check_answer(time_out=True)
        st.rerun()

    # 2. Affichage de la photo
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.current_person:
            photo_path = st.session_state.current_person['profile_path']
            st.image(f"{IMAGE_URL}{photo_path}", use_container_width=True)

    # 3. Affichage des choix
    
