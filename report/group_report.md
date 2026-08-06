# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K3             |
| Tên nhóm         | B52     |
| Repository         | https://github.com/LawAii-devAI/K3_Day10_Data-Pipeline-Data-Observability-B52 |
| Ngày hoàn thành | 06/08/2026               |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Nguyễn Văn An | 2A202601817 | Source Ingestion | `src/ingestion/crossref.py`, `data/raw/` |
| 2 | Đào Trung Hiếu | 2A202601059 | Cleaning & Test set | `src/ingestion/cleaning.py`, `src/evaluation/testset.py` |
| 3 | Phạm Thái Sơn | 2A202601984 | Observability & Reporting | `src/observability/quality.py`, `reporting.py` |
| 4 | Nguyễn Trọng Đức | 2A202601673 | Corruption & Repair | `src/ingestion/corruption.py` |
| 5 | Nguyễn Trung Hiếu | 2A202601457 | Integration & Comparison | `src/pipelines/phase1.py`, `corruption_flow.py` |

## 2. Tóm tắt kết quả

**Tóm tắt của nhóm:**

Nhóm đã hoàn thành toàn bộ pipeline end-to-end cho cả hai pha, với cả ba trạng thái (baseline/corrupted/repaired) được đánh giá bằng **cùng một LLM provider** (`openai`/`gpt-4o-mini`) để đảm bảo so sánh công bằng. Pha 1 (baseline): Thành viên 1 lấy 24 record từ Crossref API và lưu raw response/records; Thành viên 2 làm sạch thành 24 dòng cleaned dataset và tạo 24 câu hỏi evaluation (8 tài liệu × 3 loại câu hỏi: summary/authors/date); Thành viên 5 ghép thành `phase1.py` chạy ra embedding index (ChromaDB + MiniLM), `baseline_metrics.json`, quality/freshness report và `phase1_report.md`. Baseline đạt `retrieval_hit_rate=1.0`, `mean_token_f1=1.0`, `judge_accuracy=0.9583`, `mean_judge_score=4.8333`, quality PASSED, freshness FRESH.

Pha 2: Thành viên 4 tạo 6 loại lỗi dữ liệu có seed cố định (drop latest records, blank summary, inject noise, truncate title, stale date, duplicate rows) trên bản copy của cleaned dataset. Ảnh hưởng rõ nhất đến agent là tổ hợp `blank_summary` + `inject_summary_noise` + `duplicate_rows`: `retrieval_hit_rate` giảm còn 0.625, `mean_token_f1` giảm còn 0.5116, `judge_accuracy` giảm còn 0.4583, đồng thời `paper_id_unique` và `summary_valid` trong quality check chuyển sang FAILED. `stale_published_date` làm freshness chuyển sang STALE (5 dòng, mới nhất lùi về 2026-07-02). Repair (Thành viên 5, rebuild trực tiếp từ `data/raw/crossref_records.json`) phục hồi quality/freshness về PASSED/FRESH giống hệt baseline, và toàn bộ 4 metric RAG (`retrieval_hit_rate`, `mean_token_f1`, `judge_accuracy`, `mean_judge_score`) đều quay về **đúng bằng giá trị baseline** — bằng chứng rõ ràng nhất cho việc repair phục hồi hoàn toàn chất lượng agent.

Giới hạn còn lại: RAGAS và demo agent (bước tùy chọn) chưa được bật/chạy lại trong lần chạy cuối cùng vì lý do thời gian; nhóm ưu tiên đồng bộ provider cho bốn metric chính trước.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

Điều chỉnh sơ đồ dưới đây nếu cách triển khai thực tế của nhóm khác starter:

```text
Crossref API
    -> raw response/raw records
    -> cleaning và data modeling
    -> embedding + ChromaDB index
    -> evaluation baseline
    -> quality/freshness reports
    -> corruption
    -> re-index và re-evaluate
    -> repair từ dữ liệu nguồn
    -> comparison report
```

### Trách nhiệm của từng khối

