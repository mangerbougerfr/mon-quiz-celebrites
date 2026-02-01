import streamlit as st
import requests
import random
import re
import time

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI !!!
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w342" 
GAME_DURATION = 30 
MEMORY_TIME = 60 

st.set_page_config(page_title="Super Quiz", page_icon="🎮", layout="centered")

# --- CSS ---
st.markdown("""
<style>
    .stButton button {
        height: 60px;
        font-size: 18px;
        width: 100%;
        margin-top: 0px;
    }
    /* Force le centrage des images dans leur colonne */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    div[data-testid="stImage"] > img {
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    .found-name {
        color: #00FF00;
        font-weight: bold;
        text-align: center;
        font-size: 13px;
        margin-top: -5px;
    }
    .hidden-img img {
        filter: brightness(0) !important;
        -webkit-filter: brightness(0) !important; 
        pointer-events: none;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    /* Réduire les espaces vides */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 0rem;
    }
    div[data-testid="column"] {
        padding: 0px;
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
        <svg width="60" height="60" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#333" stroke-width="8" />
            <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="8"
                    stroke-dasharray="{283 * (percent/100)} 283"
                    transform="rotate(-90 50 50)" stroke-linecap="round" />
            <text x="50" y="55" text-anchor="middle" font-size="28" font-weight="bold" fill="white">{int(remaining_time)}</text>
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

def get_16_top_stars():
    stars = []
    for page in range(1, 4):
        raw = fetch_popular_people(page)
        for p in raw:
            if (p['profile_path'] and is_latin(p['name']) and 
                p.get('popularity', 0) > 15 and 
                not p.get('adult', False)):
                if p not in stars:
                    stars.append(p)
                if len(stars) == 16:
                    return stars
    return stars

# --- LOGIQUE QUIZ ---
def new_round_celeb():
    page = random.randint(1, 10)
    raw = fetch_popular_people(page)
    valid = [p for p in raw if p['profile_path'] and is_latin(p['name']) and p.get('popularity', 0) > 5]
    if len(valid) < 4: new_round_celeb(); return
    correct = random.choice(valid)
    same_gender = [p for p in valid if p['id'] != correct['id'] and p['gender'] == correct['gender']]
    others = same_gender if len(same_gender) >= 3 else [p for p in valid if p['id'] != correct['id']]
    if len(others) < 3: new_round_celeb(); return
    choices = random.sample(others, 3) + [correct]
    random.shuffle(choices)
    st.session_state.current_item = correct
    st.session_state.current_image = correct['profile_path']
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

def new_round_movie():
    valid = []
    for _ in range(5):
        page = random.randint(1, 20)
        raw = fetch_popular_movies(page)
        valid = [m for m in raw if m['backdrop_path'] and is_latin(m['title'])]
        if len(valid) >= 4: break
    if len(valid) < 4: st.error("Erreur API Films."); return
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

# --- LOGIQUE MÉMOIRE ---
def new_round_memory():
    people = get_16_top_stars()
    if len(people) < 16: st.error("Pas assez de stars."); return
    random.shuffle(people)
    st.session_state.memory_people = people
    st.session_state.memory_found = []
    st.session_state.game_phase = "memorize"
    st.session_state.start_time = time.time()
    st.session_state.input_memory = ""

def check_memory_input():
    user_text = st.session_state.input_memory.strip().lower()
    found_new = False
    for p in st.session_state.memory_people:
        if p['id'] not in st.session_state.memory_found:
            names_parts = p['name'].lower().replace("-", " ").split()
            if user_text in names_parts and len(user_text) > 2:
                st.session_state.memory_found.append(p['id'])
                st.session_state.score += 1
                found_new = True
    if found_new: st.toast(f"✅ Trouvé : {user_text}", icon="🎉")
    st.session_state.input_memory = ""

# --- STATE ---
if 'score' not in st.session_state: st.session_state.score = 0
if 'game_phase' not in st.session_state: st.session_state.game_phase = "init"
if 'game_mode' not in st.session_state: st.session_state.game_mode = "Célébrités"
if 'current_item' not in st.session_state: st.session_state.current_item = None
if 'current_image' not in st.session_state: st.session_state.current_image = None
if 'choices' not in st.session_state: st.session_state.choices = []
if 'message' not in st.session_state: st.session_state.message = ""
if 'start_time' not in st.session_state: st.session_state.start_time = 0
if 'memory_people' not in st.session_state: st.session_state.memory_people = []
if 'memory_found' not in st.session_state: st.session_state.memory_found = []

# --- INTERFACE ---
st.sidebar.title("Menu")
selected_mode = st.sidebar.radio("Jeu :", ["Célébrités", "Films", "Mémoire (16 Visages)"])

if selected_mode != st.session_state.game_mode:
    st.session_state.game_mode = selected_mode
    st.session_state.game_phase = "init"
    st.session_state.score = 0
    st.rerun()

st.title(f"🌟 {st.session_state.game_mode}")

if st.session_state.game_mode == "Mémoire (16 Visages)" and st.session_state.game_phase == "recall":
    st.metric("Score", f"{len(st.session_state.memory_found)} / 16")
elif st.session_state.game_mode != "Mémoire (16 Visages)":
    st.metric("Score", st.session_state.score)

# 1. ACCUEIL
if st.session_state.game_phase == "init":
    if st.button("LANCER LE JEU", type="primary"):
        if st.session_state.game_mode == "Célébrités": new_round_celeb()
        elif st.session_state.game_mode == "Films": new_round_movie()
        else: new_round_memory()
        st.rerun()

# ---------------------------------------------------------
# JEU MÉMOIRE (IMAGES RÉDUITES)
# ---------------------------------------------------------
elif st.session_state.game_mode == "Mémoire (16 Visages)":
    
    # PHASE MEMO
    if st.session_state.game_phase == "memorize":
        elapsed = time.time() - st.session_state.start_time
        remaining = MEMORY_TIME - elapsed
        st.write(f"### 🧠 Mémorise ! ({int(remaining)}s)")
        st.progress(max(0, remaining / MEMORY_TIME))
        
        people = st.session_state.memory_people
        for i in range(0, 16, 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(people):
                    p = people[i+j]
                    with cols[j]:
                        # WIDTH=115 pour réduire la taille dans la grille
                        st.image(f"{IMAGE_URL}{p['profile_path']}", width=115)
                        st.caption(p['name'])
        
        if remaining <= 0:
            st.session_state.game_phase = "recall"
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()

    # PHASE DEVINETTE
    elif st.session_state.game_phase == "recall":
        st.text_input("Qui as-tu vu ?", key="input_memory", on_change=check_memory_input)
        st.write("---")
        people = st.session_state.memory_people
        
        for i in range(0, 16, 4):
            cols = st.columns(4)
            for j in range(4):
                if i + j < len(people):
                    p = people[i+j]
                    with cols[j]:
                        if p['id'] in st.session_state.memory_found:
                            st.image(f"{IMAGE_URL}{p['profile_path']}", width=115)
                            st.markdown(f"<div class='found-name'>{p['name']}</div>", unsafe_allow_html=True)
                        else:
                            st.markdown(
                                f"""<div class="hidden-img" style="display:flex; justify-content:center;">
                                    <img src="{IMAGE_URL}{p['profile_path']}" style="width:115px; border-radius: 5px;">
                                </div>""", 
                                unsafe_allow_html=True
                            )
        
        if len(st.session_state.memory_found) == 16:
            st.balloons()
            st.success("BRAVO !")
            if st.button("Rejouer"):
                new_round_memory()
                st.rerun()

# ---------------------------------------------------------
# JEUX QUIZ (IMAGES CENTRÉES)
# ---------------------------------------------------------
elif st.session_state.game_phase == "question":
    
    if st.session_state.game_mode == "Célébrités":
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(max(0, remaining), GAME_DURATION)
        if remaining <= 0: check_answer(None, time_out=True); st.rerun()

        # CENTRAGE : On utilise 3 colonnes et on met l'image au milieu
        c_left, c_center, c_right = st.columns([1, 2, 1])
        with c_center:
             # Width 300 pour portrait
            st.image(f"https://image.tmdb.org/t/p/w500{st.session_state.current_image}", width=300)

    else: # Films
        # CENTRAGE : Idem
        c_left, c_center, c_right = st.columns([1, 6, 1]) # Colonne milieu plus large pour film
        with c_center:
            # Width 500 pour film
            st.image(f"https://image.tmdb.org/t/p/w780{st.session_state.current_image}", width=500)

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

    if st.session_state.game_mode == "Célébrités":
        time.sleep(1)
        st.rerun()

elif st.session_state.game_phase == "resultat":
    item = st.session_state.current_item
    
    # CENTRAGE RÉSULTAT AUSSI
    c_left, c_center, c_right = st.columns([1, 2, 1])
    with c_center:
        if st.session_state.game_mode == "Célébrités":
            st.image(f"https://image.tmdb.org/t/p/w500{item['profile_path']}", width=200)
        else:
            st.image(f"https://image.tmdb.org/t/p/w780{item['backdrop_path']}", width=400)

    if "✅" in st.session_state.message: st.success(st.session_state.message)
    elif "⏰" in st.session_state.message: st.warning(st.session_state.message)
    else: st.error(st.session_state.message)
    
    if st.button("Question Suivante ➡️", type="primary"):
        if st.session_state.game_mode == "Célébrités": new_round_celeb()
        else: new_round_movie()
        st.rerun()
