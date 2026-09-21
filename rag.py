import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv
from google import genai
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pydantic import BaseModel
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer


CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-base"
GEMINI_MODEL_NAME = "gemini-3.5-flash-lite"
CHROMA_PATH = Path("chroma_db")
NOT_FOUND_ANSWER = "Bu bilgi belgede bulunamadı."


class GeminiServiceError(Exception):
    pass


class AnswerResponse(BaseModel):
    answer: str
    source_ids: list[int]


load_dotenv()


def read_pdf(pdf_file):
    documents = []

    try:
        reader = PdfReader(pdf_file)
    except Exception as error:
        raise ValueError(
            f"'{pdf_file.name}' PDF dosyası okunamadı."
        ) from error

    for page_number, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text()
        except Exception:
            continue

        if text and text.strip():
            documents.append({
                "text": text,
                "page": page_number,
                "source": pdf_file.name
            })

    if not documents:
        raise ValueError(
            f"'{pdf_file.name}' dosyasından metin çıkarılamadı. "
            "PDF taranmış/görüntü tabanlı veya boş olabilir."
        )

    return documents


def create_chunks(documents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = []
    chunk_index = 0

    for document in documents:
        split_texts = text_splitter.split_text(document["text"])

        for text in split_texts:
            clean_text = text.strip()

            if not clean_text:
                continue

            chunks.append({
                "text": clean_text,
                "page": document["page"],
                "source": document["source"],
                "chunk_index": chunk_index
            })

            chunk_index += 1

    return chunks


def process_pdfs(uploaded_files):
    documents = []

    for uploaded_file in uploaded_files:
        documents.extend(read_pdf(uploaded_file))

    chunks = create_chunks(documents)

    if not chunks:
        raise ValueError(
            "Yüklenen belgelerden işlenebilir metin parçaları oluşturulamadı."
        )

    return chunks


def load_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL_NAME)


def create_embeddings(chunks, embedding_model):
    passage_texts = [
        f"passage: {chunk['text']}"
        for chunk in chunks
    ]

    return embedding_model.encode(passage_texts)


def get_chroma_client():
    CHROMA_PATH.mkdir(parents=True, exist_ok=True)

    return chromadb.PersistentClient(path=str(CHROMA_PATH))


def list_collection_names(client):
    names = []

    for collection in client.list_collections():
        if isinstance(collection, str):
            names.append(collection)
        else:
            names.append(collection.name)

    return names


def get_collection_name(document_fingerprint):
    return f"docs_{document_fingerprint[:32]}"


def create_vector_store(chunks, embeddings, document_fingerprint=None):
    client = get_chroma_client()

    if document_fingerprint:
        collection_name = get_collection_name(document_fingerprint)
    else:
        collection_name = "active_documents"

    existing_collections = list_collection_names(client)

    if collection_name in existing_collections:
        client.delete_collection(collection_name)

    collection = client.create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"}
    )

    collection.add(
        ids=[
            str(chunk["chunk_index"])
            for chunk in chunks
        ],
        documents=[
            chunk["text"]
            for chunk in chunks
        ],
        embeddings=[
            embedding.tolist()
            for embedding in embeddings
        ],
        metadatas=[
            {
                "source": chunk["source"],
                "page": chunk["page"],
                "chunk_index": chunk["chunk_index"]
            }
            for chunk in chunks
        ]
    )

    return collection


def load_vector_store(document_fingerprint):
    client = get_chroma_client()
    collection_name = get_collection_name(document_fingerprint)
    existing_collections = list_collection_names(client)

    if collection_name not in existing_collections:
        raise ValueError(
            "Bu belge setinin vektör indeksi bulunamadı. "
            "Belgeleri yeniden yükleyip indeksleyin."
        )

    return client.get_collection(collection_name)


def delete_vector_store(document_fingerprint):
    client = get_chroma_client()
    collection_name = get_collection_name(document_fingerprint)
    existing_collections = list_collection_names(client)

    if collection_name in existing_collections:
        client.delete_collection(collection_name)


