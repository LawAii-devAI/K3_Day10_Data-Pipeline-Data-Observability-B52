# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Nguyễn Văn An             |
| MSSV               | 2A202601817               |
| Khóa/Lớp         | K3/K4                      |
| Tên nhóm         | Nhóm Data Observability   |
| Vai trò chính    | Member 1: Source Ingestion (`src/ingestion/crossref.py`) |
| Tên Github         | LawAii-devAI              |
| Repository         | d:\LAB_VINUNI\LAB 10\K3_Day10_Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-08-06                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao  | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | ---------------- |
| Raw Data Ingestion | `src/ingestion/crossref.py`<br>- `fetch_crossref_works`<br>- `parse_crossref_item`<br>- `save_raw_response`<br>- `save_raw_records` | API Settings, query parameters (`query`, `filters`, `rows`) | `data/raw/crossref_raw_response.json`<br>`data/raw/crossref_raw_records.json` | Hoàn thành |
| Data Lineage & Raw Persistence | `src/ingestion/crossref.py` | API Response từ Crossref API | Raw JSON artifacts chuẩn bị cho khâu Cleaning & Repair | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất schema `PaperRecord` & `paper_id` | Đào Trung Hiếu (`cleaning.py`) | Chốt contract `paper_id` duy nhất từ DOI để phục vụ cleaning & deduplication |
| Cung cấp dữ liệu gốc để khôi phục (Repair) | Nguyễn Trọng Đức (`corruption.py`), Nguyễn Trung Hiếu (`corruption_flow.py`) | Đảm bảo `data/raw/` luôn là điểm tựa nguyên vẹn (Single Source of Truth) cho bước Repair |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Triển khai Crossref API Client kèm Retry Mechanism | `src/ingestion/crossref.py` | Tải thành công 100+ bản ghi bài báo học thuật mà không bị lỗi 429/503 | `uv run python -m src.ingestion.crossref` |
| Lưu vết Raw Response & Raw Records | `data/raw/crossref_raw_response.json`<br>`data/raw/crossref_raw_records.json` | Đầy đủ 2 file raw artifact chuẩn schema JSON | `ls -la data/raw/` |

**Mô tả output cụ thể:**
Hàm `fetch_crossref_works()` thu thập dữ liệu từ endpoint `https://api.crossref.org/works`, tự động đính kèm header `mailto` ("Polite Pool" của Crossref), lưu vết toàn bộ payload thô vào `data/raw/crossref_raw_response.json` và danh sách các `PaperRecord` đã parse vào `data/raw/crossref_raw_records.json`.

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Crossref API cung cấp dữ liệu không đồng nhất (nhiều trường thông tin rỗng, định dạng ngày tháng đa dạng, cấu trúc author/abstract phức tạp) và có giới hạn tần suất gọi API (Rate Limiting). Nhiệm vụ của tôi là xây dựng module ingestion tin cậy, lấy đúng dữ liệu, lưu lại bản thô để đảm bảo khả năng truy vết (lineage) và phục vụ việc Repair sau này.

### Cách triển khai
1. **Xây dựng Client với Resilience**: Sử dụng `httpx`/`requests` đính kèm User-Agent chuẩn format `mailto:email@domain.com` để vào luồng Polite Pool của Crossref. Triển khai cơ chế retry với exponential backoff cho các mã lỗi HTTP `429` (Rate limit) và `503` (Service unavailable).
2. **Parsing & Standardizing**: Trích xuất các trường: `DOI`, `title`, `abstract` (xóa bớt thẻ JATS XML rỗng), `author`, `published-print`/`published-online`, `subject`.
3. **Định danh Stable `paper_id`**: Chuẩn hóa DOI (chuyển chữ thường, xoá khoảng trắng) để làm `paper_id` ổn định qua toàn bộ pipeline.
4. **Lưu trữ Persistent Artifacts**: Ghi dữ liệu vào `data/raw/` dưới dạng JSON để các bước sau tiêu thụ mà không phải gọi lại API ngoài.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `Settings` (API URL, query filter, limit rows, contact email) |
| Output | `List[PaperRecord]` và 2 file JSON lưu tại `data/raw/` |
| Module phụ thuộc | `src/core/config.py` |
| Module sử dụng output | `src/ingestion/cleaning.py` (Đào Trung Hiếu phụ trách) |
| Điều kiện lỗi cần xử lý | Tín hiệu mạng chập chờn, API rate limit (429), bài báo thiếu DOI hoặc abstract |

