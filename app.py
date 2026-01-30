import streamlit as st
import requests
import random

# --- CONFIGURATION ---
# Remplace la clé ci-dessous par la tienne !
API_KEY = "266f486999f6f5487f4ee8f974607538"
BASE_URL = "https://api.themoviedb.org/3"
IMAGE_URL = "https://image.tmdb.org/t/p/w500"

st.set_page_config(page_title="Quiz Célébrités", page_icon="🎬")

# --- FONCTIONS ---
def get_random_page():
    return random.randint(1, 50) # On cherche parmi les 50 pages les plus populaires

def get_people_from_api():
    try:
        page = get_random_page()
        url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page}"
        response = requests.get(url)
        data = response.json()
        
        if "results" in data:
            # On filtre pour n'avoir que ceux qui ont une photo
            valid_people = [p for p in data["results"] if p['profile_path']]
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
    st.session_state.game_phase = "question" # ou "resultat"

def new_round():
    people_list = get_people_from_api()
    if not people_list:
        st.error("Erreur de connexion à TMDB")
        return

    # Choisir la bonne réponse
    correct_person = random.choice(people_list)
    
    # Choisir 3 mauvaises réponses
    others = [p for p in people_list if p['id'] != correct_person['id']]
    wrong_answers = random.sample(others, 3)
    
    # Mélanger le tout
    choices = wrong_answers + [correct_person]
    random.shuffle(choices)
    
    st.session_state.current_person = correct_person
    st.session_state.choices = choices
    st.session_state.game_phase = "question"
    st.session_state.message = ""

def check_answer(selected_person):
    if selected_person['id'] == st.session_state.current_person['id']:
        st.session_state.score += 1
        st.session_state.message = "✅ BRAVO ! C'est bien " + selected_person['name']
    else:
        st.session_state.message = f"❌ RATÉ... C'était {st.session_state.current_person['name']}"
    
    st.session_state.game_phase = "resultat"

# --- INTERFACE ---
st.title("🌟 Quiz Célébrités")
st.write(f"**Score actuel : {st.session_state.score}**")

# Lancer le premier tour si nécessaire
if st.session_state.current_person is None:
    new_round()

# Affichage
if st.session_state.current_person:
    # Afficher l'image
    photo_path = st.session_state.current_person['profile_path']
    st.image(f"{IMAGE_URL}{photo_path}", width=300)

    # Si on est en phase de QUESTION
    if st.session_state.game_phase == "question":
        st.write("### Qui est cette personne ?")
        cols = st.columns(2)
        for i, person in enumerate(st.session_state.choices):
            if cols[i % 2].button(person['name'], use_container_width=True):
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
