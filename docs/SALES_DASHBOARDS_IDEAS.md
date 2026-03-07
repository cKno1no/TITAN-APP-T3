# Ý tưởng đột phá: Sales Lookup, Sales Order Approval & Sales Dashboard  
## Kiến trúc, phong cách thiết kế, tương tác, ấn tượng

*Tập trung vào **cảm giác sử dụng**, **bản sắc hình ảnh** và **tương tác rõ ràng** cho 3 trang bán hàng. Mục tiêu: vào trang là hiểu ngay mục đích, thao tác mượt, kết quả đáng nhớ.*

---

## A. SALES LOOKUP DASHBOARD (Tra Cứu Bán Hàng)

*Hiện tại: Form tra cứu Mã/Tên hàng + Khách hàng → 3 block kết quả (Tồn & Giá, Lịch sử ĐH Bán/Xuất/HĐ, Lịch sử PO/Phiếu Nhập). Có "Tra nhanh", dropdown KH, modal BackOrder.*

### 1. Kiến trúc: "Một dòng biết đang tra gì" — Context strip

**Ý tưởng:** Ngay dưới form (hoặc sticky dưới header), một thanh ngắn chỉ khi **đã có kết quả**:  
*"Đang xem: 5 mặt hàng · Khách: [Tên KH hoặc 'Giá chung'] · Cập nhật: vừa xong"*  
Số mặt hàng lấy từ `results.block1|length`; tên KH từ `object_id_display`; "vừa xong" có thể là timestamp hoặc text tĩnh.

- **Ấn tượng:** Người dùng luôn biết **ngữ cảnh tra cứu** hiện tại, tránh nhầm "đang xem giá của ai". Cảm giác hệ thống "nhớ" lựa chọn của mình.

---

### 2. Kiến trúc: Form tra cứu = "Thanh lệnh" (Command bar)

**Ý tưởng:** Không coi form là "card form" dày đặc label. Thu gọn thành **một thanh ngang** (command bar): ô Mã/Tên hàng (chiếm rộng) + ô Khách hàng (autocomplete) + 2 nút "Tra nhanh" | "Tra cứu" — tất cả trên **một dòng** (trên desktop), label nhỏ phía trên hoặc placeholder đủ ý.

- **Ấn tượng:** Cảm giác **tra cứu nhanh như search Google** — một dòng, gõ xong Enter. Giảm cảm giác "điền form", tăng tốc thao tác lặp.

---

### 3. Phong cách: Kết quả theo "bậc" (tier) — Block 1 là hero

**Ý tưởng:** Block 1 (Tồn kho & Giá) là **nội dung chính** — card to hơn, shadow/viền rõ, có thể full width. Block 2 và 3 (Lịch sử) là **bổ sung**: có thể thu gọn mặc định (accordion hoặc "Xem thêm lịch sử" mới mở), hoặc layout 2 cột nhỏ hơn.

- **Ấn tượng:** Mắt tập trung vào **bảng giá & tồn** trước; lịch sử không làm "ngợp" lần đầu. Trang có **thứ bậc thông tin** rõ.

---

### 4. Tương tác: Bảng Tồn & Giá — Hover = "Tóm tắt một dòng"

**Ý tưởng:** Khi hover một dòng trong block 1: hiện **tooltip hoặc dải nhỏ** (không cần mở modal): *"Tồn: X · BackOrder: Y · Lần bán gần nhất: [ngày]"* — nếu backend có thể cung cấp thêm 1–2 field tóm tắt. Hoặc đơn giản: highlight cả dòng + viền trái màu primary.

- **Ấn tượng:** Người dùng **cảm nhận phản hồi ngay** khi rê chuột; bảng không "im lặng". Click vẫn mở modal BackOrder như hiện tại.

---

### 5. Tương tác: "Tra nhanh" có feedback rõ

**Ý tưởng:** Nút "Tra nhanh" (tồn): khi đang gọi API — nút chuyển trạng thái (spinner + text "Đang tra..."); khi xong — toast nhỏ *"Đã cập nhật tồn cho N mã hàng"* hoặc highlight nhẹ vùng kết quả (animation fade-in). Nếu lỗi: toast đỏ rõ ràng.

- **Ấn tượng:** Người dùng **biết chắc** thao tác đã xử lý; không bấm rồi không rõ có chạy hay không.

---

