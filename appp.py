import streamlit as st
import requests
import random
import re
import time

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI !!!
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w780"
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
    try:
        url = f"{BASE_URL}/movie/{movie_id}/images?api_key={API_KEY}"
        data = requests.get(url).json()
        if "backdrops" in data and len(data["backdrops"]) > 0:
            textless = [img for img in data["backdrops"] if img['iso_639_1'] is None]
            if textless: return random.choice(textless)["file_path"]
            elif len(data["backdrops"]) > 1: return random.choice(data["backdrops"][1:])["file_path"]
    except: pass
    return default_path

# --- LOGIQUE JEU ---
def new_round_celeb():
    page = random.randint(1, 10)
    raw = fetch_popular_people(page)
    valid = [p for p in raw if p['profile_path'] and is_latin(p['name']) and p.get('popularity', 0) > 5]
    
    if len(valid) < 4:
        st.warning("Pas assez de célébrités trouvées, réessaie.")
        return

    correct = random.choice(valid)
    same_gender = [p for p in valid if p['id'] != correct['id'] and p['gender'] == correct['gender']]
    others = same_gender if len(same_gender) >= 3 else [p for p in valid if p['id'] != correct['id']]
    
    if len(others) < 3:
        new_round_celeb() # Retry simple
        return

    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    
    st.session_state.current_item = correct
    st.session_state.current_image = correct['profile_path']
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

def new_round_movie():
    # Retry loop pour trouver des films valides
    valid = []
    for _ in range(5):
        page = random.randint(1, 20)
        raw = fetch_popular_movies(page)
        valid = [m for m in raw if m['backdrop_path'] and is_latin(m['title'])]
        if len(valid) >= 4: break
    
    if len(valid) < 4:
        st.error("Impossible de charger les films. Vérifie ta connexion ou ta clé API.")
        return

    correct = random.choice(valid)
    others = [m for m in valid if m['id'] != correct['id']]
    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    
    scene_image = get_random_scene_image(correct['id'], correct['backdrop_path'])
    
    st.session_state.current_item = correct
    st.session_state.current_image = scene_image
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.message = ""

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

# 1. ÉCRAN D'ACCUEIL
if st.session_state.game_phase == "init":
    if st.button("LANCER LE JEU", type="primary"):
        if st.session_state.game_mode == "Célébrités":
            new_round_celeb()
        else:
            new_round_movie()
        st.rerun()

# 2. PHASE DE QUESTION
elif st.session_state.game_phase == "question":
    
    # --- AFFICHAGE SPÉCIFIQUE CÉLÉBRITÉS ---
    if st.session_state.game_mode == "Célébrités":
        # Calcul du Timer
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(max(0, remaining), GAME_DURATION)
        
        # Vérification fin du temps
        if remaining <= 0:
            check_answer(None, time_out=True)
            st.rerun()
            
        # Image (Format Portrait centré)
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.image(f"{IMAGE_URL}{st.session_state.current_image}", use_container_width=True)

    # --- AFFICHAGE SPÉCIFIQUE FILMS ---
    else:
        # Pas de Timer, juste l'image (Format Paysage)
        if st.session_state.current_image:
            st.image(f"{IMAGE_URL}{st.session_state.current_image}", use_container_width=True)
        else:
            st.error("Erreur d'affichage de l'image.")

    # --- BOUTONS DE RÉPONSE (COMMUN) ---
    st.write("### Qui est-ce ?" if st.session_state.game_mode == "Célébrités" else "### Quel est ce film ?")
    
    c1, c2 = st.columns(2)
    name_key = 'title' if st.session_state.game_mode == "Films" else 'name'
    
    if st.session_state.choices:
        for i, choice in enumerate(st.session_state.choices):
            col = c1 if i < 2 else c2
            with col:
                if st.button(choice[name_key], key=f"btn_{choice['id']}", use_container_width=True):
                    check_answer(choice)
                    st.rerun()

    # --- RAFRAICHISSEMENT AUTOMATIQUE (UNIQUEMENT POUR LE TIMER) ---
    if st.session_state.game_mode == "Célébrités":
        time.sleep(1)
        st.rerun()

# 3. PHASE RÉSULTAT
elif st.session_state.game_phase == "resultat":
    item = st.session_state.current_item
    
    if st.session_state.game_mode == "Célébrités":
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image(f"{IMAGE_URL}{item['profile_path']}", width=150)
    else:
        # Affiche l'image de fond principale (souvent avec le titre) pour la réponse
        st.image(f"{IMAGE_URL}{item['backdrop_path']}", use_container_width=True)

    if "✅" in st.session_state.message:
        st.success(st.session_state.message)
    elif "⏰" in st.session_state.message:
        st.warning(st.session_state.message)
    else:
        st.error(st.session_state.message)
    
    if st.button("Question Suivante ➡️", type="primary"):
        if st.session_state.game_mode == "Célébrités":
            new_round_celeb()
        else:
            new_round_movie()
        st.rerun()