| Khối             | Input          | Xử lý chính             | Output/artifact          | Owner          |
| ----------------- | -------------- | -------------------------- | ------------------------ | -------------- |
| Ingestion         | Crossref REST API (`https://api.crossref.org/works`), query `agentic retrieval augmented generation large language model`, filter `from-pub-date`/`has-abstract`, `max_results=24` | Gọi API kèm header liên hệ (Polite Pool), retry/backoff cho `429`/`503`, parse thành `PaperRecord` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Nguyễn Văn An |
| Cleaning          | `PaperRecord` list, `run_date` | Chuẩn hoá text/list, chuẩn hoá ngày, loại record thiếu `paper_id`/`title` hoặc trùng ID, tính `age_days`, ghép `text_for_embedding` | `data/clean/papers_clean.csv`, `papers_clean.json` | Đào Trung Hiếu |
| Evaluation set     | Cleaned DataFrame | Chọn 8 document theo `paper_id`, sinh câu hỏi `summary`/`authors`/`date` deterministic | `data/eval/test_set.json` (24 câu hỏi) | Đào Trung Hiếu |
| Embedding/index   | Cleaned/corrupted/repaired DataFrame | `sentence-transformers/all-MiniLM-L6-v2` encode `text_for_embedding`, nạp vào ChromaDB (`papers-baseline`/`-corrupted`/`-repaired`, cosine HNSW) | `data/embeddings/*.json`, `data/chroma/` | Code tham khảo có sẵn trong starter (`src/retrieval/index.py`, `embeddings.py`), không thuộc TODO riêng của thành viên nào |
| Scoring/metrics    | Index, test set | `evaluate_pipeline`: retrieval hit rate, token F1, LLM-as-judge, RAGAS (tuỳ chọn) | `data/results/*_metrics.json`, `*_answers.json` | Code tham khảo có sẵn (`src/evaluation/metrics.py`) |
| Observability     | Cleaned/corrupted/repaired DataFrame | `run_data_quality_checks` (row count, `paper_id` not-null/unique, `title` not-null, độ dài `summary`, freshness theo `age_days`), `build_freshness_report` | `data/quality/*.json` | Phạm Thái Sơn |
| Corruption/repair | Cleaned DataFrame | 6 scenario lỗi có seed cố định (`seed=42`), rebuild `text_for_embedding`; repair bằng cách build lại từ raw | `data/clean/*_corrupted.*`, `*_repaired.*`, `data/results/corruption_log.json` | Nguyễn Trọng Đức |
| Orchestration     | Toàn bộ module trên | `phase1.py`, `corruption_flow.py`: gọi đúng thứ tự phụ thuộc, xử lý fallback provider, sinh report | `data/reports/phase1_report.md`, `corruption_report.md` | Nguyễn Trung Hiếu |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình             | Giá trị sử dụng |
| ---------------------------- | ------------------- |
| `LLM_PROVIDER`             | `openai`, đồng nhất cho cả ba trạng thái (baseline, corrupted, repaired). Ban đầu Pha 1 chạy bằng `gemini` nhưng bị `429 RESOURCE_EXHAUSTED` (giới hạn free-tier 20 request/ngày); sau khi đổi sang OpenAI cho Pha 2, nhóm chạy lại Pha 1 bằng OpenAI để cả ba trạng thái cùng điều kiện |
| `LLM_MODEL`                | `gpt-4o-mini` (baseline, corrupted, repaired) |
| Embedding model              | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | `max_results=24` (config); thực nhận 24 raw records, 24 cleaned records |
| Retrieval`top_k`           | `4` |
| Freshness threshold          | `180` ngày |
| Random seed, nếu có        | Corruption dùng `seed=42` (`CorruptionConfig`); evaluation set không dùng random seed, chọn document theo thứ tự `paper_id` ổn định |

Không dán nội dung API key hoặc file `.env` vào báo cáo.

### Lệnh cài đặt

```bash
uv sync
```

### Lệnh chạy

Baseline:

```bash
uv run python script/run_phase1.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_phase1.py
```

Corruption flow:

```bash
uv run python script/run_corruption_flow.py
```

Hoặc với môi trường `pip` đã kích hoạt:

```bash
python script/run_corruption_flow.py
```

### Kết quả tái hiện

