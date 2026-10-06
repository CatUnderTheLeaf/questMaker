from google import genai
import streamlit as st

st.set_page_config(page_title="QuestMaker chat")
st.title("Chat", icon=":material/chat:")


@st.cache_resource
def get_client():
    return genai.Client(
        api_key=st.secrets["GEMINI_API_KEY"]
    )


client = get_client()

WORKING_MODELS = ["gemini-3.5-flash", "gemini-3.5-flash-lite"]

st.session_state.setdefault("ai_model", WORKING_MODELS[0])
st.session_state.setdefault("messages", [])
st.session_state.setdefault("prev_interaction_id", None)

with st.sidebar:
    st.selectbox("Model", WORKING_MODELS, key="ai_model")
    if st.button("Clear chat", icon=":material/delete:"):
        st.session_state.messages = []
        st.session_state.prev_interaction_id = None
        st.rerun()

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if prompt := st.chat_input("What is up?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        try:
            with st.spinner("Thinking..."):
                interaction = client.interactions.create(
                    model=st.session_state.ai_model,
                    input=prompt,
                    previous_interaction_id=st.session_state.prev_interaction_id,
                    timeout=60,
                )
            response = interaction.output_text or "(empty response)"
            st.write(response)
        except Exception as e:
            st.error(f"Gemini call failed: {type(e).__name__}: {e}")
            with st.expander("Debug details"):
                st.write(f"model: {st.session_state.ai_model}")
                st.write(f"prev_interaction_id: {st.session_state.prev_interaction_id}")
                st.exception(e)
            st.stop()

    st.session_state.messages.append({"role": "assistant", "content": response})
    st.session_state.prev_interaction_id = interaction.id
