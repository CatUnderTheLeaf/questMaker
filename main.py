from google import genai
import streamlit as st

from tasks import load_tasks

TASKS = load_tasks()
# Every registered task runs for each clue word. New modules added under
# tasks/ register themselves via @register_task, so nothing to update here.
TASK_ORDER = sorted(TASKS)

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
    submitted = st.form_submit_button(
        "Generate tasks", type="primary", icon=":material/play_arrow:"
    )

if submitted:
    for key in [k for k in st.session_state if k.startswith("hint_")]:
        del st.session_state[key]
    words = [w.strip() for w in clue_words.split(",") if w.strip()]
    items = []
    skipped = []
    for w in words:
        encoded_any = False
        errors = []
        for task_id in TASK_ORDER:
            task = TASKS[task_id]
            if not task.eligible(w):
                continue
            try:
                encode = getattr(task, "encode", None)
                if not callable(encode):
                    raise TypeError(f"Task {task.name!r} does not provide a callable encode() method")

                items.append(
                    {
                        "word": w,
                        "task_id": task.id,
                        "task_name": task.name,
                        "image": encode(w),
                        "hints": task.hints,
                    }
                )
                encoded_any = True
            except Exception as e:
                errors.append(f"Could not encode {w!r} with {task.name}: {e}")
        if not encoded_any:
            skipped.append(w)
            for msg in errors:
                st.error(msg)
    st.session_state.quest_items = items
    if skipped:
        st.warning(f"Skipped (unsuitable for all tasks): {', '.join(skipped)}")

for i, item in enumerate(st.session_state.quest_items):
    with st.container(border=True):
        st.subheader(f"{i + 1}. {item['word']} — {item['task_name']}")
        img_col, hint_col = st.columns(2)
        with img_col:
            st.image(item["image"], alt=f"{item['task_name']} task for {item['word']}")
        with hint_col:
            st.pills(
                "Hint",
                item["hints"],
                selection_mode="single",
                wrap=True,
                key=f"hint_{i}",
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
