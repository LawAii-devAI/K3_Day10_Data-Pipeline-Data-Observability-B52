# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Trọng Đức |
| MSSV | 01673 |
| Khóa/Lớp | K3 |
| Tên nhóm | B52 |
| Vai trò chính | Thành viên 4 — Corruption & repair owner |
| Repository | `LawAii-devAI/K3_Day10_Data-Pipeline-Data-Observability-B52` |
| Branch | `role4-NguyenTrongDuc` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Cấu hình corruption | `src/ingestion/corruption.py` — `CorruptionConfig` | Các tỷ lệ corruption, seed và tham số | Cấu hình deterministic để tái hiện cùng lỗi dữ liệu | Hoàn thành |
| Tạo dữ liệu hỏng | `corrupt_clean_dataframe` | Cleaned DataFrame và đường dẫn log | Corrupted DataFrame và corruption log JSON | Hoàn thành ở mức module |
| Repair dữ liệu | `repair_clean_dataframe` | Corrupted DataFrame và trusted clean DataFrame | Repaired DataFrame, tùy chọn repair log | Hoàn thành ở mức module |
| Xác minh repair | `validate_repaired_dataframe` | Repaired DataFrame và trusted DataFrame | Kết quả kiểm tra schema, số dòng, ID và nội dung | Hoàn thành |
| Kiểm thử module | `tests/test_corruption.py` | Fixture clean DataFrame | 4 test case cho corruption/repair | Hoàn thành — 4 test passed |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Đồng bộ contract với cleaning | Thành viên 2 — `src/ingestion/cleaning.py` | `text_for_embedding` sau corruption giữ đúng format `Title`, `Summary`, `Authors`, `Categories`, `Published` |
| Chuẩn bị API tích hợp | Thành viên 5 — `src/pipelines/corruption_flow.py` | Export các hàm corruption, repair và validation qua `src/ingestion/__init__.py` |
| Đồng bộ code chung | Toàn nhóm | Merge `origin/main` vào branch Role 4 và điều chỉnh theo data contract mới |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Mô phỏng sáu loại lỗi dữ liệu | `corrupt_clean_dataframe` | Drop latest records, blank summary, summary noise, truncate title, stale date và duplicate rows | Kiểm tra implementation và các assertion trong `tests/test_corruption.py` |
| Bảo đảm corruption tái lập | `CorruptionConfig(seed=42)` | Cùng input và config sẽ chọn cùng record để làm hỏng | Test gọi hàm hai lần và so sánh hai DataFrame |
| Đồng bộ derived fields | `_rebuild_text_for_embedding` | Rebuild nội dung embedding sau khi title, summary hoặc published thay đổi | Đối chiếu format với `build_clean_dataframe` của Role 2 |
| Ghi audit log | `data/results/corruption_log.json` khi flow được chạy | Ghi timestamp, seed, số dòng input/output, config, scenario, count và `record_ids` | Schema log được tạo trong `corrupt_clean_dataframe`; artifact thực tế chờ Role 5 chạy flow |
| Phục hồi từ nguồn đáng tin cậy | `repair_clean_dataframe` | Tạo bản repaired từ trusted clean snapshot thay vì đoán giá trị trên dữ liệu hỏng | Validation bắt buộc trước khi trả kết quả |
| Xác minh toàn vẹn sau repair | `validate_repaired_dataframe` | Kiểm tra cột, số dòng, thứ tự ID và toàn bộ nội dung | `is_valid=True` chỉ khi tất cả điều kiện cùng đạt |

Các commit chính của phần việc là:

- `d2840c8` — `Implement data corruption and repair`.
- `266d2cb` — merge code mới nhất từ `origin/main`.
- `aaeb959` — `Align corruption with cleaning contract`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline cần tạo lỗi dữ liệu có chủ đích để chứng minh data quality và chất lượng RAG thay đổi ra sao. Corruption phải đủ rõ để quan sát được completeness, freshness, validity và uniqueness, đồng thời phải deterministic để kết quả có thể tái hiện. Sau đó dữ liệu cần được phục hồi từ nguồn đáng tin cậy và phải có bằng chứng rằng repair thực sự trả dữ liệu về trạng thái sạch.

### Các corruption scenario

