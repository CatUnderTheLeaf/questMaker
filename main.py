import json

from google import genai
import streamlit as st

from tasks import load_tasks

from utils.types import CatalogEntry, QuestRequest, QuestResponse, ScoredOption, Selection
from utils.pdf import QuestStop, build_quest_pdf

# Temporary: mock the model response for UI design (no model call).
DEV_MODE = False
USE_MOCK_RESPONSE = False
MOCK_CLUE_WORDS = "table, cat, refrigerator, balcony, coach, kettle, bathroom"
MOCK_PARTICIPANTS = (
    "my kids are 6 years old, know a little bit of math, "
    "just simple subtraction and addition."
)
MOCK_PARTICIPANTS_ALT = (
    "my kids are 12 years old, "
    "they love math and puzzles."
)
MOCK_RESPONSE = {
    "picks": [
    {
      "task_id": "table_borders",
      "why": "A 3x3 table with letters and visual border decoding."
    },
    {
      "task_id": "anagram",
      "why": "Rearranging shuffled letters to recover the word."
    },
    {
      "task_id": "knight_move",
      "why": "Involves chess knight moves and tour orders."
    },
    {
      "task_id": "n_queens",
      "why": "Involves the chess queen puzzle and board cells."
    },
    {
      "task_id": "shopping_list",
      "why": "Observational task using first letters of items."
    },
    {
      "task_id": "prime_numbers",
      "why": "Replaces letters with prime numbers using alphabet order."
    },
    {
      "task_id": "coordinates",
      "why": "Uses a table with row and column cell coordinates."
    }
  ]
}

TASKS = load_tasks()
# Every registered task runs for each clue word. New modules added under
# tasks/ register themselves via @register_task, so nothing to update here.
TASK_ORDER = sorted(TASKS)

SYSTEM_INSTRUCTION = (
    "Pick exactly one task per word. "
    "picks[i] is for words[i] and task_id must come from candidates[i][*].task_id. "
    "Each candidate carries score 1-5, the effective difficulty of that word "
    "with that task (1=instant, 2=single-step, 3=key lookup, 4=cipher/math, "
    "5=chess/multi-constraint). "
    "Judge mechanics from catalog[id].description; judge fit from score. "
    "user_message is the participant profile (age, knowledge, skill). Map it "
    "to a target band: young/beginners (younger than 10 years old) aim 1-2, "
    "older/skilled (~10-14 years old) aim 2-4, experts (15+ years old) aim 4-5. If user_message is empty or "
    "too vague to infer age/skill, aim 2-4 (medium). "
    "Prefer candidates at or just above the target; never pick far below it "
    "(a score-1 task on a short word like 'cat' is trivial for 12-year-olds). "
    "Prefer each task_id used at most once across picks: a solved mechanic is "
    "no challenge again. If no unused candidate fits the target, drop below "
    "the target to stay unique (a fresh easier puzzle beats repeating a solved "
    "one); never go above the kids' ability just for uniqueness — repeat a "
    "fitting task rather than serve a frustrating one. "
    "type_preference controls the mix of catalog entry types ('text' vs 'math'): "
    "'Any' means ignore type; 'More text' means prefer entries with type 'text'; "
    "'More math' means prefer entries with type 'math'; 'Balanced' means alternate "
    "between 'text' and 'math' across picks. "
    "Preference is a tiebreaker: when two candidate tasks suit a word about equally, "
    "pick the one matching the preference; never pick a clearly unsuitable task just "
    "to satisfy the mix. "
    "Keep why short but explanatory, not just a description of the task."
)


def build_prompt(req: QuestRequest) -> str:
    return req.model_dump_json(indent=2)


REPICK_SYSTEM_INSTRUCTION = (
    "Pick a single replacement task for one word. "
    "Return a JSON Selection with task_id chosen from candidates[*].task_id "
    "and a short explanatory why (max 120 chars). "
    "Never pick excluded_task_id. Avoid locked_task_ids (tasks already used "
    "on other stops): a fresh easier puzzle beats repeating a solved one; "
    "repeat a fitting task rather than serve a frustrating one. "
    "Each candidate carries score 1-5 (1=instant, 5=chess/multi-constraint). "
    "If reason is 'Too easy', prefer a higher score than current_score; "
    "if 'Too hard', prefer a lower score; if 'Different', stay near "
    "current_score but with different mechanics. "
    "type_preference is a tiebreaker only, never pick a clearly unsuitable "
    "task just to satisfy the mix."
)


