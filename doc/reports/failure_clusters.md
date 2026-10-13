# Phân tích lỗi Phase A

Nhóm: Slopper

Người phụ trách: Lê Thị Thùy Trang - 2A202602678

Nguồn: `artifacts/ragas_50q.json`; run timestamp: 2026-10-13T03:19:00.722826+00:00.
Generation mode/fallback và điều kiện chạy: Chạy live bằng pipeline RAG hoàn chỉnh (Qdrant vector database + BAAI/bge-m3 dense search + BM25Okapi tiếng Việt + CrossEncoderReranker kết hợp RRF), sinh câu trả lời bằng OpenAI gpt-4o-mini-2024-07-18 theo đúng context truy xuất được.
Models generation/evaluator: generation: gpt-4o-mini-2024-07-18; evaluator: ragas-answer-relevancy, ragas-context-precision, ragas-context-recall, ragas-faithfulness (từ metadata adapter m4_eval).

## Điểm theo distribution

| Metric | factual (20) | multi_hop (20) | adversarial (10) |
|---|---|---|---|
| faithfulness | 0.9250 | 0.4100 | 0.8333 |
| answer_relevancy | 0.8347 | 0.6339 | 0.6271 |
| context_precision | 0.8469 | 0.8763 | 0.9039 |
| context_recall | 0.8750 | 0.8042 | 0.6167 |
| avg_score | 0.8704 | 0.6811 | 0.7453 |

## Bottom 10 và nguyên nhân

Bảng dưới đây liệt kê chính xác 10 câu hỏi có điểm trung bình RAGAS thấp nhất trích xuất từ Task 3:

| Rank | ID | Distribution | Câu hỏi | Avg Score | Worst Metric | Diagnosis | Suggested Fix |
|---|---|---|---|---|---|---|---|
| 1 | 27 | multi_hop | Nhân viên có thâm niên 7 năm theo v2024 được nghỉ bao nhiêu ngày phép? Nếu bị trừ thêm 4 ngày ốm không có giấy y tế thì còn lại bao nhiêu? | 0.2500 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 2 | 39 | multi_hop | So sánh yêu cầu mật khẩu giữa policy v1.0 và v2.0 về độ dài tối thiểu, thời hạn đổi và MFA. | 0.2500 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 3 | 50 | adversarial | Nhân viên Manager có thể dùng VPN cá nhân (như NordVPN) khi WFH để tăng bảo mật thêm không? | 0.3333 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 4 | 5 | factual | Muốn mua thiết bị trị giá 55 triệu cần ai phê duyệt? | 0.3434 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 5 | 22 | multi_hop | Nếu cần mua một chiếc laptop 30 triệu cho nhân viên mới, ai phê duyệt và cần gì từ phòng CNTT? | 0.3556 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 6 | 33 | multi_hop | Nhân viên Manager có thâm niên 12 năm: tổng phụ cấp hàng tháng và số ngày phép năm theo v2024 là bao nhiêu? | 0.3750 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 7 | 44 | adversarial | Bao lâu phải đổi mật khẩu một lần? | 0.5222 | answer_relevancy | Answer doesn't match question | Improve prompt template |
| 8 | 40 | multi_hop | Nhân viên cấp Manager có thời hạn thử việc 90 ngày, đang trong tháng thứ 3, phát hiện vi phạm bảo mật. Họ nên và không nên làm gì theo chính sách? | 0.6011 | context_precision | Too many irrelevant chunks | Add reranking or metadata filter |
| 9 | 31 | multi_hop | Nhân viên đi công tác trong nước, ở khách sạn 2 đêm với giá 1.500.000 VNĐ/đêm. Công ty thanh toán tối đa bao nhiêu cho tiền khách sạn? | 0.6214 | faithfulness | LLM hallucinating | Tighten system prompt, lower temperature |
| 10 | 8 | factual | Nhân viên được nghỉ bao nhiêu ngày khi cha hoặc mẹ mất? | 0.6474 | context_precision | Too many irrelevant chunks | Add reranking or metadata filter |

### Đối chiếu bằng chứng và phân tích nhóm lỗi tiêu biểu:
1. **Lỗi Hallucination trong câu hỏi Multi-hop (Câu 27, 39, 22)**:
   * Ở câu 27, câu hỏi đòi hỏi kết hợp giữa hai văn bản: `nghi_phep_nam_v2024.md` (tính thâm niên 7 năm = 15 + 1 = 16 ngày phép) và `nghi_om.md` (nghỉ ốm không giấy tờ y tế bị trừ vào phép năm). Mặc dù các đoạn context được retrieve khá đầy đủ, mô hình LLM khi tính toán số học trừ 4 ngày vẫn có xu hướng tự diễn giải thêm các điều kiện ngoài lề, dẫn đến chỉ số `faithfulness` bị chấm 0 điểm do câu trả lời chứa nhận định không được context hỗ trợ trực tiếp.