| Lệnh             | Trạng thái                                    | Thời điểm chạy gần nhất | Bằng chứng                         |
| ----------------- | ----------------------------------------------- | ----------------------------- | ------------------------------------ |
| Baseline pipeline | Thành công (exit code 0). Chạy 2 lần: lần 1 bằng Gemini (lần đầu crash ở bước demo agent optional do `429`, đã fix bằng try/except); lần 2 (dùng cho báo cáo cuối) bằng OpenAI để đồng bộ provider | 2026-08-06T05:51 UTC (lần chạy OpenAI, dùng cho số liệu cuối) | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow   | Thành công (exit code 0). Chạy lại bằng OpenAI sau khi baseline được đồng bộ provider | 2026-08-06T05:51 UTC | `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính                | Giá trị                             |
| --------------------------- | ------------------------------------- |
| Source                      | Crossref REST API — `https://api.crossref.org/works` |
| Query/filter                | Query: `agentic retrieval augmented generation large language model`; filter: `from-pub-date:<180 ngày trước ngày chạy>,has-abstract:true` |
| Thời điểm lấy dữ liệu | Raw artifact được Thành viên 1 fetch và merge vào `origin/main` trước khi Thành viên 5 chạy pipeline tích hợp; không có timestamp fetch riêng được lưu lại ngoài `data/raw/crossref_records.json` đã có sẵn khi bắt đầu Pha 1 |
| Số record nhận được    | 24 (`raw_count=24` trong `phase1_report.md`) |
| Cơ chế retry/backoff      | Header liên hệ dạng `mailto`/`User-Agent` để vào Polite Pool của Crossref, retry với exponential backoff cho `429`/`503` (chi tiết trong báo cáo Thành viên 1) |

### Raw và clean schema

| Trường        | Kiểu dữ liệu | Bắt buộc?  | Ý nghĩa   | Xử lý khi thiếu/sai |
| --------------- | --------------- | ------------ | ----------- | ---------------------- |
| `paper_id` | `str` | Có | DOI đã chuẩn hoá (lowercase), dùng làm document ID xuyên suốt pipeline | Record thiếu `paper_id` bị loại khỏi cleaned dataset |
| `title` | `str` | Có | Tiêu đề bài báo | Record thiếu `title` bị loại khỏi cleaned dataset |
| `summary` | `str` | Không | Abstract, có thể rỗng | Giữ chuỗi rỗng `""`; bị `run_data_quality_checks` báo `summary_valid=false` nếu rỗng |
| `authors` / `categories` | `list[str]` | Không | Danh sách tác giả/chủ đề | Chuẩn hoá thành list không trùng, có thể rỗng |
| `published` / `updated` | `str` (ISO date) | Không (nhưng cần cho freshness) | Ngày công bố/cập nhật | Parse lỗi → chuỗi rỗng; `age_days=None` nếu không parse được |
| `age_days` | `int` (derived) | — | `run_date - published`, floor tại 0 | Dùng cho freshness check với ngưỡng 180 ngày |
| `text_for_embedding` | `str` (derived) | — | Ghép `Title/Summary/Authors/Categories/Published` thành một chuỗi, dùng để encode embedding | Rebuild lại bắt buộc mỗi khi field nguồn thay đổi (ví dụ sau corruption) |

### Quy tắc cleaning

| Quy tắc                                 | Quality dimension liên quan | Số record bị tác động | Cách xác minh      |
| ---------------------------------------- | ---------------------------- | -------------------------: | -------------------- |
| Loại record thiếu `paper_id` hoặc `title`, hoặc `paper_id` trùng (giữ bản đầu tiên) | Validity / Uniqueness | 0 trong lần chạy thực tế (24 raw → 24 clean) | `data/clean/papers_clean.json` có đúng 24 dòng, `paper_id_unique` PASSED trong `data/quality/baseline.json` |
| Chuẩn hoá whitespace cho text, chuẩn hoá `authors`/`categories` thành list không trùng | Consistency | 24/24 dòng đi qua bước chuẩn hoá | So khớp `data/raw/crossref_records.json` với `data/clean/papers_clean.json` |
| Parse `published`/`updated` qua `pd.to_datetime(errors="coerce")`, lỗi → chuỗi rỗng | Validity | 0 dòng lỗi parse trong lần chạy thực tế | `freshness_report.json`: `latest_published`/`oldest_published` đều có giá trị hợp lệ |
| Sắp xếp ổn định theo `published` giảm dần, `paper_id` tăng dần | Consistency (thứ tự tái lập được) | Toàn bộ 24 dòng | So sánh thứ tự dòng giữa các lần chạy `build_clean_dataframe` |

