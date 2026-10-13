# Blueprint CI/CD cho RAG và guardrails

Nhóm: Slopper

Người phụ trách: Lê Thị Thùy Trang - 2A202602678

Đây là **đề xuất CI/CD**, không phải workflow đã được triển khai/chạy.
Nguồn kết quả: artifacts/ragas_50q.json, judge_results.json, guard_results.json.
Run timestamp: 2026-10-12T18:37:37.564336+00:00; guard models: local-guard-stub.
Models generation/evaluator/judge từ A/B: generation: gpt-4o-mini-2024-07-18; evaluator: ragas metrics (ragas-faithfulness, ragas-answer-relevancy, ragas-context-precision, ragas-context-recall); judge: gpt-4o-mini.

## Kiến trúc và failure action

Input → Presidio → NeMo input → RAG → NeMo output → response.
Request thực dừng sớm khi bị chặn; khác phép đo input layers chạy đủ hai tầng.

### Luồng dữ liệu và cơ chế xử lý lỗi (Data Flow & Failure Action):
1. **Tầng Input Guard (Presidio + NeMo Input)**:
   * Khi người dùng gửi câu hỏi, hệ thống đầu tiên chuyển qua **Presidio** để quét các thực thể định danh cá nhân (PII) như Số Căn cước công dân (CCCD), Số điện thoại (SĐT), Email cá nhân. Nếu phát hiện câu hỏi chứa dữ liệu nhạy cảm hoặc tấn công chèn PII trái phép, request sẽ bị chặn ngay lập tức (short-circuit), trả về thông báo từ chối.
   * Tiếp theo, câu hỏi đi qua **NeMo Input Guard** để phát hiện các mối đe dọa an toàn thông tin bao gồm Jailbreak (DAN, đóng vai quản trị viên), Prompt Injection (ghi đè system prompt), và câu hỏi lạc đề (Off-topic như hỏi công thức nấu ăn, giá tiền mã hóa). Nếu vi phạm, request dừng ngay và ghi log sự cố.
2. **Tầng RAG Pipeline**:
   * Khi câu hỏi vượt qua tầng Input an toàn, hệ thống thực hiện Hybrid Search (Vector Dense bge-m3 kết hợp BM25Okapi tiếng Việt), kết hợp điểm Reciprocal Rank Fusion (RRF) và Cross-Encoder Reranker để chọn ra Top-5 chunks ngữ cảnh tốt nhất.
   * Mô hình `gpt-4o-mini-2024-07-18` sinh câu trả lời bám sát ngữ cảnh với nhiệt độ thấp (temperature = 0).
3. **Tầng Output Guard (NeMo Output)**:
   * Câu trả lời sinh ra được rà soát lần cuối để ngăn chặn rò rỉ dữ liệu mật (mật khẩu quản trị, số CCCD nhân viên). Nếu phát hiện thông tin không an toàn, câu trả lời sẽ bị chặn hoặc ẩn danh (redacted) và trả về thông điệp mặc định: "Tôi không thể hỗ trợ yêu cầu này."
4. **Quản lý Secrets, Logging và Fallback**:
   * **Bảo mật Secrets**: Các khóa API (`OPENAI_API_KEY`, kết nối cơ sở dữ liệu Qdrant) được lưu trữ độc quyền trong GitHub Secrets hoặc Vault, nạp qua biến môi trường (.env), tuyệt đối không lưu cứng trong mã nguồn.
   * **Logging & Redaction**: Mọi câu hỏi vi phạm đều được che giấu dữ liệu định danh trước khi ghi vào log giám sát, tuân thủ tiêu chuẩn an toàn bảo mật thông tin.
   * **Cơ chế Fallback**: Khi dịch vụ OpenAI hoặc Qdrant gặp sự cố gián đoạn kết nối, hệ thống kích hoạt cơ chế fallback tìm kiếm cục bộ hoặc trả về thông báo thử lại sau thay vì làm sập ứng dụng.

## Phạm vi và số đo latency

Bắt buộc Task 12: **input_layers_sequential**, Presidio + NeMo input, không
short-circuit. Engines tạo trước đo; có hai warm-up thật không tính vào mẫu.
Percentile nội suy tuyến tính từ raw samples; tổng từ tổng từng sample.

