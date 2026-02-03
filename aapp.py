import streamlit as st
import requests
import re
import time
import unicodedata
import secrets

# =========================
# CONFIG
# =========================
API_KEY = "266f486999f6f5487f4ee8f974607538"  # <-- Mets ta clé TMDB ici
BASE_URL = "https://api.themoviedb.org/3"

IMG_PERSON_GRID = "https://image.tmdb.org/t/p/w342"   # mémoire
IMG_PERSON_QUIZ = "https://image.tmdb.org/t/p/w500"   # célébrités
IMG_MOVIE = "https://image.tmdb.org/t/p/w780"         # films

GAME_DURATION = 30
MEMORY_TIME = 60

st.set_page_config(page_title="Super Quiz", page_icon="🎮", layout="centered")

# =========================
# CSS (réponses comme la capture)
# =========================
st.markdown("""
<style>
.block-container { padding-top: 1rem; padding-bottom: 1rem; }
div[data-testid="column"] { padding: 0px !important; }

/* Centrer images */
div[data-testid="stImage"] { display:flex; justify-content:center; }
div[data-testid="stImage"] > img { margin:auto; object-fit:cover; }

/* --- Réponses : 4 grands rectangles identiques --- */
button[kind="primary"]{
    height: 64px !important;
    width: 100% !important;
    border-radius: 16px !important;
    font-size: 18px !important;
    border: 1px solid rgba(255,255,255,0.20) !important;
    background: rgba(255,255,255,0.06) !important;
    color: #fff !important;
}
button[kind="primary"]:hover{
    background: rgba(255,255,255,0.10) !important;
    border-color: rgba(255,255,255,0.35) !important;
    transform: translateY(-1px);
}

/* Espace horizontal entre les 2 colonnes */
div[data-testid="stHorizontalBlock"]{ gap: 16px !important; }

/* Espace vertical entre rangées */
.answers-row-gap{ height: 16px; }

/* --- Mémoire --- */
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
    border-radius: 14px;
}

/* Petit bouton indice */
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
        color = "#2ecc71"
    elif remaining_time > 10:
        color = "#f1c40f"
    elif remaining_time > 5:
        color = "#e67e22"
    else:
        color = "#e74c3c"

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
# TMDB cache (pages)
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
        return secrets.choice(textless).get("file_path", default_path)
    if len(backdrops) > 1:
        return secrets.choice(backdrops[1:]).get("file_path", default_path)
    return default_path

# =========================
# Session State init
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
ss_init("memory_history_ids", [])     # anti-répétition (id récents)
ss_init("memory_reveal_locked", False)

# =========================
# MODE MEMOIRE (tirage vraiment aléatoire)
# =========================
def pick_16_random_stars():
    """
    On tire des pages ALÉATOIRES à chaque manche (1..200),
    puis on choisit 16 personnes au hasard dans ces candidats.
    Anti-répétition sur les ~6 manches précédentes.
    """
    rng_pages = set()
    while len(rng_pages) < 14:
        rng_pages.add(secrets.randbelow(200) + 1)

    history = set(st.session_state.get("memory_history_ids", []))

    candidates = []
    seen = set()

    # 1) filtre "stars connues"
    def is_candidate(p, min_pop=18):
        if not p.get("id"): return False
        if not p.get("profile_path"): return False
        if p.get("known_for_department") != "Acting": return False
        if p.get("adult", False): return False
        if not is_latin(p.get("name", "")): return False
        if p.get("popularity", 0) < min_pop: return False
        return True

    # 2) on récupère des candidats depuis pages aléatoires
    for page in rng_pages:
        for p in fetch_people_page(page):
            pid = p.get("id")
            if not pid or pid in seen:
                continue
            if not is_candidate(p, min_pop=18):
                continue
            seen.add(pid)
            candidates.append(p)

    # 3) si pas assez, on relâche un peu (mais garde acting+photo)
    if len(candidates) < 16:
        for page in rng_pages:
            for p in fetch_people_page(page):
                pid = p.get("id")
                if not pid or pid in seen:
                    continue
                if not is_candidate(p, min_pop=10):
                    continue
                seen.add(pid)
                candidates.append(p)
                if len(candidates) >= 40:
                    break

    if len(candidates) < 16:
        return []

    # 4) on évite les ids récents si possible
    filtered = [p for p in candidates if p["id"] not in history]
    if len(filtered) >= 16:
        candidates = filtered

    # 5) tirage 16 sans remplacement (façon secrets)
    # on mélange en triant par un aléa fort
    shuffled = sorted(candidates, key=lambda _: secrets.randbits(64))
    sample = shuffled[:16]

    # update history (garde ~96 ids)
    new_ids = [p["id"] for p in sample]
    old = st.session_state.get("memory_history_ids", [])
    st.session_state.memory_history_ids = (old + new_ids)[-96:]

    return sample

def start_memory_round():
    """
    Même rôle que ▶️ Commencer : reset total + nouvelles 16 célébrités + phase memorize
    """
    st.session_state.memory_round_id += 1
    st.session_state.memory_input_key = f"mem_input_{st.session_state.memory_round_id}"

    st.session_state.memory_people = []
    st.session_state.memory_found = []
    st.session_state.memory_revealed_faces = []
    st.session_state.show_solution = False
    st.session_state.memory_reveal_locked = False

    people = pick_16_random_stars()
    if len(people) < 16:
        st.error("❌ Impossible de générer 16 célébrités (clé TMDB ou filtre trop strict).")
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
    st.session_state.memory_reveal_locked = True

def memory_clear_all():
    """
    Tout effacer = plus rien à l'écran, uniquement 🔄 Prochaine manche.
    """
    st.session_state.show_solution = False
    st.session_state.memory_reveal_locked = False

    st.session_state.memory_people = []
    st.session_state.memory_found = []
    st.session_state.memory_revealed_faces = []

    # On supprime aussi la valeur du champ texte de cette manche
    k = st.session_state.memory_input_key
    if k in st.session_state:
        del st.session_state[k]

    st.session_state.phase = "memory_empty"

# =========================
# QUIZ Célébrités / Films
# =========================
def get_valid_people_for_quiz():
    for _ in range(8):
        page = secrets.randbelow(20) + 1
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

    correct = secrets.choice(people)
    g = correct.get("gender", 0)

    same_gender = [p for p in people if p["id"] != correct["id"] and p.get("gender", 0) == g]
    others = same_gender if len(same_gender) >= 3 else [p for p in people if p["id"] != correct["id"]]

    wrong = sorted(others, key=lambda _: secrets.randbits(64))[:3]
    choices = wrong + [correct]
    choices = sorted(choices, key=lambda _: secrets.randbits(64))

    st.session_state.current_item = correct
    st.session_state.current_image = correct["profile_path"]
    st.session_state.choices = choices
    st.session_state.phase = "question"
    st.session_state.start_time = time.time()
    st.session_state.message = ""

def get_valid_movies_for_quiz():
    for _ in range(8):
        page = secrets.randbelow(20) + 1
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

    correct = secrets.choice(movies)
    others = [m for m in movies if m["id"] != correct["id"]]
    wrong = sorted(others, key=lambda _: secrets.randbits(64))[:3]
    choices = wrong + [correct]
    choices = sorted(choices, key=lambda _: secrets.randbits(64))

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

if st.session_state.mode == "Mémoire (16 visages)" and st.session_state.phase in ("memorize", "recall"):
    st.metric("🧠 Trouvés", f"{len(st.session_state.memory_found)} / 16")
elif st.session_state.mode == "Mémoire (16 visages)" and st.session_state.phase == "memory_empty":
    st.metric("🧹 État", "Tout effacé")
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

    # Tout effacé = uniquement "Prochaine manche"
    if st.session_state.phase == "memory_empty":
        st.write("🧹 **Tout a été effacé.**")
        if st.button("🔄 Prochaine manche", type="secondary"):
            start_memory_round()
            st.rerun()
        st.stop()

    # Mémorisation
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

    # Recall
    if st.session_state.phase == "recall":
        st.text_input(
            "✍️ Écris un prénom / nom (séparés par virgules si tu veux)",
            key=st.session_state.memory_input_key,
            on_change=check_memory_input
        )

        c1, c2, c3 = st.columns(3)

        with c1:
            if st.button("👀 Tout révéler", type="secondary"):
                memory_reveal_all()
                st.rerun()
                st.stop()

        with c2:
            if st.button("🧹 Tout effacer", type="secondary"):
                memory_clear_all()
                st.rerun()
                st.stop()

        with c3:
            if st.button("🔄 Prochaine manche", type="secondary", disabled=st.session_state.memory_reveal_locked):
                start_memory_round()
                st.rerun()
                st.stop()

        if st.session_state.memory_reveal_locked:
            st.warning("⚠️ Tu as cliqué sur **👀 Tout révéler**. Clique sur **🧹 Tout effacer** avant **🔄 Prochaine manche**.")

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
                                st.stop()
                            st.markdown("</div>", unsafe_allow_html=True)

# =========================================================
# QUIZ (Célébrités / Films)
# =========================================================
elif st.session_state.phase == "question":

    # ----- Célébrités -----
    if st.session_state.mode == "Célébrités":
        elapsed = time.time() - st.session_state.start_time
        remaining = GAME_DURATION - elapsed
        display_circular_timer(remaining, GAME_DURATION)

        if remaining <= 0:
            st.session_state.message = f"⏰ Temps écoulé… C’était **{st.session_state.current_item['name']}**"
            st.session_state.phase = "result"
            st.rerun()

        # image plus grande
        left, center, right = st.columns([1, 2, 1])
        with center:
            st.image(f"{IMG_PERSON_QUIZ}{st.session_state.current_image}", width=460)

        st.write("### 👤 Qui est-ce ?")

        # réponses centrées comme ta capture
        L, M, R = st.columns([1, 5, 1])
        with M:
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

            st.markdown("<div class='answers-row-gap'></div>", unsafe_allow_html=True)

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

    # ----- Films -----
    else:
        left, center, right = st.columns([1, 6, 1])
        with center:
            st.image(f"{IMG_MOVIE}{st.session_state.current_image}", width=820)

        st.write("### 🎬 Quel est ce film ?")

        L, M, R = st.columns([1, 6, 1])
        with M:
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

            st.markdown("<div class='answers-row-gap'></div>", unsafe_allow_html=True)

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
            st.image(f"{IMG_PERSON_QUIZ}{st.session_state.current_item['profile_path']}", width=280)
        else:
            st.image(f"{IMG_MOVIE}{st.session_state.current_item['backdrop_path']}", width=640)

    st.markdown(st.session_state.message)

    if st.button("➡️ Question suivante", type="secondary"):
        if st.session_state.mode == "Célébrités":
            new_round_celeb_quiz()
        else:
            new_round_movie_quiz()
        st.rerun()