def _repick_target(current_score: int, reason: str) -> int:
    if reason == "Too easy":
        return min(5, current_score + 1)
    if reason == "Too hard":
        return max(1, current_score - 1)
    return current_score


def pick_local_replacement(
    options: list[ScoredOption],
    current_id: str,
    locked_ids: set[str],
    reason: str,
    type_preference: str = "Any",
    catalog: dict[str, CatalogEntry] | None = None,
) -> tuple[str | None, bool]:
    """Pick a replacement from already-scored candidates.

    Returns (task_id, repeated_flag). repeated_flag is True when no unused
    task existed and the pick reuses a locked id. None when no alternative
    exists at all.
    """
    score_by_id = {o.task_id: o.score for o in options}
    current_score = score_by_id.get(current_id, 3)
    target = _repick_target(current_score, reason)

    fresh = [o for o in options if o.task_id != current_id and o.task_id not in locked_ids]
    repeated = False
    pool = fresh
    if not pool:
        # No fresh mechanic left: allow repeating the closest fit.
        pool = [o for o in options if o.task_id != current_id]
        repeated = True
    if not pool:
        return None, False

    def sort_key(o: ScoredOption):
        dist = abs(o.score - target)
        # Prefer moving in the requested direction on ties.
        if reason == "Too easy":
            direction_penalty = 0 if o.score >= current_score else 1
        elif reason == "Too hard":
            direction_penalty = 0 if o.score <= current_score else 1
        else:
            direction_penalty = 0
        type_penalty = 0
        if catalog is not None and type_preference in ("More text", "More math"):
            want = "text" if type_preference == "More text" else "math"
            entry = catalog.get(o.task_id)
            if entry is not None and entry.type != want:
                type_penalty = 1
        return (dist, direction_penalty, type_penalty, o.task_id)

    best = sorted(pool, key=sort_key)[0]
    return best.task_id, repeated


def build_repick_prompt(
    word: str,
    options: list[ScoredOption],
    catalog: dict[str, CatalogEntry],
    current_id: str,
    current_score: int,
    locked_ids: list[str],
    reason: str,
    note: str,
    type_preference: str,
    user_message: str,
) -> str:
    payload = {
        "word": word,
        "candidates": [o.model_dump() for o in options],
        "catalog": {tid: entry.model_dump() for tid, entry in catalog.items()},
        "current_task_id": current_id,
        "current_score": current_score,
        "locked_task_ids": locked_ids,
        "excluded_task_id": current_id,
        "reason": reason,
        "note": note[:200],
        "type_preference": type_preference,
        "user_message": user_message,
    }
    return json.dumps(payload, indent=2)


def _request_repick(i: int) -> None:
    """on_click callback: mark stop i for replacement before the next run.

    Callbacks run before the script body, so the render loop already knows
    a replacement is in flight and can keep showing the cached old image
    instead of re-encoding it.
    """
    pending = st.session_state.get("repick_pending")
    if not isinstance(pending, dict):
        pending = {}
        st.session_state["repick_pending"] = pending
    pending[i] = True


def _is_quota_error(e: Exception) -> bool:
    status = getattr(e, "status", None) or getattr(getattr(e, "response", None), "status_code", None)
    if status == 429:
        return True
    text = f"{type(e).__name__}: {e}".lower()
    return (
        "429" in text
        or "resource_exhausted" in text
        or "quota" in text
        or "rate limit" in text
        or "rate_limit" in text
        or "too many requests" in text
    )


