# Ý tưởng đột phá: Study Room, Course Detail & Customer Profile  
## Cấu trúc, phong cách thiết kế, tương tác, ấn tượng

*Tập trung vào **trải nghiệm học tập**, **trang khóa học dễ nắm** và **Customer 360 có chiều sâu** — mục tiêu: mỗi trang tạo cảm giác rõ ràng, chuyên nghiệp và đáng nhớ.*

---

## A. STUDY ROOM (Phòng học — Xem tài liệu + Titan Tutor + Quiz)

*Hiện tại: Layout 2 cột full-screen (viewer PDF/PPT + sidebar chat/tutor), toolbar trang, vòng tròn tiến độ, quick prompts, đề nghị giảng dạy, nút Quiz mở khi ≥90%, modal Quiz với tráo câu khi chưa đạt. Focus mode ẩn header/sidebar.*

### 1. Kiến trúc: "Một dòng biết đang ở đâu" — Progress strip trong toolbar

**Ý tưởng:** Trong thanh toolbar (phía viewer), thêm **một dải ngắn** luôn hiển thị: *"Bài X / Y · Đã đọc Z% · Quiz: [Khóa / Mở]"* — X = thứ tự bài trong khóa (nếu backend truyền), Y = tổng bài, Z = % hiện tại, trạng thái Quiz. Có thể đặt giữa toolbar thay vì chỉ có nút Back + tên file.

- **Ấn tượng:** Học viên **luôn biết vị trí** trong hành trình (bài nào, đã xem bao nhiêu, có được làm quiz chưa). Giảm cảm giác "lạc" trong tài liệu dài.

---

### 2. Kiến trúc: Sidebar = "Trợ lý cố định" — Thu gọn được

**Ý tưởng:** Sidebar bên phải không chỉ là chat: coi là **panel trợ lý** có 3 vùng rõ ràng — (1) Đầu: Avatar Titan + tiến độ đọc + trạng thái Online; (2) Giữa: Lịch sử chat + quick prompts (có thể thu gọn thành "Gợi ý hỏi" accordion khi scroll); (3) Chân: Đề nghị giảng dạy + Quiz + ô nhập. Thêm **nút thu gọn sidebar** (icon chevron): khi thu gọn chỉ còn dải hẹp (icon Titan + % + nút mở lại), viewer chiếm gần full màn hình.

- **Ấn tượng:** Người muốn **chỉ đọc** có thể tối đa hóa vùng tài liệu; khi cần hỏi hoặc làm quiz mới mở rộng. Cảm giác "tôi điều khiển không gian học".

---

### 3. Phong cách: Viewer "phòng đọc" — Nền và viền tách bạch

**Ý tưởng:** Vùng hiển thị PDF/PPT không chỉ là nền xám: thêm **viền nhẹ** hoặc shadow bên trong để trang/canvas nổi lên như "tờ giấy trên bàn". Nền viewer có thể gradient rất nhạt (xám đậm → xám nhạt) để tạo chiều sâu. Toolbar tối (đã có) giữ contrast với vùng nội dung.

- **Ấn tượng:** **Tài liệu là nhân vật chính**, không bị hòa lẫn với nền. Cảm giác "đang ngồi trong phòng đọc" chuyên nghiệp.

---

### 4. Tương tác: Quick prompts — Hover + click rõ ràng

**Ý tưởng:** Ba nút gợi ý (Tóm tắt 3 ý, Ứng dụng thực tế, Tự kiểm tra) không chỉ là nút outline: **hover** có background nhạt + scale nhẹ; **sau khi click** (đã gửi) có thể đổi thành trạng thái "đã gửi" (icon check + màu success nhạt) để không bấm trùng. Tin nhắn AI đang trả lời: thay "spinner" bằng **skeleton text** (vài dòng gợn sóng) để cảm giác "đang viết" thay vì "đang load".

- **Ấn tượng:** Mỗi thao tác **có phản hồi**; không có cảm giác "bấm xong không biết có gửi không". Chat có nhịp điệu (đang gõ → hiện câu trả lời).

---

### 5. Tương tác: Quiz — Mở ra "có kịch bản"

**Ý tưởng:** Khi đạt ≥90% và nút Quiz mở: **micro-animation** (icon khóa → mở khóa, hoặc pulse nhẹ một lần) để thu hút sự chú ý. Trong modal Quiz: sau khi nộp bài và **chưa đạt**, thông báo "đổi 1 câu mới" kèm **progress nhỏ** (ví dụ "Câu 5 đã được thay — 4 câu giữ nguyên") và nút "Làm lại" rõ ràng; khi **đạt**: confetti nhẹ hoặc badge "Hoàn thành bài học" trước khi reload.

