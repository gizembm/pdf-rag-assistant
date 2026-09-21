import streamlit as st


WORKSPACE_CSS = """
<style>
:root {
    --workspace-bg: #f7f3ec;
    --paper-bg: #fffdf8;
    --panel-bg: #fbf7ef;
    --panel-soft: #f1eadf;
    --panel-border: #ded2c2;
    --text-main: #2f2a24;
    --text-muted: #766c60;
    --accent: #8b5e34;
    --accent-strong: #6f461f;
    --green: #4f7b62;
}

.stApp { background: var(--workspace-bg); color: var(--text-main); }

header[data-testid="stHeader"] {
    background: var(--workspace-bg);
    border-bottom: 1px solid var(--panel-border);
}

header[data-testid="stHeader"] * { color: var(--text-main) !important; }

section[data-testid="stSidebar"] {
    background: #efe6d9;
    border-right: 1px solid var(--panel-border);
}

section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    padding-top: 1rem;
}

section[data-testid="stSidebar"] [data-testid="stSidebarHeader"] {
    position: absolute;
    z-index: 2;
    top: 0.7rem;
    right: 0.65rem;
    width: auto;
    height: 2rem;
    min-height: 0;
}

section[data-testid="stSidebar"] [data-testid="stLogoSpacer"] { display: none; }

section[data-testid="stSidebar"] [data-testid="stSidebarUserContent"] {
    padding: 0 1.15rem 2rem;
}

section[data-testid="stSidebar"] h1 {
    margin: 0 2.25rem 0.2rem 0;
    font-size: 1.55rem;
    line-height: 1.25;
}

section[data-testid="stSidebar"] h3 {
    margin: 0;
    font-size: 1rem;
    line-height: 1.35;
}

section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--text-muted) !important;
    font-size: 0.9rem;
    line-height: 1.45;
}

section[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
section[data-testid="stSidebar"] label { color: var(--text-main) !important; }

section[data-testid="stSidebar"] hr {
    margin: 1rem 0;
    border-color: var(--panel-border);
}

h1, h2, h3 { letter-spacing: 0; color: var(--text-main); }

.block-container {
    padding-top: 4.75rem;
    padding-bottom: 4rem;
    max-width: 1500px;
}

div[data-testid="stVerticalBlockBorderWrapper"] { border-color: var(--panel-border); }

div[data-testid="stForm"] {
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    background: var(--paper-bg);
    padding: 0.95rem 1rem 1rem;
}

.workspace-panel {
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    background: var(--paper-bg);
    padding: 1rem;
    margin-bottom: 0.9rem;
    box-shadow: 0 1px 0 rgba(91, 72, 48, 0.04);
}

.eyebrow, .message-role {
    color: var(--accent);
    font-size: 0.74rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

.eyebrow { margin-bottom: 0.35rem; }
.muted-copy { color: var(--text-muted); font-size: 0.94rem; line-height: 1.55; white-space: pre-wrap; }
.page-title { margin: 0.15rem 0 0.2rem; font-size: 2rem; line-height: 1.15; }
.section-title { margin: 0 0 0.4rem; font-size: 1.08rem; font-weight: 750; }

.status-bar {
    display: grid;
    grid-template-columns: 1.4fr 0.55fr 0.55fr 1fr;
    gap: 0.7rem;
    margin-bottom: 1rem;
}

.status-item {
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    background: var(--paper-bg);
    padding: 0.78rem 0.9rem;
    min-height: 4.4rem;
}

.status-label { color: var(--text-muted); font-size: 0.76rem; margin-bottom: 0.25rem; }
.status-value { color: var(--text-main); font-size: 1rem; font-weight: 700; overflow-wrap: anywhere; }
.document-list { display: grid; gap: 0.45rem; margin-top: 0.65rem; }

.document-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.75rem;
    border-top: 1px solid var(--panel-soft);
    padding-top: 0.48rem;
    color: var(--text-main);
    font-size: 0.92rem;
}

.document-row span:last-child { color: var(--text-muted); white-space: nowrap; }

.log-stream {
    display: flex;
    flex-direction: column;
    gap: 0.8rem;
    margin-top: 0.8rem;
}

.message-row { display: flex; width: 100%; }
.message-row.user { justify-content: flex-end; }
.message-row.assistant { justify-content: flex-start; }

.message-card {
    width: fit-content;
    max-width: 82%;
    padding: 0.8rem 0.95rem;
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    box-shadow: 0 1px 0 rgba(91, 72, 48, 0.04);
}

.message-row.user .message-card {
    background: #e8d8c5;
    border-color: #d5bea4;
    border-bottom-right-radius: 2px;
}

.message-row.assistant .message-card {
    background: #fffdf8;
    border-bottom-left-radius: 2px;
}

.message-role { margin-bottom: 0.3rem; }
.message-row.user .message-role { color: #6f461f; text-align: right; }
.message-body { color: var(--text-main); line-height: 1.55; white-space: pre-wrap; overflow-wrap: anywhere; }

.source-card {
    border: 1px solid var(--panel-border);
    border-radius: 8px;
    background: var(--paper-bg);
    padding: 0.8rem;
    margin-bottom: 0.65rem;
}

.source-file { color: var(--text-main); font-weight: 700; overflow-wrap: anywhere; }
.source-page { color: var(--green); font-size: 0.86rem; margin-top: 0.2rem; }

.empty-card {
    border: 1px dashed var(--panel-border);
    border-radius: 8px;
    background: rgba(255, 253, 248, 0.58);
    padding: 1rem;
    color: var(--text-muted);
}

.pill-row { display: flex; flex-wrap: wrap; gap: 0.5rem; margin-top: 0.85rem; }
.pill { border: 1px solid var(--panel-border); border-radius: 999px; padding: 0.38rem 0.68rem; color: var(--text-muted); font-size: 0.84rem; background: var(--panel-bg); }

div.stButton > button,
[data-testid="stFormSubmitButton"] > button {
    border-radius: 8px;
    border: 1px solid var(--panel-border);
    background: var(--paper-bg);
    color: var(--text-main);
    min-height: 2.45rem;
}

div.stButton > button:hover { border-color: var(--accent); color: var(--accent-strong); background: #f6ecdf; }

div.stButton > button[kind="primary"],
[data-testid="stFormSubmitButton"] > button {
    background: #66503e !important;
    color: #fffdf8 !important;
    border-color: #66503e !important;
    font-weight: 700;
    box-shadow: none !important;
}

[data-testid="stFormSubmitButton"] > button:disabled {
    background: #b9aa9b !important;
    color: #f9f5ef !important;
    border-color: #b9aa9b !important;
}

[class*="st-key-delete_doc_"] button,
[class*="st-key-delete_chat_"] button {
    background: #292824 !important;
    border-color: #292824 !important;
    color: #ffffff !important;
    min-width: 2.5rem;
    padding-left: 0.55rem;
    padding-right: 0.55rem;
}

[class*="st-key-delete_doc_"] button:hover,
[class*="st-key-delete_chat_"] button:hover { background: #151412 !important; border-color: #151412 !important; }

[data-testid="stFileUploaderDropzone"] {
    background: var(--paper-bg) !important;
    border: 1px dashed var(--panel-border) !important;
    border-radius: 8px !important;
}

[data-testid="stFileUploaderDropzone"] *,
div[data-testid="stFileUploader"] small,
div[data-testid="stForm"] label,
div[data-testid="stForm"] p,
div[data-testid="stCaptionContainer"] { color: var(--text-muted) !important; }

[data-testid="stFileUploaderDropzone"] button {
    background: var(--panel-soft) !important;
    border: 1px solid var(--panel-border) !important;
    color: var(--text-main) !important;
}

[data-testid="stFileUploaderDropzone"] button p { font-size: 0; }
[data-testid="stFileUploaderDropzone"] button p::after { content: "PDF seç"; font-size: 0.875rem; }
[data-testid="stFileUploaderDropzoneInstructions"] span { display: none; }
[data-testid="stFileUploaderDropzoneInstructions"]::after { content: "Dosya başına en fazla 200 MB · PDF"; color: var(--text-muted); font-size: 0.8rem; }

textarea { color: var(--text-main) !important; background: #fffaf2 !important; border-color: var(--panel-border) !important; border-radius: 8px !important; }
textarea::placeholder { color: #8d8174 !important; opacity: 1 !important; }
.stAlert { border-radius: 8px; }

@media (max-width: 1100px) {
    .status-bar { grid-template-columns: 1fr 1fr; }
}

@media (max-width: 640px) {
    .block-container { padding-top: 4.25rem; }
    .message-card { max-width: 92%; }
}
</style>
"""


def inject_workspace_css():
    st.markdown(WORKSPACE_CSS, unsafe_allow_html=True)