def retrieve(question, collection, embedding_model, top_k=3):
    query_text = f"query: {question}"
    question_embedding = embedding_model.encode([query_text])[0]

    result_count = min(top_k, collection.count())

    if result_count == 0:
        return []

    results = collection.query(
        query_embeddings=[question_embedding.tolist()],
        n_results=result_count,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    retrieved_chunks = []

    for document, metadata, distance in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0]
    ):
        retrieved_chunks.append({
            "text": document,
            "source": metadata["source"],
            "page": metadata["page"],
            "chunk_index": metadata.get("chunk_index"),
            "distance": distance
        })

    return retrieved_chunks


def get_chunk_by_index(collection, chunk_index):
    if chunk_index is None:
        return None

    result = collection.get(
        ids=[str(chunk_index)],
        include=[
            "documents",
            "metadatas"
        ]
    )

    if not result["ids"]:
        return None

    metadata = result["metadatas"][0]

    return {
        "text": result["documents"][0],
        "source": metadata["source"],
        "page": metadata["page"],
        "chunk_index": metadata.get("chunk_index"),
        "distance": None
    }


def expand_with_neighbors(retrieved_results, collection, window=1):
    expanded_results = []
    seen_indexes = set()

    for result in retrieved_results:
        chunk_index = result.get("chunk_index")

        if chunk_index is None:
            key = (
                result["source"],
                result["page"],
                result["text"]
            )

            if key not in seen_indexes:
                expanded_results.append(result)
                seen_indexes.add(key)

            continue

        for neighbor_index in range(
            chunk_index - window,
            chunk_index + window + 1
        ):
            if neighbor_index in seen_indexes:
                continue

            neighbor = get_chunk_by_index(
                collection,
                neighbor_index
            )

            if neighbor is None:
                continue

            expanded_results.append(neighbor)
            seen_indexes.add(neighbor_index)

    return expanded_results


def create_context(retrieved_chunks):
    context_parts = []

    for index, chunk in enumerate(retrieved_chunks, start=1):
        context_parts.append(
            f"[PARÇA {index}]\n"
            f"Kaynak: {chunk['source']}\n"
            f"Sayfa: {chunk['page']}\n"
            f"İçerik:\n{chunk['text']}"
        )

    return "\n\n---\n\n".join(context_parts)


def get_gemini_client():
    api_key = (
        os.getenv("GEMINI_API_KEY")
        or os.getenv("GOOGLE_API_KEY")
    )

    if not api_key:
        raise GeminiServiceError(
            "GEMINI_API_KEY bulunamadı. .env dosyasına Gemini API anahtarınızı ekleyin."
        )

    return genai.Client(api_key=api_key)


def generate_answer(question, retrieved_chunks):
    if not retrieved_chunks:
        return NOT_FOUND_ANSWER, []

    client = get_gemini_client()
    context = create_context(retrieved_chunks)

    prompt = f"""
Sen belgeye dayalı çalışan bir soru-cevap asistanısın.

Yalnızca aşağıdaki BAĞLAM bölümünde açıkça verilen bilgileri
kullanarak kullanıcının sorusunu cevapla.

Kurallar:
- Kendi genel bilgini kullanma.
- Bağlamda bulunmayan bilgi ekleme.
- Soruda geçen kelimelerin bağlamda bulunması, cevabın da bağlamda bulunduğu anlamına gelmez.
- Bağlamın soruyu gerçekten cevaplayıp cevaplamadığını kontrol et.
- source_ids alanına yalnızca cevabı gerçekten destekleyen PARÇA numaralarını ekle.
- Bir parçanın yalnızca konuyla ilgili olması yeterli değildir; cevaptaki bilgiyi gerçekten desteklemelidir.
- Eğer bağlam sorunun cevabını içermiyorsa answer alanı tam olarak "{NOT_FOUND_ANSWER}" olmalı ve source_ids boş liste olmalıdır.

BAĞLAM:
{context}

SORU:
{question}
"""

    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL_NAME,
            contents=prompt,
            config={
                "response_mime_type": "application/json",
                "response_schema": AnswerResponse
            }
        )
    except Exception as error:
        raise GeminiServiceError(
            f"Gemini cevap üretimi sırasında hata oluştu: {error}"
        ) from error

    result = response.parsed
    answer = result.answer.strip()

    if answer == NOT_FOUND_ANSWER:
        return answer, []

    source_ids = [
        source_id
        for source_id in result.source_ids
        if 1 <= source_id <= len(retrieved_chunks)
    ]

    return answer, source_ids
