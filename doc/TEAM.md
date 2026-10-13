# Nhóm thực hiện K4 Track 3A

Tên nhóm: Slopper

Repo chung: https://github.com/Sukemcute/K4-Track-3A-Day24-LeThiThuyTrang-2A202602678-Eval-Guard

Trưởng nhóm/người nộp: Lê Thị Thùy Trang - 2A202602678

Ngày lab/deadline áp dụng: 2026-10-12 23:59 — Asia/Ho_Chi_Minh (UTC+07:00)

Commit dùng để chấm: b9f8d5b53bc4f94899aa30fdc52c30be0e96eb6d

Mỗi nhóm nộp một repo. Điền đủ thành viên và một mục INDIVIDUAL cho từng người.

## Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò / công việc thật | Bằng chứng |
|---|---|---|---|---|
| 1 | Lê Thị Thùy Trang | 2A202602678 | Thiết lập toàn bộ pipeline RAG, code Phase A (RAGAS), Phase B (Judge LLM), Phase C (Guardrails) và tổng hợp báo cáo | Git commits, artifacts/*.json, reports trong doc/reports/ |

Người tích hợp/chạy batch/nộp link: Lê Thị Thùy Trang, thực hiện thiết lập môi trường Docker Qdrant, chạy các script thực nghiệm `--live` và hoàn thiện nộp repo.

## Môi trường và chuẩn bị trước lớp

OS/Python/compiler: Windows 11 64-bit, Python 3.12.2, Microsoft Visual C++ Build Tools.
Virtualenv/dependencies/imports: Tạo venv Python 3.12, cài đặt dependencies từ requirements/requirements.txt và constraints-core.txt, đã xác nhận import thành công các module RAG và Presidio.
Models/Qdrant/50 answers đã chuẩn bị: Chạy Qdrant container qdrant/qdrant:v1.9.7 trên port 6333 qua Docker Compose; tải model embedding BAAI/bge-m3; cấu hình OpenAI API key gọi gpt-4o-mini; chạy setup_answers.py tạo đủ 50 câu trả lời RAG có căn cứ contexts lưu tại artifacts/answers_50q.json.
Do môi trường Windows trên Python 3.12 gặp hạn chế build thư viện Annoy của NeMo Guardrails đầy đủ, nhóm đã kích hoạt kiến trúc fallback nội bộ regex & flow matching tương đương chuẩn Colang 1.0 trong phase_c_guard.py để đảm bảo 100% logic chặn adversarial và cho qua clean controls.

## INDIVIDUAL

### LeThiThuyTrang-2A202602678

- Phần được giao và phần thực tế đã làm: Toàn bộ bài lab bao gồm việc mang các module m1-m5 từ Day 18 sang; hoàn thiện các hàm TODO trong phase_a_ragas.py (nhóm distribution, chạy RAGAS, lọc bottom 10, ma trận lỗi), phase_b_judge.py (pairwise judge, swap-and-average, Cohen kappa, bias report), phase_c_guard.py (quét PII CCCD/SĐT/Email bằng Presidio, input rail, adversarial suite, output rail, đo latency P95); chạy các script thực nghiệm sinh artifacts thật và viết 3 báo cáo kỹ thuật.
- Bằng chứng: Lịch sử commit trên repo Git, 4 file artifact JSON (answers_50q.json, ragas_50q.json, judge_results.json, guard_results.json) và các báo cáo trong doc/reports/.
- Cách kiểm tra: Chạy kiểm thử offline bằng lệnh `python -m pytest tests/ -q` đạt 86/86 tests pass; chạy thực nghiệm live bằng `scripts/run_experiments.py` cho cả 3 phase A, B, C; kiểm tra bài nộp bằng `python scripts/check_lab.py --with-tests`.
- Điều đã học: Hiểu sâu về phương pháp đánh giá hệ thống RAG trong thực tế sản xuất bằng 4 metrics RAGAS (faithfulness, relevancy, precision, recall); cách phát hiện và giảm thiểu position bias / verbosity bias của LLM-as-a-Judge qua kỹ thuật swap-and-average; đo lường độ tin cậy giữa LLM và con người bằng Cohen's Kappa; cách thiết lập kiến trúc đa tầng Guardrails (Presidio PII regex/NER kết hợp NeMo input/output rails) và đo đạc độ trễ P95 tuần tự đáp ứng budget production.
- Giới hạn/cách xử lý: Ban đầu điểm Factual bị thấp hơn Adversarial do một số câu truy vấn chính sách đặc biệt bị Reranker đè điểm, nhóm đã phát hiện và tinh chỉnh lại thuật toán overlap token trong CrossEncoderReranker kết hợp RRF của HybridSearch và mở rộng top_k=5, giúp điểm Factual tăng vọt lên 0.8704 và đạt trọn vẹn bonus Phase A.
- Nguồn/AI hỗ trợ nếu có: Sử dụng tài liệu bài giảng VinUni Track 3A, tài liệu chính thức RAGAS, Presidio, NeMo Guardrails và trợ lý AI hỗ trợ rà soát kiểm thử code.

## Cập nhật sau khi nộp

Bản nộp đầu tiên đúng hạn trước 23:59 ngày lab, không có cập nhật chỉnh sửa sau deadline.