- **Ấn tượng:** Quiz không chỉ là form — có **câu chuyện** (mở khóa → làm bài → đạt/không đạt → thử lại với câu mới). Tăng động lực hoàn thành.

---

### 6. Phong cách: Đề nghị giảng dạy — Giới hạn rõ, không gây lo

**Ý tưởng:** Khối "Cần giảng viên hướng dẫn?" đã có số lượt còn lại; có thể thêm **progress nhỏ** (ví dụ 3 ô tròn: còn 2 lượt = 2 ô đầy, 1 ô rỗng) để nhìn là biết "còn bao nhiêu". Sau khi gửi thành công: toast + **cập nhật ngay** số lượt và trạng thái nút (disabled khi hết) mà không cần reload.

- **Ấn tượng:** **Giới hạn minh bạch** — không bấm xong mới biết hết lượt. Cảm giác hệ thống công bằng và rõ ràng.

---

### 7. Empty / Loading

**Ý tưởng:** Khi đang tải PDF: thay vì chỉ spinner, hiện **skeleton** hình chữ nhật tỷ lệ trang A4 (placeholder trang) với shimmer. Khi lỗi tải file: thông báo lỗi kèm **nút "Quay lại khóa học"** (link về course detail) để không bị kẹt.

- **Ấn tượng:** Mọi trạng thái **có đường thoát** và có chủ đích.

---

## B. COURSE DETAIL (Chi tiết khóa học — Danh sách bài học)

*Hiện tại: Breadcrumb, cột trái = card sticky (ảnh, title, category, mô tả, số bài/XP/tiến độ %, nút Tiếp tục/Đã hoàn thành), cột phải = list-group từng bài (icon trạng thái, tên, trang, badge).*

### 1. Kiến trúc: "Một dòng hành trình khóa" — Hero strip

**Ý tưởng:** Ngay dưới breadcrumb (hoặc dưới title khóa), một dải ngắn: *"Z bài học · Đã hoàn thành X/Y (W%) · Còn N bài · +K XP khi hoàn thành"* — Z = tổng bài, X/Y = đã xong / tổng, W = %, N = chưa làm, K = XP thưởng. Có thể kèm **progress bar ngang** (đã có % — thể hiện bằng thanh màu primary/success).

- **Ấn tượng:** **Một câu đọc xong** là nắm tiến độ cả khóa; tạo cảm giác "roadmap" rõ, động lực "còn N bài nữa là xong".

---

### 2. Kiến trúc: Card khóa = "Bìa sách" — Cảm giác sản phẩm

**Ý tưởng:** Card bên trái không chỉ là box ảnh + chữ: (1) **Ảnh thumbnail** có tỷ lệ chuẩn (ví dụ 4:3), bo góc, có shadow nhẹ như bìa sách; (2) **Title** là typography chủ đạo (font-size lớn, font-weight bold); (3) **Category** và **XP** dùng badge/pill rõ ràng; (4) **Mô tả** giới hạn 2–3 dòng + "Xem thêm" nếu dài. Nút **"Tiếp tục học"** hoặc **"Đã hoàn thành"** đặt nổi bật (full width, màu primary/success), có icon play/check.

- **Ấn tượng:** Card đọc như **bìa khóa học** — có cảm giác "sản phẩm", không chỉ là form thông tin.

---

### 3. Phong cách: Danh sách bài = "Chương sách" — Có thứ bậc

**Ý tưởng:** Mỗi hàng bài học không chỉ là list-group-item: (1) **Số thứ tự** rõ (1, 2, 3...) hoặc icon lớn (khóa / play / check) tương ứng trạng thái; (2) **Tên bài** là dòng chính, phụ (số trang, "Đang học dở") là secondary; (3) **Hover**: cả hàng có background nhạt + viền trái primary; (4) **Đã hoàn thành**: có thể thêm dấu tích nhỏ và màu success nhạt để quét mắt thấy "đã xong" ngay.

- **Ấn tượng:** Danh sách đọc như **mục lục chương** — dễ quét, dễ chọn "bài tiếp theo" hoặc "quay lại bài X".

---

### 4. Tương tác: "Tiếp tục học" — Nhảy đúng bài, có feedback

**Ý tưởng:** Nút "Tiếp tục học" đã link tới `first_incomplete` — đảm bảo **focus** khi vào study_room mở đúng trang (last_page) nếu có. Sau khi hoàn thành một bài và quay lại course detail: **trạng thái cập nhật** (bài vừa xong chuyển sang "Xong", bài tiếp theo thành "Tiếp tục"). Có thể thêm toast nhẹ khi vào trang: *"Tiếp tục từ bài [Tên bài]"* nếu từ deep link.

