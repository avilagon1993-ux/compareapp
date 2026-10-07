import difflib
import hashlib
import io

import streamlit as st
import streamlit.components.v1 as components
from pypdf import PdfReader

st.set_page_config(page_title="Comparador de PDFs", page_icon="📄", layout="wide")
st.title("📄 Comparador de documentos")
st.caption("Subí dos archivos (PDF o TXT) y verificá si su contenido es igual.")


def extract_pages(data: bytes, name: str) -> list[str]:
    """Devuelve el texto de cada página (TXT = una sola 'página')."""
    if name.lower().endswith(".txt"):
        return [data.decode("utf-8", errors="ignore")]
    reader = PdfReader(io.BytesIO(data))
    return [(p.extract_text() or "") for p in reader.pages]


def normalize(text: str, ignore_case: bool, ignore_ws: bool) -> str:
    lines = text.splitlines()
    if ignore_ws:
        lines = [" ".join(l.split()) for l in lines]
        lines = [l for l in lines if l]
    out = "\n".join(lines)
    return out.lower() if ignore_case else out


# ---------- Opciones ----------
with st.sidebar:
    st.header("Opciones")
    ignore_ws = st.checkbox("Ignorar espacios y saltos de línea extra", value=True)
    ignore_case = st.checkbox("Ignorar mayúsculas/minúsculas", value=False)

col1, col2 = st.columns(2)
file_a = col1.file_uploader("Archivo A", type=["pdf", "txt"], key="a")
file_b = col2.file_uploader("Archivo B", type=["pdf", "txt"], key="b")

if file_a and file_b:
    bytes_a, bytes_b = file_a.getvalue(), file_b.getvalue()

    try:
        pages_a = [normalize(p, ignore_case, ignore_ws) for p in extract_pages(bytes_a, file_a.name)]
        pages_b = [normalize(p, ignore_case, ignore_ws) for p in extract_pages(bytes_b, file_b.name)]
    except Exception as e:
        st.error(f"No pude leer uno de los archivos: {e}")
        st.stop()

    text_a, text_b = "\n".join(pages_a), "\n".join(pages_b)

    if not text_a.strip() or not text_b.strip():
        st.warning(
            "Uno de los archivos no tiene texto extraíble (probablemente es un PDF escaneado "
            "o una imagen). Esta app compara texto; para escaneos haría falta OCR."
        )

    same_bytes = hashlib.sha256(bytes_a).hexdigest() == hashlib.sha256(bytes_b).hexdigest()
    same_text = text_a == text_b
    ratio = difflib.SequenceMatcher(None, text_a, text_b, autojunk=False).ratio() if text_a or text_b else 1.0

    st.divider()
    if same_text:
        st.success("✅ El contenido de texto es IDÉNTICO.")
    else:
        st.error("❌ El contenido es DISTINTO.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Archivos idénticos byte a byte", "Sí" if same_bytes else "No")
    m2.metric("Texto idéntico", "Sí" if same_text else "No")
    m3.metric("Similitud", f"{ratio * 100:.2f}%")
    m4.metric("Páginas A / B", f"{len(pages_a)} / {len(pages_b)}")

    if same_text and not same_bytes:
        st.info("El texto coincide, pero los archivos no son idénticos a nivel binario "
                "(metadatos, fuentes, compresión, etc.).")

    if not same_text:
        # Resumen por página
        st.subheader("Comparación por página")
        rows = []
        for i in range(max(len(pages_a), len(pages_b))):
            pa = pages_a[i] if i < len(pages_a) else None
            pb = pages_b[i] if i < len(pages_b) else None
            if pa is None or pb is None:
                status = "Solo existe en " + ("B" if pa is None else "A")
                sim = 0.0
            else:
                sim = difflib.SequenceMatcher(None, pa, pb, autojunk=False).ratio()
                status = "✅ Igual" if pa == pb else "❌ Distinta"
            rows.append({"Página": i + 1, "Estado": status, "Similitud %": round(sim * 100, 2)})
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Diff visual
        st.subheader("Diferencias (línea por línea)")
        only_changes = st.checkbox("Mostrar solo cambios (con contexto)", value=True)
        html = difflib.HtmlDiff(wrapcolumn=70).make_file(
            text_a.splitlines(),
            text_b.splitlines(),
            fromdesc=file_a.name,
            todesc=file_b.name,
            context=only_changes,
            numlines=2,
        )
        components.html(html, height=600, scrolling=True)
else:
    st.info("Cargá ambos archivos para comenzar.")
