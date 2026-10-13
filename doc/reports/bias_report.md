# Đánh giá LLM Judge Phase B

Nhóm: Slopper

Người phụ trách: Lê Thị Thùy Trang - 2A202602678

Nguồn: `artifacts/judge_results.json`; run timestamp: 2026-10-12T03:19:51.728139+00:00.
Models generation/judge: generation: gpt-4o-mini-2024-07-18; judge: gpt-4o-mini.

## Năm cặp A/B và hai lượt

Nguồn cố định: A từ artifacts/answers_50q.json:answer; B từ fixtures/human_labels_10q.json:model_answer; reference từ fixtures/test_set_50q.json:ground_truth.
Ids: 1, 5, 12, 21, 41. Không đổi nguồn sau khi xem kết quả judge.

Dưới đây là bảng kết quả chi tiết của 5 cặp so sánh pairwise qua hai lượt hoán đổi vị trí (đã quy về nhãn A/B gốc):

| ID | Candidate A | Candidate B | Winner Pass 1 | Winner Pass 2 | Final Winner | Position Consistent | Scores Pass 1 (A/B) | Scores Pass 2 (A/B) |
|---|---|---|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc khi kết hôn. | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | B | B | B | True | A: 0.5 / B: 1.0 | A: 0.5 / B: 1.0 |
| 5 | Trưởng phòng (Manager) phê duyệt. | Cần Giám đốc phòng ban phê duyệt. | B | tie | tie | False | A: 0.0 / B: 0.7 | A: 0.0 / B: 0.0 |
| 12 | Thưởng Tết tối thiểu cho nhân viên chính thức có từ 6 tháng trở lên là 1 tháng lương. | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | A | A | A | True | A: 1.0 / B: 1.0 | A: 1.0 / B: 0.5 |
| 21 | Nhân viên có 9 năm thâm niên sẽ được 18 ngày phép (15 + 3) theo quy định. Số ngày phép này là có lương, vì thuộc vào chính sách nghỉ phép năm. | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | A | A | A | True | A: 1.0 / B: 1.0 | A: 1.0 / B: 1.0 |
| 41 | Nhân viên chính thức được hưởng 15 ngày phép năm có lương. | Nhân viên được nghỉ 12 ngày phép năm. | A | A | A | True | A: 1.0 / B: 0.0 | A: 1.0 / B: 0.0 |

Position bias count/rate: count = 1; rate = 0.20 (20.0%).
Verbosity win rate: 1.00 (100.0%); decisive cases: 4 (trong đó candidate A thắng khi dài hơn: 3; candidate B thắng khi dài hơn: 1).

### Giải thích các case không nhất quán và các winner dài hơn:
1. **Case không nhất quán do Position Bias (Câu 5)**:
   * Ở Pass 1 (thứ tự hiển thị là A rồi B): Judge chọn B thắng với điểm số A=0.0, B=0.7. Lý do judge đưa ra là "B gần đúng hơn quy định vì Giám đốc phòng ban có thẩm quyền cao hơn Trưởng phòng".
   * Tuy nhiên, sang Pass 2 (đảo thứ tự thành B rồi A): Judge lại phán quyết `tie` với điểm số cả hai câu đều là 0.0. Lý do là khi đọc lại một cách khắt khe, judge nhận thấy theo chính sách thì đơn hàng trên 50 triệu VNĐ bắt buộc phải do Tổng Giám đốc duyệt, nên cả A và B đều hoàn toàn sai.
   * Điều này chứng minh hiệu ứng Position Bias: Thứ tự xuất hiện trước/sau trong prompt làm thay đổi phân bố attention của LLM, dẫn đến tiêu chuẩn chấm ở Pass 1 có phần nới lỏng chọn "câu đỡ sai hơn", trong khi Pass 2 lại khắt khe đánh trượt cả hai câu. Nhờ cơ chế swap hai lượt và chỉ công nhận chiến thắng khi đồng thuận ở cả 2 pass, hệ thống đã đưa ra phán quyết an toàn cuối cùng là `tie`.
