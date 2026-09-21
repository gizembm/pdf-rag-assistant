# PDF RAG Assistant

PDF RAG Assistant, yüklenen PDF belgeleri üzerinde kaynaklı soru-cevap deneyimi sunan yerel bir Streamlit uygulamasıdır. Belgeler parçalara ayrılır, çok dilli embedding modeliyle vektörleştirilir ve Chroma üzerinde saklanır. İlgili parçalar Gemini'ye bağlam olarak verilerek belgeye dayalı cevaplar üretilir.

## Özellikler

- Birden fazla PDF yükleme ve kalıcı belge setleri
- Türkçe dahil çok dilli anlamsal arama
- Chroma tabanlı yerel vektör deposu
- Gemini ile yalnızca belge bağlamına dayalı cevap üretimi
- Kaynak dosya ve sayfa bilgisi
- SQLite üzerinde kalıcı sohbet geçmişi
- Kayıtlı belge setleri ve sohbet yönetimi
- Açık renkli, üç panelli Streamlit çalışma alanı
- Embedding modelinin ihtiyaç anında yüklenmesi

## Kullanılan Teknolojiler

- Python
- Streamlit
- Sentence Transformers (`intfloat/multilingual-e5-base`)
- ChromaDB
- Google Gemini
- SQLite
- PyPDF

## Kurulum

Projeyi klonlayın ve proje klasörüne geçin:

```bash
git clone <repository-url>
cd pdf-rag-assistant
```

Sanal ortam oluşturup etkinleştirin:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Bağımlılıkları yükleyin:

```powershell
pip install -r requirements.txt
```

`.env.example` dosyasını `.env` olarak kopyalayın ve Gemini API anahtarınızı ekleyin:

```env
GEMINI_API_KEY=your_gemini_api_key_here
```

Uygulamayı başlatın:

```powershell
streamlit run streamlit_app.py
```

Ardından tarayıcıda `http://localhost:8501` adresini açın.

## Kullanım

1. Sol panelden bir veya daha fazla PDF seçin.
2. Belgeleri kaydedip indeksleyin veya daha önce kaydedilmiş bir belge setini açın.
3. Belge hakkında sorunuzu çalışma alanına yazın.
4. Cevabı ve kullanılan kaynakların sayfa bilgilerini sağ panelden inceleyin.
5. Kayıtlı sohbetler arasında sol panelden geçiş yapın.

İlk indeksleme veya ilk soru sırasında embedding modelinin belleğe yüklenmesi biraz sürebilir. Model uygulama süreci boyunca önbellekte tutulur. Kayıtlı ve sağlam bir Chroma indeksi açılırken model gereksiz yere yüklenmez.

## Proje Yapısı

```text
streamlit_app.py       Streamlit arayüzü ve uygulama akışı
styles.py              Arayüz stilleri
rag.py                 PDF işleme, embedding, retrieval ve Gemini akışı
document_service.py    Belge seti ve indeks yaşam döngüsü
database.py            SQLite belge ve sohbet kayıtları
storage.py             Yüklenen PDF dosyalarının yerel saklanması
requirements.txt       Python bağımlılıkları
```

## Yerel Veriler

Aşağıdaki içerikler Git deposuna eklenmez:

- `.env` ve API anahtarları
- `chat_history.db`
- `chroma_db/`
- `data/uploads/`
- `documents/`
- `.venv/`

Bu dosyalar uygulama çalışırken yerel olarak oluşturulur veya kullanıcı tarafından sağlanır.

## Güvenlik Notu

API anahtarınızı kaynak koduna yazmayın ve `.env` dosyasını Git'e eklemeyin. Uygulama cevap üretirken Gemini API'ye soru ile seçilen belge parçalarını gönderir.

## Lisans

Bu proje için henüz bir lisans tanımlanmamıştır.