- **Ấn tượng:** **Liền mạch** — một click là vào đúng chỗ học tiếp, không phải tìm lại.

---

### 5. Tương tác: Click bài — Rõ "sẽ mở gì"

**Ý tưởng:** Click vào một bài: chuyển tới study_room (đã có). Có thể thêm **title** hoặc **tooltip** trên từng hàng: *"Mở bài: [Tên] — [X] trang"* hoặc *"Đã hoàn thành — Xem lại"* để người dùng biết trước khi click. Trên mobile: hàng có thể hơi cao hơn (padding) để dễ chạm.

- **Ấn tượng:** **Affordance** rõ — "đây là nút vào bài", không mơ hồ.

---

### 6. Empty state

**Ý tưởng:** Khi khóa **chưa có bài** (materials rỗng): không chỉ icon + chữ "đang cập nhật" — thêm **nút "Về Học viện"** (link /training) và có thể dòng chữ *"Khóa này sẽ sớm có nội dung. Bạn có thể xem khóa khác."*

- **Ấn tượng:** Trống có **hướng đi**, không gây ngơ ngác.

---

## C. CUSTOMER PROFILE (Customer 360 — Hồ sơ khách hàng)

*Hiện tại: Title + badge ID + địa chỉ; 3 metric cards (báo cáo, báo giá/đơn YTD, TG thanh toán TB); 3 KPI cards (Doanh số YTD/target, Công nợ/quá hạn, OTIF) với progress bar; 2 cột chart (Xu hướng 5 năm, Cơ cấu nhóm hàng); 2 bảng (Top 30 SP, Cơ hội bỏ lỡ); 1 chart Giá bán vs QĐ; modal drill-down. Bảo mật: chặn in, select, F12.*

### 1. Kiến trúc: "Một dòng tổng quan KH" — Hero strip

**Ý tưởng:** Ngay dưới header (tên KH + mã + địa chỉ), một dải ngắn: *"Doanh số YTD: X tỷ (Y% mục tiêu) · Công nợ: Z tỷ · OTIF: W%"* — lấy từ metrics đã có, số có màu theo ngưỡng (đạt target xanh, chưa primary; nợ quá hạn đỏ). Có thể kèm **mini progress** (một đoạn ngắn) cho % mục tiêu.

- **Ấn tượng:** **Một câu** là nắm "sức khỏe" khách hàng — doanh số, nợ, giao hàng. Sau đó mới đi sâu chart/bảng.

---

### 2. Kiến trúc: KPI cards — "Sống" theo ngưỡng

**Ý tưởng:** Ba card Doanh số / Công nợ / OTIF không chỉ hiển thị số: (1) **Viền trái hoặc accent** theo ngưỡng — Doanh số: xanh nếu đạt target, primary nếu 70–99%, cam nếu &lt;70%; Công nợ: đỏ nếu quá hạn &gt;0; OTIF: xanh/primary/đỏ theo %; (2) **Progress bar** trong card đã có — đảm bảo màu bar thống nhất với ý nghĩa (đạt/ chưa đạt/ cảnh báo); (3) **Hover**: nâng nhẹ card + shadow.

- **Ấn tượng:** **Quét mắt** là biết KH đang "tốt" hay "cần chú ý". Số liệu có ngữ cảnh.

---

### 3. Phong cách: Chart và bảng — Có "lớp" rõ

**Ý tưởng:** Vùng chart (Xu hướng, Cơ cấu, Giá bán): (1) **Tiêu đề card** có icon + màu nhất quán (ví dụ doanh số = primary, nợ = warning, OTIF = success); (2) **Chart** nền trong suốt hoặc trùng với card, trục và chữ dùng biến theme; (3) **Bảng** (Top SP, Cơ hội bỏ lỡ): header sticky, hover hàng có background nhạt, số tiền/tỷ trọng căn phải và font-weight rõ. Có thể thêm **striped** nhẹ cho bảng để dễ đọc.

- **Ấn tượng:** Chart và bảng **hợp một thể** với phần KPI; không rời rạc. Cảm giác "báo cáo chỉn chu".

---

### 4. Tương tác: Drill-down — Mở nhanh, đóng rõ

**Ý tưởng:** Click vào cột/nhóm trên chart → mở modal drill-down (đã có). (1) **Modal**: tiêu đề rõ (năm nào, nhóm nào), bảng load xong mới hiện (tránh "Đang tải..." quá lâu — có skeleton cho bảng); (2) **Đóng**: nút Đóng + click overlay + **Esc**; (3) Có thể thêm **breadcrumb** trong modal: *"Customer 360 > [Tên KH] > Doanh số năm 2024"* để biết đang xem chi tiết gì.