Số mẫu timed: 20; warm-up: 2; phương pháp: linear.

| Layer / scope | P50 ms | P95 ms | P99 ms | Tình trạng |
|---|---|---|---|---|
| Presidio | 10.88 | 14.71 | 15.66 | Đã đo thực tế Task 12 |
| NeMo input | 0.12 | 0.18 | 0.18 | Đã đo thực tế Task 12 |
| Input guard sequential | 10.98 | 14.89 | 15.84 | Đã đo thực tế Task 12 |
| RAG | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| NeMo output | chưa đo | chưa đo | chưa đo | Ngoài phạm vi bắt buộc |
| Full guard / short-circuit request | chưa đo | chưa đo | chưa đo | Không suy từ input_guard_ms |

Input-layer budget target: 500ms; kết quả thực tế/budget_ok: P95 = 14.89 ms; budget_ok: True.

### Phân tích hiệu năng và kế hoạch đo kiểm:
* **Đánh giá kết quả đo**:
  Tổng thời gian xử lý của tầng bảo vệ đầu vào (Input Guard Sequential) đạt mức P95 là 14.89 ms, vượt xa mục tiêu ngân sách trễ đề ra (< 500 ms). Trong đó, Presidio chiếm phần lớn thời gian (P95 = 14.71 ms) do phải xử lý phân tích cú pháp regex và so khớp thực thể tiếng Việt, trong khi tầng NeMo Input chạy cực nhanh (P95 = 0.18 ms) nhờ xử lý mẫu luật được biên dịch trước. Do đó, tầng guardrail đầu vào hoàn toàn không gây tắc nghẽn (bottleneck) cho hệ thống.
* **Kế hoạch đo lường cho các tầng mở rộng**:
  Đối với các tầng nằm ngoài phạm vi bắt buộc của Task 12 (RAG pipeline, NeMo output, và full request flow), báo cáo giữ nguyên trạng thái "chưa đo" nhằm phản ánh trung thực dữ liệu thực nghiệm đã xác thực. Khi triển khai giai đoạn kế tiếp, nhóm đề xuất đo lường bằng cách lấy 50 mẫu câu hỏi đa dạng, thực hiện 5 lượt warm-up ban đầu, sử dụng hàm đo thời gian có độ chính xác nano giây (`time.perf_counter_ns()`) để ghi nhận độ trễ trọn vẹn từ lúc tiếp nhận truy vấn đến khi hoàn tất phản hồi.

## CI gates đề xuất

- RAGAS faithfulness ≥0.75, avg_score ≥0.65 trên 50 câu.
- Attacks ≥18/20 cho CI đề xuất; clean 8/8 allowed; output cases đúng 4/4.
- Full guard P95 <500ms chỉ áp dụng sau khi thực sự đo full guard.

Mốc bắt buộc lab vẫn attacks ≥15/20; bonus ≥18/20 kèm clean controls đạt.

### Thiết kế CI Workflow và Quality Gates tự động:
* **Workflow đề xuất trong CI/CD**:
  Nhóm đề xuất xây dựng luồng kiểm tra tự động trên GitHub Actions mỗi khi có Pull Request mới vào nhánh `main`. Quy trình bao gồm các bước:
  1. Kiểm tra định dạng và unit tests: `pytest tests/ -v`
  2. Chạy kiểm thử guardrail đầu vào và đầu ra: `python scripts/run_experiments.py --phase c`
  3. Đánh giá chất lượng RAG trên bộ câu hỏi mẫu: `python scripts/run_experiments.py --phase a`
* **Cơ chế trả mã lỗi nonzero để chặn merge**:
  Các biến môi trường ngưỡng (ví dụ `MIN_FAITHFULNESS=0.75`, `MIN_ATTACKS_PASSED=18`) sẽ được cấu hình trong runner. Script kiểm tra sẽ thực thi các lệnh assertion cụ thể:
  ```bash
  python -c "import json; data=json.load(open('artifacts/guard_results.json')); assert data['adversarial']['passed'] >= 18, 'Failed attacks gate'; assert data['clean']['false_positive_rate'] == 0, 'Clean queries blocked'"
  ```
  Nếu bất kỳ chỉ số nào rơi xuống dưới ngưỡng yêu cầu, lệnh sẽ trả về mã thoát khác 0 (`exit code 1`), khiến GitHub Actions đánh dấu đỏ (failed) và tự động khóa tính năng merge pull request.
