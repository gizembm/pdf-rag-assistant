import argparse
from io import BytesIO
from pathlib import Path

from evaluation_benchmarks import BENCHMARK_CASES
from rag import (
    NOT_FOUND_ANSWER,
    create_embeddings,
    create_vector_store,
    evaluate_answerability,
    expand_with_neighbors,
    generate_answer,
    load_embedding_model,
    process_pdfs,
    retrieve
)


class UploadedFileForEvaluation(BytesIO):
    def __init__(self, path):
        self.file_path = Path(path)
        super().__init__(self.file_path.read_bytes())
        self.name = self.file_path.name

    def getvalue(self):
        current_position = self.tell()
        self.seek(0)
        value = self.read()
        self.seek(current_position)

        return value


def make_uploaded_file(path):
    uploaded_file = UploadedFileForEvaluation(path)

    return uploaded_file


def contains_all(text, keywords):
    normalized_text = text.casefold()

    return all(
        keyword.casefold() in normalized_text
        for keyword in keywords
    )


def evaluate_case(case, collection, embedding_model, use_final_answer):
    retrieved_results = retrieve(
        case["question"],
        collection,
        embedding_model,
        top_k=3
    )

    expanded_results = expand_with_neighbors(
        retrieved_results,
        collection
    )

    retrieved_text = "\n".join(
        result["text"]
        for result in expanded_results
    )

    retrieval_passed = contains_all(
        retrieved_text,
        case["must_retrieve"]
    )

    answerable, evidence_ids = evaluate_answerability(
        case["question"],
        expanded_results
    )

    answerability_passed = (
        answerable == case["expected_answerable"]
    )

    answer = ""
    final_answer_passed = True

    if use_final_answer:
        answer, source_ids = generate_answer(
            case["question"],
            expanded_results
        )

        if case["expected_answerable"]:
            final_answer_passed = (
                answer != NOT_FOUND_ANSWER
                and bool(source_ids)
                and contains_all(
                    answer,
                    case["must_answer"]
                )
            )
        else:
            final_answer_passed = (
                answer == NOT_FOUND_ANSWER
                and not source_ids
            )

    return {
        "id": case["id"],
        "question": case["question"],
        "retrieval_passed": retrieval_passed,
        "answerability_passed": answerability_passed,
        "final_answer_passed": final_answer_passed,
        "answerable": answerable,
        "evidence_ids": evidence_ids,
        "answer": answer
    }


def print_result(result):
    status = "PASS"

    if not (
        result["retrieval_passed"]
        and result["answerability_passed"]
        and result["final_answer_passed"]
    ):
        status = "FAIL"

    print(f"[{status}] {result['id']}")
    print(f"  Soru: {result['question']}")
    print(f"  Retrieval: {result['retrieval_passed']}")
    print(f"  Answerability: {result['answerability_passed']}")
    print(f"  Final answer: {result['final_answer_passed']}")
    print(f"  Answerable: {result['answerable']}")
    print(f"  Evidence IDs: {result['evidence_ids']}")

    if result["answer"]:
        print(f"  Cevap: {result['answer']}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="PDF RAG Assistant regression evaluation"
    )
    parser.add_argument(
        "--pdf",
        required=True,
        help="Benchmark PDF dosyasının yolu"
    )
    parser.add_argument(
        "--skip-final-answer",
        action="store_true",
        help="Sadece retrieval ve answerability kontrollerini çalıştır"
    )

    args = parser.parse_args()

    uploaded_file = make_uploaded_file(args.pdf)
    embedding_model = load_embedding_model()
    chunks = process_pdfs([uploaded_file])
    embeddings = create_embeddings(chunks, embedding_model)
    collection = create_vector_store(chunks, embeddings)

    use_final_answer = not args.skip_final_answer
    results = []

    for case in BENCHMARK_CASES:
        result = evaluate_case(
            case,
            collection,
            embedding_model,
            use_final_answer=use_final_answer
        )
        results.append(result)
        print_result(result)

    failed_results = [
        result
        for result in results
        if not (
            result["retrieval_passed"]
            and result["answerability_passed"]
            and result["final_answer_passed"]
        )
    ]

    print("=" * 72)
    print(f"Toplam: {len(results)}")
    print(f"Başarılı: {len(results) - len(failed_results)}")
    print(f"Başarısız: {len(failed_results)}")

    if failed_results:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
