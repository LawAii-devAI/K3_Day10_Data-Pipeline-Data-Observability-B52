# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | [Điền họ và tên] |
| MSSV | [Điền MSSV] |
| Khóa/Lớp | K3 |
| Tên nhóm | [Điền tên hoặc mã nhóm] |
| Vai trò chính | Thành viên 2 — Cleaning & test-set owner |
| Repository | `D:\K3_Day10_Data-Pipeline-Data-Observability-B52` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cleaning và data modeling | `src/ingestion/cleaning.py` — `build_clean_dataframe` | `data/raw/crossref_records.json`, danh sách `PaperRecord`, `run_date` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Hoàn thành |
| Evaluation set | `src/evaluation/testset.py` — `build_test_set` | Cleaned DataFrame | `data/eval/test_set.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra raw artifact và data contract | Thành viên 1 — `crossref.py` | Xác nhận 24 records, 24 `paper_id` duy nhất và các trường chính không bị thiếu |
| Xác minh đầu vào cho pipeline tích hợp | Thành viên 5 — `phase1.py` | Bàn giao cleaned dataset và evaluation set; baseline pipeline hiện chưa chạy vì `phase1.py` còn TODO |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa raw records, loại record không hợp lệ và duplicate | `src/ingestion/cleaning.py` | 24 cleaned records; `paper_id` duy nhất; tạo các cột phụ và `text_for_embedding` | Chạy hàm cleaning trên `data/raw/crossref_records.json`; `py_compile` thành công |
| Tạo evaluation set ổn định | `src/evaluation/testset.py` | 24 samples trong `data/eval/test_set.json`, gồm summary/authors/date | Kiểm tra JSON, `ground_truth_doc_ids` và phân bố `question_type` |

Output cụ thể: cleaned dataset có 24 records và evaluation set có 24 câu hỏi. Evaluation set dùng cùng document ID (`paper_id`) làm `ground_truth_doc_ids`, để các trạng thái baseline, corrupted và repaired có thể được so sánh trên cùng một bộ câu hỏi.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Raw data từ Crossref có thể chứa text thừa, danh sách tác giả/chủ đề chưa phù hợp để lưu vào DataFrame, ngày tháng không đồng nhất và record trùng. Pipeline cần một schema ổn định trước khi tạo embedding và evaluation.

### Cách triển khai

`build_clean_dataframe` chuẩn hóa text bằng cách loại khoảng trắng thừa, chuyển DOI về lowercase, chuẩn hóa danh sách authors/categories và ngày thành ISO date. Record thiếu `paper_id` hoặc `title` và record trùng DOI bị loại. Hàm tạo `authors_joined`, `categories_joined`, `summary_chars`, `age_days` và ghép các trường quan trọng vào `text_for_embedding`. DataFrame được sắp xếp ổn định theo ngày xuất bản và `paper_id`.

`build_test_set` chọn tối đa 8 document theo thứ tự `paper_id` để tạo evaluation set deterministic. Với mỗi document, hàm tạo câu hỏi summary, authors và date nếu dữ liệu tương ứng tồn tại; category question chỉ tạo khi source có category. Ground truth document ID luôn là `paper_id` của document gốc.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `PaperRecord` từ `data/raw/crossref_records.json`; `run_date` để tính freshness |
| Output | DataFrame có 16 cột cleaned; CSV/JSON trong `data/clean/`; test set JSON trong `data/eval/` |
| Module phụ thuộc | `src/ingestion/crossref.py`, `src/core/utils.py`, pandas |
| Module sử dụng output | `retrieval/index.py`, `evaluation/metrics.py`, observability và pipeline integration |
| Điều kiện lỗi cần xử lý | Raw list rỗng, thiếu cột bắt buộc, thiếu `paper_id`/`title`, duplicate ID, không tạo được evaluation sample |

### Cách xác minh

```powershell
python -m py_compile src/ingestion/cleaning.py src/evaluation/testset.py
```

Ngoài ra, đã chạy kiểm tra trên raw artifact với kết quả:

- **Kết quả mong đợi:** 24 cleaned records, ID không trùng, `text_for_embedding` không rỗng và evaluation set hợp lệ.
- **Kết quả thực tế:** 24 cleaned records và 24 evaluation samples; kiểm tra module độc lập thành công.
- **Artifact/log:** `data/clean/papers_clean.csv`, `data/clean/papers_clean.json`, `data/eval/test_set.json`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần tạo evaluation set có thể tái lập và dùng lại cho baseline, corrupted và repaired.
- **Các phương án đã cân nhắc:** Chọn ngẫu nhiên document ở mỗi lần chạy hoặc chọn document theo thứ tự ổn định.
- **Phương án đã chọn:** Sắp xếp theo `paper_id` và chọn tối đa 8 document; tạo ID sample từ `paper_id` và question type.
- **Lý do:** Cách này không phụ thuộc random seed, giúp ba trạng thái dùng đúng cùng test set và dễ truy vết từ câu hỏi về document gốc.
- **Bằng chứng quyết định phù hợp:** `data/eval/test_set.json` có ID ổn định và mọi sample đều có `ground_truth_doc_ids`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement cleaning pipeline.` và `NotImplementedError: Student task: implement test set builder.`
- **Lệnh hoặc bước tái hiện:** Gọi các hàm starter trên raw records.
- **Nguyên nhân gốc:** Hai hàm trong starter chưa được implement.
- **Cách xử lý:** Implement cleaning rules, schema phụ trợ, deterministic test-set generation và ghi JSON output.
- **Cách xác minh sau khi sửa:** Chạy `py_compile` và kiểm tra trên 24 records; kết quả `clean/testset: OK`.
- **Điều học được:** Cần cố định data contract và document identity trước khi các module embedding, evaluation và corruption dùng chung dữ liệu.

