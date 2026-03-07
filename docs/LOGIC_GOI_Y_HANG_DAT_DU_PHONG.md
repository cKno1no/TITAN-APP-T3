# Rà soát: Logic tính toán Gợi ý Hàng đặt Dự phòng

## Tổng quan luồng dữ liệu

| Màn hình / Tính năng        | Service / Blueprint        | Stored Procedure (SP)        | Bảng/View ERP chính |
|-----------------------------|----------------------------|------------------------------|----------------------|
| **Portal (widget Gợi ý dự phòng)** | `portal_service.py`        | `sp_GetPortalReplenishment`  | DTCL, CRM_TON KHO BACK ORDER, VELOCITY_SKU_* |
| **Dự phòng Tổng thể**       | `lookup_bp` + `db_manager` | `sp_GetTotalReplenishmentNeeds` | CRM_TON KHO BACK ORDER, VELOCITY_SKU_GROUP |
| **Dự phòng theo Khách hàng**| `lookup_bp` + `db_manager` | `sp_GetCustomerReplenishmentSuggest` | CRM_TON KHO BACK ORDER, VELOCITY_SKU_* |
| **Chi tiết nhóm hàng**      | `lookup_bp` + `db_manager` | `sp_GetReplenishmentGroupDetails` | CRM_TON KHO BACK ORDER |
| **Chatbot (check_replenishment)** | `chatbot_service` → `lookup_service` | `sp_GetCustomerReplenishmentSuggest` | Giống Dự phòng theo KH |

---

## 1. Config (SP được dùng)

**File:** `config.py`

| Hằng số              | SP (ERP)                          | Ghi chú |
|----------------------|------------------------------------|---------|
| `SP_REPLENISH_PORTAL`| `dbo.sp_GetPortalReplenishment`    | Widget trang chủ Portal |
| `SP_REPLENISH_TOTAL` | `dbo.sp_GetTotalReplenishmentNeeds`| Báo cáo dự phòng tổng thể |
| `SP_REPLENISH_GROUP` | `dbo.sp_GetReplenishmentGroupDetails` | Chi tiết từng nhóm hàng (Varchar05) |
| `SP_CROSS_SELL_GAP`  | `dbo.sp_GetCustomerReplenishmentSuggest` | Theo 1 khách hàng + Chatbot |

---

## 2. Bảng / View ERP và cột liên quan

### 2.1. `[dbo].[DTCL]` (Doanh thu / Chỉ tiêu)

- **Dùng trong:** `sp_GetPortalReplenishment` (bước 1 – lọc KH VIP).
- **Cột dùng:** `[MA KH]`, `[TEN kh]`, `[Nam]`, `[PHU TRACH DS]`, `[DK]`.
- **Logic:** Chỉ lấy KH có `[DK] > 300_000_000` (doanh số đăng ký > 300tr) và `[PHU TRACH DS] = @UserCode`, `[Nam] = @Year`.

### 2.2. `[OMEGA_STDD].[dbo].[CRM_TON KHO BACK ORDER]`

- **Dùng trong:** Tất cả 4 SP (tồn + hàng đang về).
- **Cột dùng:** `Varchar05` (mã nhóm hàng), `I01ID`, `I02ID`, `Ton` (tồn), `con` (đang về), `InventoryID`, `InventoryName`.
- **Logic:**  
  - Lọc `I01ID IN ('A', 'B', 'D')`.  
  - Trong Portal SP: bỏ nhóm có `I02ID` chứa 'X' hoặc Null.  
  - CTE `StockStatus`: `GROUP BY Varchar05` → `CurrentStock = SUM(Ton)`, `IncomingStock = SUM(con)`.

### 2.3. `dbo.VELOCITY_SKU_CUSTOMER`

- **Dùng trong:** `sp_GetPortalReplenishment`, `sp_GetCustomerReplenishmentSuggest`.
- **Cột dùng:** `Varchar05`, `ObjectID` (mã KH), `CustomerMonthlyVelocity`, `Flag`.
- **Logic:** Tốc độ tiêu thụ theo SKU theo từng khách; lọc `Flag = 'Recurring'` và `CustomerMonthlyVelocity > 0`.

### 2.4. `dbo.VELOCITY_SKU_GROUP`

- **Dùng trong:** Cả 4 SP (để có ROP / LeadTime).
- **Cột dùng:** `Varchar05`, `LeadTime_Days`, và trong Total SP có `ROP`, `TotalMonthlyVelocity`.
- **Logic:**  
  - **ROP (Reorder Point):** nhu cầu trong thời gian lead time (velocity/30.4 * LeadTime_Days).  
  - **Gợi ý lượng đặt:** `QuantitySuggestion = NhuCauTrongLeadTime - (CurrentStock + IncomingStock)` (trong Portal/Total/Customer tùy từng SP).