Giải thích cách nhóm tạo `text_for_embedding`, document ID và `age_days`:

`text_for_embedding` được ghép từ các dòng có tiền tố cố định — `Title: ...`, `Summary: ...` (chỉ thêm nếu không rỗng), `Authors: ...`, `Categories: ...`, `Published: ...` — nối bằng `\n`. Document ID (`paper_id`) là DOI đã `lower()` và loại khoảng trắng, giữ ổn định xuyên suốt raw → clean → corrupted → repaired nên `ground_truth_doc_ids` trong evaluation set luôn tham chiếu đúng document dù dữ liệu có bị corrupt. `age_days = max(0, (run_date - published).days)`, dùng `run_date` là thời điểm pipeline chạy cleaning, nên freshness luôn được tính so với thời điểm chạy thực tế chứ không phải thời điểm fetch raw data.

## 6. Evaluation setup

| Thành phần                             | Cấu hình thực tế          |
| ---------------------------------------- | ----------------------------- |
| Số câu hỏi                            | 24 |
| Các`question_type`                    | `summary` (8), `authors` (8), `date` (8) — trên 8 document đại diện; `categories` không phát sinh câu hỏi trong dataset này |
| Ground-truth document ID                 | Chính là `paper_id` của document nguồn dùng để sinh câu hỏi |
| Embedding model                          | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection                  | ChromaDB `PersistentClient`, collection `papers-baseline`/`papers-corrupted`/`papers-repaired`, HNSW cosine |
| Retrieval`top_k`                       | 4 |
| LLM provider/model                       | `gemini-2.5-flash` (baseline) / `gpt-4o-mini` (corrupted, repaired) |
| Test set dùng chung cho ba trạng thái | `data/eval/test_set.json` (không đổi giữa ba lần gọi `evaluate_pipeline`) |

Giải thích vì sao test set được giữ nguyên khi đánh giá baseline, corrupted và repaired:

`corruption_flow.py` gọi `evaluate_pipeline` với cùng `test_set_path=settings.paths.eval_testset` cho cả corrupted và repaired, và test set này chính là file baseline đã dùng ở Pha 1 — pipeline không tạo lại test set mới ở Pha 2. Vì `ground_truth_doc_ids` không đổi và cùng bộ câu hỏi được hỏi lại trên ba index khác nhau, chênh lệch metric giữa ba trạng thái phản ánh đúng thay đổi của dữ liệu/index, không phải do câu hỏi hoặc ground truth bị thay đổi.

## 7. Kết quả baseline

### Artifact checklist

| Artifact                 | Đường dẫn thực tế                | Trạng thái | Ghi chú   |
| ------------------------ | -------------------------------------- | ------------ | ---------- |
| Raw response/records     | `data/raw/`                          | Có | `crossref_response.json`, `crossref_records.json` |
| Cleaned dataset          | `data/clean/`                        | Có | `papers_clean.csv`, `papers_clean.json`, 24 dòng |
| Embedding manifest/index | `data/embeddings/`                   | Có | `papers_embeddings.json` + ChromaDB persist tại `data/chroma/` |
| Evaluation set           | `data/eval/`                         | Có | `test_set.json`, 24 câu hỏi |
| Baseline metrics         | `data/results/baseline_metrics.json` | Có | 24 samples |
| Quality/freshness        | `data/quality/`                      | Có | `baseline.json`, `freshness_report.json` |
| Baseline report          | `data/reports/phase1_report.md`      | Có | Đã khớp với artifact thực tế sau khi sửa lỗi key mismatch (xem Mục 11) |

### Baseline metrics

| Metric                 |       Giá trị | Diễn giải                             |
| ---------------------- | --------------: | --------------------------------------- |
| `retrieval_hit_rate` |     1.0 | Toàn bộ 24 câu hỏi đều retrieve đúng document ground-truth trong top-4 |
| `mean_token_f1`      |     1.0 | Câu trả lời trích xuất trùng khớp hoàn toàn với ground truth trên dữ liệu sạch |
| `judge_accuracy`     |     0.9583 | LLM judge (`gpt-4o-mini`) đánh giá 23/24 câu trả lời là đúng |
| `mean_judge_score`   |     4.8333 | Gần tối đa trên thang 1–5; không tuyệt đối dù dữ liệu sạch 100%, cho thấy bản thân LLM-judge có độ biến thiên riêng |
| Ragas, nếu có        | Bỏ qua (`RUN_RAGAS` không được set) | Nhóm chưa bật RAGAS do thời gian chạy lâu hơn; đây là giới hạn đã biết, xem Mục 12 |

