import uuid
from html import escape
from pathlib import Path
from textwrap import dedent

import streamlit as st

from database import (
    add_message,
    create_conversation,
    delete_conversation,
    delete_conversations_for_documents,
    get_conversations,
    get_document_sets,
    get_documents,
    get_messages,
    initialize_database,
    update_conversation_title
)
from document_service import (
    load_document_set,
    process_new_document_set,
    remove_document_set
)
from rag import (
    GeminiServiceError,
    expand_with_neighbors,
    generate_answer,
    load_embedding_model,
    retrieve
)
from styles import inject_workspace_css


NOT_FOUND_ANSWER = "Bu bilgi belgede bulunamadı."


st.set_page_config(
    page_title="PDF RAG Assistant",
    page_icon="PDF",
    layout="wide",
    initial_sidebar_state="expanded"
)

initialize_database()


@st.cache_resource(show_spinner=False)
def get_loaded_embedding_model():
    return load_embedding_model()


class LazyEmbeddingModel:
    def encode(self, *args, **kwargs):
        model = get_loaded_embedding_model()
        return model.encode(*args, **kwargs)


@st.cache_resource(show_spinner=False)
def get_embedding_model():
    return LazyEmbeddingModel()


def render_html(content):
    st.markdown(dedent(content).strip(), unsafe_allow_html=True)


def create_chat_title(question):
    max_length = 42
    clean_question = question.strip().replace("\n", " ")

    if len(clean_question) <= max_length:
        return clean_question

    return clean_question[:max_length].rstrip() + "..."


def clear_document_state():
    for key in [
        "collection",
        "embedding_model",
        "files_fingerprint",
        "chunk_count",
        "active_documents",
        "latest_sources",
        "latest_answer",
        "latest_source_chat_id"
    ]:
        st.session_state.pop(key, None)

    st.session_state["active_chat_id"] = None


def activate_document_set(document_data):
    st.session_state["collection"] = document_data["collection"]
    st.session_state["files_fingerprint"] = document_data["fingerprint"]
    st.session_state["chunk_count"] = document_data["chunk_count"]
    st.session_state["active_documents"] = document_data["documents"]
    st.session_state["active_chat_id"] = None
    st.session_state["latest_sources"] = []
    st.session_state["latest_answer"] = ""
    st.session_state["latest_source_chat_id"] = None


def create_chat(document_fingerprint):
    conversations = get_conversations(document_fingerprint)
    active_conversation = get_active_conversation(conversations)

    if active_conversation:
        messages = get_messages(active_conversation["id"])

        if not messages:
            return active_conversation["id"]

    conversation_id = str(uuid.uuid4())

    create_conversation(
        conversation_id,
        "Yeni Sohbet",
        document_fingerprint
    )

    st.session_state["active_chat_id"] = conversation_id
    st.session_state["latest_sources"] = []
    st.session_state["latest_answer"] = ""
    st.session_state["latest_source_chat_id"] = conversation_id

    return conversation_id


def get_active_conversation(conversations):
    active_chat_id = st.session_state.get("active_chat_id")

    if not active_chat_id:
        return None

    for conversation in conversations:
        if conversation["id"] == active_chat_id:
            return conversation

    return None


def select_default_chat(conversations):
    if not conversations:
        st.session_state["active_chat_id"] = None
        return

    active_chat_id = st.session_state.get("active_chat_id")
    conversation_ids = [
        conversation["id"]
        for conversation in conversations
    ]

    if active_chat_id in conversation_ids:
        return

    st.session_state["active_chat_id"] = conversations[0]["id"]


def delete_chat(chat_id, conversations):
    conversation_ids = [
        conversation["id"]
        for conversation in conversations
    ]

    if chat_id not in conversation_ids:
        return

    deleted_index = conversation_ids.index(chat_id)
    delete_conversation(chat_id)

    if st.session_state.get("active_chat_id") != chat_id:
        return

    remaining_ids = [
        conversation_id
        for conversation_id in conversation_ids
        if conversation_id != chat_id
    ]

    if not remaining_ids:
        st.session_state["active_chat_id"] = None
        st.session_state["latest_sources"] = []
        st.session_state["latest_answer"] = ""
        st.session_state["latest_source_chat_id"] = None
        return

    new_index = min(
        deleted_index,
        len(remaining_ids) - 1
    )

    st.session_state["active_chat_id"] = remaining_ids[new_index]


