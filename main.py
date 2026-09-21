import os

from dotenv import load_dotenv
from google import genai
from pypdf import PdfReader
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity


# ==================================================
# AYARLAR
# ==================================================

DOCUMENTS_FOLDER = "documents"

EMBEDDING_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
GEMINI_MODEL_NAME = "gemini-3.5-flash-lite"

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100

TOP_K = 3
SIMILARITY_THRESHOLD = 0.30


# ==================================================
# TEK BİR PDF'Yİ OKUMA
# ==================================================

def read_pdf(pdf_path):
    """
    Tek bir PDF dosyasını sayfa sayfa okur.

    Her sayfa için:
    - text
    - page
    - source

    bilgilerini saklar.
    """

    reader = PdfReader(pdf_path)

    documents = []

    for page_number, page in enumerate(reader.pages, start=1):

        text = page.extract_text()

        # Metin çıkarılamayan boş sayfaları atla
        if not text:
            continue

        document = {
            "text": text,
            "page": page_number,
            "source": pdf_path
        }

        documents.append(document)

    return documents


# ==================================================
# DOCUMENTS KLASÖRÜNDEKİ TÜM PDF'LERİ OKUMA
# ==================================================

def load_documents(folder_path):
    """
    Verilen klasördeki bütün PDF dosyalarını bulur
    ve sayfalarını tek bir documents listesinde toplar.
    """

    documents = []

    for file_name in os.listdir(folder_path):

        # PDF olmayan dosyaları atla
        if not file_name.lower().endswith(".pdf"):
            continue

        pdf_path = os.path.join(
            folder_path,
            file_name
        )

        print(f"PDF yükleniyor: {pdf_path}")

        pdf_documents = read_pdf(pdf_path)

        # PDF'deki sayfaları ana listeye ekle
        documents.extend(pdf_documents)

    return documents


# ==================================================
# CHUNK OLUŞTURMA
# ==================================================

def create_chunks(
    documents,
    chunk_size=500,
    chunk_overlap=100
):
    """
    Document'ları daha küçük parçalara böler.

    Her chunk'ın:
    - text
    - page
    - source

    metadata bilgilerini korur.
    """

    if chunk_overlap >= chunk_size:
        raise ValueError(
            "chunk_overlap, chunk_size değerinden küçük olmalıdır."
        )

    chunks = []

    for document in documents:

        text = document["text"]

        start = 0

        while start < len(text):

            end = start + chunk_size

            # Metnin sonuna henüz ulaşmadıysak
            # kelimenin ortasında kesmemeye çalış.
            if end < len(text):

                last_space = text.rfind(
                    " ",
                    start,
                    end
                )

                if last_space != -1:
                    end = last_space

            chunk_text = text[start:end].strip()

            # Boş chunk oluşturma
            if chunk_text:

                chunk = {
                    "text": chunk_text,
                    "page": document["page"],
                    "source": document["source"]
                }

                chunks.append(chunk)

            # Bir sonraki chunk overlap kadar geriden başlasın
            new_start = end - chunk_overlap

            # Yeni chunk kelimenin ortasından başlamasın
            if new_start > 0:

                next_space = text.find(
                    " ",
                    new_start
                )

                if next_space != -1:
                    new_start = next_space + 1

            # Sonsuz döngü oluşmasını engelle
            if new_start <= start:
                new_start = end

            start = new_start

    return chunks


# ==================================================
# EMBEDDING OLUŞTURMA
# ==================================================

def create_embeddings(chunks, embedding_model):
    """
    Chunk metinlerini embedding vektörlerine dönüştürür.
    """

    chunk_texts = [
        chunk["text"]
        for chunk in chunks
    ]

    embeddings = embedding_model.encode(
        chunk_texts
    )

    return embeddings


# ==================================================
# RETRIEVAL
# ==================================================

def retrieve(
    question,
    chunks,
    chunk_embeddings,
    embedding_model,
    top_k=3,
    similarity_threshold=0.30
):
    """
    Kullanıcı sorusuyla en alakalı chunk'ları bulur.

    Her sonuç:
    {
        "text": ...,
        "page": ...,
        "source": ...,
        "score": ...
    }

    şeklinde döner.
    """

    # Soruyu embedding'e dönüştür
    question_embedding = embedding_model.encode(
        [question]
    )

    # Soruyla bütün chunk'ları karşılaştır
    similarities = cosine_similarity(
        question_embedding,
        chunk_embeddings
    )[0]

    # En yüksek skorlu Top-K chunk'ı bul
    top_indices = similarities.argsort()[::-1][:top_k]

    print("\n--- DEBUG: En yüksek benzerlikler ---\n")

    for index in top_indices:
        print(f"Skor: {similarities[index]:.4f}")
        print(f"Kaynak: {chunks[index]['source']}")
        print(f"Sayfa: {chunks[index]['page']}")
        print(f"Metin: {chunks[index]['text'][:300]}")
        print()

    results = []

    for index in top_indices:

        score = similarities[index]

        # Threshold'un altındaysa kullanma
        if score < similarity_threshold:
            continue

        result = {
            "text": chunks[index]["text"],
            "page": chunks[index]["page"],
            "source": chunks[index]["source"],
            "score": float(score)
        }

        results.append(result)

    return results