- **Ấn tượng:** **Đào sâu** có ngữ cảnh, không "popup lạ". Đóng nhanh, quay lại chart rõ ràng.

---

### 5. Tương tác: Nút "Cập nhật" và "Quay lại"

**Ý tưởng:** Header đã có "Cập nhật" (reload) và "Quay lại" (profit_analysis). **Cập nhật**: khi click có thể hiện **spinner nhỏ** trên nút hoặc disable 2–3 giây để tránh double-click; sau khi load xong có thể toast *"Đã làm mới dữ liệu"*. **Quay lại**: giữ rõ, có thể thêm title *"Về Phân tích lợi nhuận"* để rõ đích.

- **Ấn tượng:** Hành động **có kết thúc** — người dùng biết đã refresh xong, biết quay về đâu.

---

### 6. Phong cách: Metric cards hàng đầu — Nhất quán với KPI

**Ý tưởng:** Ba card đầu (Báo cáo, Báo giá/Đơn YTD, TG thanh toán TB) đã có icon-box và metric-value; có thể **đồng bộ** với theme (viền, shadow, hover) giống các card KPI bên dưới. Số lớn (metric-value) có thể tăng nhẹ font-weight hoặc size để dễ quét.

- **Ấn tượng:** **Một gia đình** — toàn bộ block số liệu cùng phong cách, trang gọn và chuyên nghiệp.

---

### 7. Responsive & in ấn (nếu cần)

**Ý tưởng:** Trên mobile: hero strip có thể xuống dòng (flex-wrap); KPI cards xếp 1 cột; chart/bảng scroll ngang hoặc thu nhỏ. **In**: hiện tại đã chặn in (bảo mật); nếu sau này cần "export PDF báo cáo KH" thì có thể thêm nút riêng gọi API xuất file thay vì in trang.

- **Ấn tượng:** Trên mọi thiết bị **vẫn dùng được**; bảo mật và nhu cầu báo cáo tách bạch.

---

## D. GỢI Ý ƯU TIÊN TRIỂN KHAI

| Trang | Ý tưởng | Effort | Ấn tượng |
|-------|--------|--------|----------|
| **Study Room** | Progress strip trong toolbar (bài X/Y, %, Quiz) | Thấp | Cao |
| **Study Room** | Nút thu gọn sidebar (viewer full) | Trung bình | Cao |
| **Study Room** | Quick prompts: trạng thái "đã gửi" + skeleton khi AI trả lời | Thấp | Trung bình |
| **Study Room** | Quiz: animation mở khóa + confetti khi đạt | Thấp | Cao |
| **Course Detail** | Hero strip (Z bài · X/Y hoàn thành · N còn · +K XP) | Thấp | Cao |
| **Course Detail** | Card khóa kiểu "bìa sách" + progress bar ngang | Trung bình | Cao |
| **Course Detail** | Danh sách bài: số TT + hover viền trái | Thấp | Trung bình |
| **Customer Profile** | Hero strip một dòng (DS YTD · Nợ · OTIF) | Thấp | Cao |
| **Customer Profile** | KPI cards màu theo ngưỡng (xanh/primary/đỏ) | Thấp | Cao |
| **Customer Profile** | Drill-down modal: breadcrumb + skeleton bảng | Thấp | Trung bình |
| **Customer Profile** | Nút Cập nhật: spinner + toast khi xong | Thấp | Trung bình |

---

## E. TÓM TẮT BẢN SẮC CHUNG

- **Study Room:** "Phòng đọc có trợ lý" — viewer là trung tâm, sidebar thu gọn được, tiến độ và quiz có kịch bản rõ, chat có phản hồi (skeleton, trạng thái đã gửi).
- **Course Detail:** "Bìa khóa + mục lục chương" — một dòng hero nắm tiến độ, card khóa như sản phẩm, danh sách bài như chương sách dễ quét, "Tiếp tục học" đưa đúng bài.
- **Customer Profile:** "Một câu biết sức khỏe KH" — hero strip tổng quan, KPI và metric có màu theo ngưỡng, chart/bảng nhất quán, drill-down có ngữ cảnh và đóng rõ.

*Ba trang đều hướng tới: **ít scroll để nắm ý chính**, **tương tác có phản hồi**, **thông tin có thứ bậc** — tạo ấn tượng sản phẩm chỉn chu và đáng tin.*