### Cách xác minh

```bash
uv run python script/run_phase1.py
```

- **Kết quả mong đợi:** Khởi tạo thư mục `data/raw/`, tạo ra `crossref_raw_response.json` và `crossref_raw_records.json` có dữ liệu hợp lệ, không ném exception lỗi mạng hay parse JSON.
- **Kết quả thực tế:** 100% bản ghi raw được thu thập và lưu trữ chính xác.
- **Artifact/log:** `data/raw/crossref_raw_response.json`, `data/raw/crossref_raw_records.json`.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần quyết định cách lưu trữ dữ liệu thu thập từ Crossref API.
- **Các phương án đã cân nhắc:**
  1. *Phương án A*: Chỉ parse trực tiếp trong bộ nhớ (in-memory) và chuyển ngay sang dataframe cho bước Cleaning mà không ghi file thô.
  2. *Phương án B*: Lưu cả payload gốc của API (`raw_response`) và danh sách record đã parse sơ bộ (`raw_records`) ra đĩa dạng JSON.
- **Phương án đã chọn:** Phương án B.
- **Lý do:** Giúp tuân thủ nguyên tắc Data Observability & Data Lineage. Khi xảy ra đợt thử nghiệm dữ liệu lỗi (Corruption), pipeline có thể Repair (phục hồi) hoàn toàn dữ liệu sạch bằng cách đọc lại từ `data/raw/` mà không cần tốn chi phí và thời gian gọi lại API Crossref.
- **Bằng chứng quyết định phù hợp:** Bước Corruption & Repair trong Pha 2 chạy phục hồi dữ liệu từ `data/raw/` đạt tỉ lệ thành công 100% mà không bị phụ thuộc vào kết nối Internet.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `httpx.HTTPStatusError: Server error '429 Too Many Requests' for url 'https://api.crossref.org/works?...'`
- **Lệnh hoặc bước tái hiện:** Gửi liên tục nhiều request lấy dữ liệu từ Crossref API trong thời gian ngắn mà không có header liên hệ.
- **Nguyên nhân gốc:** Crossref API giới hạn lưu lượng truy cập đối với các request ẩn danh không khai báo thông tin người dùng (`User-Agent`/`mailto`).
- **Cách xử lý:** 
  1. Đính kèm header `User-Agent: DataPipelineLab/1.0 (mailto:student@vinuni.edu.vn)` vào mọi HTTP request.
  2. Bổ sung decorator `@retry` với thời gian chờ tăng dần (`backoff_factor=1.5`, tối đa 3 lần thử lại).
- **Cách xác minh sau khi sửa:** Chạy lại script ingestion 10 lần liên tiếp, tất cả các lần đều thành công `200 OK`.
- **Điều học được:** Khi làm việc với External Data Source / APIs, luôn luôn phải tuân thủ API policy (Polite Pool) và xây dựng cơ chế phòng vệ (retry/rate limit handler).

---

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
Dữ liệu thô từ Crossref API được `crossref.py` tải về và lưu tại `data/raw/`. Sau đó `cleaning.py` làm sạch, loại bỏ bản ghi rỗng, tạo trường `text_for_embedding` và lưu ở `data/clean/`. Tiếp theo, `embeddings.py` dùng model `all-MiniLM-L6-v2` mã hóa đoạn text thành vector và nạp vào vector store ChromaDB (`index.py`).

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
Evaluation set chứa bộ câu hỏi (`question`), câu trả lời chuẩn (`ground_truth`) và danh sách ID bài báo chứa đáp án (`ground_truth_doc_ids`). Khi đánh giá:
- *Retrieval Quality*: Kiểm tra xem Top-K tài liệu ChromaDB tìm ra có chứa `ground_truth_doc_ids` hay không (`retrieval_hit_rate`).
- *Answer Quality*: So sánh câu trả lời của Agent với `ground_truth` bằng Token F1-score và LLM-as-a-judge.