## 8. Data quality và freshness

### Quality checks

| Check        | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline      | Bằng chứng |
| ------------ | ----------------- | ------------------ | ----------------------- | ------------ |
| `row_count` | Completeness | `total_rows > 0` | PASS — 24 dòng | `data/quality/baseline.json` |
| `paper_id_not_null` | Completeness | 0 giá trị null/rỗng | PASS — 0 | `data/quality/baseline.json` |
| `paper_id_unique` | Uniqueness | 0 duplicate | PASS — 0 duplicate | `data/quality/baseline.json` |
| `title_not_null` | Completeness | 0 giá trị null/rỗng | PASS — 0 | `data/quality/baseline.json` |
| `summary_valid` | Completeness | 0 summary rỗng | PASS — 0 rỗng, độ dài TB 1698.38 ký tự | `data/quality/baseline.json` |
| `freshness` | Timeliness | `age_days ≤ 180`, 0 dòng stale | PASS — 0 dòng stale | `data/quality/baseline.json` |

### Freshness

| Thuộc tính               | Giá trị                           |
| -------------------------- | ----------------------------------- |
| Freshness được đo tại | Cleaned DataFrame (baseline), qua `build_freshness_report` |
| Timestamp mới nhất       | `2026-08-01` (`latest_published`); cũ nhất `2026-02-12` (`oldest_published`) |
| Ngưỡng freshness         | 180 ngày |
| Trạng thái baseline      | FRESH (`is_fresh=true`, `stale_rows=0`) |
| Lý do                     | Toàn bộ 24 record có `published` trong vòng 180 ngày tính từ thời điểm chạy, không có record nào vượt ngưỡng |

## 9. Corruption scenarios và repair

| Corruption         | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair   |
| ------------------ | ---------- | ---------------------: | ------------------------ | --------------------- | -------------- |
| `drop_latest_records` | Sắp xếp `published` giảm dần, xoá các record mới nhất (15%) | 4 | Completeness/freshness giảm | `output_rows` giảm từ 24 xuống 23; góp phần làm `retrieval_hit_rate` giảm | Rebuild từ `data/raw/crossref_records.json` |
| `blank_summary` | `summary=""`, `summary_chars=0` (20%) | 4 | Completeness giảm | `summary_valid.passed=false`, `empty_count=2` (sau overlap với duplicate) | Rebuild từ raw |
| `inject_summary_noise` | Nối `" [CORRUPTED_NOISE] xqzv 000 ???"` vào summary (20%) | 4 | Validity/relevance giảm | Vector embedding bị nhiễu, góp phần giảm `retrieval_hit_rate`/`mean_token_f1` | Rebuild từ raw |
| `truncate_title` | Cắt title còn tối đa 18 ký tự (20%) | 4 | Metadata validity giảm | Giảm khả năng nhận diện tài liệu qua title | Rebuild từ raw |
| `stale_published_date` | Trừ 730 ngày khỏi `published`, cộng 730 vào `age_days` (20%) | 4 | Freshness giảm | `freshness_report_corrupted.json`: `is_fresh=false`, `stale_rows=5`, `latest_published` lùi còn `2026-07-02` | Rebuild từ raw |
| `duplicate_rows` | Sao chép record và nối vào cuối DataFrame (15%) | 3 | Uniqueness giảm | `paper_id_unique.passed=false`, `duplicate_count=3` | Rebuild từ raw (loại trùng tự nhiên vì build lại từ `PaperRecord` gốc) |

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: Có
- Nhận xét: Log ghi đầy đủ `seed=42`, `input_rows=24`, `output_rows=23`, config tỷ lệ từng loại lỗi, và với mỗi scenario có `count` và danh sách `record_ids` (DOI) bị tác động — đủ chi tiết để truy vết ngược từng record.