Blocker tích hợp còn lại: `src/pipelines/phase1.py` vẫn chưa được thành viên 5 implement, vì vậy chưa có baseline metrics để điền vào phần phân tích kết quả.

## 7. Hiểu biết về luồng end-to-end

1. Thành viên 1 lấy metadata từ Crossref và lưu raw response/raw records. Cleaning chuyển records thành schema sạch, sau đó `retrieval/index.py` dùng `text_for_embedding` để tạo embedding và nạp vào ChromaDB.
2. Evaluation set chứa câu hỏi, ground truth và `ground_truth_doc_ids`. Khi agent trả lời, pipeline kiểm tra document ID được retrieval có trùng ground truth hay không, đồng thời tính token F1 và judge metrics.
3. Quality checks kiểm tra tính đầy đủ, hợp lệ, duplicate và độ dài summary. Freshness monitoring tập trung vào ngày xuất bản, tuổi dữ liệu và ngưỡng freshness.
4. Cùng một test set giúp thay đổi metrics phản ánh tác động của corruption/repair thay vì tác động do câu hỏi hoặc ground truth bị thay đổi.
5. Repair thành công khi cleaned/repaired artifact được tạo lại từ nguồn raw đáng tin cậy, quality/freshness signals được cải thiện và các metrics retrieval/answer được phục hồi tương ứng.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa chạy | Chưa chạy | Chưa chạy | Chờ thành viên 5 chạy pipeline |
| `mean_token_f1` | Chưa chạy | Chưa chạy | Chưa chạy | Chưa có metrics artifact |
| `judge_accuracy` | Chưa chạy | Chưa chạy | Chưa chạy | Chưa có LLM evaluation |
| `mean_judge_score` | Chưa chạy | Chưa chạy | Chưa chạy | Chưa có LLM evaluation |
| Quality checks | Chưa chạy | Chưa chạy | Chưa chạy | Chờ thành viên 3 tích hợp observability |
| Freshness status | Chưa chạy | Chưa chạy | Chưa chạy | `age_days` đã có trong cleaned dataset |

### Kết luận từ số liệu

Chưa thể kết luận định lượng về tác động của corruption hoặc repair vì `phase1.py` và `corruption_flow.py` chưa chạy tạo metrics. Artifact hiện có mới chứng minh được đầu vào cleaning và evaluation set đã hợp lệ.

1. Chuỗi cần kiểm chứng: **data corruption** → quality/freshness signal thay đổi → `retrieval_hit_rate`/answer metrics thay đổi.
2. Chuỗi cần kiểm chứng: **repair từ raw** → cleaned artifact và quality signal phục hồi → metrics agent phục hồi.

Corruption ảnh hưởng rõ nhất và kết quả khác kỳ vọng: chưa đủ dữ liệu để đánh giá; cần chờ các artifact corrupted/repaired và metrics tương ứng.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data contract và document ID phải ổn định trước khi dữ liệu được đưa vào embedding/index.
2. Evaluation set cần deterministic và phải giữ nguyên giữa các trạng thái để so sánh có ý nghĩa.
3. Chất lượng `summary`, metadata và `text_for_embedding` ảnh hưởng trực tiếp đến khả năng retrieval và câu trả lời của agent.

### Nếu có thêm thời gian

Bổ sung test tự động cho các trường hợp thiếu title, duplicate DOI, ngày không hợp lệ, summary rỗng và title có ký tự đặc biệt. Có thể đo thêm tỷ lệ record bị loại và số lượng field được chuẩn hóa để quality report giải thích rõ hơn thay đổi của dataset.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đã có đều có artifact hoặc kiểm tra để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** [Điền họ và tên]
**Ngày xác nhận:** 2026-08-06