| Scenario | Cách tạo | Tỷ lệ mặc định | Quality dimension/tác động kỳ vọng |
| --- | --- | ---: | --- |
| `drop_latest_records` | Parse `published`, sắp xếp giảm dần và xóa các record mới nhất; luôn giữ ít nhất một dòng | 15% | Completeness và freshness giảm; retrieval có thể mất tài liệu mới |
| `blank_summary` | Đặt `summary=""` và cập nhật `summary_chars=0` | 20% | Completeness giảm; embedding thiếu nội dung |
| `inject_summary_noise` | Nối marker `[CORRUPTED_NOISE] xqzv 000 ???` vào summary | 20% | Validity/relevance giảm; vector embedding bị nhiễu |
| `truncate_title` | Cắt title còn tối đa 18 ký tự | 20% | Metadata validity và khả năng nhận diện tài liệu giảm |
| `stale_published_date` | Trừ 730 ngày khỏi `published`, đồng thời cộng 730 vào `age_days` | 20% | Freshness giảm, record có khả năng bị đánh dấu stale |
| `duplicate_rows` | Sao chép một số dòng và thêm vào cuối DataFrame | 15% | Uniqueness giảm; index có thể trả kết quả lặp |

### Luồng xử lý của hàm corruption

```text
Clean DataFrame
    -> kiểm tra required columns
    -> deep copy để không sửa dữ liệu gốc
    -> drop latest records
    -> blank/noise summary
    -> truncate title
    -> làm cũ published và age_days
    -> rebuild text_for_embedding
    -> thêm duplicate rows
    -> ghi corruption log
    -> trả về Corrupted DataFrame
```

Các cột bắt buộc là `paper_id`, `title`, `summary`, `published` và `text_for_embedding`. Nếu thiếu cột, hàm dừng sớm với `ValueError` chỉ rõ schema không hợp lệ. Tất cả phép biến đổi được thực hiện trên deep copy, vì vậy clean baseline truyền vào không bị thay đổi.

Sau khi các trường nguồn bị sửa, `_rebuild_text_for_embedding` tạo lại chuỗi theo đúng contract của cleaning:

```text
Title: ...
Summary: ...
Authors: ...
Categories: ...
Published: ...
```

Nếu không rebuild trường này, embedding vẫn có thể sử dụng nội dung sạch cũ và corruption sẽ không tác động thật đến retrieval.

### Cách repair và validation

`repair_clean_dataframe(corrupted_df, trusted_df)` không đoán lại các giá trị đã bị thay đổi. Hàm lấy bản sao từ `trusted_df`, tức cleaned baseline đáng tin cậy hoặc dữ liệu sạch được build lại từ raw source. Cách này phục hồi được cả record đã bị xóa và nội dung gốc đã bị truncate/noise.

Trusted DataFrame không được có duplicate `paper_id`. Sau khi tạo repaired DataFrame, validation kiểm tra đồng thời:

1. Danh sách và thứ tự cột giống nhau.
2. Số lượng record giống nhau.
3. Danh sách `paper_id` theo thứ tự giống nhau.
4. Toàn bộ nội dung DataFrame giống nhau.

Nếu bất kỳ điều kiện nào sai, `is_valid` là `False`; hàm repair không coi quá trình là thành công.

## 5. Input, output và contract tích hợp

| Thành phần | Mô tả |
| --- | --- |
| Input corruption | Cleaned DataFrame từ `data/clean/papers_clean.csv` hoặc output của `build_clean_dataframe` |
| Output corruption | Corrupted DataFrame để Role 5 lưu thành CSV/JSON và rebuild index |
| Corruption audit | `data/results/corruption_log.json` |
| Input repair | Corrupted DataFrame và trusted clean DataFrame/baseline được tái tạo từ raw source |
| Output repair | Repaired DataFrame để lưu vào `data/clean/papers_clean_repaired.*` |
| Output validation | Dictionary gồm `is_valid`, `same_columns`, `same_row_count`, `same_ordered_paper_ids`, `same_content` |
| Module phụ thuộc | pandas và `core.utils.write_json` |
| Module sử dụng output | `pipelines/corruption_flow.py`, retrieval index, evaluation và observability |

Ví dụ tích hợp dự kiến:

```python
corrupted_df = corrupt_clean_dataframe(
    baseline_df,
    settings.paths.corruption_log,
)

repaired_df = repair_clean_dataframe(
    corrupted_df,
    baseline_df,
)
```

