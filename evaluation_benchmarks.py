BENCHMARK_CASES = [
    {
        "id": "positive_embedding",
        "question": "Embedding nedir?",
        "expected_answerable": True,
        "must_retrieve": [
            "embedding"
        ],
        "must_answer": [
            "vektör"
        ]
    },
    {
        "id": "positive_context_window",
        "question": "Context window ne anlama gelir?",
        "expected_answerable": True,
        "must_retrieve": [
            "context"
        ],
        "must_answer": [
            "model"
        ]
    },
    {
        "id": "positive_overlap",
        "question": "Overlap neden kullanılır?",
        "expected_answerable": True,
        "must_retrieve": [
            "overlap"
        ],
        "must_answer": [
            "bağlam"
        ]
    },
    {
        "id": "positive_metadata",
        "question": "Metadata ne işe yarar?",
        "expected_answerable": True,
        "must_retrieve": [
            "metadata"
        ],
        "must_answer": [
            "kaynak"
        ]
    },
    {
        "id": "positive_rag_flow_uppercase",
        "question": "RAG akışı nasıl olmalı?",
        "expected_answerable": True,
        "must_retrieve": [
            "RAG",
            "akış"
        ],
        "must_answer": [
            "PDF",
            "chunk"
        ]
    },
    {
        "id": "positive_rag_flow_mixedcase",
        "question": "Rag akışı nasıl olmalı?",
        "expected_answerable": True,
        "must_retrieve": [
            "RAG",
            "akış"
        ],
        "must_answer": [
            "PDF",
            "chunk"
        ]
    },
    {
        "id": "positive_hallucination",
        "question": "RAG hallucination riskini nasıl azaltır?",
        "expected_answerable": True,
        "must_retrieve": [
            "hallucination"
        ],
        "must_answer": [
            "belge"
        ]
    },
    {
        "id": "negative_capital",
        "question": "Türkiye'nin başkenti neresidir?",
        "expected_answerable": False,
        "must_retrieve": [],
        "must_answer": []
    },
    {
        "id": "negative_mars_cats",
        "question": "Mars'ta kaç kedi vardır?",
        "expected_answerable": False,
        "must_retrieve": [],
        "must_answer": []
    },
    {
        "id": "negative_python_creator",
        "question": "Python'u kim geliştirdi?",
        "expected_answerable": False,
        "must_retrieve": [],
        "must_answer": []
    }
]