---

## 3. Công thức tính gợi ý (chung)

- **Nhu cầu trong lead time:**  
  `NhuCauTrongLeadTime = (CustomerMonthlyVelocity / 30.4) * LeadTime_Days`  
  (hoặc dùng ROP/TotalMonthlyVelocity ở báo cáo tổng thể).
- **Lượng thiếu / gợi ý đặt:**  
  `QuantitySuggestion = NhuCauTrongLeadTime - (CurrentStock + IncomingStock)`  
  với `CurrentStock = SUM(Ton)`, `IncomingStock = SUM(con)` từ `CRM_TON KHO BACK ORDER` theo `Varchar05`.
- **Làm tròn ROP (một số SP):** Nếu ROP ≥ 10 thì làm tròn lên bội 10: `CEILING(ROP/10)*10`.

---

## 4. Từng Stored Procedure chi tiết

### 4.1. `sp_GetPortalReplenishment` (@UserCode, @Year)

- **Bảng/View:** `DTCL`, `CRM_TON KHO BACK ORDER`, `VELOCITY_SKU_CUSTOMER`, `VELOCITY_SKU_GROUP`.
- **Bước 1:** Lấy KH VIP vào `#VipCustomers`: `DTCL` với `DK > 300000000`, `PHU TRACH DS = @UserCode`, `Nam = @Year`.
- **Bước 2:** CTE `StockStatus` từ `CRM_TON KHO BACK ORDER`: `I01ID IN ('A','B','D')`, `I02ID NOT LIKE '%X%'`, `I02ID IS NOT NULL`, group theo `Varchar05` → CurrentStock, IncomingStock.
- **Bước 3:** Join `VELOCITY_SKU_CUSTOMER` với `#VipCustomers`, `VELOCITY_SKU_GROUP`, `StockStatus`; lọc `Flag = 'Recurring'`, velocity > 0, và **QuantitySuggestion > 2**; `TOP 20`, sort theo QuantitySuggestion DESC.
- **Output cột:** `InventoryItemID`, `ItemName`, `QuantitySuggestion`, `CustomerID`, `CustomerName`.

### 4.2. `sp_GetTotalReplenishmentNeeds` (không tham số)

- **Bảng/View:** `CRM_TON KHO BACK ORDER`, `VELOCITY_SKU_GROUP` (không theo KH).
- **CTE StockStatus:** Giống lọc I01ID, group theo Varchar05.
- **Output:** NhomHang, Deficit_Group (1= cần đặt, 2= không), NganhHang_I02ID, LuongThieuDu, DiemTaiDatROP, TonBO, TieuHaoThang, TonKhoHienTai, HangDangVe, ROP_Goc.
- **Sắp xếp:** Deficit_Group, NganhHang_I02ID, NhomHang.

### 4.3. `sp_GetCustomerReplenishmentSuggest` (@ObjectID = mã KH)

- **Bảng/View:** `CRM_TON KHO BACK ORDER`, `VELOCITY_SKU_CUSTOMER`, `VELOCITY_SKU_GROUP`.
- **CTE StockStatus:** I01ID IN ('A','B','D'), group Varchar05.
- **Join:** VELOCITY_SKU_CUSTOMER (ObjectID = @ObjectID), VELOCITY_SKU_GROUP, StockStatus.
- **Output:** NhomHang, NhuCauTrongLeadTime_Goc, LuongThieuDu, DiemTaiDatROP, TonBO, TieuHaoThang, Deficit_Group, NganhHang_I02ID, TonKhoHienTai, HangDangVe, LeadTime_Days.
- **Sắp xếp:** Deficit_Group, NganhHang_I02ID, NhomHang.

### 4.4. `sp_GetReplenishmentGroupDetails` (@Varchar05 = mã nhóm)

- **Bảng/View:** Chỉ `CRM_TON KHO BACK ORDER`.
- **Lọc:** `Varchar05 = @Varchar05`, `I01ID IN ('A','B','D')`.
- **Output:** InventoryID, InventoryName, TonKhoHienTai, HangDangVe.

---

## 5. File HTML / Service thể hiện

### 5.1. Portal (trang chủ) – Widget “Gợi ý dự phòng”