### 6. Phong cách: Lịch sử (Block 2, 3) — Tab thay vì 2 card dài

**Ý tưởng:** Thay vì 2 block dọc (ĐH Bán/Xuất/HĐ và PO/Phiếu Nhập) chiếm nhiều scroll: gộp thành **một card "Lịch sử"** với **2 tab**: "ĐH Bán & Xuất & HĐ" | "PO & Phiếu Nhập". Mỗi tab chỉ hiện một bảng.

- **Ấn tượng:** Trang **ngắn lại**, không phải scroll dài; người dùng chủ động chọn loại lịch sử cần xem. Cảm giác gọn, có tổ chức.

---

### 7. Empty & Loading

**Ý tưởng:** Khi chưa tra: vùng kết quả có thể hiện **placeholder nhẹ** (icon kính lúp + "Nhập mã hàng và bấm Tra cứu"). Khi đang POST: skeleton cho 3 block (hình chữ nhật shimmer) thay vì để trắng. Khi "Không tìm thấy": icon + câu gợi ý (*"Thử mở rộng từ khóa hoặc bỏ lọc khách hàng"*).

- **Ấn tượng:** Mọi trạng thái đều **có chủ đích** — không "trống trơn" hay "đơ" không rõ.

---

## B. SALES ORDER APPROVAL (Duyệt Đơn Hàng Bán — DHB)

*Hiện tại: Filter ngày + search; bảng đơn với Hệ số, Mã DHB, Loại, Ngày, KH, NVKD, Tổng GT, Kết quả kiểm tra, Nút Duyệt. htmx lọc, Alpine modal chi tiết, approve qua API.*

### 1. Kiến trúc: "Một dòng tình hình duyệt" — Funnel strip

**Ý tưởng:** Ngay dưới form lọc, một thanh ngang (giống quote_approval):  
*"Tổng: N đơn · Tự duyệt: X · Chờ duyệt: Y · Lỗi/Chưa đạt: Z"*  
Số liệu lấy từ `orders` (đếm theo `ApprovalResult.Passed`, PENDING, FAILED). Mỗi số có thể click → filter nhanh (chỉ hiện đơn thuộc nhóm đó).

- **Ấn tượng:** Người dùng **nắm pipeline duyệt** trong một giây; có thể nhảy thẳng vào "Chờ duyệt" hoặc "Lỗi" mà không cần đọc từng dòng.

---

### 2. Kiến trúc: Filter + Search = One line

**Ý tưởng:** Từ ngày, Đến ngày, ô Tìm (Mã DHB, KH) và nút Lọc gói trong **một dòng** (inline), không cần card form riêng. Có thể thêm 2–3 nút nhanh: "Hôm nay", "Tuần này", "Tháng này" → set sẵn date_from/date_to và submit.

- **Ấn tượng:** Vùng lọc **gọn**, nội dung chính là bảng đơn; thao tác lặp (đổi khoảng ngày) nhanh hơn.

---

### 3. Phong cách: Bảng đơn — Cột "Hệ số" là tín hiệu màu

**Ý tưởng:** Cột Hệ số không chỉ là số: **nền hoặc viền trái** theo ngưỡng (ví dụ: &lt; 138 đỏ, 138–150 vàng, &gt; 150 xanh). Cả dòng có thể có viền trái màu tương ứng (đã có `status-pass/fail/pending` — có thể tăng cường bằng background nhạt theo từng trạng thái).

- **Ấn tượng:** **Quét mắt** là thấy đơn nào "nguy cơ", đơn nào "sạch". Giảm đọc chữ, tăng tốc ra quyết định.

---

### 4. Tương tác: Click hàng = Chi tiết bên cạnh (split view) hoặc modal rõ ràng

**Ý tưởng:** Giữ modal chi tiết nhưng: (1) Khi mở modal — focus trap, đóng bằng Esc; (2) Tiêu đề modal có breadcrumb nhỏ *"DHB &gt; [Mã ĐH]"*; (3) Bảng dòng đơn trong modal: cột "Giá QĐ" có icon ✓/✗ (đạt/chưa đạt) rõ ràng, số lệch có thể màu đỏ.  
*Tuỳ chọn nâng cao:* Trên desktop rộng, có thể thử **split view**: bảng bên trái, chi tiết đơn chọn bên phải (panel cố định) — giảm đóng/mở modal liên tục.