def create_with_fallback(
    *,
    input: str,
    system_instruction: str,
    response_schema: dict,
    timeout: int = 60,
) -> tuple:
    """Call the model, falling back to the next model on 429/quota errors.

    Order: current ai_model first, then the rest of WORKING_MODELS.
    Returns (interaction, used_model, fell_back).
    """
    preferred = st.session_state.get("ai_model", WORKING_MODELS[0])
    ordered = [preferred] + [m for m in WORKING_MODELS if m != preferred]
    last_error: Exception | None = None
    for idx, model in enumerate(ordered):
        try:
            interaction = client.interactions.create(
                model=model,
                input=input,
                system_instruction=system_instruction,
                response_format={
                    "type": "text",
                    "mime_type": "application/json",
                    "schema": response_schema,
                },
                timeout=timeout,
            )
            if model != preferred:
                print(f"Model fallback: {preferred!r} busy, used {model!r}")
            return interaction, model, idx > 0
        except Exception as e:
            last_error = e
            if _is_quota_error(e) and idx < len(ordered) - 1:
                print(f"Model {model!r} quota hit ({type(e).__name__}), trying next...")
                continue
            raise
    assert last_error is not None
    raise last_error

st.set_page_config(page_title="QuestMaker", page_icon=":material/map:")
st.title("QuestMaker", icon=":material/map:")
st.markdown("Hide the treasure, we'll make the hunt")
st.caption(
    "You pick the hiding spots — we turn each one into a puzzle "
    "that points to the next. "
    "Puzzles are AI-selected (Google Gemini flash-lite family) from a large catalog, not AI-generated."
)

st.space("small")
steps = st.columns(3, border=True, gap="small")
with steps[0]:
    st.markdown(":material/location_on: **You hide**")
    st.caption("List your spots, e.g., couch, fridge, balcony")
with steps[1]:
    st.markdown(":material/extension: **We puzzle**")
    st.caption("The right brain-teaser per spot")
with steps[2]:
    st.markdown(":material/emoji_events: **They hunt**")
    st.caption("Each answer reveals where to sneak to next")

st.space("small")


@st.cache_resource
def get_client():
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )


client = get_client()

WORKING_MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-3.8-flash", "gemini-3.7-flash", "gemini-3.6-flash", "gemini-3.5-flash"]

st.session_state.setdefault("ai_model", WORKING_MODELS[0])
st.session_state.setdefault("eligibility_words", [])
st.session_state.setdefault("quest_request_json", None)
st.session_state.setdefault("quest_response_json", None)
st.session_state.setdefault("quest_images", [])
st.session_state.setdefault("quest_fingerprint", None)
st.session_state.setdefault("repick_notice", {})
st.session_state.setdefault("repick_pending", {})
if USE_MOCK_RESPONSE:
    st.session_state.setdefault("clue_words", MOCK_CLUE_WORDS)
    st.session_state.setdefault("participants_info", MOCK_PARTICIPANTS)

if DEV_MODE:
    with st.sidebar:
        st.selectbox("Model", WORKING_MODELS, key="ai_model")


# Main part


with st.container(border=False, gap="small"):
    st.subheader("Create your quest", icon=":material/play_arrow:")
    st.caption("Add your hiding spots and tell us who is hunting.")
    with st.form("quest_words", border=False):

        st.segmented_control(
            "Task mix",
            ["Any", "More text", "More math", "Balanced"],
            default="Any",
            key="type_preference",
        )
        clue_words = st.text_input(
            "Clue-words *",
            placeholder="coach, dinner table",
            key="clue_words",
        )
        st.text_area(
            "How do you describe your participants? (This data is not stored)",
            placeholder="Age, knowledge, preferences, e.g. kids 8-10, easy math",
            key="participants_info",
            max_chars=500,
        )
        submitted = st.form_submit_button(
            "Make my hunt", type="primary", icon=":material/play_arrow:"
        )
    st.caption(
        "AI selection may misjudge difficulty and may repeat puzzle types "
        "when nothing fresh fits."
    )

if submitted:
    words = [w.strip() for w in clue_words.split(",") if w.strip()]
    st.session_state.eligibility_words = words
    st.session_state.quest_request_json = None
    st.session_state.quest_response_json = None
    st.session_state.quest_images = []
    st.session_state.quest_fingerprint = None
    st.session_state["repick_notice"] = {}
    st.session_state["repick_pending"] = {}
    

