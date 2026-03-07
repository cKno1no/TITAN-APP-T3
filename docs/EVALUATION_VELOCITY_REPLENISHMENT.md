# Đánh giá logic Velocity & Replenishment — Góc nhìn chuyên gia & vận hành

Tài liệu đánh giá **logic tính tốc độ tiêu thụ (velocity)** và **gợi ý dự phòng (replenishment)** cho mã hàng/nhóm hàng mà app đang sử dụng, về **tính logic** và **cấu trúc dữ liệu**.

---

## 1. Tổng quan luồng dữ liệu

```
[GT9000 - Phiếu giao dịch bán] 
        → sp_CalculateAllSalesVelocity (Job định kỳ)
        → VELOCITY_SKU_CUSTOMER (velocity theo KH + nhóm hàng)
        → VELOCITY_SKU_GROUP (velocity tổng nhóm + ROP)
        ↓
[CRM_TON KHO BACK ORDER - Tồn + Đang về]  (theo Varchar05 hoặc InventoryID)
        ↓
Replenishment: LuongThieuDu = NhuCauTrongLeadTime - (Ton + HangDangVe)
        → sp_GetTotalReplenishmentNeeds / sp_GetCustomerReplenishmentSuggest / sp_GetPortalReplenishment
```

- **Velocity** = tốc độ tiêu thụ (số lượng / tháng), tính từ lịch sử bán.
- **ROP** = Reorder Point = nhu cầu trong thời gian lead time + safety stock.
- **Gợi ý đặt thêm** = phần thiếu so với ROP (hoặc so với nhu cầu trong lead time đối với từng KH).

---

## 2. Đánh giá logic Velocity

### 2.1 Nguồn dữ liệu bán hàng (GT9000)

- **Cách dùng:** Lấy giao dịch từ `[OMEGA_STDD].[dbo].[GT9000]` với:
  - `CreditAccountID LIKE '5%'` → coi là giao dịch bán (doanh thu).
  - `Quantity > 0`, `VoucherDate` trong 48 tháng.
  - Join `IT1302` lấy `Varchar05` (nhóm hàng), lọc `I01ID IN ('A','B','D')`.

**Ưu điểm:**

- Dùng sổ cái (GT9000) thống nhất với kế toán, có thể đối chiếu với báo cáo tài chính.
- 48 tháng đủ dài để có chuỗi lịch sử ổn định cho nhóm hàng bán đều.

**Lưu ý / Rủi ro:**

- **GT9000 thường ghi nhận theo “dòng giao dịch kế toán”** (tài khoản Nợ/Có, số tiền, có thể có số lượng). Cần xác nhận rằng:
  - Cột `Quantity` trong GT9000 thực sự là **số lượng xuất bán** (đơn vị bán), không phải số lượng theo đơn vị khác (quy đổi, đơn vị kho khác).
- Nếu một lần xuất bán được ghi nhiều dòng (ví dụ từng kho, từng tài khoản), có thể **trùng lượng** nếu chỉ SUM(Quantity) mà không gộp theo chứng từ/dòng nghiệp vụ. Nên rà soát mẫu dữ liệu GT9000 (một vài voucher bán) so với phiếu xuất kho thực tế.
- **CreditAccountID LIKE '5%'** đúng với chuẩn tài khoản doanh thu 5xx; cần thống nhất với kế toán là mọi bán hàng đều vào 5xx và không có bán hàng qua tài khoản khác (ví dụ 6xx, 7xx).

**Kết luận:** Logic nguồn dữ liệu **hợp lý** nếu GT9000 đại diện đúng “lượng bán theo thời gian”. Nên có **tài liệu xác nhận** (hoặc kiểm tra mẫu) để tránh double-count hoặc sai đơn vị.

---

### 2.2 Công thức Velocity theo khách hàng (60/40)

- **CustomerMonthlyVelocity** (cho từng cặp Varchar05 + ObjectID):
  - **Project:** PurchaseCount = 1 → velocity = 0 (hợp lý: không dự báo lặp lại).
  - **New:** ≤ 3 tháng và < 2 lần mua → không thấy công thức riêng trong SP; trong INSERT dùng cùng công thức 60/40 với Recurring. Cần kiểm tra: nếu “New” cũng được gán 60/40 thì vẫn chấp nhận được nhưng có thể quá lạc quan cho khách mới.
  - **Recurring:**  
    `(Qty_Last24M / 24) * 0.6 + (Qty_Prev24M / 24) * 0.4`  
    → **đơn vị: số lượng / tháng**.

**Ưu điểm:**

- **Trọng số 60/40** cho 24 tháng gần / 24 tháng xa là cách làm chuẩn trong dự báo: ưu tiên xu hướng gần, vẫn giữ ổn định khi có đủ lịch sử.
- Chỉ dùng **Recurring** khi tính **TotalMonthlyVelocity** nhóm và ROP → tránh nhiễu từ hàng dự án / khách thử một lần.

**Gợi ý cải tiến (không bắt buộc):**

