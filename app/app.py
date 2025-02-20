import streamlit as st
import requests

# --------------------------------------------------------------------------
# CONFIGURACIÓN DE LA PÁGINA
# --------------------------------------------------------------------------
st.set_page_config(page_title="Chat RAG de Grafos", layout="wide")

# --------------------------------------------------------------------------
# ESTILOS CSS
# --------------------------------------------------------------------------
st.markdown("""
<style>
/* Fondo oscuro para la zona principal */
main.block-container {
    background-color: #1e1e1e;
    color: #f0f0f0;
    padding: 0.5rem 1rem;
}

/* Barra lateral con fondo oscuro */
[data-testid="stSidebar"] {
    background-color: #2b2b2b;
    color: #f0f0f0;
}

/* Títulos y textos de la barra lateral */
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] p, 
[data-testid="stSidebar"] label {
    color: #f0f0f0;
}

/* Estilo para el botón en la barra lateral */
.stButton > button {
    background-color: #E74C3C !important; /* Rojo oscuro, por ejemplo */
    color: #fff !important;
    border: none !important;
    padding: 0.5rem 1rem !important;
    margin-top: 0.5rem !important;
    border-radius: 4px !important;
    font-size: 0.9rem !important;
    cursor: pointer;
}
.stButton > button:hover {
    background-color: #C0392B !important; /* Un poco más oscuro al pasar el mouse */
}

/* Ajuste de la fuente del selectbox en la barra lateral */
[data-testid="stSidebar"] .stSelectbox label {
    color: #f0f0f0 !important;
}

/* Ajustes en la parte principal del chat */
.chat-container {
    margin-top: 1rem;
}
</style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------
# URL DE LA API (MODIFICA SI ES NECESARIO)
# --------------------------------------------------------------------------
API_URL = "http://host.docker.internal:8000/chat"

# --------------------------------------------------------------------------
# ESTADO DE SESIÓN
# --------------------------------------------------------------------------
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hola, soy tu asistente. ¿En qué puedo ayudarte hoy?"}
    ]
if "selected_package" not in st.session_state:
    st.session_state.selected_package = "faucet"

# --------------------------------------------------------------------------
# FUNCIÓN PARA OBTENER RESPUESTA DESDE LA API
# --------------------------------------------------------------------------
def obtener_respuesta_desde_api(user_input: str, package: str):
    params = {
        "q": user_input,
        "package": package,
        "limit": 5
    }
    try:
        response = requests.post(API_URL, params=params)
        if response.status_code == 200:
            data = response.json()
            return data.get("answer", "No se pudo obtener respuesta.")
        else:
            return f"Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"Error al conectar con la API: {e}"

# --------------------------------------------------------------------------
# FUNCIÓN PARA BORRAR HISTORIAL
# --------------------------------------------------------------------------
def borrar_historial():
    st.session_state.messages = [
        {"role": "assistant", "content": "Historial borrado. ¿En qué puedo ayudarte hoy?"}
    ]

# --------------------------------------------------------------------------
# BARRA LATERAL
# --------------------------------------------------------------------------
with st.sidebar:
    st.title("Chat RAG de Grafos")
    st.write("Bienvenido a tu asistente de chat con la API RAG de Grafos.")

    # Selectbox y botón en la barra lateral
    st.session_state.selected_package = st.selectbox(
        "Selecciona el paquete:",
        options=["faucet", "taplock"],
        index=0,
        key="package_select"
    )
    st.button("Borrar Historial", on_click=borrar_historial)

# --------------------------------------------------------------------------
# ZONA PRINCIPAL PARA EL CHAT
# --------------------------------------------------------------------------
st.markdown('<div class="chat-container">', unsafe_allow_html=True)

st.markdown("## Chat")

# Mostrar historial de mensajes
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# Campo de entrada tipo chat
if user_input := st.chat_input("Escribe tu pregunta..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.write(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Pensando..."):
            respuesta = obtener_respuesta_desde_api(
                user_input,
                st.session_state.selected_package
            )
            st.write(respuesta)
    st.session_state.messages.append({"role": "assistant", "content": respuesta})

st.markdown('</div>', unsafe_allow_html=True)
