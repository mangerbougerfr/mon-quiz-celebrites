import streamlit as st
import requests
import random
import re
import time
import unicodedata

# =========================
# CONFIG
# =========================
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <-- Mets ta clé TMDB ici
BASE_URL = "https://api.themoviedb.org/3"

# Images
IMG_PERSON_GRID = "https://image.tmdb.org/t/p/w342"   # mémoire
IMG_PERSON_QUIZ = "https://image.tmdb.org/t/p/w500"   # célébrités quiz
IMG_MOVIE = "https://image.tmdb.org/t/p/w780"         # films quiz

GAME_DURATION = 30      # timer célébrités
MEMORY_TIME = 60        # mémorisation mémoire

st.set_page_config(page_title="Super Quiz", page_icon="🎮", layout="centered")

# =========================
# CSS
# - Réponses en 4 cartes égales (arrondies, espacées, centrées)
# =========================
st.markdown("""
<style>
/* Layout */
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
div[data-testid="column"] { padding: 0px !important; }

/* Centrer images dans colonnes */
div[data-testid="stImage"] { display:flex; justify-content:center; }
div[data-testid="stImage"] > img { margin:auto; object-fit:cover; }

/* ====== Cartes de réponses (seulement en type="primary") ======
   IMPORTANT: utilise type="primary" uniquement pour les 4 réponses,
   pas pour les autres boutons.
*/
button[kind="primary"]{
    height: 78px !important;
    width: 100% !important;
    border-radius: 16px !important;
    font-size: 18px !important;
    border: 1px solid rgba(255,255,255,0.18) !important;
    background: rgba(255,255,255,0.06) !important;
    color: #fff !important;
    transition: 0.15s ease-in-out;
}
button[kind="primary"]:hover{
    transform: translateY(-1px);
    border-color: rgba(255,255,255,0.30) !important;
    background: rgba(255,255,255,0.10) !important;
}

/* Gap plus propre entre colonnes */
div[data-testid="stHorizontalBlock"]{
    gap: 14px !important;
}

/* Sépare légèrement les 2 rangées (même distance) */
.answers-row { margin-top: 14px; }

/* ===== Mémoire ===== */
.found-name{
    color:#00C853; font-weight:800; text-align:center;
    font-size:13px; margin-top:-6px; margin-bottom:12px;
}
.missed-name{
    color:#FF5252; font-weight:800; text-align:center;
    font-size:13px; margin-top:-6px; margin-bottom:12px;
}
.hidden-img img{
    filter: brightness(0) !important;
    -webkit-filter: brightness(0) !important;
    pointer-events:none;
    border-radius: 12px;
}

/* Petit bouton indice en mémoire */
.small-btn button{
    height: 34px !important;
    font-size: 14px !important;
    border-radius: 12px !important;
}

/* Timer */
.timer-wrap{ display:flex; justify-content:center; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# =========================
# Utils
# =========================
def is_latin(text: str) -> bool:
    return bool(re.match(r"^[a-zA-Zà-üÀ-Ü0-9\s\-\.\':]+$", text or ""))

def normalize_text(s: str) -> str:
    if not s:
        return ""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = re.sub(r"[^a-z0-9\s\-']", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tmdb_get(url: str, timeout: int = 10):
    try:
        return requests.get(url, timeout=timeout).json()
    except Exception:
        return {}

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
    <div class="timer-wrap">
        <svg width="70" height="70" viewBox="0 0 100 100">
            <circle cx="50" cy="50" r="45" fill="none" stroke="#333" stroke-width="8" />
            <circle cx="50" cy="50" r="45" fill="none" stroke="{color}" stroke-width="8"
                    stroke-dasharray="{283 * (percent/100)} 283"
                    transform="rotate(-90 50 50)" stroke-linecap="round" />
            <text x="50" y="56" text-anchor="middle" font-size="30" font-weight="800" fill="white">{int(remaining_time)}</text>
        </svg>
    </div>
    """
    st.markdown(svg_code, unsafe_allow_html=True)

# =========================
# TMDB cache
# =========================
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
    textless = [b for b in backdrops if b.get("iso_639_1") is None]
    if textless:
        return random.choice(textless).get("file_path", default_path)
    if len(backdrops) > 1:
        return random.choice(backdrops[1:]).get("file_path", default_path)
    return default_path

# =========================
# MODE MEMOIRE: pool + tirage aléatoire réel
# + anti-répétition (historique)
# =========================
@st.cache_data(ttl=24 * 3600)
def build_star_pool(pages: int = 40):
    """
    Pool de célébrités très connues (Acting + photo + latin).
    On garde une pool large pour permettre un vrai hasard.
    """
    pool = []
    seen = set()

    for page in range(1, pages + 1):
        raw = fetch_people_page(page)
        for p in raw:
            pid = p.get("id")
            if not pid or pid in seen:
                continue
            if not p.get("profile_path"):
                continue
            if p.get("known_for_department") != "Acting":
                continue
            if p.get("adult", False):
                continue
            if not is_latin(p.get("name", "")):
                continue
            if p.get("popularity", 0) < 15:
                continue

            seen.add(pid)
            pool.append(p)

    pool.sort(key=lambda x: x.get("popularity", 0), reverse=True)
    # pool large pour varier
    return pool[:500]

def pick_16_random_stars():
    pool = build_star_pool(pages=40)
    if len(pool) < 16:
        return []

    rng = random.SystemRandom()

    history = st.session_state.get("memory_history_ids", [])
    history_set = set(history)

    candidates = [p for p in pool if p["id"] not in history_set]
    if len(candidates) < 16:
        candidates = pool[:]  # fallback

    sample = rng.sample(candidates, 16)

    # update history (garde 96 ids max)
    new_ids = [p["id"] for p in sample]
    history = (history + new_ids)[-96:]
    st.session_state.memory_history_ids = history

    return sample

def start_memory_round():
    """
    Nouvelle manche mémoire, reset total.
    """
    st.session_state.memory_round_id += 1
    st.session_state.memory_input_key = f"mem_input_{st.session_state.memory_round_id}"

    # reset
    st.session_state.memory_people = []
    st.session_state.memory_found = []
    st.session_state.memory_revealed_faces = []
    st.session_state.show_solution = False
    st.session_state.memory_need_clear = False

    people = pick_16_random_stars()
    if len(people) < 16:
        st.error("❌ Impossible de générer 16 célébrités. Vérifie la clé TMDB.")
        return

    st.session_state.memory_people = people
    st.session_state.phase = "memorize"
    st.session_state.start_time = time.time()

def reveal_face(person_id: int):
    if person_id not in st.session_state.memory_revealed_faces:
        st.session_state.memory_revealed_faces.append(person_id)

def check_memory_input():
    key = st.session_state.memory_input_key
    raw_text = st.session_state.get(key, "")
    if not raw_text.strip():
        return

    guesses = [normalize_text(x) for x in re.split(r"[,\n;]+", raw_text) if normalize_text(x)]
    found_any = False

    for guess in guesses:
        for p in st.session_state.memory_people:
            if p["id"] in st.session_state.memory_found:
                continue
            full = normalize_text(p["name"])
            parts = set(full.replace("-", " ").split())

            if (guess in parts and len(guess) > 2) or (guess == full and len(guess) > 2):
                st.session_state.memory_found.append(p["id"])
                found_any = True

    if found_any:
        st.toast("✅ Validé !")

    st.session_state[key] = ""

def memory_reveal_all():
    st.session_state.show_solution = True
    st.session_state.memory_need_clear = True

def memory_clear_all():
    """
    'Tout effacer' = retirer l'affichage des noms/solutions,
    et autoriser 'Prochaine manche'.
    """
    st.session_state.show_solution = False
    st.session_state.memory_need_clear = False

# =========================
# QUIZ Célébrités / Films
# =========================
def get_valid_people_for_quiz():
    for _ in range(8):
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
        if len(valid) >= 10:
            return valid
    return []

def new_round_celeb_quiz():
    people = get_valid_people_for_quiz()
    if len(people) < 4:
        st.error("❌ Problème de chargement (clé TMDB ?).")
        st.stop()

    correct = random.choice(people)
    g = correct.get("gender", 0)

    same_gender = [p for p in people if p["id"] != correct["id"] and p.get("gender", 0) == g]
    others = same_gender if len(same_gender) >= 3 else [p for p in people if p["id"] != correct["id"]]

    wrong = random.sample(others, 3)
    choices = wrong + [correct]
    random.shuffle(choices)

    st.session_state.current_item = correct
    st.session_state.current_image = correct["profile_path"]
    st.session_state.choices = choices
    st.session_state.phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

def get_valid_movies_for_quiz():
    for _ in range(8):
        page = random.randint(1, 20)
        raw = fetch_movies_page(page)
        valid = []
        for m in raw:
            if not m.get("backdrop_path"):
                continue
            if not is_latin(m.get("title", "")):
                continue
            valid.append(m)
        if len(valid) >= 10:
            return valid
    return []

def new_round_movie_quiz():
    movies = get_valid_movies_for_quiz()
    if len(movies) < 4:
        st.error("❌ Problème de chargement (clé TMDB ?).")
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

def check_answer_quiz(selected_id: int, name_key: str):
    correct_id = st.session_state.current_item["id"]
    correct_name = st.session_state.current_item[name_key]

    if selected_id == correct_id:
        st.session_state.score += 1
        st.session_state.message = f"✅ Bonne réponse ! C’était **{correct_name}**"
    else:
        st.session_state.message = f"❌ Mauvaise réponse… C’était **{correct_name}**"

    st.session_state.phase = "result"


# =========================
# Session state init
# =========================
def ss_init(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

ss_init("mode", "Célébrités")
ss_init("phase", "init")
ss_init("score", 0)
ss_init("start_time", 0.0)
ss_init("message", "")
ss_init("current_item", None)
ss_init("current_image", None)
ss_init("choices", [])

# mémoire
ss_init("memory_people", [])
ss_init("memory_found", [])
ss_init("memory_revealed_faces", [])
ss_init("show_solution", False)
ss_init("memory_round_id", 0)
ss_init("memory_input_key", "mem_input_0")
ss_init("memory_history_ids", [])
ss_init("memory_need_clear", False)

# =========================
# UI - Menu
# =========================
st.sidebar.title("🎮 Menu")
selected = st.sidebar.radio("Choisis un mode :", ["Célébrités", "Films", "Mémoire (16 visages)"])

if selected != st.session_state.mode:
    st.session_state.mode = selected
    st.session_state.phase = "init"
    st.session_state.score = 0
    st.session_state.message = ""
    st.session_state.current_item = None
    st.session_state.current_image = None
    st.session_state.choices = []
    st.rerun()

st.title(f"⭐ {st.session_state.mode}")

# Compteurs
if st.session_state.mode == "Mémoire (16 visages)" and st.session_state.phase in ("memorize", "recall"):
    st.metric("🧠 Trouvés", f"{len(st.session_state.memory_found)} / 16")
else:
    st.metric("🏆 Score", st.session_state.score)

# =========================
# INIT
# =========================
if st.session_state.phase == "init":
    if st.button("▶️ Commencer", type="secondary"):
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

    # Phase memorize (AUCUN nom ici)
    if st.session_state.phase == "memorize":
        elapsed = time.time() - st.session_state.start_time
        remaining = MEMORY_TIME - elapsed

        st.write(f"🧠 **Mémorisation :** {int(max(0, remaining))} s")
        st.progress(max(0.0, min(1.0, remaining / MEMORY_TIME)))

        people = st.session_state.memory_people
        if len(people) == 16:
            for i in range(0, 16, 4):
                cols = st.columns(4)
                for j in range(4):
                    p = people[i + j]
                    with cols[j]:
                        st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=120)

        if remaining <= 0:
            st.session_state.phase = "recall"
            st.rerun()
        else:
            time.sleep(1)
            st.rerun()

    # Phase recall
    elif st.session_state.phase == "recall":
        st.text_input(
            "✍️ Écris un prénom / nom (séparés par virgules si tu veux)",
            key=st.session_state.memory_input_key,
            on_change=check_memory_input
        )

        c1, c2, c3 = st.columns(3)
        with c1:
            st.button("👀 Tout révéler", on_click=memory_reveal_all)
        with c2:
            st.button("🧹 Tout effacer", on_click=memory_clear_all)
        with c3:
            # Désactivé si l'utilisateur a révélé tout mais n'a pas effacé
            st.button(
                "🔄 Prochaine manche",
                disabled=st.session_state.memory_need_clear,
                on_click=start_memory_round
            )

        if st.session_state.memory_need_clear:
            st.warning("⚠️ Tu as révélé toutes les réponses. Clique sur **🧹 Tout effacer** avant de lancer la prochaine manche.")

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
                            st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=120)
                            st.markdown(f"<div class='found-name'>{p['name']}</div>", unsafe_allow_html=True)

                        elif st.session_state.show_solution:
                            st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=120)
                            st.markdown(f"<div class='missed-name'>{p['name']}</div>", unsafe_allow_html=True)

                        elif pid in st.session_state.memory_revealed_faces:
                            st.image(f"{IMG_PERSON_GRID}{p['profile_path']}", width=120)
                            st.markdown("<div style='height:22px'></div>", unsafe_allow_html=True)

                        else:
                            st.markdown(
                                f"""
                                <div class="hidden-img" style="display:flex; justify-content:center;">
                                    <img src="{IMG_PERSON_GRID}{p['profile_path']}" style="width:120px;">
                                </div>
                                """,
                                unsafe_allow_html=True
                            )
                            st.markdown('<div class="small-btn">', unsafe_allow_html=True)
                            if st.button("👁️ Indice", key=f"hint_{rid}_{pid}"):
                                reveal_face(pid)
                                st.rerun()
                            st.markdown("</div>", unsafe_allow_html=True)