if st.session_state.eligibility_words:
    type_preference = st.session_state.get("type_preference", "Any")
    if type_preference not in ("Any", "More text", "More math", "Balanced"):
        type_preference = "Any"
    candidates = [
        [
            ScoredOption(task_id=tid, score=TASKS[tid].score(w))
            for tid in TASK_ORDER if TASKS[tid].eligible(w)
        ]
        for w in st.session_state.eligibility_words
    ]
    eligible_union = {opt.task_id for opts in candidates for opt in opts}
    request = QuestRequest(
        words=list(st.session_state.eligibility_words),
        candidates=candidates,
        catalog={
            tid: CatalogEntry(
                name=TASKS[tid].name,
                description=TASKS[tid].description,
                type=TASKS[tid].type,
            )
            for tid in sorted(eligible_union)
        },
        type_preference=type_preference,
        user_message=st.session_state.get("participants_info", "").strip()[:500],
    )
    print(request.model_dump_json(indent=2))
    

    model_slot = st.container()
    if USE_MOCK_RESPONSE:
        if st.session_state.quest_response_json is None:
            st.session_state.quest_request_json = request.model_dump_json()
            st.session_state.quest_response_json = json.dumps(MOCK_RESPONSE, indent=2)
            print(st.session_state.quest_response_json)
    elif any(not ids for ids in candidates):
        st.warning("Skipped model call: a word has no eligible tasks.")
    elif st.session_state.quest_request_json != request.model_dump_json():
        with model_slot.spinner(
            "Thinking — generating the most suitable quest for you..."
        ):
            try:
                interaction, used_model, fell_back = create_with_fallback(
                    input=build_prompt(request),
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_schema=QuestResponse.model_json_schema(),
                    timeout=60,
                )
                st.session_state.ai_model = used_model
                if fell_back:
                    st.caption("High demand — used backup model")
                raw = interaction.output_text or ""
                result = QuestResponse.model_validate_json(raw)
                for sel in result.picks:
                    sel.why = sel.why[:120]
                st.session_state.quest_request_json = request.model_dump_json()
                st.session_state.quest_response_json = result.model_dump_json(indent=2)
                print(st.session_state.quest_response_json)
            except Exception as e:
                st.error(f"Model call failed: {type(e).__name__}: {e}")
                with st.expander("Debug details"):
                    st.exception(e)
                print(f"Model call failed: {type(e).__name__}: {e}")
    if st.session_state.quest_response_json:
        try:
            quest = QuestResponse.model_validate_json(
                st.session_state.quest_response_json
            )
        except Exception as e:
            st.error(f"Invalid model response: {type(e).__name__}: {e}")
            quest = None
        if quest is not None:
            words = st.session_state.eligibility_words
            if len(quest.picks) != len(words):
                st.error(
                    "Model response does not match the words: "
                    f"{len(quest.picks)} picks for {len(words)} words."
                )
            else:
                st.subheader("Your hunt", icon=":material/map:")
                st.caption(f"{len(words)} stops • Solve each to find the next")
                # Fingerprint the current quest. Only invalidate images for
                # indices whose (word, task) changed so repicks keep the rest.
                fingerprint = [(w, sel.task_id) for w, sel in zip(words, quest.picks)]
                old_fingerprint = st.session_state.quest_fingerprint
                images = list(st.session_state.get("quest_images", []))
                if old_fingerprint != fingerprint:
                    if (
                        not isinstance(old_fingerprint, list)
                        or len(old_fingerprint) != len(fingerprint)
                        or len(images) != len(fingerprint)
                    ):
                        images = [None] * len(words)
                    else:
                        for idx, (old_fp, new_fp) in enumerate(
                            zip(old_fingerprint, fingerprint)
                        ):
                            if old_fp != new_fp:
                                images[idx] = None
                    st.session_state["quest_images"] = images
                    st.session_state.quest_fingerprint = fingerprint
                pending_map = st.session_state.get("repick_pending", {})
                if not isinstance(pending_map, dict):
                    pending_map = {}
                    st.session_state["repick_pending"] = pending_map
                any_repick_pending = any(pending_map.values())
                for i, (w, sel) in enumerate(zip(words, quest.picks)):
                    task = TASKS.get(sel.task_id)
                    if task is None:
                        st.error(f"Unknown task id: {sel.task_id!r}")
                        continue
                    is_repick_pending = bool(pending_map.get(i, False))
                    # Reuse the already-generated image. Hint pills only change
                    # selection state, so encode() must NOT run again here.
                    # While a replacement is in flight, keep showing the cached
                    # old image and never re-encode it: imgs[i] is cleared only
                    # after the new task_id is confirmed below.
                    cached_images = st.session_state.get("quest_images", [])
                    image = cached_images[i] if i < len(cached_images) else None
                    if image is None and not is_repick_pending:
                        try:
                            encode = getattr(task, "encode", None)
                            if not callable(encode):
                                raise TypeError(
                                    f"Task {task.name!r} does not provide a callable encode() method"
                                )
                            image = encode(w)
                            imgs = list(st.session_state.get("quest_images", []))
                            # update copy and reassign to avoid typing issues with session_state __setitem__
                            imgs[i] = image
                            st.session_state["quest_images"] = imgs
                        except Exception as e:
                            st.error(f"Could not encode {w!r} with {task.name}: {e}")
                            continue
                    is_last = i == len(words) - 1
                    with st.container(border=True):
                        if is_last:
                            st.badge(
                                f"Final stop — {w} → prize",
                                icon=":material/emoji_events:",
                                color="green",
                            )
                        else:
                            st.badge(
                                f"Stop {i + 1} — {w}",
                                icon=":material/location_on:",
                                color="blue",
                            )
                        img_col, hint_col = st.columns(2, vertical_alignment="center")
                        with img_col:
                            if image is not None:
                                st.image(image, alt=f"{task.name} task for {w}")  # type: ignore
                            else:
                                st.caption("Loading replacement puzzle...")
                        with hint_col:
                            st.markdown(f":material/extension: **{task.name}**")
                            if sel.why:
                                st.caption(f"AI reasoning: {sel.why}")
                            with st.expander("Need a nudge?"):
                                st.markdown(
                                    "\n".join(f"- {h}" for h in task.hints)
                                )
                            with st.expander("Change this puzzle"):
                                st.radio(
                                    "What's wrong?",
                                    ["Too easy", "Too hard", "Different"],
                                    index=2,
                                    key=f"repick_reason_{i}",
                                    horizontal=True,
                                    disabled=is_repick_pending,
                                )
                                st.text_input(
                                    "What didn't work? (optional)",
                                    placeholder="e.g. too simple for a 12-year-old",
                                    max_chars=200,
                                    key=f"repick_note_{i}",
                                    disabled=is_repick_pending,
                                )
                                notice = st.session_state.get("repick_notice", {}).get(i)
                                if notice:
                                    st.caption(notice)
                                pressed = st.button(
                                    "Finding another puzzle..."
                                    if is_repick_pending
                                    else "Get another puzzle",
                                    key=f"repick_btn_{i}",
                                    icon=":material/refresh:",
                                    on_click=_request_repick,
                                    args=(i,),
                                    disabled=is_repick_pending or any_repick_pending,
                                )
                                if is_repick_pending or pressed:
                                    reason_val = st.session_state.get(
                                        f"repick_reason_{i}", "Different"
                                    )
                                    note_val = (
                                        st.session_state.get(f"repick_note_{i}", "") or ""
                                    ).strip()[:200]
                                    options = candidates[i]
                                    locked = [
                                        s.task_id
                                        for j, s in enumerate(quest.picks)
                                        if j != i
                                    ]
                                    locked_set = set(locked)
                                    score_by_id = {o.task_id: o.score for o in options}
                                    current_score = score_by_id.get(sel.task_id, 3)
                                    new_id: str | None = None
                                    new_why = ""
                                    repeated = False
                                    if USE_MOCK_RESPONSE:
                                        new_id, repeated = pick_local_replacement(
                                            options,
                                            sel.task_id,
                                            locked_set,
                                            reason_val,
                                            type_preference,
                                            request.catalog,
                                        )
                                        if new_id is not None:
                                            new_task = TASKS.get(new_id)
                                            new_score = score_by_id.get(new_id, "?")
                                            extra = f" — {note_val}" if note_val else ""
                                            new_why = (
                                                f"Replacement ({reason_val.lower()}, "
                                                f"score {new_score}): "
                                                f"{new_task.name if new_task else new_id}"
                                                f"{extra}"
                                            )[:120]
                                    else:
                                        with st.spinner("Finding another puzzle..."):
                                            try:
                                                prompt = build_repick_prompt(
                                                    w,
                                                    options,
                                                    request.catalog,
                                                    sel.task_id,
                                                    current_score,
                                                    locked,
                                                    reason_val,
                                                    note_val,
                                                    type_preference,
                                                    request.user_message,
                                                )
                                                interaction, used_model, _ = create_with_fallback(
                                                    input=prompt,
                                                    system_instruction=REPICK_SYSTEM_INSTRUCTION,
                                                    response_schema=Selection.model_json_schema(),
                                                    timeout=60,
                                                )
                                                st.session_state.ai_model = used_model
                                                result = Selection.model_validate_json(
                                                    interaction.output_text or ""
                                                )
                                                cand_ids = {o.task_id for o in options}
                                                has_unused = any(
                                                    o.task_id != sel.task_id
                                                    and o.task_id not in locked_set
                                                    for o in options
                                                )
                                                if (
                                                    result.task_id not in cand_ids
                                                    or result.task_id == sel.task_id
                                                    or (
                                                        result.task_id in locked_set
                                                        and has_unused
                                                    )
                                                ):
                                                    raise ValueError(
                                                        "Model repick invalid or duplicated, "
                                                        "using local fallback"
                                                    )
                                                new_id = result.task_id
                                                new_why = result.why[:120]
                                                repeated = new_id in locked_set
                                            except Exception as e:
                                                print(f"Repick model failed, fallback: {e}")
                                                new_id, repeated = pick_local_replacement(
                                                    options,
                                                    sel.task_id,
                                                    locked_set,
                                                    reason_val,
                                                    type_preference,
                                                    request.catalog,
                                                )
                                                if new_id is not None:
                                                    new_task = TASKS.get(new_id)
                                                    new_score = score_by_id.get(new_id, "?")
                                                    new_why = (
                                                        f"Replacement ({reason_val.lower()}, "
                                                        f"score {new_score}): "
                                                        f"{new_task.name if new_task else new_id}"
                                                    )[:120]
                                                else:
                                                    new_why = (
                                                        "Could not find another puzzle: "
                                                        f"{type(e).__name__}: {e}"
                                                    )
                                    if new_id is None:
                                        notices = dict(
                                            st.session_state.get("repick_notice", {})
                                        )
                                        notices[i] = (
                                            new_why
                                            or "No alternative puzzle available for this word."
                                        )
                                        st.session_state["repick_notice"] = notices
                                        pending_map.pop(i, None)
                                        st.rerun()
                                    else:
                                        quest.picks[i].task_id = new_id
                                        quest.picks[i].why = new_why
                                        st.session_state.quest_response_json = (
                                            quest.model_dump_json(indent=2)
                                        )
                                        imgs = list(
                                            st.session_state.get("quest_images", [])
                                        )
                                        if i < len(imgs):
                                            imgs[i] = None
                                            st.session_state["quest_images"] = imgs
                                        notices = dict(
                                            st.session_state.get("repick_notice", {})
                                        )
                                        if repeated:
                                            notices[i] = (
                                                "No fresh puzzle left — repeated the closest fit."
                                            )
                                        elif i in notices:
                                            notices.pop(i, None)
                                        st.session_state["repick_notice"] = notices
                                        pending_map.pop(i, None)
                                        st.rerun()
                    if not is_last:
                        st.caption(
                            ":material/arrow_downward: Solve to reveal the next clue",
                            text_alignment="center",
                        )
                # Export the rendered quest (cached images + hint lists).
                stops = []
                for i, (w, sel) in enumerate(zip(words, quest.picks)):
                    task = TASKS.get(sel.task_id)
                    images = st.session_state.get("quest_images", [])
                    img = images[i] if task is not None and i < len(images) else None
                    if task is None or img is None:
                        continue
                    stops.append(
                        QuestStop(
                            number=i + 1,
                            clue_word=w,
                            image=img,
                            hints=list(task.hints),
                            task_name=task.name,
                        )
                    )
                if stops:
                    with st.container(horizontal_alignment="right"):
                        st.download_button(
                            "Print my hunt",
                            data=build_quest_pdf(stops),
                            file_name="quest.pdf",
                            mime="application/pdf",
                            icon=":material/picture_as_pdf:",
                            type="primary",
                        )
