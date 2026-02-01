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

st.set_page_config(page_title="Quiz Célébrités", page_icon="🎬", layout="centered")

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

# --- FONCTIONS ---
def is_latin(text):
    return bool(re.match(r'^[a-zA-Zà-üÀ-Ü\s\-\.\']+$', text))

# On utilise le cache pour éviter de rappeler l'API quand le timer tourne
@st.cache_data(ttl=3600)
def fetch_people_from_page(page_num):
    try:
        url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page_num}"
        response = requests.get(url)
        data = response.json()
        if "results" in data:
            return data["results"]
        return []
    except:
        return []

def get_valid_people():
    # On essaie de trouver des gens valides sur 3 pages aléatoires différentes
    # pour éviter de tourner en rond si une page est vide
    for _ in range(3):
        page = random.randint(1, 10) # Top 10 des pages pour avoir des gens connus
        raw_people = fetch_people_from_page(page)
        
        valid_people = []
        for p in raw_people:
            # Filtres : Photo + Nom Latin + Popularité décente
            if (p['profile_path'] and 
                is_latin(p['name']) and 
                p.get('popularity', 0) > 5): # J'ai baissé un peu la sévérité
                valid_people.append(p)
        
        if len(valid_people) >= 4:
            return valid_people
            
    return []

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

# --- ETAT DU JEU ---
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

# --- MOTEUR DU JEU ---
def new_round():
    people_list = get_valid_people()
    
    if not people_list or len(people_list) < 4:
        st.error("Erreur de connexion API ou pas assez de résultats. Vérifie ta clé API.")
        st.stop() # Arrête le script ici pour éviter la boucle infinie
        return

    correct_person = random.choice(people_list)
    correct_gender = correct_person['gender']
    
    same_gender_people = [p for p in people_list if p['id'] != correct_person['id'] and p['gender'] == correct_gender]
    others = same_gender_people if len(same_gender_people) >= 3 else [p for p in people_list if p['id'] != correct_person['id']]

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
        st.warning("Pas assez de données pour générer une question cohérente. Réessaie.")

def check_answer(selected_person=None, time_out=False):
    if time_out:
        st.session_state.message = f"⏰ TEMPS ÉCOULÉ ! C'était {st.session_state.current_person['name']}"
    elif selected_person['id'] == st.session_state.current_person['id']:
        st.session_state.score += 1
        st.session_state.message = f"✅ BRAVO ! C'est bien {selected_person['name']}"
    else:
        st.session_state.message = f"❌ RATÉ... C'était {st.session_state.current_person['name']}"
    
    st.session_state.game_phase = "resultat"

# --- AFFICHAGE ---
st.title("🌟 Quiz Célébrités")
st.metric(label="Score", value=st.session_state.score)

# 1. ÉCRAN D'ACCUEIL
if st.session_state.game_phase == "init":
    if st.button("COMMENCER LE JEU", type="primary"):
        new_round()
        st.rerun()

# 2. QUESTION
elif st.session_state.game_phase == "question":
    
    # Calcul du temps
    elapsed = time.time() - st.session_state.start_time
    remaining = GAME_DURATION - elapsed
    
    # Affiche le timer
    display_circular_timer(max(0, remaining), GAME_DURATION)
    
    # Vérifie si temps écoulé
    if remaining <= 0:
        check_answer(time_out=True)
        st.rerun()

    # Affiche l'image
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.session_state.current_person:
            p_path = st.session_state.current_person['profile_path']
            st.image(f"{IMAGE_URL}{p_path}", use_container_width=True)

    st.write("### Qui est cette personne ?")
    
    # Affiche les boutons
    if st.session_state.choices:
        c1, c2 = st.columns(2)
        for i, person in enumerate(st.session_state.choices):
            col = c1 if i < 2 else c2
            with col:
                # IMPORTANT: On met une clé unique basée sur l'ID de la personne pour éviter les confusions
                if st.button(person['name'], key=f"btn_{person['id']}", use_container_width=True):
                    check_answer(person)
                    st.rerun()
    
    # Boucle de rafraichissement (placée à la toute fin)
    if remaining > 0:
        time.sleep(1)
        st.rerun()

# 3. RÉSULTAT
elif st.session_state.game_phase == "resultat":
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        p_path = st.session_state.current_person['profile_path']
        st.image(f"{IMAGE_URL}{p_path}", width=150)

    if "✅" in st.session_state.message:
        st.success(st.session_state.message)
    elif "⏰" in st.session_state.message:
        st.warning(st.session_state.message)
    else:
        st.error(st.session_state.message)
    
    if st.button("Question Suivante ➡️", type="primary"):
        new_round()
        st.rerun()