## 6. Cách xác minh

### Kiểm tra tĩnh đã thực hiện

```bash
.venv/bin/python -m compileall -q src/ingestion tests/test_corruption.py
git diff --check
```

Kết quả: kiểm tra cú pháp và whitespace diff thành công trước khi commit/push.

### Bộ test đã chuẩn bị

```bash
uv run pytest -q tests/test_corruption.py
```

Các test bao phủ:

- Corruption deterministic khi dùng cùng seed.
- Input clean DataFrame không bị mutation.
- Đủ sáu loại scenario trong audit log.
- Có duplicate, blank summary và noise trong output.
- Noise xuất hiện trong `text_for_embedding` sau rebuild.
- Repair trả dữ liệu giống trusted snapshot.
- Repair log ghi validation thành công.
- Schema thiếu `paper_id` bị từ chối.
- Các tỷ lệ bằng 0 không làm thay đổi nội dung.

Do `.venv` chính vẫn đang tải các dependency lớn như PyTorch và NVIDIA/CUDA, bộ test được chạy trong môi trường tạm chỉ cài các dependency cần thiết. Kết quả thực tế: `4 passed in 0.41s`.

Smoke test trên `data/clean/papers_clean.csv` cũng thành công: 24 dòng clean tạo thành 23 dòng corrupted; số record tác động lần lượt là drop latest 4, blank summary 4, inject noise 4, truncate title 4, stale date 4 và duplicate 3. Repair validation trả về `is_valid=True`.

## 7. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Một số lỗi như xóa latest record hoặc truncate title làm mất thông tin gốc, nên không thể sửa chính xác chỉ bằng corrupted dataset.
- **Các phương án cân nhắc:** Vá từng record dựa vào corruption log; hoặc khôi phục từ raw/clean snapshot đáng tin cậy.
- **Phương án đã chọn:** Restore toàn bộ repaired DataFrame từ trusted clean snapshot, sau đó so sánh toàn bộ dữ liệu.
- **Lý do:** Audit log cho biết record nào bị tác động nhưng không nhất thiết lưu toàn bộ giá trị gốc. Restore từ trusted source tránh đoán dữ liệu và phù hợp yêu cầu repair từ raw/baseline.
- **Bằng chứng:** `validate_repaired_dataframe` chỉ trả `is_valid=True` khi schema, số dòng, ordered IDs và content đều giống trusted source.

## 8. Một vấn đề tích hợp đã xử lý

- **Triệu chứng:** Phiên bản Role 4 ban đầu rebuild `text_for_embedding` bằng cách nối trực tiếp title, summary, authors và categories.
- **Nguyên nhân:** Khi Role 4 được làm song song, implementation cleaning của Role 2 chưa có. Sau khi merge `origin/main`, contract thực tế sử dụng các prefix `Title:`, `Summary:`, `Authors:`, `Categories:` và thêm `Published:`.
- **Cách xử lý:** Cập nhật `_rebuild_text_for_embedding` theo đúng format của `build_clean_dataframe`, cập nhật fixture/test và mở rộng exports trong `ingestion/__init__.py`.
- **Cách xác minh:** Đối chiếu trực tiếp implementation của hai module, chạy `compileall`, `git diff --check` và commit thay đổi tại `aaeb959`.
- **Điều học được:** Các derived field dùng cho embedding phải có một contract thống nhất; khác format có thể làm metric thay đổi vì nguyên nhân ngoài corruption cần đo.

## 9. Hiểu biết về luồng end-to-end

1. Crossref ingestion lấy raw response, parse thành `PaperRecord` và lưu raw snapshot.
2. Cleaning chuẩn hóa record, tính `age_days`, tạo `summary_chars` và `text_for_embedding`.
3. Baseline pipeline tạo embedding/index, chạy agent trên evaluation set cố định, tính metrics và quality/freshness signals.
4. Corruption tạo sáu dạng lỗi, ghi audit log và rebuild `text_for_embedding`; pipeline phải rebuild index corrupted.
5. Corrupted dataset được đánh giá bằng đúng evaluation set baseline để chênh lệch metric phản ánh thay đổi dữ liệu thay vì thay đổi câu hỏi.
6. Repair phục hồi từ trusted raw/clean source, rebuild repaired index và chạy lại cùng evaluation set.
7. Comparison report so sánh baseline, corrupted và repaired trên retrieval, answer quality, data quality và freshness.

