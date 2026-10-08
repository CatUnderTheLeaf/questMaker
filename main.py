from typing import Literal

import json

from google import genai
import streamlit as st

from tasks import load_tasks

from lib.types import CatalogEntry, QuestRequest, QuestResponse

# Temporary: mock the model response for UI design (no model call).
USE_MOCK_RESPONSE = True
MOCK_CLUE_WORDS = "table, cat, refrigerator"
MOCK_PARTICIPANTS = (
    "my kids are 6 years old, know a little bit of math, "
    "just simple subtraction and addition."
)
MOCK_RESPONSE = {
    "picks": [
        {
            "task_id": "table_borders",
            "why": "A short, visual table-based game that relies on spatial recognition rather than complex arithmetic.",
        },
        {
            "task_id": "reverse_word",
            "why": "Simple for 6-year-olds; reversing a short word like 'cat' is an easy and engaging logic puzzle.",
        },
        {
            "task_id": "shopping_list",
            "why": "Observational and intuitive, requiring only basic reading skills, perfectly suited for young children.",
        },
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
    "Honor type_preference; user_message is context only. "
    "Keep why short."
)


def build_prompt(req: QuestRequest) -> str:
    return (
        "Select the most suitable task for each word "
        "based on its description in catalog.\n"
        f"{req.model_dump_json(indent=2)}\n"
        "Return picks aligned positionally to words."
    )

st.set_page_config(page_title="QuestMaker chat")
st.title("Quest builder")


@st.cache_resource
def get_client():
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )


client = get_client()

WORKING_MODELS = ["gemini-3.1-flash-lite","gemini-3.5-flash", "gemini-3.5-flash-lite"]

st.session_state.setdefault("ai_model", WORKING_MODELS[0])
st.session_state.setdefault("messages", [])
st.session_state.setdefault("prev_interaction_id", None)
st.session_state.setdefault("quest_items", [])
st.session_state.setdefault("eligibility_words", [])
st.session_state.setdefault("quest_request_json", None)
st.session_state.setdefault("quest_response_json", None)
if USE_MOCK_RESPONSE:
    st.session_state.setdefault("clue_words", MOCK_CLUE_WORDS)
    st.session_state.setdefault("participants_info", MOCK_PARTICIPANTS)

with st.sidebar:
    st.selectbox("Model", WORKING_MODELS, key="ai_model")
    if st.button("Clear chat", icon=":material/delete:"):
        st.session_state.messages = []
        st.session_state.prev_interaction_id = None
        st.rerun()

with st.form("quest_words", border=False):
    clue_words = st.text_input(
        "Clue-words",
        placeholder="coach, dinner table",
        key="clue_words",
    )
    st.segmented_control(
        "Task mix",
        ["Any", "More text", "More math", "Balanced"],
        default="Any",
        key="type_preference",
    )
    st.text_area(
        "Participants",
        placeholder="Age, knowledge, preferences, e.g. kids 8-10, easy math",
        key="participants_info",
        max_chars=500,
    )
    submitted = st.form_submit_button(
        "Generate tasks", type="primary", icon=":material/play_arrow:"
    )

if submitted:
    for key in [k for k in st.session_state if k.startswith("hint_")]:
        del st.session_state[key]
    words = [w.strip() for w in clue_words.split(",") if w.strip()]
    st.session_state.eligibility_words = words
    st.session_state.quest_request_json = None
    st.session_state.quest_response_json = None
    # items = []
    # skipped = []
    # for w in words:
    #     encoded_any = False
    #     errors = []
    #     for task_id in TASK_ORDER:
    #         task = TASKS[task_id]
    #         if not task.eligible(w):
    #             continue
    #         try:
    #             encode = getattr(task, "encode", None)
    #             if not callable(encode):
    #                 raise TypeError(f"Task {task.name!r} does not provide a callable encode() method")

    #             items.append(
    #                 {
    #                     "word": w,
    #                     "task_id": task.id,
    #                     "task_name": task.name,
    #                     "image": encode(w),
    #                     "hints": task.hints,
    #                 }
    #             )
    #             encoded_any = True
    #         except Exception as e:
    #             errors.append(f"Could not encode {w!r} with {task.name}: {e}")
    #     if not encoded_any:
    #         skipped.append(w)
    #         for msg in errors:
    #             st.error(msg)
    # st.session_state.quest_items = items
    # if skipped:
    #     st.warning(f"Skipped (unsuitable for all tasks): {', '.join(skipped)}")

if st.session_state.eligibility_words:
    pref_map: dict[str, Literal["any", "more_text", "more_math", "balanced"]] = {
        "Any": "any",
        "More text": "more_text",
        "More math": "more_math",
        "Balanced": "balanced",
    }
    type_preference = pref_map.get(
        st.session_state.get("type_preference", "Any"),
        "any",
    )
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
                for i, (w, sel) in enumerate(zip(words, quest.picks)):
                    task = TASKS.get(sel.task_id)
                    if task is None:
                        st.error(f"Unknown task id: {sel.task_id!r}")
                        continue
                    try:
                        encode = getattr(task, "encode", None)
                        if not callable(encode):
                            raise TypeError(
                                f"Task {task.name!r} does not provide a callable encode() method"
                            )
                        image: object = encode(w)
                    except Exception as e:
                        st.error(f"Could not encode {w!r} with {task.name}: {e}")
                        continue
                    with st.container(border=True):
                        st.subheader(f"{i + 1}. {w} — {task.name}")
                        if sel.why:
                            st.caption(sel.why)
                        img_col, hint_col = st.columns(2)
                        with img_col:
                            st.image(image, alt=f"{task.name} task for {w}")  # type: ignore
                        with hint_col:
                            st.pills(
                                "Hint",
                                task.hints,
                                selection_mode="single",
                                wrap=True,
                                key=f"hint_{i}",
                            )

# for i, item in enumerate(st.session_state.quest_items):
#     with st.container(border=True):
#         st.subheader(f"{i + 1}. {item['word']} — {item['task_name']}")
#         img_col, hint_col = st.columns(2)
#         with img_col:
#             st.image(item["image"], alt=f"{item['task_name']} task for {item['word']}")
#         with hint_col:
#             st.pills(
#                 "Hint",
#                 item["hints"],
#                 selection_mode="single",
#                 wrap=True,
#                 key=f"hint_{i}",
#             )

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