2. **Lỗi xung đột phiên bản và bẫy phủ định (Câu 39, 50)**:
   * Câu 39 yêu cầu so sánh song song giữa `mat_khau_v1.md` và `mat_khau_v2.md`. Retrieval lấy được cả hai đoạn nhưng do context bị phân mảnh, LLM bị nhầm lẫn giữa mốc 90 ngày của v1 và 180 ngày/MFA của v2.
   * Câu 50 là câu hỏi gài bẫy: chính sách quy định bắt buộc dùng WireGuard VPN của công ty và cấm VPN ngoài, nhưng LLM dễ bị thiên lệch nhầm rằng "càng dùng VPN thì càng bảo mật" nếu không đọc kỹ chữ cấm trong context.
3. **Lỗi nhiễu context (Context Precision ở câu 8, 40)**:
   * Câu 8 tìm kiếm về tang lễ, mặc dù đã lấy đúng file `nghi_phep_dac_biet.md`, nhưng do truy vấn chứa các từ "nhân viên", "nghỉ", bộ tìm kiếm vẫn kéo thêm các chunk từ `nghi_om.md` khiến tỷ lệ chunk hữu ích trên tổng số chunk bị giảm sút.

## Matrix và nhóm yếu nhất

Dưới đây là ma trận phân bố số câu hỏi có điểm thấp nhất rơi vào từng metric ứng với từng nhóm distribution (tổng mỗi cột là 20 factual, 20 multi_hop, 10 adversarial):

| Worst Metric | factual (20) | multi_hop (20) | adversarial (10) | Tổng câu |
|---|---|---|---|---|
| faithfulness | 1 | 16 | 2 | 19 |
| context_recall | 3 | 2 | 6 | 11 |
| context_precision | 7 | 1 | 0 | 8 |
| answer_relevancy | 9 | 1 | 2 | 12 |

Nhóm yếu theo mean thấp nhất: multi_hop; mean: 0.6811.
Worst metric xuất hiện nhiều nhất: faithfulness; số câu: 19.

### Phân tích nguyên nhân và đề xuất cải tiến:
* **Tại sao nhóm multi_hop yếu nhất (0.6811)?**
  Nhóm câu hỏi multi-hop đòi hỏi phải gom thông tin từ ít nhất 2 đến 3 tài liệu khác nhau (ví dụ vừa xem bảng lương, vừa xem quy chế thử việc, vừa xem chính sách công tác phí). Điểm nghẽn lớn nhất là `faithfulness` cực thấp (trung bình chỉ 0.4100, có tới 16/20 câu có metric thấp nhất là faithfulness). Khi phải tổng hợp nhiều ngữ cảnh, mô hình sinh dễ bị "bịa" (hallucinate) các suy luận logic hoặc tính toán số học mà không trích dẫn trực tiếp từ ngữ cảnh.
* **Đề xuất sửa đổi cụ thể**:
  1. Thắt chặt system prompt ở tầng sinh: Yêu cầu LLM thực hiện kỹ thuật Chain-of-Thought từng bước ("Trích dẫn đoạn văn A $\rightarrow$ Trích dẫn đoạn văn B $\rightarrow$ Thực hiện phép tính").
  2. Bổ sung re-ranking đa tài liệu: Sử dụng query expansion để phân rã câu hỏi multi-hop thành các câu hỏi con (sub-queries), sau đó mới tổng hợp chunk.
  3. Cách chạy lại kiểm chứng: Thực hiện chạy lại `setup_answers.py --live` với prompt mẫu mới và đo lại bằng `run_experiments.py --phase a --live` để so sánh faithfulness của nhóm multi_hop.

## Bẫy adversarial và giới hạn

### Bẫy phiên bản và phủ định:
* Nhóm Adversarial có điểm trung bình là 0.7453, thấp hơn đáng kể so với nhóm Factual (0.8704). Điều này chứng minh bộ dữ liệu thử nghiệm phản ánh đúng tính chất thách thức của các câu hỏi gài bẫy:
  - Bẫy phiên bản cũ/mới (Câu 41, 42, 44): Trong tài liệu công ty tồn tại cả bản quy định cũ (v2023 có 12 ngày phép, mật khẩu v1 đổi 90 ngày) và bản mới (v2024 có 15 ngày phép, mật khẩu v2 đổi 180 ngày). Nếu retrieval không phân biệt được tag phiên bản, hệ thống sẽ trả về chính sách đã hết hiệu lực. Ở câu 44, RAG trả lời lan man cả hai phiên bản dẫn đến `answer_relevancy` chỉ đạt 0.5222.
  - Bẫy phủ định (Câu 46, 50): Câu 50 bẫy về việc dùng VPN cá nhân. Mặc dù câu hỏi hỏi rất lịch sự nhằm đánh lừa AI đồng ý, context của công ty nêu rõ bắt buộc dùng WireGuard.
* **Giới hạn thực nghiệm**:
  Bộ dữ liệu gồm 50 câu hỏi (trong đó 10 câu adversarial) là tập mẫu chuẩn hóa kiểm thử ban đầu, chưa bao quát hết mọi tình huống prompt injection tinh vi. Việc đánh giá dựa trên RAGAS với mô hình evaluator gpt-4o-mini đôi khi có thể gặp sai số định lượng nhẹ ở các câu trả lời ngắn, tuy nhiên xu hướng phân bố điểm giữa các nhóm là hoàn toàn nhất quán và có ý nghĩa thực tiễn cao.