## 10. Phân tích kết quả hiện tại

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | Chưa có artifact | Chưa chạy | Chưa chạy | Chờ Role 5 chạy ba trạng thái trên cùng test set |
| `mean_token_f1` | Chưa có artifact | Chưa chạy | Chưa chạy | Chưa đủ số liệu để kết luận tác động |
| `judge_accuracy` | Chưa có artifact | Chưa chạy | Chưa chạy | Phụ thuộc LLM evaluation và credentials |
| `mean_judge_score` | Chưa có artifact | Chưa chạy | Chưa chạy | Chưa đủ số liệu |
| Duplicate paper IDs | Clean artifact hiện có | Kỳ vọng tăng | Kỳ vọng về baseline | Cần xác minh bằng quality artifact |
| Missing/blank summary | Clean artifact hiện có | Kỳ vọng tăng | Kỳ vọng về baseline | Cần xác minh bằng quality artifact |
| Freshness/`age_days` | Freshness artifact baseline hiện có | Kỳ vọng xấu đi | Kỳ vọng phục hồi | Cần chạy corruption flow để có số thực tế |

### Kết luận có thể đưa ra

Code hiện đã tạo được các cơ chế gây lỗi và repair có thể kiểm tra độc lập, nhưng repo chưa có `data/results/corruption_log.json`, corrupted/repaired datasets hoặc comparison metrics. Vì vậy chưa thể tuyên bố corruption đã làm giảm agent metric hoặc repair đã phục hồi metric.

Các quan hệ cần được Role 5 xác minh bằng artifact là:

1. Blank/noisy summary, truncated title và duplicate → quality signal xấu đi → retrieval/answer metric có thể giảm.
2. Drop latest và stale publication date → freshness signal xấu đi → khả năng trả lời câu hỏi về tài liệu mới có thể giảm.
3. Restore từ trusted snapshot → schema/content/quality phục hồi → retrieval và answer metrics tiến gần baseline.

## 11. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Chưa chạy corruption flow end-to-end | Chưa có số lượng record thực tế và metrics so sánh | Sau khi `uv sync` hoàn tất, chạy `script/run_corruption_flow.py` và đối chiếu artifacts |
| Repair hiện dùng trusted clean snapshot | Cần giữ snapshot baseline đáng tin cậy | Role 5 có thể rebuild trusted DataFrame trực tiếp từ `data/raw/crossref_records.json` trước khi repair |
| Các scenario dùng tỷ lệ mặc định chung | Mức tác động có thể quá nhẹ hoặc quá mạnh với dataset khác kích thước | Chạy nhiều cấu hình và ghi seed/config vào log để so sánh |
| Một record có thể chịu nhiều corruption | Khó tách riêng causal impact của từng scenario | Thêm chế độ disjoint sampling hoặc chạy từng scenario riêng trong ablation test |
| `.venv` chính chưa sync xong | Chưa chạy test bằng toàn bộ môi trường dự án | Sau khi `uv sync` hoàn tất, chạy lại `uv run pytest -q tests/test_corruption.py`; bộ test tối thiểu hiện đã đạt 4/4 |

## 12. Điều học được và hướng phát triển

### Ba điều quan trọng nhất

1. Corruption phải được rebuild vào trường dùng thực tế cho embedding; chỉ sửa metadata bề mặt có thể không tạo tác động lên RAG.
2. Reproducibility cần seed, log tham số và record ID để kết quả có thể tái hiện và giải thích.
3. Repair đáng tin cậy phải dựa trên nguồn sạch có thể truy vết, không nên suy đoán dữ liệu đã mất từ corrupted output.

### Nếu có thêm thời gian

Tôi sẽ bổ sung ablation test chạy riêng từng corruption scenario, tạo checksum cho trusted/repaired datasets và đo recovery ratio cho từng quality signal. Việc này giúp xác định loại corruption nào thực sự ảnh hưởng nhiều nhất thay vì chỉ quan sát kết quả của sáu lỗi kết hợp.

## 13. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận đã có đều gắn với code, commit hoặc artifact để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho metric end-to-end chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo không sao chép nguyên văn báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Trọng Đức

**MSSV:** 01673

**Ngày xác nhận:** 2026-08-06