def prepare_sources(answer, source_ids, results):
    sources = []

    if answer == NOT_FOUND_ANSWER or not source_ids:
        return sources

    seen_sources = set()

    for source_id in source_ids:
        result_index = source_id - 1

        if not 0 <= result_index < len(results):
            continue

        result = results[result_index]
        source_key = (
            result["source"],
            result["page"]
        )

        if source_key in seen_sources:
            continue

        sources.append({
            "source": result["source"],
            "page": result["page"]
        })
        seen_sources.add(source_key)

    return sources


def get_last_assistant_payload(messages):
    for message in reversed(messages):
        if message["role"] == "assistant":
            return message.get("content", ""), message.get("sources", [])

    return "", []


def set_latest_sources(chat_id, answer, sources):
    st.session_state["latest_source_chat_id"] = chat_id
    st.session_state["latest_answer"] = answer
    st.session_state["latest_sources"] = sources


def render_html_message(role, content):
    css_role = "user" if role == "user" else "assistant"
    label = "Siz" if role == "user" else "Belge asistanı"
    safe_content = escape(content)

    return (
        f'<div class="message-row {css_role}">'
        f'<div class="message-card {css_role}">'
        f'<div class="message-role">{label}</div>'
        f'<div class="message-body">{safe_content}</div>'
        '</div></div>'
    )


def get_document_name(document):
    return (
        document.get("file_name")
        or document.get("name")
        or document.get("source")
        or "PDF belgesi"
    )


def get_document_title(document):
    file_name = get_document_name(document)
    stem = Path(file_name).stem
    readable_name = " ".join(stem.replace("_", " ").replace("-", " ").split())

    return readable_name or "PDF belgesi"


def get_document_set_title(document_set):
    documents = get_documents(document_set["fingerprint"])

    if not documents:
        return "Kayıtlı belge seti"

    first_title = get_document_title(documents[0])
    remaining_count = document_set["document_count"] - 1

    if remaining_count > 0:
        return f"{first_title} + {remaining_count} belge"

    return first_title


def render_document_workspace(documents_ready, documents):
    if not documents_ready:
        body = (
            '<div class="muted-copy">'
            'Sol panelden PDF yüklediğinizde çalışma alanı burada açılır. '
            'Belgeler, sohbetler ve kaynaklar uygulama içinde kayıtlı kalır.'
            '</div>'
        )
    elif not documents:
        body = (
            '<div class="muted-copy">'
            'Aktif belge setinde gösterilecek dosya bulunamadı.'
            '</div>'
        )
    else:
        rows = []

        for index, document in enumerate(documents, start=1):
            safe_name = escape(get_document_title(document))
            rows.append(
                '<div class="document-row">'
                f'<span>{safe_name}</span><span>PDF {index}</span>'
                '</div>'
            )

        body = f'<div class="document-list">{"".join(rows)}</div>'

    render_html(
        f"""
        <div class="workspace-panel">
            <div class="eyebrow">Belge çalışma alanı</div>
            <div class="section-title">Aktif dosyalar</div>
            {body}
        </div>
        """
    )


def render_source_cards(sources):
    if not sources:
        st.markdown(
            """
            <div class="empty-card">
                Bu cevap için gösterilecek kaynak yok. Belge dışında kalan
                sorularda kaynak paneli boş kalır.
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    for source in sources:
        safe_source = escape(source["source"])

        st.markdown(
            f"""
            <div class="source-card">
                <div class="source-file">{safe_source}</div>
                <div class="source-page">Sayfa {source['page']}</div>
            </div>
            """,
            unsafe_allow_html=True
        )


def render_status_bar(documents_ready, documents, active_conversation):
    if documents_ready:
        if documents:
            active_set = get_document_title(documents[0])

            if len(documents) > 1:
                active_set += f" + {len(documents) - 1} belge"
        else:
            active_set = "Belge seti"

        pdf_count = len(documents)
        chunk_count = st.session_state.get("chunk_count", 0)
    else:
        active_set = "Yok"
        pdf_count = 0
        chunk_count = 0

    chat_title = (
        active_conversation["title"]
        if active_conversation
        else "Yeni çalışma alanı"
    )
    safe_active_set = escape(str(active_set))
    safe_chat_title = escape(chat_title)

    st.markdown(
        f"""
        <div class="status-bar">
            <div class="status-item">
                <div class="status-label">Aktif belge seti</div>
                <div class="status-value">{safe_active_set}</div>
            </div>
            <div class="status-item">
                <div class="status-label">PDF</div>
                <div class="status-value">{pdf_count}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Parça</div>
                <div class="status-value">{chunk_count}</div>
            </div>
            <div class="status-item">
                <div class="status-label">Aktif sohbet</div>
                <div class="status-value">{safe_chat_title}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )


