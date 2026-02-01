import streamlit as st
import requests
import random
import re
import time

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI !!!
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"
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

# --- FONCTIONS UTILITAIRES ---
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

# --- FONCTIONS API (CACHE) ---
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

# --- LOGIQUE CÉLÉBRITÉS ---
def get_valid_people():
    for _ in range(3):
        page = random.randint(1, 10)
        raw = fetch_popular_people(page)
        valid = [p for p in raw if p['profile_path'] and is_latin(p['name']) and p.get('popularity', 0) > 5]
        if len(valid) >= 4: return valid
    return []

def new_round_celeb():
    people = get_valid_people()
    if not people or len(people) < 4:
        st.error("Erreur API Célébrités.")
        return

    correct = random.choice(people)
    same_gender = [p for p in people if p['id'] != correct['id'] and p['gender'] == correct['gender']]
    others = same_gender if len(same_gender) >= 3 else [p for p in people if p['id'] != correct['id']]
    
    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    
    st.session_state.current_item = correct
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

# --- LOGIQUE FILMS ---
def get_valid_movies():
    for _ in range(3):
        page = random.randint(1, 20) # Plus large choix de films
        raw = fetch_popular_movies(page)
        # On veut des films avec une image de fond (backdrop) car l'affiche contient le titre !
        valid = [m for m in raw if m['backdrop_path'] and is_latin(m['title'])]
        if len(valid) >= 4: return valid
    return []

def new_round_movie():
    movies = get_valid_movies()
    if not movies or len(movies) < 4:
        st.error("Erreur API Films.")
        return

    correct = random.choice(movies)
    others = [m for m in movies if m['id'] != correct['id']]
    
    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    
    st.session_state.current_item = correct
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.message = ""
    # Pas de timer pour l'instant pour les films

# --- GESTION DE LA RÉPONSE (COMMUNE) ---
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

# --- INITIALISATION SESSION ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'game_phase' not in st.session_state: st.session_state.game_phase = "init"
if 'game_mode' not in st.session_state: st.session_state.game_mode = "Célébrités"
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'choices' not in st.session_state: st.session_state.choices = []
if 'message' not in st.session_state: st.session_state.message = ""
if 'start_time' not in st.session_state: st.session_state.start_time = 0

# --- INTERFACE ---
st.sidebar.title("Menu")
selected_mode = st.sidebar.radio("Choisis ton jeu :", ["Célébrités", "Films"])

# Reset si on change de mode
if selected_mode != st.session_state.game_mode:
    st.session_state.game_mode = selected_mode
    st.session_state.game_phase = "init"
    st.session_state.score = 0 # On remet le score à 0 si on change de jeu
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
    
    # Gestion Timer (Seulement pour Célébrités)
    if st.session_state.game_mode == "Célébrités":
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(max(0, remaining), GAME_DURATION)
        if remaining <= 0:
            check_answer(None, time_out=True)
            st.rerun()

    # Affichage Image
    item = st.session_state.current_item
    if item:
        if st.session_state.game_mode == "Célébrités":
            # Image verticale (Portrait)
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image(f"{IMAGE_URL}{item['profile_path']}", use_container_width=True)
        else:
            # Image horizontale (Paysage/Backdrop) pour les films
            st.image(f"{IMAGE_URL}{item['backdrop_path']}", use_container_width=True)

    st.write("### Qui est-ce ?" if st.session_state.game_mode == "Célébrités" else "### Quel est ce film ?")
    
    # Choix
    c1, c2 = st.columns(2)
    name_key = 'title' if st.session_state.game_mode == "Films" else 'name'
    
    for i, choice in enumerate(st.session_state.choices):
        col = c1 if i < 2 else c2
        with col:
            if st.button(choice[name_key], key=f"btn_{choice['id']}", use_container_width=True):
                check_answer(choice)
                st.rerun()
    
    # Rafraichissement Timer (Seulement Célébrités)
    if st.session_state.game_mode == "Célébrités":
        time.sleep(1)
        st.rerun()

# 3. RÉSULTAT
elif st.session_state.game_phase == "resultat":
    item = st.session_state.current_item
    
    if st.session_state.game_mode == "Célébrités":
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image(f"{IMAGE_URL}{item['profile_path']}", width=150)
    else:
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
