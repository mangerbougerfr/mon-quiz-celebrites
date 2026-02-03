import streamlit as st
import requests
import random
import re
import time
import unicodedata

# -----------------------------
# CONFIG
# -----------------------------
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <-- Mets ta clé TMDB ici
BASE_URL = "https://api.themoviedb.org/3"

# Images (TMDB)
IMG_PERSON_GRID = "https://image.tmdb.org/t/p/w342"   # mémoire (petit)
IMG_PERSON_QUIZ = "https://image.tmdb.org/t/p/w500"   # quiz célébrités
IMG_MOVIE = "https://image.tmdb.org/t/p/w780"         # quiz films

GAME_DURATION = 30          # timer célébrités
MEMORY_TIME = 60            # mémorisation mémoire

st.set_page_config(page_title="Super Quiz", page_icon="🎬", layout="centered")

# -----------------------------
# CSS
# -----------------------------
st.markdown("""
<style>
    .stButton button {
        height: 58px;
        font-size: 18px;
        width: 100%;
    }

    /* Centrage images dans colonnes */
    div[data-testid="stImage"] {
        display: flex;
        justify-content: center;
    }
    div[data-testid="stImage"] > img {
        display: block;
        margin-left: auto;
        margin-right: auto;
        object-fit: cover;
    }

    .found-name {
        color: #00C853;
        font-weight: 700;
        text-align: center;
        font-size: 13px;
        margin-top: -6px;
        margin-bottom: 12px;
    }

    .missed-name {
        color: #FF5252;
        font-weight: 700;
        text-align: center;
        font-size: 13px;
        margin-top: -6px;
        margin-bottom: 12px;
    }

    .hidden-img img {
        filter: brightness(0) !important;
        -webkit-filter: brightness(0) !important;
        pointer-events: none;
        display: block;
        margin-left: auto;
        margin-right: auto;
        border-radius: 8px;
    }

    .tiny-btn button {
        height: 34px !important;
        font-size: 14px !important;
        margin-top: 6px !important;
        background: #262626 !important;
        border: 1px solid #3a3a3a !important;
    }

    .block-container {
        padding-top: 1rem;
        padding-bottom: 1rem;
    }
    div[data-testid="column"] {
        padding: 0px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Utils
# -----------------------------
def is_latin(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Zà-üÀ-Ü0-9\s\-\.\':]+$", text or ""))

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join([c for c in s if not unicodedata.combining(c)])
    s = re.sub(r"[^a-z0-9\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tmdb_get(url: str, timeout: int = 10):
    try:
        r = requests.get(url, timeout=timeout)
        return r.json()
    except Exception:
        return {}

# Timer circulaire
def display_circular_timer(remaining_time, total_time):
    remaining_time = max(0, remaining_time)
    percent = (remaining_time / total_time) * 100 if total_time else 0

    if remaining_time > 15:
        color = "#2ecc71"  # vert
    elif remaining_time > 10:
        color = "#f1c40f"  # jaune
    elif remaining_time > 5:
        color = "#e67e22"  # orange
    else:
        color = "#e74c3c"  # rouge

    svg_code = f"""
    <div style="display:flex; justify-content:center; margin-bottom: 8px;">
        <svg width="64" height="64" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#333" stroke-width="8" />
            <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="8"
                    stroke-dasharray="{283 * (percent/100)} 283"
                    transform="rotate(-90 50 50)" stroke-linecap="round" />
            <text x="50" y="56" text-anchor="middle" font-size="30" font-weight="700" fill="white">{int(remaining_time)}</text>
        </svg>
    </div>
    """
    st.markdown(svg_code, unsafe_allow_html=True)

# -----------------------------
# TMDB cache (pages)
# -----------------------------
@st.cache_data(ttl=24 * 3600)
def fetch_people_page(page_num: int):
    url = f"{BASE_URL}/person/popular?api_key={API_KEY}&language=fr-FR&page={page_num}"
    return tmdb_get(url).get("results", [])

@st.cache_data(ttl=6 * 3600)
def fetch_movies_page(page_num: int):
    url = f"{BASE_URL}/movie/popular?api_key={API_KEY}&language=fr-FR&page={page_num}"
    return tmdb_get(url).get("results", [])

@st.cache_data(ttl=24 * 3600)
def fetch_movie_images(movie_id: int):
    url = f"{BASE_URL}/movie/{movie_id}/images?api_key={API_KEY}"
    return tmdb_get(url)

def get_random_scene_image(movie_id: int, default_path: str) -> str:
    data = fetch_movie_images(movie_id)
    backdrops = data.get("backdrops", []) or []
    # on privilégie les backdrops "sans langue" (souvent sans texte)
    textless = [b for b in backdrops if b.get("iso_639_1") is None]
    if len(textless) >= 1:
        return random.choice(textless).get("file_path", default_path)
    # sinon, on évite la toute première si possible
    if len(backdrops) > 1:
        return random.choice(backdrops[1:]).get("file_path", default_path)
    return default_path

# -----------------------------
# MEMORY MODE: pool + tirage
# -----------------------------
@st.cache_data(ttl=24 * 3600)
def build_star_pool(pages: int = 30):
    """
    Construit une pool de célébrités populaires.
    -> On filtre Acting + photo + latin.
    -> On trie par popularité, puis on garde une tranche assez grande pour varier.
    """
    pool = []
    seen = set()

    for page in range(1, pages + 1):
        raw = fetch_people_page(page)
        for p in raw:
            pid = p.get("id")
            name = p.get("name", "")
            if not pid or pid in seen:
                continue
            if not p.get("profile_path"):
                continue
            if p.get("known_for_department") != "Acting":
                continue
            if p.get("adult", False):
                continue
            if not is_latin(name):
                continue

            seen.add(pid)
            pool.append(p)

    pool.sort(key=lambda x: x.get("popularity", 0), reverse=True)

    # Filtre "stars vraiment connues" : on garde d'abord celles au-dessus d'un seuil
    # (mais on garde quand même assez de monde pour varier).
    def keep_with_threshold(th):
        return [p for p in pool if p.get("popularity", 0) >= th]

    for th in [35, 30, 25, 20]:
        subset = keep_with_threshold(th)
        if len(subset) >= 120:
            return subset[:350]

    # secours
    return pool[:300]

def pick_16_random_stars():
    """
    Tire 16 personnes au hasard dans la pool, en évitant de refaire exactement la même liste.
    """
    pool = build_star_pool(pages=30)
    if len(pool) < 16:
        return []

    rng = random.SystemRandom()
    last_ids = set(st.session_state.get("memory_last_ids", []))

    best = None
    best_new = -1

    for _ in range(30):
        sample = rng.sample(pool, 16)
        ids = {p["id"] for p in sample}
        new_count = len(ids - last_ids)
        if new_count > best_new:
            best_new = new_count
            best = sample
        if new_count >= 12:
            break

    st.session_state.memory_last_ids = [p["id"] for p in best]
    return best

def start_memory_round():
    """
    Nouvelle manche mémoire :
    - génère un nouvel input key (évite les bugs Streamlit)
    - tire 16 nouvelles stars
    - passe en phase 'memorize'
    """
    st.session_state.memory_round_id += 1
    st.session_state.memory_input_key = f"mem_input_{st.session_state.memory_round_id}"

    people = pick_16_random_stars()
    if len(people) < 16:
        st.session_state.memory_people = []
        st.error("Impossible de générer 16 célébrités (pool trop petite).")
        return

    st.session_state.memory_people = people
    st.session_state.memory_found = []
    st.session_state.memory_revealed_faces = []
    st.session_state.show_solution = False
    st.session_state.phase = "memorize"
    st.session_state.start_time = time.time()

def reveal_face(person_id: int):
    if person_id not in st.session_state.memory_revealed_faces:
        st.session_state.memory_revealed_faces.append(person_id)

def check_memory_input():
    key = st.session_state.memory_input_key
    raw_text = st.session_state.get(key, "")
    text = normalize_text(raw_text)
    if not text:
        return

    # Permet de taper plusieurs réponses séparées par virgule / retour ligne / ;
    guesses = [normalize_text(x) for x in re.split(r"[,\n;]+", raw_text) if normalize_text(x)]

    found_any = False

    for guess in guesses:
        for p in st.session_state.memory_people:
            if p["id"] in st.session_state.memory_found:
                continue

            full = normalize_text(p["name"])
            parts = set(full.replace("-", " ").split())

            # accepte:
            # - prénom OU nom exact (token)
            # - nom complet exact
            if (guess in parts and len(guess) > 2) or (guess == full and len(guess) > 2):
                st.session_state.memory_found.append(p["id"])
                found_any = True

    if found_any:
        st.toast("Réponse validée")

    # reset input
    st.session_state[key] = ""

# -----------------------------
# QUIZ: célébrités
# -----------------------------
def get_valid_people_for_quiz():
    # pages 1..20 pour avoir beaucoup de connus
    for _ in range(6):
        page = random.randint(1, 20)
        raw = fetch_people_page(page)
        valid = []
        for p in raw:
            if not p.get("profile_path"):
                continue
            if not is_latin(p.get("name", "")):
                continue
            if p.get("adult", False):
                continue
            if p.get("popularity", 0) < 8:
                continue
            valid.append(p)
        if len(valid) >= 8:
            return valid
    return []

def new_round_celeb_quiz():
    people = get_valid_people_for_quiz()
    if len(people) < 4:
        st.error("Impossible de charger des célébrités. Vérifie ta clé TMDB.")
        st.stop()

    correct = random.choice(people)
    correct_gender = correct.get("gender", 0)

    same_gender = [p for p in people if p["id"] != correct["id"] and p.get("gender", 0) == correct_gender]
    others = same_gender if len(same_gender) >= 3 else [p for p in people if p["id"] != correct["id"]]

    wrong = random.sample(others, 3)
    choices = wrong + [correct]
    random.shuffle(choices)

    st.session_state.current_item = correct
    st.session_state.choices = choices
    st.session_state.phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

def check_answer_quiz(selected_id: int, name_key: str):
    correct_id = st.session_state.current_item["id"]
    if selected_id == correct_id:
        st.session_state.score += 1
        st.session_state.message = f"Correct : {st.session_state.current_item[name_key]}"
    else:
        st.session_state.message = f"Faux. Réponse : {st.session_state.current_item[name_key]}"
    st.session_state.phase = "result"

# -----------------------------
# QUIZ: films
# -----------------------------
def get_valid_movies_for_quiz():
    for _ in range(6):
        page = random.randint(1, 20)
        raw = fetch_movies_page(page)
        valid = []
        for m in raw:
            if not m.get("backdrop_path"):
                continue
            if not is_latin(m.get("title", "")):
                continue
            valid.append(m)
        if len(valid) >= 8:
            return valid
    return []

def new_round_movie_quiz():
    movies = get_valid_movies_for_quiz()
    if len(movies) < 4:
        st.error("Impossible de charger des films. Vérifie ta clé TMDB.")
        st.stop()

    correct = random.choice(movies)
    others = [m for m in movies if m["id"] != correct["id"]]
    wrong = random.sample(others, 3)
    choices = wrong + [correct]
    random.shuffle(choices)

    scene = get_random_scene_image(correct["id"], correct["backdrop_path"])

    st.session_state.current_item = correct
    st.session_state.current_image = scene
    st.session_state.choices = choices
    st.session_state.phase = "question"
    st.session_state.message = ""

# -----------------------------
# Session state init
# -----------------------------
if "mode" not in st.session_state:
    st.session_state.mode = "Célébrités"
if "phase" not in st.session_state:
    st.session_state.phase = "init"
if "score" not in st.session_state:
    st.session_state.score = 0
if "start_time" not in st.session_state:
    st.session_state.start_time = 0
if "message" not in st.session_state:
    st.session_state.message = ""
if "current_item" not in st.session_state:
    st.session_state.current_item = None
if "current_image" not in st.session_state:
    st.session_state.current_image = None
if "choices" not in st.session_state:
    st.session_state.choices = []

# Mémoire state
if "memory_people" not in st.session_state:
    st.session_state.memory_people = []
if "memory_found" not in st.session_state:
    st.session_state.memory_found = []
if "memory_revealed_faces" not in st.session_state:
    st.session_state.memory_revealed_faces = []
if "show_solution" not in st.session_state:
    st.session_state.show_solution = False
if "memory_round_id" not in st.session_state:
    st.session_state.memory_round_id = 0
if "memory_input_key" not in st.session_state:
    st.session_state.memory_input_key = "mem_input_0"
if "memory_last_ids" not in st.session_state:
    st.session_state.memory_last_ids = []

# -----------------------------
# UI: menu
# -----------------------------
st.sidebar.title("Menu")
selected = st.sidebar.radio("Mode", ["Célébrités", "Films", "Mémoire (16 visages)"])

if selected != st.session_state.mode:
    st.session_state.mode = selected
    st.session_state.phase = "init"
    st.session_state.score = 0
    st.session_state.message = ""
    st.session_state.current_item = None
    st.session_state.current_image = None
    st.session_state.choices = []
    st.rerun()

st.title(st.session_state.mode)

# Score / compteur
if st.session_state.mode == "Mémoire (16 visages)" and st.session_state.phase in ("recall", "memorize"):
    st.metric("Trouvés", f"{len(st.session_state.memory_found)} / 16")
else:
    st.metric("Score", st.session_state.score)

# -----------------------------
# INIT screen
# -----------------------------
if st.session_state.phase == "init":
    if st.button("Commencer", type="primary"):
        if st.session_state.mode == "Célébrités":
            new_round_celeb_quiz()
        elif st.session_state.mode == "Films":
            new_round_movie_quiz()
        else:
            start_memory_round()
        st.rerun()

# =========================================================
# MODE MEMOIRE
# =========================================================
elif st.session_state.mode == "Mémoire (16 visages)":

    if st.session_state.phase == "memorize":
        elapsed = time.time() - st.session_state.start_time
        remaining = MEMORY_TIME - elapsed

        st.write(f"Mémorisation : {int(max(0, remaining))} s")
        st.progress(max(0.0, min(1.0, remaining / MEMORY_TIME)))

        people = st.session_state.memory_people
        if len(people) == 16:
            for i in range(0, 16, 4):
                cols = st.columns(4)
                for j in range(4):
                    p = people[i + j]
                    with cols[j]:
                        # pendant mémorisation : image couleur, sans nom
                        st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=115)

        if remaining <= 0:
            st.session_state.phase = "recall"
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()

    elif st.session_state.phase == "recall":
        # Input (clé unique par manche)
        st.text_input("Écris un prénom ou un nom", key=st.session_state.memory_input_key, on_change=check_memory_input)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Révéler tout"):
                st.session_state.show_solution = True
                st.rerun()
        with c2:
            # IMPORTANT : keys uniques via memory_round_id
            if st.button("Prochaine manche", key=f"next_{st.session_state.memory_round_id}"):
                start_memory_round()
                st.rerun()

        st.write("---")

        people = st.session_state.memory_people
        rid = st.session_state.memory_round_id

        if len(people) == 16:
            for i in range(0, 16, 4):
                cols = st.columns(4)
                for j in range(4):
                    p = people[i + j]
                    pid = p["id"]
                    with cols[j]:
                        if pid in st.session_state.memory_found:
                            st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=115)
                            st.markdown(f"<div class='found-name'>{p['name']}</div>", unsafe_allow_html=True)

                        elif st.session_state.show_solution:
                            st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=115)
                            st.markdown(f"<div class='missed-name'>{p['name']}</div>", unsafe_allow_html=True)

                        elif pid in st.session_state.memory_revealed_faces:
                            st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=115)
                            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

                        else:
                            st.markdown(
                                f"""
                                <div class="hidden-img" style="display:flex; justify-content:center;">
                                    <img src="{IMG_PERSON_GRID}{p['profile_path']}" style="width:115px;">
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            st.markdown('<div class="tiny-btn">', unsafe_allow_html=True)
                            if st.button("Indice", key=f"hint_{rid}_{pid}"):
                                reveal_face(pid)
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# MODE QUIZ (Célébrités / Films)
# =========================================================
elif st.session_state.phase == "question":

    if st.session_state.mode == "Célébrités":
        # timer
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(remaining, GAME_DURATION)

        if remaining <= 0:
            # temps écoulé => résultat direct
            st.session_state.message = f"Temps écoulé. Réponse : {st.session_state.current_item['name']}"
            st.session_state.phase = "result"
            st.rerun()

        # image centrée
        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(f"{IMG_PERSON_QUIZ}{st.session_state.current_item['profile_path']}", width=300)

        st.write("Qui est-ce ?")

        c1, c2 = st.columns(2)
        for i, p in enumerate(st.session_state.choices):
            col = c1 if i < 2 else c2
            with col:
                if st.button(p["name"], key=f"celeb_choice_{p['id']}"):
                    check_answer_quiz(p["id"], "name")
                    st.rerun()

        # rafraîchissement du timer
        time.sleep(1)
        st.rerun()

    else:
        # Films (pas de timer)
        left, center, right = st.columns([1, 6, 1])
        with center:
            st.image(f"{IMG_MOVIE}{st.session_state.current_image}", width=500)

        st.write("Quel est ce film ?")

        c1, c2 = st.columns(2)
        for i, m in enumerate(st.session_state.choices):
            col = c1 if i < 2 else c2
            with col:
                if st.button(m["title"], key=f"movie_choice_{m['id']}"):
                    check_answer_quiz(m["id"], "title")
                    st.rerun()

elif st.session_state.phase == "result":
    left, center, right = st.columns([1, 2, 1])
    with center:
        if st.session_state.mode == "Célébrités":
            st.image(f"{IMG_PERSON_QUIZ}{st.session_state.current_item['profile_path']}", width=200)
        else:
            st.image(f"{IMG_MOVIE}{st.session_state.current_item['backdrop_path']}", width=420)

    st.info(st.session_state.message)

    if st.button("Question suivante", type="primary"):
        if st.session_state.mode == "Célébrités":
            new_round_celeb_quiz()
        else:
            new_round_movie_quiz()
        st.rerun()