- Có thể thử **giảm cửa sổ** (ví dụ 12+12 tháng) cho ngành hàng thay đổi nhanh, hoặc **tuning 70/30** nếu thực tế gần đây quan trọng hơn.
- “New” nếu dùng trong gợi ý dự phòng nên có chính sách rõ: hoặc velocity = 0, hoặc hệ số giảm so với Recurring để tránh gợi ý quá lớn cho khách chưa ổn định.

---

### 2.3 Velocity cấp nhóm (Varchar05) và ROP

- **TotalMonthlyVelocity** = SUM(CustomerMonthlyVelocity) với **Flag = 'Recurring'**.
- **LeadTime_Days** = AVG(Amount04) từ IT1302 theo Varchar05.  
- **SafetyStock_Qty** = AVG(Amount05).  
- **ROP** = `(TotalMonthlyVelocity / 30.4) * LeadTime_Days + SafetyStock_Qty`.

**Ưu điểm:**

- Công thức ROP **chuẩn**: Nhu cầu trong lead time + safety stock. 30.4 ≈ ngày trung bình/tháng, dùng ổn.
- Velocity nhóm = tổng velocity khách Recurring → phản ánh “tổng nhu cầu thị trường” cho nhóm hàng đó trong phạm vi dữ liệu của công ty.

**Lưu ý:**

- **LeadTime/SafetyStock dùng AVG theo Varchar05:** Trong nhóm có thể có nhiều mã (InventoryID) với lead time và safety stock khác nhau. Hiện tại mọi mã trong cùng Varchar05 dùng chung một ROP nhóm. Ở **sp_GetInventoryRiskContext** (PO/Risk) bạn đã dùng **LeadTime/SafetyStock theo từng InventoryID** (Amount04, Amount05 của IT1302) và chỉ velocity lấy từ nhóm — cách đó **chính xác hơn** cho từng mã. Với báo cáo replenishment **theo nhóm** (Varchar05) thì dùng ROP nhóm là chấp nhận được.
- **Varchar05:** Cần đảm bảo master data (IT1302) gán Varchar05 nhất quán; nếu một nhóm logic bị tách nhiều Varchar05 thì velocity và ROP bị chia nhỏ, gợi ý có thể “nhỏ hơn thực tế” khi tổng hợp.

---

## 3. Đánh giá logic Replenishment (gợi ý đặt hàng)

### 3.1 Tồn kho & đang về (CRM_TON KHO BACK ORDER)

- Tồn hiện tại và đang về lấy từ view **CRM_TON KHO BACK ORDER** (Ton, con), lọc I01ID IN ('A','B','D').
- **Tổng thể / Khách hàng:** Gộp theo **Varchar05** → CurrentStock, IncomingStock.
- **Risk context (PO):** Gộp theo **InventoryID** → TonKho, HangDangVe từng mã.

**Đánh giá:**

- Cấu trúc **nhất quán**: Replenishment nhóm dùng tồn theo nhóm; Risk/PO dùng tồn theo mã. Phù hợp với từng use case.
- Điều kiện **ổn** nếu view đã chuẩn hóa Ton = tồn thực tế, con = đang về (đơn đã đặt chưa giao). Nên xác nhận với nghiệp vụ kho rằng view cập nhật đủ tần suất (realtime / EOD / batch) và không trùng lặp (một lượng không vừa Ton vừa con).

---

### 3.2 Công thức “Lượng thiếu / dư” và điểm đặt

**Tổng thể (sp_GetTotalReplenishmentNeeds):**

- `LuongThieuDu = ROP - (CurrentStock + IncomingStock)`.
- Điểm đặt (DiemTaiDatROP): làm tròn ROP, nếu ROP ≥ 10 thì làm tròn lên bội 10.

**Khách hàng (sp_GetCustomerReplenishmentSuggest):**

- Nhu cầu trong lead time: `(CustomerMonthlyVelocity / 30.4) * LeadTime_Days`.
- `LuongThieuDu = NhuCauTrongLeadTime - (CurrentStock + IncomingStock)`.
- Chỉ lấy **Flag = 'Recurring'** và **CustomerMonthlyVelocity > 0**.
- Điểm đặt: làm tròn tương tự theo nhu cầu trong lead time.

**Portal (sp_GetPortalReplenishment):**

- Cùng công thức “nhu cầu trong lead time − tồn”, lọc KH VIP (DS đăng ký > 300tr), chỉ gợi ý khi **QuantitySuggestion > 2**.

**Đánh giá:**

- **Logic nghiệp vụ đúng:** So sánh “cần bao nhiêu trong lead time” (hoặc ROP) với “đã có + sắp có”, phần dương là thiếu → cần đặt. Làm tròn bội 10 giúp dễ đặt lệnh trong thực tế.
- **Tổng thể dùng ROP**, **theo khách dùng nhu cầu trong lead time** là hợp lý: tổng thể theo “điểm đặt tổng” của nhóm; theo khách thì theo nhu cầu riêng của khách đó trong thời gian chờ giao.
- **Portal chỉ Recurring + velocity > 0 và suggestion > 2** tránh gợi ý nhiễu hoặc quá nhỏ.

