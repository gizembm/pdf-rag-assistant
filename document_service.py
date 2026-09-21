import hashlib
from io import BytesIO
from pathlib import Path

from database import (
    add_document,
    create_document_set,
    delete_document_set,
    document_set_exists,
    get_documents
)
from rag import (
    create_embeddings,
    create_vector_store,
    delete_vector_store,
    load_vector_store,
    process_pdfs
)
from storage import (
    delete_uploaded_files,
    documents_exist,
    save_uploaded_files
)


class StoredPdfFile(BytesIO):
    def __init__(self, document):
        self.file_path = Path(document["file_path"])
        super().__init__(self.file_path.read_bytes())
        self.name = document["file_name"]

    def getvalue(self):
        current_position = self.tell()
        self.seek(0)
        value = self.read()
        self.seek(current_position)

        return value


def get_files_fingerprint(uploaded_files):
    hasher = hashlib.sha256()

    for uploaded_file in uploaded_files:
        file_bytes = uploaded_file.getvalue()

        hasher.update(uploaded_file.name.encode("utf-8"))
        hasher.update(file_bytes)

    return hasher.hexdigest()


def rebuild_document_set_index(document_fingerprint, documents, embedding_model):
    uploaded_files = [
        StoredPdfFile(document)
        for document in documents
    ]

    chunks = process_pdfs(uploaded_files)
    embeddings = create_embeddings(chunks, embedding_model)

    collection = create_vector_store(
        chunks,
        embeddings,
        document_fingerprint=document_fingerprint
    )

    return collection


def process_new_document_set(uploaded_files, embedding_model):
    document_fingerprint = get_files_fingerprint(uploaded_files)

    if document_set_exists(document_fingerprint):
        documents = get_documents(document_fingerprint)

        if not documents_exist(documents):
            raise ValueError(
                "Kayıtlı belge setinin PDF dosyaları eksik. "
                "Belge setini silip yeniden yükleyin."
            )

        try:
            collection = load_vector_store(document_fingerprint)
        except ValueError:
            collection = rebuild_document_set_index(
                document_fingerprint,
                documents,
                embedding_model
            )

        return {
            "fingerprint": document_fingerprint,
            "collection": collection,
            "documents": documents,
            "chunk_count": collection.count(),
            "is_new": False
        }

    saved_files = []
    collection_created = False

    try:
        saved_files = save_uploaded_files(
            uploaded_files,
            document_fingerprint
        )

        chunks = process_pdfs(uploaded_files)
        embeddings = create_embeddings(chunks, embedding_model)

        collection = create_vector_store(
            chunks,
            embeddings,
            document_fingerprint=document_fingerprint
        )
        collection_created = True

        create_document_set(document_fingerprint)

        for saved_file in saved_files:
            add_document(
                document_fingerprint,
                saved_file["file_name"],
                saved_file["file_path"]
            )

        return {
            "fingerprint": document_fingerprint,
            "collection": collection,
            "documents": saved_files,
            "chunk_count": len(chunks),
            "is_new": True
        }

    except Exception:
        delete_uploaded_files(document_fingerprint)

        if collection_created:
            delete_vector_store(document_fingerprint)

        delete_document_set(document_fingerprint)

        raise


def load_document_set(document_fingerprint, embedding_model):
    documents = get_documents(document_fingerprint)

    if not documents:
        raise ValueError("Belge seti bulunamadı.")

    if not documents_exist(documents):
        raise ValueError(
            "Bu belge setinin PDF dosyaları eksik. "
            "Belge setini silip yeniden yükleyin."
        )

    try:
        collection = load_vector_store(document_fingerprint)
    except ValueError:
        collection = rebuild_document_set_index(
            document_fingerprint,
            documents,
            embedding_model
        )

    return {
        "fingerprint": document_fingerprint,
        "collection": collection,
        "documents": documents,
        "chunk_count": collection.count(),
        "is_new": False
    }


def remove_document_set(document_fingerprint):
    delete_uploaded_files(document_fingerprint)
    delete_vector_store(document_fingerprint)
    delete_document_set(document_fingerprint)