- **Ấn tượng:** Xem chi tiết **thoải mái**, không bị kẹt trong popup nhỏ; nút Duyệt luôn trong tầm tay (trong modal footer hoặc trên hàng).

---

### 5. Tương tác: Duyệt xong — Toast + cập nhật tại chỗ (không reload toàn trang)

**Ý tưởng:** Sau khi bấm Duyệt thành công: (1) Toast *"Đã duyệt đơn [Mã]"*; (2) Nếu dùng htmx/partial: **chỉ cập nhật hàng đó** (đổi badge "Tự duyệt" hoặc ẩn hàng) thay vì `location.reload()`. Nếu chưa dùng partial: ít nhất toast + reload mượt (scroll giữ vị trí cũ nếu có thể).

- **Ấn tượng:** **Phản hồi tức thì**; không bị "nháy" cả trang, cảm giác app hiện đại.

---

### 6. Phong cách: Nút "Duyệt" và trạng thái — Rõ ràng không nhầm

**Ý tưởng:** Nút "Duyệt" chỉ hiện khi user thuộc `approver_id` và đơn Passed; các trường hợp còn lại dùng **badge** (Tự duyệt, Lỗi, Chờ xử lý) với màu nhất quán. Có thể thêm tooltip ngắn: "Bạn có quyền duyệt đơn này" / "Đơn đã tự duyệt (DTK &lt; 100M)".

- **Ấn tượng:** Người dùng **không bấm nhầm** và hiểu tại sao một số đơn không có nút Duyệt.

---

### 7. Empty state

**Ý tưởng:** Khi không có đơn: icon hòm thư trống hoặc checklist + *"Không có đơn hàng trong khoảng ngày đã chọn"* + gợi ý *"Thử mở rộng khoảng ngày hoặc bỏ bớt từ khóa tìm kiếm"*.

- **Ấn tượng:** Trống có **ý nghĩa**, không giống lỗi.

---

## C. SALES DASHBOARD (Báo Cáo Hiệu Suất Bán Hàng)

*Hiện tại: 3 KPI cards (Mục tiêu, YTD, Đơn chờ giao) + bảng từng nhân viên với progress bar YTD, click row → sales_detail.*

### 1. Kiến trúc: "Một dòng tổng quan năm" — Hero strip

**Ý tưởng:** Ngay dưới page title, một dải ngắn:  
*"Năm {{ current_year }}: Mục tiêu X tỷ · Đã đạt Y tỷ (Z%) · Còn Z đơn chờ giao"*  
Z% = (Y/X)*100; có thể dùng progress bar mini (chỉ một đoạn ngắn) trong strip.

- **Ấn tượng:** **Một câu đọc xong** là biết tình hình cả năm; sau đó mới đi sâu bảng từng NV. Cảm giác "cockpit" rõ.

---

### 2. Kiến trúc: 3 KPI cards — Số lớn, có "nhịp"

**Ý tưởng:** Mỗi card: (1) **Số lớn** (đã có) — có thể tăng size nhẹ, font-weight 800; (2) **Viền trái màu** (đã có icon-box) — thống nhất: Mục tiêu = xanh lá, YTD = primary, Chờ giao = đỏ/cảnh báo; (3) **Hover**: nâng nhẹ (translateY -4px), shadow đậm hơn; (4) Tuỳ chọn: dưới số có dòng nhỏ *"So với tháng trước: +X%"* nếu sau này có data.

- **Ấn tượng:** KPI **đập vào mắt**, không lẫn với bảng; cảm giác "sống" khi hover.

---

### 3. Phong cách: Bảng NV — Progress bar là "câu chuyện"

**Ý tưởng:** Cột "Thực Đạt YTD" không chỉ là thanh %: (1) **Màu** theo ngưỡng (đạt &gt;= 100%: xanh; 70–99%: primary; &lt; 70%: cam/đỏ nhạt); (2) Số tiền **trong** thanh (đã có) — đảm bảo contrast (chữ trắng khi nền đậm); (3) Có thể thêm **tooltip** hover: "Đạt X% mục tiêu · Còn Y tỷ đến chỉ tiêu".

- **Ấn tượng:** Mỗi hàng **kể nhanh** câu chuyện: đạt hay chưa, còn bao xa. Giảm tính toán trong đầu.

---