2. **Hiện tượng Verbosity Win Rate đạt 1.0 (100% trong 4 decisive cases)**:
   * Về mặt thống kê, toàn bộ 4 cặp câu phân định thắng bại (ID 1, 12, 21, 41) thì câu trả lời dài hơn đều giành chiến thắng chung cuộc.
   * Tuy nhiên, khi phân tích nội dung, đây không phải là thiên lệch mù quáng theo độ dài (spurious correlation) mà do câu dài hơn thực sự cung cấp thông tin chuẩn xác và đầy đủ hơn:
     - Ở câu 1: B dài hơn A vì bổ sung thông tin then chốt là "có lương".
     - Ở câu 12: A dài hơn B vì làm rõ đối tượng điều kiện "nhân viên chính thức có từ 6 tháng trở lên".
     - Ở câu 21: A dài hơn và giải thích tường minh bản chất số ngày phép có lương theo chính sách.
     - Ở câu 41: A dẫn chiếu đúng chính sách cập nhật v2024 (15 ngày), trong khi B ngắn hơn nhưng lại dẫn số liệu cũ v2023 (12 ngày).
   * Dù vậy, các nghiên cứu cũng chỉ ra LLM Judge có xu hướng bị ấn tượng bởi lối hành văn giải thích mạch lạc, do đó nhóm vẫn ghi nhận đây là một yếu tố cần kiểm soát chặt chẽ khi thiết kế prompt cho Judge.

## Calibration đúng model_answer

Helper đánh giá đúng question/model_answer đang có trong fixtures/human_labels_10q.json; không lấy answer mới của pipeline. Prompt chỉ nhận question, answer, reference. Không gửi human_label, human_note hoặc phân bố nhãn human vào prompt.

Bảng đối chiếu 10 câu hỏi hiệu chuẩn giữa quyết định của LLM Judge và nhãn chuyên gia con người (Human Label):

| Question ID | Model Answer gốc | Judge Label | Human Label | Agree | Reasoning của Judge |
|---|---|---|---|---|---|
| 1 | Nhân viên được nghỉ 3 ngày làm việc có lương khi kết hôn. | 1 | 1 | True | Câu trả lời chính xác theo thông tin trong tài liệu tham khảo, nêu rõ số ngày nghỉ và điều kiện không trừ vào phép năm. |
| 5 | Cần Giám đốc phòng ban phê duyệt. | 0 | 0 | True | Câu trả lời sai vì yêu cầu phê duyệt cho đơn hàng trên 50 triệu là từ Tổng Giám đốc, không phải Giám đốc phòng ban. |
| 12 | Nhân viên được thưởng Tết tối thiểu 1 tháng lương. | 1 | 1 | True | Câu trả lời chính xác theo thông tin trong reference, nêu rõ điều kiện và mức thưởng cho nhân viên chính thức có từ 6 tháng trở lên. |
| 21 | Được nghỉ 18 ngày phép (15 cơ bản + 3 thâm niên). Lương Senior từ 20 đến 35 triệu. | 1 | 1 | True | Câu trả lời chính xác theo reference, nêu rõ số ngày phép và khoảng lương cho nhân viên Senior với 9 năm thâm niên. |
| 23 | Hoàn trả 25 triệu vì chưa đủ 1 năm cam kết. | 1 | 1 | True | Câu trả lời chính xác theo thông tin trong reference, nêu rõ nhân viên phải hoàn trả 25 triệu do chưa đủ 1 năm cam kết. |
| 29 | Trưởng phòng phê duyệt. Phạt 2% tháng trên 8 triệu. | 0 | 0 | True | Câu trả lời sai vì chỉ đề cập Trưởng phòng phê duyệt mà không nhắc đến Kế toán trưởng, và phí phạt được tính cho quá hạn 15 ngày chứ không phải 30 ngày. |
| 33 | Phép: 19 ngày. Phụ cấp: 1.500.000 VNĐ/tháng. | 1 | 1 | True | Câu trả lời cung cấp đúng số ngày phép và tổng phụ cấp hàng tháng theo thông tin trong tài liệu tham khảo. |
| 41 | Nhân viên được nghỉ 12 ngày phép năm. | 0 | 0 | True | Câu trả lời sai vì nó dựa trên chính sách cũ (v2023) thay vì chính sách hiện hành (v2024), trong đó quy định nhân viên được nghỉ 15 ngày phép năm. |
| 46 | Nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần. | 1 | 1 | True | Câu trả lời chính xác theo reference, nêu rõ rằng nhân viên thử việc không được nghỉ phép năm và phải xin nghỉ không lương nếu cần, đồng thời không bỏ qua điều kiện cần có sự phê duyệt của trưởng phòng. |
| 50 | Được, miễn là đảm bảo kết nối an toàn. | 0 | 0 | True | Câu trả lời sai vì khẳng định rằng nhân viên Manager có thể dùng VPN cá nhân khi WFH, trong khi chính sách rõ ràng cấm việc này. |