| Thành phần   | File / Service |
|-------------|-----------------|
| **Service** | `services/portal_service.py` – trong `get_dashboard_data()`: gọi `SP_REPLENISH_PORTAL` (`sp_GetPortalReplenishment`) với `(user_code, current_year)`; gom nhóm theo KH → `data['urgent_replenish']`. |
| **Template**| `templates/portal_dashboard.html`: khối “Giao Hàng & Tồn Kho” hiển thị `dashboard_data.urgent_replenish`; modal `#modalReplenish` in bảng theo nhóm KH; link “Tới trang Tồn kho dự phòng” → `lookup_bp.customer_replenishment_dashboard`. |
| **Blueprint**| Portal dùng `portal_bp`; data do `portal_service.get_dashboard_data()` cung cấp. |

### 5.2. Dự phòng Tổng thể

| Thành phần   | File |
|-------------|------|
| **Route**   | `blueprints/lookup_bp.py`: `@lookup_bp.route('/total_replenishment')` → `total_replenishment_dashboard()`. |
| **Logic**   | `db_manager.execute_sp_multi(config.SP_REPLENISH_TOTAL, None)` → `alert_list`. |
| **Template**| `templates/total_replenishment.html`: DataTable `#replenishmentTable` với `alert_list`; chi tiết nhóm gọi API `GET /sales/api/replenishment_details/<group_code>` (SP_REPLENISH_GROUP). |
| **Export**  | `export_total_replenishment` (stub, chưa xuất Excel thật). |

### 5.3. Dự phòng theo Khách hàng

| Thành phần   | File |
|-------------|------|
| **Route**   | `lookup_bp`: `@lookup_bp.route('/customer_replenishment')` → `customer_replenishment_dashboard()`. |
| **Template**| `templates/customer_replenishment.html`: chọn KH → gọi `GET /sales/api/customer_replenishment/<customer_id>`; trả về từ `SP_CROSS_SELL_GAP`; click dòng → `GET /sales/api/replenishment_details/<group_code>`. |
| **API**     | `api_get_customer_replenishment_data(customer_id)` và `api_get_replenishment_details(group_code)` trong `lookup_bp.py`. |

### 5.4. Chatbot – “Kiểm tra dự phòng”

| Thành phần   | File |
|-------------|------|
| **Service** | `services/chatbot_service.py`: tool `check_replenishment` → `_wrapper_replenishment` → `_handle_replenishment_check_final()` gọi `lookup_service.get_replenishment_needs(customer_id)`. |
| **Lookup**  | `services/sales_lookup_service.py`: `get_replenishment_needs(customer_id)` gọi `execute_sp_multi(config.SP_CROSS_SELL_GAP, (customer_id,))` → cùng SP `sp_GetCustomerReplenishmentSuggest`. |

---

## 6. Tóm tắt bảng/cột ERP và SP

| Nguồn dữ liệu (ERP)           | Cột chính dùng | Vai trò |
|------------------------------|----------------|---------|
| **DTCL**                     | MA KH, TEN kh, Nam, PHU TRACH DS, DK | Lọc KH VIP (Portal). |
| **CRM_TON KHO BACK ORDER**   | Varchar05, I01ID, I02ID, Ton, con, InventoryID, InventoryName | Tồn hiện tại + hàng đang về theo nhóm/mã hàng. |
| **VELOCITY_SKU_CUSTOMER**    | Varchar05, ObjectID, CustomerMonthlyVelocity, Flag | Tốc độ tiêu thụ theo KH + SKU. |
| **VELOCITY_SKU_GROUP**       | Varchar05, LeadTime_Days, ROP, TotalMonthlyVelocity | Lead time và ROP theo nhóm. |

| SP | Tham số | Bảng/View chính |
|----|--------|------------------|
| **sp_GetPortalReplenishment** | UserCode, Year | DTCL, CRM_TON KHO BACK ORDER, VELOCITY_SKU_CUSTOMER, VELOCITY_SKU_GROUP |
| **sp_GetTotalReplenishmentNeeds** | — | CRM_TON KHO BACK ORDER, VELOCITY_SKU_GROUP |
| **sp_GetCustomerReplenishmentSuggest** | ObjectID (mã KH) | CRM_TON KHO BACK ORDER, VELOCITY_SKU_CUSTOMER, VELOCITY_SKU_GROUP |
| **sp_GetReplenishmentGroupDetails** | Varchar05 (nhóm hàng) | CRM_TON KHO BACK ORDER |

---

*Tài liệu rà soát logic gợi ý hàng đặt dự phòng – bảng/cột ERP, SP và các file HTML, service thể hiện.*
