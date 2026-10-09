import json

from google import genai
import streamlit as st

from tasks import load_tasks

from utils.types import CatalogEntry, QuestRequest, QuestResponse
from utils.pdf import QuestStop, build_quest_pdf

# Temporary: mock the model response for UI design (no model call).
USE_MOCK_RESPONSE = True
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
    "picks[i] is for words[i] and task_id must come from candidates[i]. "
    "Judge suitability from the task description in catalog[id].description "
    "(name and type are secondary). "
    "type_preference controls the mix of catalog entry types ('text' vs 'math'): "
    "'Any' means ignore type; 'More text' means prefer entries with type 'text'; "
    "'More math' means prefer entries with type 'math'; 'Balanced' means alternate "
    "between 'text' and 'math' across picks. "
    "Preference is a tiebreaker: when two candidate tasks suit a word about equally, "
    "pick the one matching the preference; never pick a clearly unsuitable task just "
    "to satisfy the mix. "
    "user_message is context which can help guide the selection. "
    "Keep why short but explanatory, not just a description of the task."
)


def build_prompt(req: QuestRequest) -> str:
    return req.model_dump_json(indent=2)

st.set_page_config(page_title="QuestMaker", page_icon=":material/map:")
st.title("QuestMaker", icon=":material/map:")
st.markdown("Hide the treasure, we'll make the hunt")
st.caption(
    "You pick the hiding spots — we turn each one into a puzzle "
    "that points to the next."
)

st.space("small")
steps = st.columns(3, border=True, gap="small")
with steps[0]:
    st.markdown(":material/location_on: **You hide**")
    st.caption("List your spots: couch, fridge, balcony")
with steps[1]:
    st.markdown(":material/extension: **We puzzle**")
    st.caption("We pick a perfect little brain-teaser per spot")
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
st.session_state.setdefault("messages", [])
st.session_state.setdefault("prev_interaction_id", None)
st.session_state.setdefault("eligibility_words", [])
st.session_state.setdefault("quest_request_json", None)
st.session_state.setdefault("quest_response_json", None)
st.session_state.setdefault("quest_images", [])
st.session_state.setdefault("quest_fingerprint", None)
if USE_MOCK_RESPONSE:
    st.session_state.setdefault("clue_words", MOCK_CLUE_WORDS)
    st.session_state.setdefault("participants_info", MOCK_PARTICIPANTS)

with st.sidebar:
    st.selectbox("Model", WORKING_MODELS, key="ai_model")
    if st.button("Clear chat", icon=":material/delete:"):
        st.session_state.messages = []
        st.session_state.prev_interaction_id = None
        st.rerun()


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
            "Clue-words",
            placeholder="coach, dinner table",
            key="clue_words",
        )
        st.text_area(
            "How do you describe your participants?",
            placeholder="Age, knowledge, preferences, e.g. kids 8-10, easy math",
            key="participants_info",
            max_chars=500,
        )
        submitted = st.form_submit_button(
            "Make my hunt", type="primary", icon=":material/play_arrow:"
        )

if submitted:
    words = [w.strip() for w in clue_words.split(",") if w.strip()]
    st.session_state.eligibility_words = words
    st.session_state.quest_request_json = None
    st.session_state.quest_response_json = None
    st.session_state.quest_images = []
    st.session_state.quest_fingerprint = None
    

if st.session_state.eligibility_words:
    type_preference = st.session_state.get("type_preference", "Any")
    if type_preference not in ("Any", "More text", "More math", "Balanced"):
        type_preference = "Any"
    candidates = [
        [tid for tid in TASK_ORDER if TASKS[tid].eligible(w)]
        for w in st.session_state.eligibility_words
    ]
    eligible_union = {tid for ids in candidates for tid in ids}
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
                interaction = client.interactions.create(
                    model=st.session_state.ai_model,
                    input=build_prompt(request),
                    system_instruction=SYSTEM_INSTRUCTION,
                    response_format={
                        "type": "text",
                        "mime_type": "application/json",
                        "schema": QuestResponse.model_json_schema(),
                    },
                    timeout=60,
                )
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
                # Fingerprint the current quest. If words or picked tasks changed,
                # drop cached images so a fresh set is generated once.
                fingerprint = [(w, sel.task_id) for w, sel in zip(words, quest.picks)]
                if st.session_state.quest_fingerprint != fingerprint:
                    st.session_state.quest_fingerprint = fingerprint
                    st.session_state.quest_images = [None] * len(words)
                for i, (w, sel) in enumerate(zip(words, quest.picks)):
                    task = TASKS.get(sel.task_id)
                    if task is None:
                        st.error(f"Unknown task id: {sel.task_id!r}")
                        continue
                    # Reuse the already-generated image. Hint pills only change
                    # selection state, so encode() must NOT run again here.
                    image = st.session_state.quest_images[i]
                    if image is None:
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
                            st.image(image, alt=f"{task.name} task for {w}")  # type: ignore
                        with hint_col:
                            st.markdown(f":material/extension: **{task.name}**")
                            if sel.why:
                                st.caption(sel.why)
                            with st.expander(f"Need a nudge?"):
                                st.markdown(
                                    "\n".join(f"- {h}" for h in task.hints)
                                )
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


with st.sidebar:
    if prompt := st.chat_input("What is up?"):
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            with st.spinner("Thinking..."):
                interaction = client.interactions.create(
                    model=st.session_state.ai_model,
                    input=prompt,
                    previous_interaction_id=st.session_state.prev_interaction_id,
                    timeout=60,
                )
            response = interaction.output_text or "(empty response)"
        except Exception as e:
            st.error(f"Gemini call failed: {type(e).__name__}: {e}")
            with st.expander("Debug details"):
                st.write(f"model: {st.session_state.ai_model}")
                st.write(f"prev_interaction_id: {st.session_state.prev_interaction_id}")
                st.exception(e)
            st.stop()

        st.session_state.messages.append({"role": "assistant", "content": response})
        st.session_state.prev_interaction_id = interaction.id

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