Giải thích cách repair đảm bảo dữ liệu được phục hồi từ nguồn đáng tin cậy thay vì chỉ che kết quả lỗi:

`corruption_flow.py` không sửa lại DataFrame đã bị corrupt. Bước repair gọi `load_raw_records(data/raw/crossref_records.json)` rồi `build_clean_dataframe` lại từ đầu trên raw records gốc — nguồn này không hề bị `corrupt_clean_dataframe` chạm tới (hàm corruption chỉ nhận bản copy của cleaned DataFrame). Vì vậy repaired dataset không phải là "vá" dữ liệu lỗi mà là tái tạo độc lập từ nguồn tin cậy, và kết quả quality/freshness của repaired trùng khớp tuyệt đối với baseline (0 duplicate, 0 stale, cùng `latest_published`/`oldest_published`) là bằng chứng cho việc phục hồi thực sự chứ không phải che giấu lỗi.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal            | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét   |
| ------------------------ | -------: | --------: | -------: | -----------------------: | --------------: | ------------ |
| `retrieval_hit_rate`   |   1.0000 |    0.6250 |   1.0000 |                  -0.3750 |    100% về baseline | |
| `mean_token_f1`        |   1.0000 |    0.5116 |   1.0000 |                  -0.4884 |    100% về baseline | |
| `judge_accuracy`       |   0.9583 |    0.4583 |   0.9583 |                  -0.5000 |    100% về baseline | Cả ba trạng thái cùng judge bằng `gpt-4o-mini` |
| `mean_judge_score`     |   4.8333 |    3.0833 |   4.8333 |                  -1.7500 |    100% về baseline | Cùng judge model, không còn nhiễu do khác provider |
| Quality checks pass/fail |   PASSED |    FAILED |   PASSED |     3 duplicate + 2 summary rỗng |  Phục hồi hoàn toàn (0 lỗi) | `data/quality/corrupted.json` vs `repaired.json` |
| Freshness status         |    FRESH |     STALE |    FRESH |            5 dòng stale, mới nhất lùi ~1 tháng |  Phục hồi hoàn toàn (0 stale) | `stale_published_date` corruption bị bắt đúng |

Hai kết luận nhân quả được hỗ trợ bởi artifact:

1. **Corruption → quality/freshness xấu đi → agent metric giảm:** `blank_summary` + `inject_summary_noise` + `duplicate_rows` (Thành viên 4, `data/results/corruption_log.json`) làm `data/quality/corrupted.json` báo `paper_id_unique.passed=false` (3 duplicate) và `summary_valid.passed=false` (2 rỗng); đồng thời `stale_published_date` làm `freshness_report_corrupted.json` báo `is_fresh=false` (5 dòng stale). Hai tín hiệu quality/freshness xấu đi này đi kèm với cả 4 metric RAG giảm đồng loạt (`retrieval_hit_rate` 1.0→0.625, `mean_token_f1` 1.0→0.5116, `judge_accuracy` 0.9583→0.4583, `mean_judge_score` 4.83→3.08) trên cùng evaluation set và cùng LLM judge — chứng minh dữ liệu lỗi làm giảm trực tiếp chất lượng RAG, không chỉ là quality check báo lỗi suông.
2. **Repair từ raw → quality/freshness phục hồi → agent metric phục hồi hoàn toàn:** `build_clean_dataframe` chạy lại trên `data/raw/crossref_records.json` (nguồn không bị corruption chạm tới) làm `data/quality/repaired.json` và `freshness_report_repaired.json` trở lại PASSED/FRESH giống hệt baseline (0 duplicate, 0 stale, cùng `latest_published`/`oldest_published`). Sau khi đồng bộ cả ba trạng thái trên cùng `LLM_PROVIDER=openai`/`gpt-4o-mini`, cả 4 metric RAG của repaired đều quay về **đúng bằng giá trị baseline** (không chỉ gần bằng) — bằng chứng mạnh nhất cho thấy repair phục hồi hoàn toàn chất lượng agent, và phần chênh lệch nhỏ quan sát được ở lần chạy trước (khi baseline dùng Gemini, corrupted/repaired dùng OpenAI) đúng là do khác judge model chứ không phải do repair chưa hoàn chỉnh.

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** `data/reports/phase1_report.md` sinh ra với `**Query**: N/A`, `**Raw Records Fetched**: N/A`, `**Clean Records Processed**: N/A` dù pipeline chạy không lỗi (exit code 0).
- **Nguyên nhân:** `generate_phase1_report` (Thành viên 3, `src/observability/reporting.py`) đọc `source_summary.get("query")`, `source_summary.get("raw_count", ...)`, `source_summary.get("clean_count", ...)`. Bản `phase1.py` đầu tiên của Thành viên 5 lại truyền key `source_query`, `source_filter`, `record_count` — sai tên field so với contract thực tế của hàm reporting, nên toàn bộ rơi vào giá trị mặc định `"N/A"` mà không có exception nào báo lỗi.
- **Cách xử lý:** Đọc trực tiếp implementation của `reporting.py` để lấy đúng tên key, sửa dict `source_summary` trong `phase1.py` thành `{"source_api", "query", "raw_count", "clean_count"}`. Không sửa `reporting.py` vì nằm ngoài phạm vi của Thành viên 5.
- **Cách xác minh:** Chạy lại `uv run python script/run_phase1.py`, đọc lại `data/reports/phase1_report.md` — các trường hiển thị đúng giá trị thật (`Query: agentic retrieval augmented generation large language model`, `Raw Records Fetched: 24`, `Clean Records Processed: 24`).