### 4. Tương tác: Hàng = Card nhỏ (trên mobile) hoặc row rõ ràng (desktop)

**Ý tưởng:** Trên desktop: hover hàng có **viền trái màu primary** hoặc nền nhạt; click cả hàng → chuyển `/sales_detail/{{ row.EmployeeID }}` (đã có). Trên mobile: có thể chuyển mỗi hàng thành **card** (avatar + tên + 3 số: Mục tiêu, YTD, PO Tồn) + nút "Xem chi tiết".

- **Ấn tượng:** **Nhất quán** giữa desktop và mobile; luôn rõ "đây là một nhân viên, click để xem thêm".

---

### 5. Tương tác: Sắp xếp nhanh (tuỳ chọn)

**Ý tưởng:** Header cột "Thực Đạt YTD" hoặc "PO Tồn" có thể click để **sort** (tăng dần/giảm dần) — client-side sort với data đã có, hoặc link query param để server sort. Ít nhất: "Xem top 5 đạt chỉ tiêu" / "Xem đơn chờ giao nhiều nhất" dạng tab hoặc nút lọc nhanh.

- **Ấn tượng:** Người dùng **tự tìm** góc nhìn (ai đạt, ai còn nợ nhiều) mà không cần scroll dài.

---

### 6. Phong cách: Cột "Chi tiết" — Chevron có động lực

**Ý tưởng:** Icon chevron-right (đã có) khi hover hàng: **dịch nhẹ sang phải** (translateX 4px) hoặc đổi màu primary. Gợi ý "bấm vào đây hoặc cả hàng để xem".

- **Ấn tượng:** **Affordance** rõ — "đây là nút đi sâu".

---

### 7. Empty state

**Ý tưởng:** Nếu không có `summary`: icon nhóm người + *"Chưa có dữ liệu hiệu suất cho năm này"* + link "Về Portal" hoặc "Xem báo cáo khác".

- **Ấn tượng:** Trống có **giải thích**, không gây hoang mang.

---

## D. GỢI Ý ƯU TIÊN TRIỂN KHAI

| Trang | Ý tưởng | Effort | Ấn tượng |
|-------|--------|--------|----------|
| **Sales Lookup** | Context strip ("Đang xem: N mặt hàng · Khách: ...") | Thấp | Cao |
| **Sales Lookup** | Form gọn một dòng (command bar) | Trung bình | Cao |
| **Sales Lookup** | Lịch sử gộp 1 card + 2 tab | Trung bình | Trung bình |
| **Sales Lookup** | Tra nhanh: toast + loading state nút | Thấp | Trung bình |
| **Sales Order Approval** | Funnel strip (Tổng / Tự duyệt / Chờ / Lỗi) | Thấp | Cao |
| **Sales Order Approval** | Filter một dòng + nút "Hôm nay", "Tuần này" | Thấp | Trung bình |
| **Sales Order Approval** | Duyệt xong: toast + cập nhật hàng (không reload) | Trung bình | Cao |
| **Sales Order Approval** | Hệ số & trạng thái: màu viền/background rõ | Thấp | Trung bình |
| **Sales Dashboard** | Hero strip một dòng tổng quan năm | Thấp | Cao |
| **Sales Dashboard** | KPI cards hover nâng + màu viền nhất quán | Thấp | Trung bình |
| **Sales Dashboard** | Progress bar màu theo % đạt (xanh/primary/đỏ) | Thấp | Cao |
| **Sales Dashboard** | Hàng: viền trái hover + chevron động | Thấp | Trung bình |

---

## E. TÓM TẮT BẢN SẮC CHUNG CHO 3 TRANG

- **Sales Lookup:** "Tra cứu như search" — một thanh lệnh, kết quả có thứ bậc (Tồn & Giá là hero), lịch sử gọn trong tab.
- **Sales Order Approval:** "Pipeline duyệt trong một dòng" — funnel strip + bảng đơn màu theo trạng thái, duyệt xong phản hồi ngay không reload.
- **Sales Dashboard:** "Một câu biết cả năm" — hero strip tổng quan + KPI số lớn có nhịp + bảng NV với progress bar kể chuyện đạt/chưa đạt.

*Cả ba đều hướng tới: **ít scroll, ít click, nhiều thông tin trong một lần nhìn** — tạo ấn tượng chuyên nghiệp và đáng nhớ.*
