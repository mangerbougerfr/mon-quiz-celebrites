import streamlit as st
import requests
import random
import re # Pour analyser le texte (alphabet latin)

# --- CONFIGURATION ---
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <--- REMETS TA CLÉ ICI
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Quiz Célébrités", page_icon="🎬", layout="centered")

# --- FONCTIONS ---
def is_latin(text):
    # Vérifie si le texte contient uniquement des lettres latines (et accents courants)
    # Cela exclut le chinois, coréen, etc.
    return bool(re.match(r'^[a-zA-Zà-üÀ-Ü\s\-\.\']+$', text))

def get_random_page():
    return random.randint(1, 50)

def get_people_from_api():
    try:
        page = get_random_page()
        # On demande la région FR pour maximiser les chances d'avoir des noms latins
        url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page}"
        response = requests.get(url)
        data = response.json()
        
        valid_people = []
        if "results" in data:
            for p in data["results"]:
                # 1. On vérifie qu'il y a une photo
                # 2. On vérifie que le nom est bien en alphabet latin
                if p['profile_path'] and is_latin(p['name']):
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
    
    # Sécurité : si la liste est vide ou trop petite, on recommence
    if not people_list or len(people_list) < 4:
        st.warning("Recherche de célébrités...")
        new_round() 
        return

    # Choisir la bonne réponse
    correct_person = random.choice(people_list)
    correct_gender = correct_person['gender'] # 1 = Femme, 2 = Homme
    
    # Filtrer les mauvaises réponses pour qu'elles aient le MÊME GENRE
    same_gender_people = [p for p in people_list if p['id'] != correct_person['id'] and p['gender'] == correct_gender]
    
    # S'il n'y a pas assez de gens du même genre, on prend n'importe qui (rare)
    if len(same_gender_people) < 3:
        others = [p for p in people_list if p['id'] != correct_person['id']]
    else:
        others = same_gender_people

    # Choisir 3 perdants
    if len(others) >= 3:
        wrong_answers = random.sample(others, 3)
        choices = wrong_answers + [correct_person]
        random.shuffle(choices)
        
        st.session_state.current_person = correct_person
        st.session_state.choices = choices
        st.session_state.game_phase = "question"
        st.session_state.message = ""
    else:
        new_round() # On relance si pas assez de choix

def check_answer(selected_person):
    if selected_person['id'] == st.session_state.current_person['id']:
        st.session_state.score += 1
        st.session_state.message = f"✅ BRAVO ! C'est bien {selected_person['name']}"
    else:
        st.session_state.message = f"❌ RATÉ... C'était {st.session_state.current_person['name']}"
    
    st.session_state.game_phase = "resultat"

# --- INTERFACE ---
st.title("🌟 Quiz Célébrités")
st.write(f"**Score : {st.session_state.score}**")

# Lancer le premier tour
if st.session_state.current_person is None:
    new_round()

if st.session_state.current_person:
    # 2. CENTRAGE DE L'IMAGE : On utilise des colonnes
    col1, col2, col3 = st.columns([1, 2, 1]) # La colonne du milieu est plus large (2)
    
    with col2:
        photo_path = st.session_state.current_person['profile_path']
        st.image(f"{IMAGE_URL}{photo_path}", use_container_width=True)

    # Si on est en phase de QUESTION
    if st.session_state.game_phase == "question":
        st.write("### Qui est cette personne ?")
        
        # Affichage des boutons en grille (2x2)
        c1, c2 = st.columns(2)
        for i, person in enumerate(st.session_state.choices):
            # On met les boutons 0 et 1 dans la colonne 1, les 2 et 3 dans la colonne 2
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

    # Si on est en phase de RÉSULTAT
    else:
        if "✅" in st.session_state.message:
            st.success(st.session_state.message)
        else:
            st.error(st.session_state.message)
        
        if st.button("Question Suivante ➡️", type="primary"):
            new_round()
            st.rerun()