Một vấn đề tích hợp thứ hai (blocker hạ tầng, không phải lỗi code, **đã được giải quyết**): bước demo agent trong `phase1.py` (optional theo Guide.md) gọi LLM thật và bị `429 RESOURCE_EXHAUSTED` khi quota free-tier của Gemini (20 request/ngày) cạn sau khi `evaluate_pipeline` đã dùng gần hết quota để chấm judge cho 24 câu hỏi ở lần chạy đầu tiên. Nhóm xử lý theo hai bước: (1) bọc bước demo trong `try/except` để không chặn pipeline chính; (2) chuyển hẳn `LLM_PROVIDER` sang OpenAI (`gpt-4o-mini`) và **chạy lại cả Pha 1 lẫn Pha 2** để cả ba trạng thái cùng judge model — kết quả cuối trong Mục 7 và Mục 10 đã phản ánh lần chạy đồng bộ này, không còn bị ảnh hưởng bởi quota Gemini.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng   | Hướng cải thiện có thể kiểm chứng |
| --------------------- | -------------- | ----------------------------------------- |
| RAGAS chưa bật | Thiếu `answer_relevancy`/`context_precision`/`context_recall`/`faithfulness` làm bằng chứng phụ | Set `RUN_RAGAS=1` và chạy lại (chấp nhận thời gian chạy lâu hơn) |
| Toàn bộ artifact và code thay đổi của Thành viên 5 hiện chưa commit lên `Role5_NguyenTrungHieu` | Rủi ro mất kết quả nếu không commit trước khi nộp | Rà `git status`, loại trừ `.env`, commit/push trước deadline |

Cập nhật (2026-08-06): báo cáo cá nhân của cả 5 thành viên, bao gồm `individual_report_PhamThaiSon_01984.md` (commit `9a470a7`), hiện đã đầy đủ trên `main`. Sau đó, nhóm đã chạy lại baseline + corruption flow đồng bộ trên `LLM_PROVIDER=openai` — hai giới hạn "khác judge model giữa các trạng thái" và "demo agent bị bỏ qua do rate-limit" nêu ở lần cập nhật trước đã được giải quyết; `data/results/agent_demo_answers.json` đã có đủ 3 câu trả lời demo thực tế.

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp (`script/run_phase1.py`, `script/run_corruption_flow.py`, cả hai exit code 0).
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (`data/eval/test_set.json`, không đổi giữa ba lần evaluate).
- [x] Bảng metrics khớp với các file trong `data/results/`.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [x] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng (5/5: `2A202601817_NguyenVanAn.md`, `individual_report_DaoTrungHieu_01059.md`, `individual_report_PhamThaiSon_01984.md`, `individual_report_NguyenTrongDuc_01673.md`, `individual_report_NguyenTrungHieu_01457.md`).
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh (`.env` nằm trong `.gitignore`, không có key nào được dán vào báo cáo).
