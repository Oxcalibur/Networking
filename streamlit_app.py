import logging
import os
import streamlit as st
from pypdf import PdfReader
from google import genai
from google.genai import types

# ==========================================
# 1. SISTEMA DE AUTENTICACIÓN
# ==========================================
def check_password() -> bool:
    """Maneja el login de la aplicación."""
    if st.session_state.get("password_correct", False):
        return True

    with st.form("login_form"):
        st.subheader("🔒 Iniciar Sesión")
        username = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Entrar")
        
    if submitted:
        # Obtenemos credenciales de st.secrets (con fallback por defecto)
        valid_user = st.secrets.get("APP_USER", "admin")
        valid_pass = st.secrets.get("APP_PASS", "admin123")
        
        if username == valid_user and password == valid_pass:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("Usuario o contraseña incorrectos")
    return False

# ==========================================
# 2. LECTURA DE CONOCIMIENTO (PDFs)
# ==========================================
@st.cache_data(show_spinner=False)
def load_knowledge_base(folder_path: str = "knowledge_base") -> str:
    """Lee todos los archivos PDF en la carpeta dada y extrae su texto."""
    if not os.path.exists(folder_path):
        return ""
    
    combined_text = ""
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(".pdf"):
            filepath = os.path.join(folder_path, filename)
            try:
                reader = PdfReader(filepath)
                text = f"\n--- PERFIL / DOCUMENTO: {filename} ---\n"
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
                combined_text += text
            except Exception as e:
                logging.error(f"Error leyendo {filename}: {e}")
    return combined_text

# ==========================================
# 3. LÓGICA DE INTELIGENCIA ARTIFICIAL
# ==========================================
def get_networking_matches(user_need: str, db_context: str, api_key: str) -> str:
    """
    Envía la necesidad del usuario y la base de datos a Gemini para obtener los 3 mejores matches.
    
    Args:
        user_need (str): La descripción de lo que busca o necesita el usuario.
        db_context (str): El texto extraído de todos los PDFs de la base de conocimiento.
        api_key (str): La clave de API de Google GenAI.
        
    Returns:
        str: La respuesta generada por el modelo con los matches y sus justificaciones, 
             o un mensaje de error si la petición falla.
    """
    try:
        # 1. Inicializamos el cliente con el nuevo SDK
        client = genai.Client(api_key=api_key)
        
        system_instruction = (
            "Actúa como un Experto en Networking Empresarial altamente capacitado. "
            "Tu objetivo es analizar la necesidad de un usuario y hacer 'matchmaking' con "
            "los perfiles extraídos de los documentos PDF proporcionados en tu contexto.\n"
            "REGLAS ESTRICTAS:\n"
            "1. NO INVENTES información, nombres, ni perfiles que no estén en los documentos provistos.\n"
            "2. Debes clasificar a los candidatos por NIVELES DE MATCH (ej. Match Alto, Match Medio, Match Bajo) e incluir un porcentaje estimado de afinidad (ej. 85%).\n"
            "3. Para cada match, incluye el nombre del perfil (o documento), el Nivel de Match con su porcentaje, y una "
            "justificación basada estrictamente en la evidencia de los PDFs.\n"
            "4. Si la necesidad del usuario es ambigua o necesitas más detalles para dar una respuesta precisa, puedes hacer preguntas de seguimiento para clarificar antes de dar los matches finales.\n"
            "5. Si el usuario menciona una categoría amplia (ej. 'tecnología', 'marketing'), intenta clarificar si busca un proveedor (comprar) o un cliente (vender). Al responder, asegúrate de incluir todos los perfiles relevantes para esa categoría.\n"
            "6. Diferencia claramente entre buscar un 'proveedor' y un 'cliente'. Si el usuario busca un **proveedor** (quiere comprar), solo perfiles que **ofrecen** ese servicio son un match alto. Perfiles que **buscan** ese mismo servicio son un match nulo o bajo para esta consulta. Si el usuario busca un **cliente** (quiere vender), la lógica es la inversa."
        )

        prompt = (
            f"Contenido de los documentos (Base de Conocimiento):\n{db_context}\n\n"
            f"Necesidad del usuario actual:\n'{user_need}'\n\n"
            "Por favor, devuelve los mejores matches clasificados por nivel de match y justificados."
        )
        
        # 2. Generamos el contenido a través del cliente
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.7
            )
        )

        return response.text

    except Exception as e:
        logging.error(f"Error al conectar con Gemini: {e}")
        # 4. Mostramos un error detallado al usuario para facilitar el diagnóstico
        return (
            "⚠️ **Hubo un problema al procesar tu solicitud.**\n\n"
            "**Detalles del error de la API:**\n"
            f"```\n{e}\n```\n\n"
            "**Posibles causas:**\n"
            "*   Tu API Key es incorrecta o está deshabilitada.\n"
            "*   El proyecto de Google Cloud asociado no tiene la facturación activada.\n"
            "*   La API 'Generative Language' no está habilitada en tu proyecto de Google Cloud.\n"
            "*   Hay un problema de red que impide la conexión con los servicios de Google."
        )

# ==========================================
# 4. LÓGICA DE INTERFAZ DE USUARIO (UI)
# ==========================================
def main() -> None:
    """Función principal que renderiza la interfaz en Streamlit y maneja los eventos."""
    
    st.set_page_config(page_title="AI Business Matchmaker", page_icon="🤝", layout="centered")
    st.title("🤝 AI Business Networking Club")

    # Verificación de Login
    if not check_password():
        return

    st.write("¡Conecta con el talento o los clientes perfectos para impulsar tus proyectos!")
    
    # --- Configuración de API Key usando st.secrets ---
    # Para configurar esto en Codespaces, crea un directorio `.streamlit` en la raíz de tu proyecto
    # y dentro un archivo `secrets.toml` con la siguiente estructura:
    # GEMINI_API_KEY = "tu_clave_aqui"
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Falta configurar `GEMINI_API_KEY` en `st.secrets`.")
        st.info("Crea un archivo `.streamlit/secrets.toml` e incluye tu API Key.")
        st.stop()
        
    api_key = st.secrets["GEMINI_API_KEY"]

    # Obtenemos la ruta absoluta al directorio del script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    kb_path = os.path.join(base_dir, "knowledge_base")

    # Cargar base de conocimiento de la carpeta de PDFs
    with st.spinner("📚 Verificando base de datos de conocimiento..."):
        knowledge_context = load_knowledge_base(kb_path)
        if not knowledge_context:
            st.warning(f"⚠️ No se encontraron documentos PDF (o no se pudieron extraer) en la carpeta:\n`{kb_path}`")
            st.info("Por favor, asegúrate de añadir archivos con extensión '.pdf' en esa ruta exacta.")

    # Inicializamos el historial del chat en el estado de la sesión
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Renderizamos el historial previo en la interfaz
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Campo de entrada (Chat input) de Streamlit
    if user_need := st.chat_input("Ej: Busco un experto en marketing para lanzar un software..."):
        # Mostramos y guardamos el mensaje del usuario
        st.session_state.messages.append({"role": "user", "content": user_need})
        with st.chat_message("user"):
            st.markdown(user_need)
            
        # Mostramos el indicador de carga mientras consultamos a Gemini
        with st.chat_message("assistant"):
            with st.spinner("Buscando en la base de datos de talento..."):
                matches_result = get_networking_matches(user_need, knowledge_context, api_key)
            st.markdown(matches_result)
        st.session_state.messages.append({"role": "assistant", "content": matches_result})

if __name__ == "__main__":
    main()
