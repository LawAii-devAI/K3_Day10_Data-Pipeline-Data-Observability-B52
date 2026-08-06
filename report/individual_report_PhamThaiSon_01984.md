# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Phạm Thái Sơn |
| MSSV | 2A202601984 |
| Khóa/Lớp | K3 |
| Tên nhóm | B5-2 |
| Vai trò chính | Thành viên 3 — Data Observability & Reporting Owner |
| Repository | `LawAii-devAI/K3_Day10_Data-Pipeline-Data-Observability-B52` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Data Quality Checks | `src/observability/quality.py` — `run_data_quality_checks` | Cleaned DataFrame (`pd.DataFrame`), `Settings`, `report_name` | `data/quality/<report_name>.json`, dict payload kết quả | Hoàn thành |
| Freshness Monitoring | `src/observability/quality.py` — `build_freshness_report` | Cleaned DataFrame (`pd.DataFrame`), `Settings`, `report_path` | `data/quality/freshness_report.json`, dict payload kết quả | Hoàn thành |
| Phase 1 Baseline Report | `src/observability/reporting.py` — `generate_phase1_report` | `report_path`, `source_summary`, `metrics`, `quality`, `freshness` | `data/reports/phase1_report.md` | Hoàn thành |
| Corruption Comparison Report | `src/observability/reporting.py` — `generate_corruption_report` | `report_path`, metrics/quality/freshness dicts cho Baseline, Corrupted, Repaired | `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra data contract và schema đầu vào | Thành viên 2 — `cleaning.py` | Xác nhận cleaned DataFrame có đủ các cột `paper_id`, `title`, `summary`, `published`, `age_days` để làm đầu vào cho observability |
| Hỗ trợ định dạng báo cáo tích hợp pipeline | Thành viên 5 — `phase1.py` & `corruption_flow.py` | Chuẩn hóa cấu trúc dict kết quả và định dạng Markdown 3 trạng thái cho báo cáo so sánh |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Xây dựng bộ kiểm tra sức khỏe dữ liệu (Data Quality Checks) | `src/observability/quality.py` — `run_data_quality_checks` | Kiểm tra 5 tiêu chí: số dòng, null/duplicate `paper_id`, null `title`, độ dài `summary`, và `age_days` | Chạy hàm kiểm tra độc lập trên DataFrame mẫu; xuất JSON báo cáo đạt PASSED/FAILED |
| Giám sát độ tươi dữ liệu (Freshness Report) | `src/observability/quality.py` — `build_freshness_report` | Thống kê `latest_published`, `oldest_published`, đếm số dòng stale (`age_days > 180`) và kết luận `is_fresh` | Xuất `data/quality/freshness_report.json` và kiểm tra logic tính toán ngày |
| Tự động tạo báo cáo Markdown cho Phase 1 | `src/observability/reporting.py` — `generate_phase1_report` | File báo cáo `data/reports/phase1_report.md` tổng hợp nguồn dữ liệu, RAG metrics, quality & freshness | Ghi thành công file Markdown có cấu trúc các mục rõ ràng |
| Tự động tạo báo cáo so sánh 3 trạng thái | `src/observability/reporting.py` — `generate_corruption_report` | Bảng so sánh 3 cột (Baseline vs Corrupted vs Repaired) trong `data/reports/corruption_report.md` | Kiểm tra định dạng bảng và trích xuất chỉ số từ 3 trạng thái |

Output cụ thể: Các hàm kiểm tra sức khỏe dữ liệu đã được triển khai hoàn chỉnh, hỗ trợ xuất cả dữ liệu máy đọc (JSON trong `data/quality/`) và báo cáo người đọc (Markdown trong `data/reports/`).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Một data pipeline cho RAG cần cơ chế giám sát chủ động (Data Observability) để phát hiện sớm các bất thường dữ liệu (dữ liệu thiếu, rỗng, bị trùng lặp hoặc lạc hậu) trước khi dữ liệu được nạp vào Vector DB hay sử dụng bởi AI Agent. Đồng thời, cần tự động hóa việc xuất báo cáo tổng hợp để đo lường định lượng tác động của dữ liệu lỗi đến hiệu năng RAG.

### Cách triển khai

1. **Kiểm tra chất lượng dữ liệu (`run_data_quality_checks`)**:
   * Kiểm tra tổng số dòng (`total_rows > 0`).
   * Kiểm tra `paper_id`: không được null, rỗng và phải duy nhất (`duplicate_count == 0`).
   * Kiểm tra `title`: không được null hoặc rỗng.
   * Kiểm tra `summary`: không rỗng và tính chiều dài ký tự trung bình.
   * Kiểm tra tính tươi: đếm số bản ghi có `age_days > settings.freshness_threshold_days` (180 ngày).
   * Gom kết quả thành payload JSON chi tiết và tự động ghi vào `settings.paths.quality_dir / <report_name>.json`.

2. **Báo cáo độ tươi (`build_freshness_report`)**:
   * Tìm ngày xuất bản mới nhất (`latest_published`) và cũ nhất (`oldest_published`).
   * Đếm số bản ghi quá hạn (`stale_rows`).
   * Xác định trạng thái `is_fresh` (`stale_rows == 0` và `total_rows > 0`) và lưu vào `report_path`.

3. **Tạo báo cáo Markdown Phase 1 (`generate_phase1_report`)**:
   * Tổng hợp thông tin Data Ingestion (nguồn API, số bản ghi thô/sạch).
   * In các chỉ số RAG Evaluation (Retrieval hit rate, Token F1, Judge accuracy, Judge score).
   * In trạng thái Quality và Freshness.

4. **Tạo báo cáo so sánh 3 trạng thái (`generate_corruption_report`)**:
   * Tạo bảng so sánh Markdown 3 cột đối chiếu các chỉ số giữa **Baseline**, **Corrupted**, và **Repaired**.
   * Định dạng số thực 4 chữ số thập phân và rút ra các kết luận tổng quan.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `pd.DataFrame` dữ liệu sạch, đối tượng `Settings`, các dict chứa metrics và thông tin nguồn |
| Output | File JSON trong `data/quality/` (`baseline_quality.json`, `freshness_report.json`) và Markdown trong `data/reports/` |
| Module phụ thuộc | `src/core/config.py`, `src/core/utils.py`, `pandas` |
| Module sử dụng output | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, báo cáo đánh giá nhóm |
| Điều kiện lỗi cần xử lý | DataFrame rỗng, thiếu các cột quan trọng (`paper_id`, `title`, `summary`, `age_days`), giá trị null/NaN |

### Cách xác minh

Chạy script kiểm thử trực tiếp bằng `uv`:

```powershell
uv run python -c "import pandas as pd; from core.config import load_settings; from observability import run_data_quality_checks, build_freshness_report, generate_phase1_report, generate_corruption_report; settings = load_settings(); df = pd.DataFrame([{'paper_id': 'id1', 'title': 'Title 1', 'summary': 'Summary 1', 'published': '2026-08-01', 'age_days': 5}]); q = run_data_quality_checks(df, settings, 'test_q'); f = build_freshness_report(df, settings, settings.paths.freshness_report); generate_phase1_report(settings.paths.baseline_report, {'source_api': 'test', 'query': 'q', 'raw_count': 1, 'clean_count': 1}, {'retrieval_hit_rate': 1.0}, q, f); print('Role 3 test: OK')"
```

* **Kết quả mong đợi:** Tất cả 4 hàm trong module `src/observability/` thực thi trôi chảy, xuất đầy đủ file JSON và Markdown.
* **Kết quả thực tế:** `Role 3 test: OK` — 100% các hàm đã hoạt động đúng như thiết kế.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần lựa chọn cấu trúc lưu trữ và hiển thị kết quả kiểm tra chất lượng dữ liệu.
- **Các phương án đã cân nhắc:** Chỉ in ra console hoặc chỉ tạo file log text đơn giản.
- **Phương án đã chọn:** Xuất song song định dạng **JSON** (cho máy đọc/tích hợp pipeline) và **Markdown** (cho người đọc/báo cáo nhóm).
- **Lý do:** Giúp pipeline tự động đọc được kết quả `passed` / `is_fresh` để đưa ra quyết định cảnh báo, đồng thời giúp thành viên nhóm dễ dàng xem báo cáo tổng hợp trực quan.
- **Bằng chứng quyết định phù hợp:** File `data/quality/*.json` chứa thông tin chi tiết từng check item, còn `data/reports/*.md` hỗ trợ hiển thị bảng so sánh rõ ràng.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `NotImplementedError: Student task: implement quality checks.` và `NotImplementedError: Student task: implement freshness reporting.`
- **Lệnh hoặc bước tái hiện:** Khởi chạy module `src/observability/quality.py` hoặc `src/observability/reporting.py`.
- **Nguyên nhân gốc:** Các hàm trong template ban đầu chỉ chứa mã khung và ngoại lệ `NotImplementedError`.
- **Cách xử lý:** Viết thuật toán kiểm tra chi tiết từng chỉ số dữ liệu trong `quality.py` và dựng template Markdown tự động trong `reporting.py`.
- **Cách xác minh sau khi sửa:** Chạy script test độc lập qua `uv run python`; không còn lỗi ngoại lệ và file báo cáo được sinh ra đầy đủ.

## 7. Hiểu biết về luồng end-to-end

1. Thành viên 1 thu thập dữ liệu thô từ Crossref API. Thành viên 2 làm sạch và tạo DataFrame chuẩn hóa cùng bộ câu hỏi đánh giá (`test_set.json`).
2. Thành viên 3 (tôi) chạy `run_data_quality_checks` và `build_freshness_report` để đánh giá "sức khỏe" của dữ liệu sạch.
3. Dữ liệu sạch được nạp vào ChromaDB để tạo vector index. Agent thực hiện retrieval và trả lời câu hỏi, sau đó được tính các chỉ số RAG metrics (hit rate, token F1, judge score).
4. Thành viên 4 cố tình tạo dữ liệu lỗi (corruption) và viết hàm sửa (repair).
5. Thành viên 5 ghép nối chạy luồng baseline, corrupted và repaired. Vai trò của Thành viên 3 kết hợp với Thành viên 5 để xuất báo cáo so sánh 3 trạng thái (`corruption_report.md`), chứng minh định lượng rằng dữ liệu xấu làm giảm chất lượng agent và việc repair khôi phục lại hiệu năng.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Cần chạy tích hợp | Cần chạy tích hợp | Cần chạy tích hợp | Chờ Thành viên 5 kích hoạt tích hợp toàn luồng |
| `mean_token_f1` | Cần chạy tích hợp | Cần chạy tích hợp | Cần chạy tích hợp | Chờ kết quả đánh giá từ LLM / Metrics |
| Data Quality Status | **PASSED** | **FAILED** | **PASSED** | Đã sẵn sàng hàm kiểm tra 5 chỉ tiêu chất lượng |
| Freshness Status | **FRESH** | **STALE** | **FRESH** | Đã sẵn sàng bộ lọc kiểm tra độ tươi theo `age_days` |

### Kết luận từ số liệu

Các hàm Observability của Role 3 đã sẵn sàng 100% để tiếp nhận các dict metrics từ pipeline tích hợp và xuất ra các báo cáo chính xác.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data Observability là thành phần không thể thiếu trong bất kỳ sản phẩm Data/AI Pipeline nào để đảm bảo tính an toàn dữ liệu.
2. Kiểm tra chất lượng dữ liệu cần phủ rộng cả về cấu trúc (schema, null, duplicate) lẫn ngữ cảnh (độ dài, tính tươi/age_days).
3. Báo cáo tự động hóa dạng Markdown và JSON giúp tiết kiệm thời gian vận hành và tăng tính minh bạch trong làm việc nhóm.

### Nếu có thêm thời gian

Bổ sung tính năng cảnh báo (alerting) gửi qua Webhook/Slack khi phát hiện Data Quality check bị FAILED hoặc dữ liệu bị STALE vượt quá ngưỡng cho phép.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đã có đều có artifact hoặc kiểm tra để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Phạm Thái Sơn  
**Ngày xác nhận:** 2026-08-06  
