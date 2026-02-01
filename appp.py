import streamlit as st
import requests
import random
import re
import time

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI !!!
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w780" # Bonne qualité
GAME_DURATION = 30 

st.set_page_config(page_title="Super Quiz", page_icon="🎮", layout="centered")

# --- CSS ---
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
</style>
""", unsafe_allow_html=True)

# --- UTILITAIRES ---
def is_latin(text):
    return bool(re.match(r'^[a-zA-Zà-üÀ-Ü0-9\s\-\.\':]+$', text))

def display_circular_timer(remaining_time, total_time):
    percent = (remaining_time / total_time) * 100
    if remaining_time > 15: color = "#4CAF50"
    elif remaining_time > 5: color = "#FFC107"
    else: color = "#F44336"

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

# --- FONCTIONS API ---
@st.cache_data(ttl=3600)
def fetch_popular_people(page_num):
    try:
        url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page_num}"
        return requests.get(url).json().get("results", [])
    except: return []

@st.cache_data(ttl=3600)
def fetch_popular_movies(page_num):
    try:
        url = f"{BASE_URL}/movie/popular?api_key={API_KEY}&language=fr-FR&page={page_num}"
        return requests.get(url).json().get("results", [])
    except: return []

def get_random_scene_image(movie_id, default_path):
    """
    Va chercher les images et filtre celles qui contiennent du texte (titre).
    """
    try:
        # On récupère toutes les images du film
        url = f"{BASE_URL}/movie/{movie_id}/images?api_key={API_KEY}"
        data = requests.get(url).json()
        
        if "backdrops" in data and len(data["backdrops"]) > 0:
            # FILTRE MAGIQUE :
            # On ne garde que les images où iso_639_1 est None (pas de langue spécifiée)
            # Les images avec 'en', 'fr', etc. ont souvent le titre écrit dessus.
            textless_scenes = [img for img in data["backdrops"] if img['iso_639_1'] is None]
            
            if textless_scenes:
                # On en prend une au hasard parmi les "propres"
                return random.choice(textless_scenes)["file_path"]
            
            # Si vraiment on a que des images avec du texte (rare), on évite au moins la première
            elif len(data["backdrops"]) > 1:
                return random.choice(data["backdrops"][1:])["file_path"]
                
    except:
        pass
    
    return default_path

# --- LOGIQUE CÉLÉBRITÉS ---
def new_round_celeb():
    page = random.randint(1, 10)
    raw = fetch_popular_people(page)
    
    valid = [p for p in raw if p['profile_path'] and is_latin(p['name']) and p.get('popularity', 0) > 5]
    
    if len(valid) < 4:
        new_round_celeb()
        return

    correct = random.choice(valid)
    same_gender = [p for p in valid if p['id'] != correct['id'] and p['gender'] == correct['gender']]
    others = same_gender if len(same_gender) >= 3 else [p for p in valid if p['id'] != correct['id']]
    
    if len(others) < 3:
        new_round_celeb()
        return

    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    
    st.session_state.current_item = correct
    st.session_state.current_image = correct['profile_path']
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

# --- LOGIQUE FILMS ---
def new_round_movie():
    # Pages 1 à 20 (Populaires)
    for _ in range(5):
        page = random.randint(1, 20) 
        raw = fetch_popular_movies(page)
        valid = [m for m in raw if m['backdrop_path'] and is_latin(m['title'])]
        if len(valid) >= 4:
            break
    else:
        st.error("Erreur API Films.")
        return

    correct = random.choice(valid)
    others = [m for m in valid if m['id'] != correct['id']]
    
    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    
    # Appel de la fonction filtrée sans texte
    scene_image = get_random_scene_image(correct['id'], correct['backdrop_path'])
    
    st.session_state.current_item = correct
    st.session_state.current_image = scene_image
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.message = ""

# --- GESTION RÉPONSE ---
def check_answer(selected, time_out=False):
    is_movie = st.session_state.game_mode == "Films"
    name_key = 'title' if is_movie else 'name'
    
    if time_out:
        st.session_state.message = f"⏰ TEMPS ÉCOULÉ ! C'était {st.session_state.current_item[name_key]}"
    elif selected['id'] == st.session_state.current_item['id']:
        st.session_state.score += 1
        st.session_state.message = f"✅ BRAVO ! C'est bien {selected[name_key]}"
    else:
        st.session_state.message = f"❌ RATÉ... C'était {st.session_state.current_item[name_key]}"
    
    st.session_state.game_phase = "resultat"

# --- STATE ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'game_phase' not in st.session_state: st.session_state.game_phase = "init"
if 'game_mode' not in st.session_state: st.session_state.game_mode = "Célébrités"
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_image' not in st.session_state: st.session_state.current_image = None
if 'choices' not in st.session_state: st.session_state.choices = []
if 'message' not in st.session_state: st.session_state.message = ""
if 'start_time' not in st.session_state: st.session_state.start_time = 0

# --- INTERFACE ---
st.sidebar.title("Menu")
selected_mode = st.sidebar.radio("Choisis ton jeu :", ["Célébrités", "Films"])

if selected_mode != st.session_state.game_mode:
    st.session_state.game_mode = selected_mode
    st.session_state.game_phase = "init"
    st.session_state.score = 0
    st.rerun()

st.title(f"🌟 Quiz {st.session_state.game_mode}")
st.metric(label="Score", value=st.session_state.score)

# 1. INIT
if st.session_state.game_phase == "init":
    if st.button("LANCER LE JEU", type="primary"):
        if st.session_state.game_mode == "Célébrités":
            new_round_celeb()
        else:
            new_round_movie()
        st.rerun()

# 2. QUESTION
elif st.session_state.game_phase == "question":
    
    if st.session_state.game_mode == "Célébrités":
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(max(0, remaining), GAME_DURATION)
        if remaining <= 0:
            check_answer(None, time_out=True)
            st.rerun()

    if st.session_state.current_image:
        if st.session_state.game_mode == "Célébrités":
            col1, col2, col3 = 