* **Lưu ý hiện trạng**: Quy trình CI trên đây là bản thiết kế đề xuất của nhóm cho môi trường sản xuất; hiện tại trên kho mã nguồn, các kiểm tra đang được chạy thủ công thông qua công cụ kiểm tra `scripts/check_lab.py` để tiết kiệm chi phí gọi API.

## Monitoring và cải tiến

Để đảm bảo hệ thống duy trì chất lượng ổn định khi đưa vào phục vụ người dùng thực tế, nhóm đề xuất kế hoạch giám sát (monitoring) và vận hành như sau:

1. **Các chỉ số giám sát và ngưỡng cảnh báo**:
   * **RAG Performance Drift**: Định kỳ hàng tuần lấy ngẫu nhiên 50 truy vấn thực tế để chạy kiểm thử RAGAS tự động. Nếu `avg_score < 0.70` hoặc `faithfulness < 0.75`, hệ thống sẽ phát cảnh báo mức độ Trung bình (Warning).
   * **Guardrail False Positive Rate**: Tỷ lệ người dùng hợp lệ bị chặn nhầm phải duy trì ở mức 0%. Nếu tỷ lệ này vượt quá 0.5%, hệ thống phát cảnh báo Cao (High).
   * **Bảo mật và Tấn công**: Bất kỳ truy vấn tấn công (jailbreak/prompt injection) nào lọt qua được tầng guardrail đều phát cảnh báo Nghiêm trọng (Critical) ngay lập tức.
   * **Độ trễ hệ thống (Latency)**: Giám sát P95 của toàn bộ luồng RAG, cảnh báo nếu vượt quá 2500 ms.
2. **Quy trình xử lý sự cố và phân quyền**:
   * Áp dụng cơ chế phân tầng thông báo qua Webhook tới kênh kỹ thuật Slack/Discord. Kỹ sư phụ trách (Lê Thị Thùy Trang) sẽ tiếp nhận xử lý trong vòng 2 giờ đối với cảnh báo nghiêm trọng.
   * Mọi dữ liệu thu thập phục vụ monitoring đều được tự động ẩn danh hóa (anonymize) để bảo vệ quyền riêng tư của nhân viên công ty.

Số liệu đo lường thực tế hiện tại của hệ thống:
RAGAS mean/worst distribution: Factual mean: 0.8704; Multi-hop mean (worst): 0.6811; Adversarial mean: 0.7453.
Cohen’s κ: 1.00 (10/10 đồng thuận tuyệt đối).
Attacks passed: 20/20 (100.0%); clean false_positive_rate: 0.00 (0%).

### Bốn đề xuất cải tiến khả thi có thể kiểm tra thực nghiệm:
1. **Tối ưu hóa khả năng suy luận Multi-hop**: Tích hợp module phân rã câu hỏi (Query Decomposition) để tách các câu hỏi phức tạp nhiều bước thành các câu hỏi đơn, nhằm nâng chỉ số `faithfulness` của nhóm multi-hop từ 0.4100 lên trên 0.7500.
2. **Nâng cấp từ điển thực thể Presidio cho thị trường Việt Nam**: Bổ sung bộ nhận diện chuyên sâu cho các mẫu số tài khoản ngân hàng nội địa (10-14 chữ số) và mã số bảo hiểm xã hội để ngăn ngừa rò rỉ dữ liệu tài chính.
3. **Cơ chế tự kiểm chứng (Self-Consistency / Verifier Step)**: Bổ sung bước kiểm tra số học nhẹ trước khi xuất câu trả lời đối với các câu hỏi liên quan đến ngày phép, công tác phí, giúp loại bỏ triệt để hiện tượng cộng trừ sai trong RAG.
4. **Bộ nhớ đệm thông minh (Semantic Cache)**: Sử dụng Redis hoặc Qdrant để lưu trữ các câu trả lời của các câu hỏi phổ biến (FAQ), giúp đưa độ trễ phản hồi của 40% câu hỏi thông dụng xuống dưới 50 ms mà không cần gọi lại LLM.