---

## 4. Cấu trúc dữ liệu — Đã ổn chưa?

### 4.1 Điểm mạnh

| Thành phần | Đánh giá |
|------------|----------|
| **Tách bảng velocity (SKU_CUSTOMER / SKU_GROUP)** | Rõ ràng: cấp khách → cấp nhóm; dễ bảo trì và kiểm tra. |
| **Job tính velocity (TRUNCATE + INSERT)** | Dữ liệu velocity đồng bộ một phiên, tránh nửa cũ nửa mới. |
| **LeadTime/SafetyStock từ IT1302** | Tận dụng master data (Amount04, Amount05); Risk context dùng per-InventoryID đúng hướng. |
| **Lọc A, B, D thống nhất** | Replenishment và velocity chỉ với nhóm hàng dự phòng, tránh nhiễu nhóm khác. |

### 4.2 Điểm cần lưu ý / rủi ro

| Vấn đề | Mô tả | Gợi ý |
|--------|--------|--------|
| **Nguồn bán: GT9000 vs phiếu xuất** | GT9000 có thể không 1-1 với “lượng xuất bán” nếu có nhiều dòng/chủng loại giao dịch. | So sánh mẫu GT9000 với phiếu xuất kho (số lượng, voucher) cho vài kỳ; nếu khác thì cân nhắc nguồn khác (ví dụ view xuất kho) hoặc hệ số hiệu chỉnh. |
| **Cập nhật velocity theo chu kỳ** | Velocity thay đổi theo tháng nhưng bảng chỉ cập nhật khi chạy job. | Đảm bảo cron chạy đều (ví dụ hàng đêm); nếu cần “gần realtime” có thể cache/refresh theo ngày. |
| **Nhóm hàng (Varchar05)** | ROP và gợi ý phụ thuộc Varchar05. Sai hoặc tách nhóm không chuẩn → velocity và ROP lệch. | Rà soát master Varchar05; thống nhất quy tắc gán nhóm cho mã mới. |
| **Stock view** | Replenishment phụ thuộc view tồn. View chậm hoặc sai → gợi ý sai. | Xác nhận view cập nhật đúng chu kỳ và logic (kho, trạng thái đơn, loại tồn). |

---

## 5. Kết luận và khuyến nghị

### 5.1 Tính logic

- **Velocity (60/40, Recurring-only cho nhóm, đơn vị /tháng):** Hợp lý, phù hợp thực hành dự báo nhu cầu.
- **ROP = (Velocity/30.4)×LeadTime + SafetyStock:** Đúng công thức chuẩn.
- **Replenishment = NhuCauTrongLeadTime (hoặc ROP) − (Tồn + Đang về):** Đúng với mục tiêu “gợi ý lượng cần đặt”.
- **Phân tầng Project / New / Recurring:** Hợp lý; cần rõ cách dùng “New” trong từng báo cáo (hiện CustomerReplenishment chỉ Recurring + velocity > 0 là ổn).

### 5.2 Cấu trúc dữ liệu

- **Đã ổn** cho mục tiêu hiện tại: tách SKU_CUSTOMER / SKU_GROUP, dùng view tồn, LeadTime/SafetyStock từ master, lọc A/B/D thống nhất. Risk context dùng velocity nhóm + LeadTime/SafetyStock theo từng mã là hướng đúng.

### 5.3 Khuyến nghị vận hành / quản trị

1. **Xác nhận nguồn bán:** Kiểm tra mẫu GT9000 (voucher, Quantity, tài khoản 5%) so với phiếu xuất kho / báo cáo bán hàng; lập checklist “Velocity đại diện đúng lượng bán” để ký duyệt nghiệp vụ.
2. **Cron job velocity:** Đảm bảo `sp_CalculateAllSalesVelocity` chạy đều (ví dụ 1 lần/ngày sau khi đóng sổ), có monitoring và cảnh báo khi job lỗi.
3. **Tài liệu hóa:** Ghi rõ trong tài liệu vận hành: nguồn GT9000, ý nghĩa 60/40, cách dùng ROP và “nhu cầu trong lead time” theo từng báo cáo (Tổng thể / Khách hàng / Portal).
4. **Tuning (tùy chọn):** Sau khi chạy ổn định, so sánh gợi ý replenishment với quyết định đặt hàng thực tế (số đơn đặt, lượng) để điều chỉnh hệ số 60/40 hoặc ngưỡng (ví dụ suggestion > 2, làm tròn bội 10) nếu cần.

Tóm lại: **Logic velocity và replenishment hiện tại hợp lý và cấu trúc dữ liệu ổn** cho việc gợi ý dự phòng theo mã/nhóm hàng. Cần bổ sung **xác minh nguồn bán (GT9000)** và **vận hành ổn định job velocity** để kết quả đáng tin cậy trong dài hạn.
