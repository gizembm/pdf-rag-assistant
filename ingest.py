import os
import chromadb

from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from langchain_text_splitters import RecursiveCharacterTextSplitter


DOCUMENTS_FOLDER = "documents"
CHROMA_PATH = "chroma_db"
COLLECTION_NAME = "pdf_documents"

EMBEDDING_MODEL_NAME = "intfloat/multilingual-e5-small"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100


def read_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    documents = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):
        text = page.extract_text()

        if not text:
            continue

        document = {
            "text": text,
            "page": page_number,
            "source": pdf_path
        }

        documents.append(document)

    return documents


def load_documents(folder_path):
    documents = []

    for file_name in sorted(
        os.listdir(folder_path)
    ):
        if not file_name.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(
            folder_path,
            file_name
        )

        print(
            f"PDF yükleniyor: {pdf_path}"
        )

        pdf_documents = read_pdf(
            pdf_path
        )

        documents.extend(
            pdf_documents
        )

    return documents


def create_chunks(
    documents,
    chunk_size=500,
    chunk_overlap=100
):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            ". ",
            " ",
            ""
        ]
    )

    chunks = []

    for document in documents:
        split_texts = text_splitter.split_text(
            document["text"]
        )

        for text in split_texts:
            chunk = {
                "text": text,
                "page": document["page"],
                "source": document["source"]
            }

            chunks.append(chunk)

    return chunks

def main():
    documents = load_documents(
        DOCUMENTS_FOLDER
    )

    if not documents:
        print(
            "documents klasöründe PDF bulunamadı."
        )
        return

    print(
        f"\nToplam sayfa: {len(documents)}"
    )

    chunks = create_chunks(
        documents,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    print(
        f"Toplam chunk: {len(chunks)}"
    )

    print(
        "\nE5 embedding modeli yükleniyor..."
    )

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )

    # E5 retrieval kullanımında belge parçalarına
    # "passage:" prefix'i ekliyoruz.
    #
    # ChromaDB'de saklayacağımız gerçek document metnini
    # değiştirmiyoruz. Prefix yalnızca embedding oluşturulurken
    # modele verilen metinde kullanılıyor.
    passage_texts = [
        f"passage: {chunk['text']}"
        for chunk in chunks
    ]

    print(
        "Embedding'ler oluşturuluyor..."
    )

    embeddings = embedding_model.encode(
        passage_texts
    )

    client = chromadb.PersistentClient(
        path=CHROMA_PATH
    )

    try:
        client.delete_collection(
            name=COLLECTION_NAME
        )
    except Exception:
        pass

    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={
            "hnsw:space": "cosine"
        }
    )

    ids = []
    chunk_texts = []
    metadatas = []

    for index, chunk in enumerate(chunks):
        ids.append(
            f"chunk_{index}"
        )

        # Burada prefix'siz gerçek metni saklıyoruz.
        chunk_texts.append(
            chunk["text"]
        )

        metadata = {
            "source": chunk["source"],
            "page": chunk["page"]
        }

        metadatas.append(metadata)

    collection.add(
        ids=ids,
        documents=chunk_texts,
        embeddings=embeddings.tolist(),
        metadatas=metadatas
    )

    print(
        "\nChromaDB oluşturuldu."
    )

    print(
        f"Kaydedilen chunk sayısı: "
        f"{collection.count()}"
    )


if __name__ == "__main__":
    main()