# ==================================================
# CONTEXT OLUŞTURMA
# ==================================================

def create_context(retrieved_chunks):
    """
    Retrieval sonucundaki chunk'ları Gemini'ye
    gönderilecek tek bir context metnine dönüştürür.
    """

    context_parts = [
        chunk["text"]
        for chunk in retrieved_chunks
    ]

    context = "\n\n".join(context_parts)

    return context


# ==================================================
# GEMINI İLE CEVAP ÜRETME
# ==================================================

def generate_answer(
    question,
    retrieved_chunks,
    client
):
    """
    Retrieval sonucundaki bilgileri kullanarak
    Gemini'den belgeye dayalı cevap üretir.
    """

    # Hiçbir chunk threshold'u geçmediyse
    # Gemini'ye gereksiz API isteği gönderme.
    if not retrieved_chunks:
        return "Bu bilgi belgede bulunamadı."

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


# ==================================================
# KAYNAKLARI GÖSTERME
# ==================================================

def print_sources(retrieved_chunks):
    """
    Retrieval sonucunda bulunan kaynakları
    terminalde gösterir.
    """

    if not retrieved_chunks:
        return

    print("\n--- Kaynaklar ---\n")

    for rank, chunk in enumerate(
        retrieved_chunks,
        start=1
    ):

        print(
            f"[Kaynak {rank}] "
            f"{chunk['source']} - "
            f"Sayfa {chunk['page']} - "
            f"Benzerlik: {chunk['score']:.4f}"
        )

        print(chunk["text"])
        print()


# ==================================================
# ANA PROGRAM
# ==================================================

def main():

    # --------------------------------------------------
    # Gemini API anahtarını yükle
    # --------------------------------------------------

    load_dotenv()

    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        raise ValueError(
            "GEMINI_API_KEY .env dosyasında bulunamadı."
        )


    # --------------------------------------------------
    # Gemini client oluştur
    # --------------------------------------------------

    client = genai.Client(
        api_key=api_key
    )


    # --------------------------------------------------
    # Embedding modelini yükle
    # --------------------------------------------------

    embedding_model = SentenceTransformer(
        EMBEDDING_MODEL_NAME
    )


    # --------------------------------------------------
    # documents/ klasöründeki PDF'leri oku
    # --------------------------------------------------

    documents = load_documents(
        DOCUMENTS_FOLDER
    )

    if not documents:
        print(
            "documents klasöründe okunabilir PDF bulunamadı."
        )
        return

    print(
        f"\nYüklenen toplam sayfa: {len(documents)}"
    )


    # --------------------------------------------------
    # Chunk'ları oluştur
    # --------------------------------------------------

    chunks = create_chunks(
        documents,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )

    print(
        f"Oluşturulan toplam chunk: {len(chunks)}"
    )


    # --------------------------------------------------
    # Chunk embedding'lerini oluştur
    # --------------------------------------------------

    chunk_embeddings = create_embeddings(
        chunks,
        embedding_model
    )


    # --------------------------------------------------
    # Kullanıcıdan soru al
    # --------------------------------------------------

    question = input(
        "\nSorunuzu yazın: "
    ).strip()

    if not question:
        print("Lütfen bir soru girin.")
        return


    # --------------------------------------------------
    # Retrieval
    # --------------------------------------------------

    retrieved_chunks = retrieve(
        question=question,
        chunks=chunks,
        chunk_embeddings=chunk_embeddings,
        embedding_model=embedding_model,
        top_k=TOP_K,
        similarity_threshold=SIMILARITY_THRESHOLD
    )


    # --------------------------------------------------
    # Cevap üret
    # --------------------------------------------------

    answer = generate_answer(
        question=question,
        retrieved_chunks=retrieved_chunks,
        client=client
    )


    # --------------------------------------------------
    # Cevabı göster
    # --------------------------------------------------

    print("\n--- Cevap ---\n")
    print(answer)


    # --------------------------------------------------
    # Kaynakları göster
    # --------------------------------------------------

    print_sources(
        retrieved_chunks
    )


# ==================================================
# PROGRAMI BAŞLAT
# ==================================================

if __name__ == "__main__":
    main()