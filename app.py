import os

import chromadb

from dotenv import load_dotenv
from google import genai
from sentence_transformers import SentenceTransformer


CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "pdf_documents"

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"
GEMINI_MODEL_NAME = "gemini-3.5-flash-lite"

TOP_K = 3


def load_collection():
    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    collection = client.get_collection(
        name=COLLECTION_NAME
    )

    return collection


def retrieve(
    question,
    collection,
    embedding_model,
    top_k=3
):
    # E5 retrieval kullanımında kullanıcı sorusuna
    # "query:" prefix'i ekliyoruz.
    query_text = f"query: {question}"

    question_embedding = embedding_model.encode(
        [query_text]
    )[0]

    results = collection.query(
        query_embeddings=[
            question_embedding.tolist()
        ],
        n_results=top_k,
        include=[
            "documents",
            "metadatas",
            "distances"
        ]
    )

    retrieved_chunks = []

    documents = results["documents"][0]
    metadatas = results["metadatas"][0]
    distances = results["distances"][0]

    for document, metadata, distance in zip(
        documents,
        metadatas,
        distances
    ):
        chunk = {
            "text": document,
            "source": metadata["source"],
            "page": metadata["page"],
            "distance": float(distance)
        }

        retrieved_chunks.append(chunk)

    return retrieved_chunks


def create_context(retrieved_chunks):
    context_parts = [
        chunk["text"]
        for chunk in retrieved_chunks
    ]

    context = "\n\n".join(
        context_parts
    )

    return context


def generate_answer(
    question,
    retrieved_chunks,
    client
):
    context = create_context(
        retrieved_chunks
    )

    prompt = f"""
Sen belgeye dayalı çalışan bir soru-cevap asistanısın.

Yalnızca aşağıdaki BAĞLAM bölümünde açıkça verilen bilgileri
kullanarak kullanıcının sorusunu cevapla.

Önemli kurallar:

- Kendi genel bilgini kullanma.
- Bağlamda bulunmayan bilgi ekleme.
- Soruda geçen kelimelerin bağlamda bulunması, cevabın da
  bağlamda bulunduğu anlamına gelmez.
- Bağlamın soruyu gerçekten cevaplayıp cevaplamadığını kontrol et.
- Eğer bağlam sorunun cevabını içermiyorsa yalnızca:
  "Bu bilgi belgede bulunamadı."
  cevabını ver.

BAĞLAM:
{context}

SORU:
{question}

CEVAP:
"""

    response = client.models.generate_content(
        model=GEMINI_MODEL_NAME,
        contents=prompt
    )

    return response.text


def print_sources(retrieved_chunks):
    print(
        "\n--- Kaynaklar ---\n"
    )

    for rank, chunk in enumerate(
        retrieved_chunks,
        start=1
    ):
        print(
            f"[Kaynak {rank}] "
            f"{chunk['source']} - "
            f"Sayfa {chunk['page']} - "
            f"Distance: {chunk['distance']:.4f}"
        )

        print(
            chunk["text"]
        )

        print()


def main():
    load_dotenv()

    api_key = os.getenv(
        "GEMINI_API_KEY"
    )

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY .env dosyasında bulunamadı."
        )

    gemini_client = genai.Client(
        api_key=api_key
    )

    print(
        "E5 embedding modeli yükleniyor..."
    )

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    collection = load_collection()

    print(
        f"ChromaDB hazır. "
        f"Toplam chunk: {collection.count()}"
    )

    question = input(
        "\nSorunuzu yazın: "
    ).strip()

    if not question:
        print(
            "Lütfen bir soru girin."
        )
        return

    retrieved_chunks = retrieve(
        question=question,
        collection=collection,
        embedding_model=embedding_model,
        top_k=TOP_K
    )

    answer = generate_answer(
        question=question,
        retrieved_chunks=retrieved_chunks,
        client=gemini_client
    )

    print(
        "\n--- Cevap ---\n"
    )

    print(answer)

    print_sources(
        retrieved_chunks
    )


if __name__ == "__main__":
    main()