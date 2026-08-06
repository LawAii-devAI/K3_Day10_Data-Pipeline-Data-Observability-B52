# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Trung Hiếu |
| MSSV | 2A202601457 |
| Khóa/Lớp | K3 |
| Tên nhóm | B52 |
| Vai trò chính | Thành viên 5 — Pipeline integration & evidence owner |
| Repository | `LawAii-devAI/K3_Day10_Data-Pipeline-Data-Observability-B52` |
| Branch | `Role5_NguyenTrungHieu` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Baseline orchestration | `src/pipelines/phase1.py` — `main` | Cleaned/raw ingestion functions, cleaning, test-set, quality, freshness, reporting, agent — tất cả do các thành viên khác implement | `data/clean/`, `data/embeddings/papers_embeddings.json`, `data/eval/test_set.json`, `data/results/baseline_metrics.json`, `data/results/baseline_answers.json`, `data/quality/baseline.json`, `data/quality/freshness_report.json`, `data/reports/phase1_report.md` | Hoàn thành, đã chạy thành công end-to-end |
| Corruption & comparison orchestration | `src/pipelines/corruption_flow.py` — `main` | `baseline_metrics.json`, cleaned baseline dataset, hàm `corrupt_clean_dataframe`, `run_data_quality_checks`, `build_freshness_report`, `generate_corruption_report` | `data/clean/papers_clean_corrupted.*`, `papers_clean_repaired.*`, `data/embeddings/*_corrupted.json`, `*_repaired.json`, `data/results/corruption_log.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` | Hoàn thành, đã chạy thành công end-to-end |
| Môi trường dự án | `pyproject.toml`, `uv.lock`, `.env` | — | Cài `uv`, chạy `uv sync` tạo `.venv` với toàn bộ dependency, tạo `.env` từ `.env.example` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Phát hiện lệch contract report | Thành viên 3 — `src/observability/reporting.py` | `generate_phase1_report` đọc key `query`, `raw_count`, `clean_count`; bản orchestration đầu tiên của tôi truyền `source_query`, `record_count` nên report ra `N/A`. Sửa lại dict `source_summary` trong `phase1.py` cho khớp contract, không sửa `reporting.py`. |
| Merge code của cả nhóm | Toàn nhóm | Merge `origin/main` (các commit của Thành viên 1, 2, 4) vào `Role5_NguyenTrungHieu`, xác nhận không conflict với `phase1.py`/`corruption_flow.py`. |
| Xử lý blocker quota LLM | Toàn nhóm (ảnh hưởng Pha 2) | Phát hiện Gemini free-tier (`gemini-2.5-flash`, giới hạn 20 request/ngày) bị `429 RESOURCE_EXHAUSTED` do các lệnh gọi LLM-judge trong `evaluate_pipeline` dùng gần hết quota; chuyển `LLM_PROVIDER=openai`, `LLM_MODEL=gpt-4o-mini` trong `.env` để chạy tiếp Pha 2. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Viết orchestration Pha 1 | `src/pipelines/phase1.py` | Gọi đúng thứ tự: fetch/load raw → clean → build Chroma index → tạo/`load` test set → `evaluate_pipeline` → quality checks → freshness report → `generate_phase1_report` → demo agent (optional, có try/except) | Chạy `uv run python script/run_phase1.py`, exit code 0, artifacts thực tế trong `data/results/`, `data/quality/`, `data/reports/` |
| Viết orchestration Pha 2 | `src/pipelines/corruption_flow.py` | Đọc baseline → `corrupt_clean_dataframe` → rebuild index & evaluate corrupted → quality/freshness corrupted → repair từ `data/raw/crossref_records.json` → rebuild index & evaluate repaired → `generate_corruption_report` | Chạy `uv run python script/run_corruption_flow.py`, exit code 0, artifacts thực tế trong `data/results/corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `data/reports/corruption_report.md` |
| Sửa lỗi tích hợp #1 | `phase1.py` — dict `source_summary` | Report không còn hiển thị `N/A` ở Query/Raw Records/Clean Records | So sánh `data/reports/phase1_report.md` trước/sau khi sửa |
| Sửa lỗi tích hợp #2 | `phase1.py` — bước demo agent | Bọc `build_agent`/`run_agent_question` trong `try/except`; lỗi `429` không còn làm crash toàn bộ pipeline, chỉ in cảnh báo và bỏ qua bước optional | Chạy lại pipeline, script kết thúc với `Phase 1 complete: 24 papers indexed.` thay vì traceback |
| Xử lý blocker quota Gemini | `.env` | Chuyển provider sang OpenAI cho Pha 2; sau đó chạy lại cả Pha 1 bằng OpenAI để đồng bộ judge model cho cả ba trạng thái | Chạy lại `script/run_phase1.py` và `script/run_corruption_flow.py` với `LLM_PROVIDER=openai` cho cả hai; `data/results/*_metrics.json` đều ghi `gpt-4o-mini` |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Các module ingestion, cleaning, evaluation, observability và corruption được các thành viên khác implement độc lập theo đúng signature đã thống nhất trong `src/core/config.py` (`Settings`, `Paths`). Nhiệm vụ của tôi là ghép các hàm đó lại thành hai flow chạy được thật, đúng thứ tự phụ thuộc, dùng đúng đường dẫn artifact, và tạo ra bằng chứng số liệu (baseline vs corrupted vs repaired) mà không sửa logic nội bộ của module khác.

### Cách triển khai

`phase1.py::main()` thực hiện tuần tự: `fetch_source_records`/`load_raw_records` (theo cờ `settings.refresh_source`) → `build_clean_dataframe` → ghi CSV/JSON → `LocalEmbeddingIndex.build` (ChromaDB + MiniLM) → `build_test_set` (theo cờ `settings.refresh_test_set`) → `evaluate_pipeline` (đã có sẵn, tự ghi `baseline_metrics.json`/`baseline_answers.json`) → `run_data_quality_checks` → `build_freshness_report` → `generate_phase1_report` → demo agent trên 3 câu hỏi đầu của test set (bước optional theo Guide.md bước 8, bọc try/except).

`corruption_flow.py::main()` đọc `baseline_metrics.json` và `papers_clean.json` đã có (dừng sớm với `RuntimeError` rõ ràng nếu baseline chưa chạy), gọi `corrupt_clean_dataframe` trên bản copy của baseline DataFrame, ghi corrupted CSV/JSON, rebuild index/evaluate trên corrupted, chạy quality/freshness trên corrupted, sau đó **repair bằng cách build lại `build_clean_dataframe` trực tiếp từ `data/raw/crossref_records.json`** (không sửa corrupted DataFrame), rebuild index/evaluate trên repaired, chạy quality/freshness trên repaired, và gọi `generate_corruption_report` so sánh cả ba trạng thái.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Toàn bộ output của Thành viên 1–4: raw records, cleaned dataset, test set, hàm quality/freshness/reporting, hàm corruption |
| Output | Hai script chạy được (`script/run_phase1.py`, `script/run_corruption_flow.py`) và toàn bộ artifact cuối trong `data/results/`, `data/reports/` |
| Module phụ thuộc | Tất cả module trong `src/ingestion`, `src/evaluation`, `src/observability`, `src/retrieval`, `src/core` |
| Module sử dụng output | Không có module downstream nào khác; đây là điểm cuối của pipeline, output phục vụ trực tiếp cho báo cáo nhóm |
| Điều kiện lỗi cần xử lý | Baseline chưa chạy khi gọi corruption flow (`RuntimeError` chủ động); LLM rate-limit ở bước demo agent (try/except, không chặn pipeline chính) |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

- **Kết quả mong đợi:** Cả hai script chạy hết, không traceback, sinh đủ artifact liệt kê ở Mục 6 README.
- **Kết quả thực tế:** Cả hai script kết thúc với exit code 0. Log kết thúc: `Phase 1 complete: 24 papers indexed.` và `Corruption flow complete.` kèm dict metrics ba trạng thái.
- **Artifact/log:** `data/results/baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json`, `corruption_log.json`, `data/reports/phase1_report.md`, `corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Bước demo agent (Guide.md bước 8, mô tả là "có thể") gọi LLM thật qua `build_agent`/`run_agent_question`; trong lần chạy đầu, `evaluate_pipeline` đã dùng gần hết quota free-tier của Gemini (20 request/ngày cho `gemini-2.5-flash`) để chấm judge cho 24 câu hỏi, khiến bước demo agent phía sau bị `429 RESOURCE_EXHAUSTED` và làm cả script `phase1.py` crash dù toàn bộ metrics/report bắt buộc đã được ghi ra trước đó.
- **Các phương án đã cân nhắc:** (1) Bỏ hẳn bước demo agent khỏi `phase1.py`; (2) thêm retry/backoff cho riêng bước demo; (3) bọc bước demo trong `try/except` và chỉ in cảnh báo.
- **Phương án đã chọn:** (3) — bọc `try/except Exception` quanh đúng đoạn demo agent, in `Skipping agent demo (optional step): <lỗi>` rồi tiếp tục.
- **Lý do:** Bước này được Guide.md mô tả là tùy chọn ("có thể demo"), không nằm trong danh sách artifact bắt buộc ở README Mục 6. Toàn bộ artifact bắt buộc (metrics, quality, freshness, report) đã được ghi trước khi gọi demo agent, nên một lỗi rate-limit ở bước phụ không nên làm mất kết quả chính đã tính đúng.
- **Bằng chứng quyết định phù hợp:** Sau khi sửa, chạy lại `script/run_phase1.py` in ra dòng cảnh báo `Skipping agent demo (optional step): ...RESOURCE_EXHAUSTED...` nhưng script vẫn kết thúc với exit code 0 và in đủ `Baseline metrics: {...}`.

## 6. Một vấn đề tích hợp đã xử lý

- **Triệu chứng:** `data/reports/phase1_report.md` sinh ra hiển thị `**Query**: `N/A``, `**Raw Records Fetched**: N/A`, `**Clean Records Processed**: N/A` dù pipeline chạy không lỗi.
- **Nguyên nhân gốc:** `generate_phase1_report` (do Thành viên 3 implement) đọc `source_summary.get("query")`, `source_summary.get("raw_count", source_summary.get("total_raw"))`, `source_summary.get("clean_count", ...)`. Bản `phase1.py` đầu tiên của tôi lại truyền key `source_query`, `source_filter`, `record_count` — không khớp tên field, nên toàn bộ rơi vào nhánh default `"N/A"`.
- **Cách xử lý:** Đọc trực tiếp `src/observability/reporting.py` để lấy đúng tên key kỳ vọng, sửa dict `source_summary` trong `phase1.py` thành `{"source_api", "query", "raw_count", "clean_count"}` — không sửa `reporting.py` vì đó không thuộc phạm vi của tôi.
- **Cách xác minh:** Chạy lại `script/run_phase1.py` và đọc `data/reports/phase1_report.md`; các trường hiển thị đúng giá trị thật (`Query: agentic retrieval augmented generation large language model`, `Raw Records Fetched: 24`, `Clean Records Processed: 24`).
- **Điều học được:** Interface giữa các module không chỉ là type signature mà còn là tên key bên trong `dict`/`Settings`; nhóm cần thống nhất rõ hơn nữa (hoặc dùng `TypedDict`/`dataclass`) để tránh lỗi "N/A" âm thầm không ném exception.

## 7. Hiểu biết về luồng end-to-end

1. Thành viên 1 gọi Crossref API (`https://api.crossref.org/works`, query `agentic retrieval augmented generation large language model`, filter theo `from-pub-date`/`has-abstract`), lưu raw response và raw records vào `data/raw/`.
2. Thành viên 2 chuẩn hoá 24 record thành `papers_clean.csv/json` với các cột phụ trợ (`authors_joined`, `categories_joined`, `summary_chars`, `age_days`, `text_for_embedding`), đồng thời tạo 24 câu hỏi evaluation trong `data/eval/test_set.json` với `ground_truth_doc_ids` chính là `paper_id`.
3. `phase1.py` (phần của tôi) dùng `LocalEmbeddingIndex.build` để encode `text_for_embedding` bằng `all-MiniLM-L6-v2` và nạp vào collection `papers-baseline` trong ChromaDB, sau đó `evaluate_pipeline` (code tham khảo có sẵn) chạy agent trên toàn bộ test set, tính `retrieval_hit_rate` (document ground-truth có nằm trong top-k kết quả không), `mean_token_f1` (so khớp token câu trả lời với ground truth) và judge score qua LLM.
4. Thành viên 3 chạy `run_data_quality_checks` (kiểm tra row count, `paper_id` not-null/unique, `title` not-null, độ dài `summary`, số dòng stale theo `age_days`) và `build_freshness_report` (latest/oldest published, số dòng stale, ngưỡng 180 ngày) trên cùng DataFrame.
5. Thành viên 4 tạo 6 loại lỗi có kiểm soát (`drop_latest_records`, `blank_summary`, `inject_summary_noise`, `truncate_title`, `stale_published_date`, `duplicate_rows`) với seed cố định (42), luôn rebuild `text_for_embedding` sau khi sửa field nguồn để corruption thực sự lan vào vector embedding chứ không chỉ ở metadata bề mặt.
6. `corruption_flow.py` (phần của tôi) rebuild index/evaluate trên bản corrupted bằng **đúng test set baseline**, chạy lại quality/freshness, sau đó repair bằng cách build lại từ `data/raw/crossref_records.json` (nguồn gốc, không đụng tới bản corrupted), rebuild index/evaluate trên bản repaired, và tổng hợp bảng so sánh ba trạng thái vào `data/reports/corruption_report.md`.
7. Vì cả ba trạng thái dùng chung một test set và chung `ground_truth_doc_ids`, mọi thay đổi về `retrieval_hit_rate`/`mean_token_f1` phản ánh đúng tác động của thay đổi dữ liệu, không phải do câu hỏi khác nhau.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.6250 | 1.0000 | Giảm 37.5 điểm phần trăm khi corrupt (mất record + nhiễu embedding), phục hồi tuyệt đối sau repair. |
| `mean_token_f1` | 1.0000 | 0.5116 | 1.0000 | Giảm gần một nửa, phục hồi tuyệt đối sau repair. |
| `judge_accuracy` | 0.9583 | 0.4583 | 0.9583 | Giảm mạnh khi corrupt, **phục hồi đúng bằng baseline** sau repair (không chỉ gần bằng). |
| `mean_judge_score` | 4.8333 | 3.0833 | 4.8333 | Cùng xu hướng với judge_accuracy, phục hồi đúng bằng baseline. |
| Data quality | PASSED (24 dòng, 0 lỗi) | **FAILED** (23 dòng, 3 `paper_id` trùng, 2 summary rỗng) | PASSED (24 dòng, 0 lỗi) | Quality check phát hiện đúng loại lỗi mà corruption tạo ra (duplicate + blank summary). |
| Freshness | FRESH (0 stale, mới nhất 2026-08-01) | **STALE** (5 stale, mới nhất lùi còn 2026-07-02, cũ nhất 2024-05-22) | FRESH (0 stale) | `stale_published_date` corruption bị freshness check bắt đúng. |

**Cập nhật về tính so sánh được:** ở lần chạy đầu, baseline được chấm bằng `gemini-2.5-flash` còn corrupted/repaired bằng `gpt-4o-mini` (do quota Gemini cạn giữa chừng), nên `judge_accuracy`/`mean_judge_score` chưa hoàn toàn cùng điều kiện. Theo đề nghị của người dùng, tôi đã chạy lại **cả Pha 1 lẫn Pha 2** với `LLM_PROVIDER=openai` cho toàn bộ ba trạng thái. Kết quả trong bảng trên là từ lần chạy đồng bộ này: `judge_accuracy`/`mean_judge_score` của baseline giảm nhẹ so với lần chạy Gemini trước đó (1.0/5.0 → 0.9583/4.8333 — bản thân `gpt-4o-mini` chấm khắt khe hơn một chút trên cùng dữ liệu sạch), nhưng đổi lại repaired giờ **khớp tuyệt đối** với baseline ở cả 4 metric, không còn khoảng cách nhỏ nào cần giải thích bằng yếu tố ngoài corruption.

### Kết luận từ số liệu

1. **Chuỗi 1:** `blank_summary` + `inject_summary_noise` + `duplicate_rows` (Thành viên 4) → `data/quality/corrupted.json` báo `paper_id_unique.passed=false` (3 duplicate) và `summary_valid.passed=false` (2 rỗng) → cả 4 metric RAG giảm đồng loạt trên cùng evaluation set và cùng judge model, vì vector embedding của các record bị hỏng không còn phản ánh đúng nội dung gốc.
2. **Chuỗi 2:** `stale_published_date` (lùi 730 ngày trên 4 record) → `freshness_report_corrupted.json` báo `is_fresh=false`, `stale_rows=5` → góp phần làm giảm khả năng agent trả lời đúng các câu hỏi liên quan ngày xuất bản trong test set.
3. **Chuỗi 3 (repair):** `build_clean_dataframe` chạy lại trực tiếp trên `data/raw/crossref_records.json` (nguồn không bị corruption chạm tới) → `data/quality/repaired.json` và `freshness_report_repaired.json` trở lại PASSED/FRESH giống hệt baseline (0 duplicate, 0 stale) → cả 4 metric RAG của repaired quay về **đúng bằng** giá trị baseline.

Mức phục hồi tuyệt đối của repair (không chỉ "gần bằng") là bằng chứng mạnh cho thấy `data/raw/` thực sự đóng vai trò nguồn đáng tin cậy (single source of truth) như thiết kế, và chênh lệch nhỏ quan sát được ở lần chạy trước là do khác judge model chứ không phải do repair chưa hoàn chỉnh.

## 9. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| RAGAS chưa bật | `ragas` trong mọi file metrics là `{"skipped": "Set RUN_RAGAS=1 ..."}`, thiếu answer_relevancy/context_precision/recall/faithfulness | Set `RUN_RAGAS=1` và chạy lại, chấp nhận thời gian chạy lâu hơn |
| Thay đổi của tôi hiện chưa commit | `phase1.py`, `corruption_flow.py` và toàn bộ artifact mới đang ở working tree trên `Role5_NguyenTrungHieu`, chưa lên remote | Rà lại `.gitignore` (đảm bảo `.env` không bị add), `git add` có chọn lọc rồi commit/push trước khi nộp bài |

*Đã giải quyết:* khác judge model giữa baseline/corrupted/repaired và demo agent bị bỏ qua do rate-limit — cả hai đã được xử lý bằng cách chạy lại toàn bộ Pha 1 và Pha 2 với `LLM_PROVIDER=openai` thống nhất (xem Mục 8); `data/results/agent_demo_answers.json` hiện có đủ 3 câu trả lời thực tế.

## 10. Điều học được và hướng phát triển

### Ba điều quan trọng nhất

1. Ghép nối các module do nhiều người viết độc lập dễ gãy ở tầng "tên key trong dict" hơn là ở tầng type signature — lỗi loại này không ném exception, chỉ âm thầm ra `N/A`, nên phải đọc code của module tiêu thụ dữ liệu (`reporting.py`) thay vì chỉ tin vào docstring.
2. Một bước "optional" (demo agent) vẫn có thể phá toàn bộ script nếu không được cô lập bằng `try/except`; artifact bắt buộc nên được ghi ra trước, artifact phụ nên fail độc lập.
3. Rate limit của LLM free-tier là một ràng buộc thật của hạ tầng, không phải lỗi code; cần có kế hoạch dự phòng provider (đã chuẩn bị sẵn OpenAI key) thay vì cố retry vô hạn trên một provider đã hết quota ngày.

### Nếu có thêm thời gian

Tôi sẽ bật `RUN_RAGAS=1` để có thêm context_precision/recall làm bằng chứng phụ cho tác động của corruption lên retrieval, không chỉ dựa vào `retrieval_hit_rate` (việc đồng bộ `LLM_PROVIDER` giữa ba trạng thái đã được thực hiện xong, xem Mục 8).

## 11. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận đã có đều gắn với code, artifact hoặc log thực tế để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng (đã nêu rõ trước đây có giới hạn về provider khác nhau và demo agent bị bỏ qua, và đã cập nhật lại sau khi chạy lại pipeline để giải quyết cả hai).
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Trung Hiếu

**MSSV:** 2A202601457

**Ngày xác nhận:** 2026-08-06