# =========================================================
# QUIZ (Célébrités / Films)
# =========================================================
elif st.session_state.phase == "question":

    # -------- Célébrités --------
    if st.session_state.mode == "Célébrités":
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(remaining, GAME_DURATION)

        if remaining <= 0:
            st.session_state.message = f"⏰ Temps écoulé… C’était **{st.session_state.current_item['name']}**"
            st.session_state.phase = "result"
            st.rerun()

        # Image un peu plus grande + centrée
        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(f"{IMG_PERSON_QUIZ}{st.session_state.current_image}", width=380)

        st.write("### 👤 Qui est-ce ?")

        # Réponses centrées sous l'image (col milieu)
        leftA, midA, rightA = st.columns([1, 3, 1])
        with midA:
            row1 = st.columns(2)
            with row1[0]:
                p = st.session_state.choices[0]
                if st.button(p["name"], type="primary", key=f"celeb_{st.session_state.current_item['id']}_0"):
                    check_answer_quiz(p["id"], "name")
                    st.rerun()
            with row1[1]:
                p = st.session_state.choices[1]
                if st.button(p["name"], type="primary", key=f"celeb_{st.session_state.current_item['id']}_1"):
                    check_answer_quiz(p["id"], "name")
                    st.rerun()

            st.markdown("<div class='answers-row'></div>", unsafe_allow_html=True)

            row2 = st.columns(2)
            with row2[0]:
                p = st.session_state.choices[2]
                if st.button(p["name"], type="primary", key=f"celeb_{st.session_state.current_item['id']}_2"):
                    check_answer_quiz(p["id"], "name")
                    st.rerun()
            with row2[1]:
                p = st.session_state.choices[3]
                if st.button(p["name"], type="primary", key=f"celeb_{st.session_state.current_item['id']}_3"):
                    check_answer_quiz(p["id"], "name")
                    st.rerun()

        time.sleep(1)
        st.rerun()

    # -------- Films --------
    else:
        # Image un peu plus grande + centrée
        left, center, right = st.columns([1, 6, 1])
        with center:
            st.image(f"{IMG_MOVIE}{st.session_state.current_image}", width=650)

        st.write("### 🎬 Quel est ce film ?")

        leftA, midA, rightA = st.columns([1, 4, 1])
        with midA:
            row1 = st.columns(2)
            with row1[0]:
                m = st.session_state.choices[0]
                if st.button(m["title"], type="primary", key=f"movie_{st.session_state.current_item['id']}_0"):
                    check_answer_quiz(m["id"], "title")
                    st.rerun()
            with row1[1]:
                m = st.session_state.choices[1]
                if st.button(m["title"], type="primary", key=f"movie_{st.session_state.current_item['id']}_1"):
                    check_answer_quiz(m["id"], "title")
                    st.rerun()

            st.markdown("<div class='answers-row'></div>", unsafe_allow_html=True)

            row2 = st.columns(2)
            with row2[0]:
                m = st.session_state.choices[2]
                if st.button(m["title"], type="primary", key=f"movie_{st.session_state.current_item['id']}_2"):
                    check_answer_quiz(m["id"], "title")
                    st.rerun()
            with row2[1]:
                m = st.session_state.choices[3]
                if st.button(m["title"], type="primary", key=f"movie_{st.session_state.current_item['id']}_3"):
                    check_answer_quiz(m["id"], "title")
                    st.rerun()


# =========================
# RESULT (Célébrités / Films)
# =========================
elif st.session_state.phase == "result":
    left, center, right = st.columns([1, 2, 1])
    with center:
        if st.session_state.mode == "Célébrités":
            st.image(f"{IMG_PERSON_QUIZ}{st.session_state.current_item['profile_path']}", width=240)
        else:
            st.image(f"{IMG_MOVIE}{st.session_state.current_item['backdrop_path']}", width=520)

    st.markdown(st.session_state.message)

    if st.button("➡️ Question suivante", type="secondary"):
        if st.session_state.mode == "Célébrités":
            new_round_celeb_quiz()
        else:
            new_round_movie_quiz()
        st.rerun()