def render_command_center(document_sets):
    st.markdown(
        """
        <div class="workspace-panel">
            <div class="eyebrow">Başlangıç</div>
            <h1 class="page-title">PDF çalışma alanı</h1>
            <div class="muted-copy">
                Sol panelden PDF yükleyin veya kayıtlı bir belge setini açın.
                Cevaplar yalnızca belgedeki kanıta dayanır; kaynaklar sağ panelde
                sayfa bilgisiyle birlikte görünür.
            </div>
            <div class="pill-row">
                <span class="pill">Kaynaklı cevap</span>
                <span class="pill">Kalıcı sohbet geçmişi</span>
                <span class="pill">Çoklu PDF desteği</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    if document_sets:
        st.info(
            "Kayıtlı belge setleriniz sol panelde hazır. Birini açarak kaldığınız yerden devam edebilirsiniz."
        )
    else:
        st.info(
            "Henüz kayıtlı belge seti yok. Sol panelden PDF yükleyerek başlayın."
        )

    st.markdown("#### Örnek başlangıç soruları")

    suggestions = [
        "Bu belgenin ana fikri nedir?",
        "Belgedeki en önemli gerekçeleri özetle.",
        "Bu belge hangi konularda kanıt sunuyor?"
    ]

    columns = st.columns(3)

    for index, suggestion in enumerate(suggestions):
        with columns[index]:
            if st.button(
                suggestion,
                key=f"empty_suggestion_{index}",
                disabled=True,
                use_container_width=True
            ):
                pass


def render_document_ready_empty():
    st.markdown(
        """
        <div class="workspace-panel">
            <div class="eyebrow">Belgeler hazır</div>
            <div class="section-title">İlk çalışma notunu oluşturun</div>
            <div class="muted-copy">
                Soru sorduğunuzda yeni bir sohbet otomatik oluşturulur.
                Cevaplar belgedeki kanıtla ilişkilendirilir ve kaynaklar sağ panelde görünür.
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    suggestions = [
        "Bu belgenin amacı nedir?",
        "Belgedeki önemli noktaları özetle.",
        "Bu belge hangi soruya cevap veriyor?"
    ]

    columns = st.columns(3)

    for index, suggestion in enumerate(suggestions):
        with columns[index]:
            if st.button(
                suggestion,
                key=f"ready_suggestion_{index}",
                use_container_width=True
            ):
                st.session_state["pending_question"] = suggestion
                st.rerun()


def render_sidebar(document_sets, documents_ready, conversations, document_fingerprint):
    with st.sidebar:
        st.title("PDF Belge Asistanı")
        st.caption("Belge kütüphanesi, sohbetler ve kaynaklı cevaplar.")

        st.divider()
        st.subheader("Belge kütüphanesi")

        uploaded_files = st.file_uploader(
            "PDF dosyalarını yükleyin",
            type=["pdf"],
            accept_multiple_files=True
        )

        if uploaded_files:
            if st.button(
                "Belgeleri Kaydet ve Aç",
                type="primary",
                use_container_width=True
            ):
                try:
                    with st.spinner("Belgeler işleniyor ve indeksleniyor..."):
                        document_data = process_new_document_set(
                            uploaded_files,
                            get_embedding_model()
                        )
                        activate_document_set(document_data)

                    st.toast("Belge seti hazır.")
                    st.rerun()

                except ValueError as error:
                    clear_document_state()
                    st.error(str(error))

                except Exception:
                    clear_document_state()
                    st.error(
                        "Belgeler işlenirken beklenmeyen bir hata oluştu."
                    )

        st.divider()
        st.subheader("Kayıtlı belge setleri")

        if not document_sets:
            st.caption("Henüz kayıtlı belge seti yok.")

        for document_set in document_sets:
            fingerprint = document_set["fingerprint"]
            is_active = fingerprint == st.session_state.get("files_fingerprint")
            set_title = get_document_set_title(document_set)

            label = (
                f"{'Aktif · ' if is_active else ''}"
                f"{set_title} · {document_set['document_count']} PDF"
            )

            open_column, delete_column = st.columns([5, 1])

            with open_column:
                if st.button(
                    label,
                    key=f"open_doc_{fingerprint}",
                    use_container_width=True
                ):
                    try:
                        with st.spinner("Belge seti açılıyor..."):
                            document_data = load_document_set(
                                fingerprint,
                                get_embedding_model()
                            )
                            activate_document_set(document_data)

                        st.rerun()

                    except ValueError as error:
                        st.error(str(error))

                    except Exception:
                        st.error(
                            "Belge seti açılırken beklenmeyen bir hata oluştu."
                        )

            with delete_column:
                confirm_key = f"confirm_delete_{fingerprint}"

                if st.session_state.get(confirm_key):
                    if st.button(
                        "Onay",
                        key=f"delete_confirm_{fingerprint}",
                        use_container_width=True
                    ):
                        remove_document_set(fingerprint)

                        if is_active:
                            clear_document_state()

                        st.session_state.pop(confirm_key, None)
                        st.rerun()
                else:
                    if st.button(
                        "Sil",
                        key=f"delete_doc_{fingerprint}",
                        help="Belge setini, sohbetlerini ve indeksini sil",
                        icon=":material/delete:",
                        use_container_width=True
                    ):
                        st.session_state[confirm_key] = True
                        st.rerun()

        if not documents_ready:
            return

        st.divider()
        st.subheader("Sohbetler")

        if st.button(
            "+ Yeni Sohbet",
            use_container_width=True
        ):
            create_chat(document_fingerprint)
            st.rerun()

        if conversations:
            for conversation in conversations:
                chat_id = conversation["id"]
                is_active = chat_id == st.session_state.get("active_chat_id")
                label = (
                    f"{'Aktif · ' if is_active else ''}"
                    f"{conversation['title']}"
                )

                chat_column, delete_column = st.columns([5, 1])

                with chat_column:
                    if st.button(
                        label,
                        key=f"chat_{chat_id}",
                        use_container_width=True
                    ):
                        st.session_state["active_chat_id"] = chat_id
                        st.rerun()

                with delete_column:
                    if st.button(
                        "Sil",
                        key=f"delete_chat_{chat_id}",
                        help="Sohbeti sil",
                        icon=":material/delete:",
                        use_container_width=True
                    ):
                        delete_chat(chat_id, conversations)
                        st.rerun()

            if st.button(
                "Tüm Sohbetleri Temizle",
                use_container_width=True
            ):
                delete_conversations_for_documents(document_fingerprint)
                st.session_state["active_chat_id"] = None
                st.session_state["latest_sources"] = []
                st.session_state["latest_answer"] = ""
                st.session_state["latest_source_chat_id"] = None
                st.rerun()
        else:
            st.caption("Bu belge seti için henüz sohbet yok.")


def render_chat_workspace(documents_ready, active_conversation, messages, document_sets):
    st.markdown(
        """
        <div class="eyebrow">Çalışma masası</div>
        <h1 class="page-title">Belge asistanı</h1>
        <div class="muted-copy">
            Sorular, cevaplar ve kaynaklar aynı çalışma akışında tutulur.
        </div>
        """,
        unsafe_allow_html=True
    )

    if not documents_ready:
        render_command_center(document_sets)
        return

    if active_conversation is None:
        render_document_ready_empty()
        return

    if not messages:
        render_document_ready_empty()
        return

    rendered_messages = [
        render_html_message(
            message["role"],
            message["content"]
        )
        for message in messages
    ]

    render_html(
        '<div class="workspace-panel">'
        '<div class="eyebrow">Soru-cevap geçmişi</div>'
        '<div class="section-title">Konuşma</div>'
        f'<div class="log-stream">{"".join(rendered_messages)}</div>'
        '</div>'
    )


def render_question_form(documents_ready):
    st.markdown(
        """
        <div class="eyebrow">Yeni soru</div>
        """,
        unsafe_allow_html=True
    )

    with st.form("question_form", clear_on_submit=True):
        question = st.text_area(
            "Belgeler hakkında bir soru yazın",
            placeholder="Örn. Bu belgenin ana fikri nedir?",
            disabled=not documents_ready,
            height=96,
            key="question_text"
        )
        submitted = st.form_submit_button(
            "Cevapla",
            type="primary",
            disabled=not documents_ready,
            use_container_width=True
        )

    if not documents_ready:
        st.caption("Soru sormak için önce sol panelden bir belge seti açın.")

    if submitted:
        return question.strip()

    return None


def render_evidence_panel(documents_ready, active_conversation, messages):
    st.markdown(
        """
        <div class="eyebrow">Kanıt paneli</div>
        <h3>Son cevabın kaynakları</h3>
        """,
        unsafe_allow_html=True
    )

    if not documents_ready:
        st.markdown(
            """
            <div class="empty-card">
                Bir belge seti açıldığında kaynaklar burada görünecek.
            </div>
            """,
            unsafe_allow_html=True
        )
        return

    current_chat_id = (
        active_conversation["id"]
        if active_conversation
        else None
    )

    if (
        st.session_state.get("latest_source_chat_id")
        == current_chat_id
    ):
        answer = st.session_state.get("latest_answer", "")
        sources = st.session_state.get("latest_sources", [])
    else:
        answer, sources = get_last_assistant_payload(messages)

    if answer:
        safe_answer = escape(answer)

        st.caption("Son cevap")
        st.markdown(
            f"""
            <div class="source-card">
                <div class="muted-copy">{safe_answer}</div>
            </div>
            """,
            unsafe_allow_html=True
        )

    render_source_cards(sources)


inject_workspace_css()

if "active_chat_id" not in st.session_state:
    st.session_state["active_chat_id"] = None

if "latest_sources" not in st.session_state:
    st.session_state["latest_sources"] = []

if "latest_answer" not in st.session_state:
    st.session_state["latest_answer"] = ""

if "latest_source_chat_id" not in st.session_state:
    st.session_state["latest_source_chat_id"] = None

document_sets = get_document_sets()

documents_ready = (
    "collection" in st.session_state
    and "files_fingerprint" in st.session_state
)

if documents_ready:
    document_fingerprint = st.session_state["files_fingerprint"]
    conversations = get_conversations(document_fingerprint)
    select_default_chat(conversations)
else:
    document_fingerprint = None
    conversations = []

active_conversation = get_active_conversation(conversations)
messages = (
    get_messages(active_conversation["id"])
    if active_conversation
    else []
)
documents = st.session_state.get("active_documents", [])

render_sidebar(
    document_sets,
    documents_ready,
    conversations,
    document_fingerprint
)

center_column, evidence_column = st.columns([2.25, 1], gap="large")

with center_column:
    render_status_bar(
        documents_ready,
        documents,
        active_conversation
    )
    render_document_workspace(
        documents_ready,
        documents
    )
    render_chat_workspace(
        documents_ready,
        active_conversation,
        messages,
        document_sets
    )
    typed_question = render_question_form(documents_ready)

with evidence_column:
    render_evidence_panel(
        documents_ready,
        active_conversation,
        messages
    )

pending_question = st.session_state.pop("pending_question", None)
question = pending_question or typed_question

if question and documents_ready:
    if active_conversation is None:
        conversation_id = create_chat(document_fingerprint)
        active_conversation = {
            "id": conversation_id,
            "title": "Yeni Sohbet"
        }
    else:
        conversation_id = active_conversation["id"]

    existing_messages = get_messages(conversation_id)

    if not existing_messages:
        title = create_chat_title(question)
        update_conversation_title(conversation_id, title)

    add_message(
        conversation_id,
        "user",
        question
    )

    try:
        with st.spinner("Cevap hazırlanıyor..."):
            retrieved_results = retrieve(
                question,
                st.session_state["collection"],
                get_embedding_model(),
                top_k=3
            )

            results = expand_with_neighbors(
                retrieved_results,
                st.session_state["collection"]
            )

            answer, source_ids = generate_answer(
                question,
                results
            )

            sources = prepare_sources(
                answer,
                source_ids,
                results
            )

        add_message(
            conversation_id,
            "assistant",
            answer,
            sources=sources
        )
        set_latest_sources(
            conversation_id,
            answer,
            sources
        )
        st.rerun()

    except GeminiServiceError as error:
        st.error(str(error))

    except Exception:
        st.error(
            "Soru işlenirken beklenmeyen bir hata oluştu."
        )