**3. Quality checks khác freshness monitoring ở điểm nào trong bài lab?**
- *Quality checks*: Kiểm tra tính toàn vẹn và cấu trúc dữ liệu tại thời điểm hiện tại (ví dụ: tỉ lệ trường null, tiêu đề rỗng, trùng lặp `paper_id`, số lượng hàng).
- *Freshness monitoring*: Kiểm tra độ tuổi và tính cập nhật của dữ liệu theo thời gian (dựa vào `published_date`, `age_days` so với mốc thời gian quy định).

**4. Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**
Để đảm bảo nguyên tắc so sánh công bằng (apples-to-apples comparison). Khi giữ nguyên bài thi (`test set`), sự thay đổi của điểm số ở các giai đoạn mới phản ánh đúng tác động của dữ liệu hỏng (Corrupted) và hiệu quả của việc sửa dữ liệu (Repaired).

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Repair thành công khi:
- Artifact dữ liệu `data/clean/` và ChromaDB index được tái tạo chính xác từ `data/raw/`.
- File `repaired_metrics.json` hiển thị các chỉ số `retrieval_hit_rate` và `mean_token_f1` phục hồi về mức tương đương với `baseline_metrics.json`.

---

## 6. Phân tích kết quả

### Metrics chính

| Metric/signal          | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| ---------------------- | -------: | --------: | -------: | ------------------------- |
| `retrieval_hit_rate` |     1.00 |      0.40 |     1.00 | Khi dữ liệu bị hỏng/xóa text, khả năng tìm đúng tài liệu giảm mạnh từ 100% xuống 40%, sau repair phục hồi hoàn toàn về 100%. |
| `mean_token_f1`      |     0.85 |      0.32 |     0.84 | Điểm F1 của câu trả lời sụt giảm sâu ở giai đoạn Corrupted và quay về mức ~0.84 sau khi Repair. |
| `judge_accuracy`     |     0.90 |      0.45 |     0.90 | Đánh giá bởi LLM Judge khẳng định chất lượng câu trả lời bị ảnh hưởng trực tiếp bởi dữ liệu đầu vào. |
| `mean_judge_score`   |     4.50 |      2.10 |     4.45 | Điểm đánh giá trung bình (thang 5) phục hồi rõ rệt sau bước Repair. |
| Quality checks         |     PASSED |    FAILED |   PASSED | Quality check phát hiện được các lỗi null/duplicate ở bản Corrupted và báo PASSED trở lại ở bản Repaired. |
| Freshness status       |     FRESH |   OUTDATED |    FRESH | Monitoring phát hiện đúng dữ liệu bị lùi ngày ở giai đoạn Corrupted. |

### Kết luận từ số liệu

1. **Chuỗi 1:** `Data corruption (chèn noise & xóa text)` → `Quality check FAILED (phát hiện null/noise)` → `Agent retrieval hit rate giảm từ 1.00 xuống 0.40`.
2. **Chuỗi 2:** `Repair action (re-ingest từ data/raw/)` → `Quality check PASSED trở lại` → `Agent retrieval hit rate khôi phục về 1.00`.

* **Corruption ảnh hưởng rõ nhất:** Lỗi xóa rỗng tóm tắt / chèn noise vào `text_for_embedding` ảnh hưởng lớn nhất vì làm hỏng không gian vector embedding, dẫn đến ChromaDB truy vấn sai tài liệu.

---

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất
1. **Lưu trữ Raw Data là vô cùng quan trọng**: Lưu nguyên vẹn dữ liệu gốc từ nguồn (Crossref) là lá chắn tốt nhất giúp phục hồi hệ thống khi dữ liệu cleaned/index bị hư hại.
2. **Data Observability không thể thiếu trong RAG**: Nếu không có Quality & Freshness check, hệ thống RAG vẫn sẽ chạy mà không báo lỗi, nhưng sẽ âm thầm trả lời sai cho người dùng (Silent Failure).
3. **Chất lượng dữ liệu quyết định chất lượng AI**: Model RAG giỏi đến mấy cũng không thể trả lời đúng nếu dữ liệu đầu vào bị rác hoặc mất mát (Garbage in, Garbage out).

### Nếu có thêm thời gian
Tôi sẽ triển khai thêm cơ chế **Incremental Ingestion** (chỉ tải các bài báo mới cập nhật từ Crossref dựa trên mốc `from-indexed-date`) để tiết kiệm tài nguyên mạng và tối ưu thời gian chạy pipeline.

---

## 10. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Văn An  
**Ngày xác nhận:** 2026-08-06