Cohen’s κ: 1.00 (hoàn hảo).
Observed/chance agreement và diễn giải:
- Tỷ lệ đồng thuận quan sát được (Observed Agreement): $P_o = 10 / 10 = 1.0$ (100.0%).
- Tỷ lệ đồng thuận ngẫu nhiên (Chance Agreement): Với phân bố nhãn gồm 6 nhãn Đúng (1) và 4 nhãn Sai (0), xác suất trùng hợp ngẫu nhiên là:
  $$P_e = \frac{6 \times 6 + 4 \times 4}{10^2} = \frac{36 + 16}{100} = 0.52$$
- Hệ số tương quan Cohen's Kappa được tính như sau:
  $$\kappa = \frac{P_o - P_e}{1 - P_e} = \frac{1.0 - 0.52}{1 - 0.52} = \frac{0.48}{0.48} = 1.0$$
- Nhận xét: Hệ số $\kappa = 1.0$ vượt xa ngưỡng kỳ vọng $\kappa > 0.6$, chứng tỏ tiêu chuẩn đánh giá của Judge hoàn toàn ăn khớp với chuyên gia con người trên 10 câu hỏi thử nghiệm, nhận biết chính xác cả các bẫy logic như câu 41 (chính sách cũ) và câu 50 (VPN cá nhân).

## Giới hạn và cách dùng judge

Dù đạt kết quả tương đồng hoàn hảo ($\kappa = 1.0$) trong đợt thử nghiệm này, nhóm xin nêu rõ các giới hạn phương pháp luận và khuyến nghị triển khai thực tế như sau:

1. **Giới hạn về quy mô mẫu và tính đại diện**:
   * Tập dữ liệu kiểm chuẩn hiện tại mới dừng ở 5 cặp so sánh pairwise và 10 câu hiệu chuẩn binary. Quy mô này phù hợp trong môi trường bài tập lớn/phòng lab nhưng còn quá nhỏ để khái quát hóa cho toàn bộ các tình huống phức tạp trong thực tế vận hành.
   * Mô hình Judge được sử dụng là `gpt-4o-mini` với prompt yêu cầu đối chiếu ground truth. Mô hình này rất mạnh trong việc so khớp sự thật hiển ngôn (explicit factual matching), nhưng có thể gặp khó khăn khi đánh giá các câu trả lời mang tính suy luận ngầm hoặc các câu trả lời dài dòng cố tình đánh lạc hướng.

2. **Cách kiểm chứng và xử lý sai lệch**:
   * Không bao giờ xem kết quả của LLM Judge là "chân lý tuyệt đối" (Ground Truth tối hậu). Judge chỉ đóng vai trò là một bộ lọc tự động sơ bộ (proxy metric) với chi phí thấp và tốc độ cao.
   * Để triệt tiêu Position Bias, bắt buộc phải áp dụng quy trình đánh giá 2 lượt đảo vị trí (Pass 1: A vs B, Pass 2: B vs A). Khi có xung đột kết quả giữa 2 lượt, hệ thống phải tự động gán nhãn `tie` hoặc đẩy vào hàng đợi rà soát thủ công.
   * Trong quy trình CI/CD và vận hành sản phẩm, nhóm khuyến nghị thiết lập cơ chế Human-in-the-loop: chọn ngẫu nhiên 5% đến 10% các câu trả lời được Judge đánh giá để chuyên gia con người thẩm định lại định kỳ, theo dõi độ trôi dạt (drift) của hệ số Kappa theo thời gian để kịp thời hiệu chỉnh prompt.
