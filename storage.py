import shutil
from pathlib import Path


UPLOADS_DIRECTORY = Path("data/uploads")


def get_document_set_directory(document_fingerprint):
    return UPLOADS_DIRECTORY / document_fingerprint


def save_uploaded_files(uploaded_files, document_fingerprint):
    document_directory = get_document_set_directory(document_fingerprint)
    document_directory.mkdir(parents=True, exist_ok=True)

    saved_files = []

    for uploaded_file in uploaded_files:
        file_path = document_directory / uploaded_file.name
        file_path.write_bytes(uploaded_file.getvalue())

        saved_files.append({
            "file_name": uploaded_file.name,
            "file_path": str(file_path)
        })

    return saved_files


def delete_uploaded_files(document_fingerprint):
    document_directory = get_document_set_directory(document_fingerprint)

    if document_directory.exists():
        shutil.rmtree(document_directory)


def documents_exist(documents):
    return all(
        Path(document["file_path"]).exists()
        for document in documents
    )