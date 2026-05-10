# CHƯƠNG 4: CHẠY MÔ PHỎNG VÀ ĐÁNH GIÁ  
## Demo & Đánh giá hệ thống Smart Logistics

---

## 4.1. Kịch bản mô phỏng

### 4.1.1. Mục tiêu mô phỏng

Để kiểm chứng khả năng hoạt động của hệ thống trong bối cảnh gần với vận hành logistics thực tế, nhóm xây dựng một kịch bản mô phỏng giao hàng chặng cuối tại khu vực đô thị. Kịch bản này không chỉ dùng để kiểm tra các chức năng cơ bản như theo dõi vị trí, phân công shipper, gán đơn hàng, mà còn dùng để đánh giá khả năng phản ứng của hệ thống khi phát sinh các tình huống bất thường trong quá trình giao hàng.

Trong repo hiện tại, hệ thống Smart Logistics được triển khai dưới dạng một ứng dụng realtime gồm backend FastAPI, frontend React/Vite, MongoDB và WebSocket. Backend duy trì một simulation engine để mô phỏng đội shipper di chuyển trên bản đồ, đồng thời phát các sự kiện realtime cho frontend thông qua WebSocket. Frontend hiển thị bản đồ, trạng thái shipper, trạng thái đơn hàng, dashboard thống kê và một Auto Demo Panel để tự động chạy các bước kiểm thử chính.

Mục tiêu của kịch bản mô phỏng gồm:

- Kiểm tra khả năng mô phỏng nhiều shipper di chuyển đồng thời.
- Kiểm tra khả năng tìm shipper gần kho nhất.
- Kiểm tra luồng dispatch shipper về kho.
- Kiểm tra luồng gán đơn hàng giao đi từ kho đến khách hàng.
- Kiểm tra cập nhật trạng thái đơn hàng và shipper theo thời gian thực.
- Kiểm tra các tình huống ngoại lệ trong giao hàng.
- Kiểm tra khả năng broadcast sự kiện realtime đến frontend.
- Đánh giá mức độ hoàn thiện của các nhóm chức năng chính trong hệ thống.

---

### 4.1.2. Thiết lập mô phỏng

Trong hệ thống hiện tại, simulation engine khởi tạo danh sách shipper ảo và duy trì trạng thái vận hành của từng shipper. Theo phần mô tả trong backend, mục tiêu demo realtime hiện tại tập trung vào nhóm shipper mô phỏng, trong đó các shipper được cập nhật vị trí liên tục và được điều phối qua các trạng thái khác nhau.

Các thông số chính của kịch bản mô phỏng:

| Thành phần | Thiết lập trong demo |
|---|---|
| Khu vực mô phỏng | TP.HCM và các khu vực lân cận trên bản đồ |
| Kho trung tâm | Warehouse cố định tại tọa độ `lat=10.8051`, `lon=106.7144` |
| Số shipper mô phỏng | Simulation engine duy trì đội shipper ảo, demo frontend ưu tiên dispatch 3 shipper gần kho |
| Cập nhật vị trí | Realtime qua WebSocket |
| Giao tiếp frontend-backend | REST API + WebSocket |
| Cơ sở dữ liệu | MongoDB |
| Backend | FastAPI |
| Frontend | React + Vite + Leaflet |
| Loại ngoại lệ được demo | Traffic jam, heavy rain, vehicle breakdown, customer absent, lost connection |
| Cơ chế gán đơn | `/simulation/assign-delivery` |
| Cơ chế apply sự cố | `/simulation/incident/apply` |
| Cơ chế resolve sự cố | `/simulation/incident/resolve/{shipper_id}` |

Trong phiên bản demo ở repo, frontend có component `AutoDemoPanel.jsx` giúp tự động chạy toàn bộ kịch bản. Component này gọi các API theo thứ tự, cập nhật trạng thái từng bước trên giao diện và hiển thị giải thích trực tiếp cho người xem demo. Nhờ đó, người dùng không cần thao tác thủ công từng API nhưng vẫn quan sát được luồng nghiệp vụ.

---

### 4.1.3. Các giai đoạn mô phỏng

Quá trình mô phỏng được chia thành nhiều giai đoạn rõ ràng, phản ánh gần đúng quy trình giao hàng chặng cuối:

1. **Khởi tạo hệ thống**
   - Backend khởi động FastAPI app.
   - Kết nối MongoDB.
   - Khởi chạy simulation engine trong background.
   - WebSocket server sẵn sàng gửi dữ liệu realtime cho frontend.

2. **Load dữ liệu shipper**
   - Frontend gọi API lấy danh sách shipper.
   - Danh sách shipper được hiển thị trên bản đồ.
   - Người dùng hoặc Auto Demo có thể chọn một shipper để xem chi tiết.

3. **Bắt đầu mô phỏng**
   - Frontend gọi `/simulation/reset` để xoá trạng thái cũ.
   - Sau đó gọi `/simulation/start` để bắt đầu mô phỏng mới.
   - Simulation engine chuyển sang trạng thái hoạt động.

4. **Tìm shipper gần kho**
   - Frontend gọi `/simulation/nearest?top_n=3`.
   - Backend tính khoảng cách từ từng shipper đến warehouse.
   - Hệ thống trả về 3 shipper gần kho nhất.

5. **Dispatch shipper về kho**
   - Frontend gọi `/simulation/dispatch`.
   - Backend chuyển trạng thái các shipper được chọn sang hướng về warehouse.
   - Simulation engine cập nhật route và vị trí của shipper theo thời gian thực.
   - Khi shipper đến kho, backend broadcast event `shipper_arrived`.
   - Khi tất cả shipper được dispatch đến kho, backend broadcast event `all_arrived_at_warehouse`.

6. **Gán đơn giao hàng**
   - Frontend gọi `/simulation/assign-delivery`.
   - Mỗi shipper nhận một đơn hàng với địa chỉ đích cụ thể.
   - Trạng thái shipper chuyển sang `DELIVERING`.
   - Order được tạo và gán cho shipper.
   - Backend broadcast event `delivery_assigned`.

7. **Theo dõi giao hàng realtime**
   - Simulation engine cập nhật vị trí shipper theo route.
   - Backend gửi các bản tin realtime qua WebSocket.
   - Frontend cập nhật marker trên bản đồ, thông tin order, ETA và trạng thái shipper.

8. **Áp dụng tình huống ngoại lệ**
   - Frontend gọi `/simulation/incident/apply`.
   - Backend cập nhật trạng thái shipper theo loại sự cố.
   - Backend broadcast các event như `incident_applied`, `customer_notification`, `route_updated`.
   - Một số sự cố có thể được resolve bằng `/simulation/incident/resolve/{shipper_id}`.

9. **Hoàn tất giao hàng**
   - Khi shipper đến điểm giao, backend hoàn tất delivery.
   - Backend broadcast event `delivery_completed`.
   - Khi toàn bộ luồng kết thúc, hệ thống có thể broadcast `simulation_completed`.

---

### 4.1.4. Luồng demo tự động trong frontend

Trong repo hiện tại, file `frontend/src/components/AutoDemoPanel.jsx` triển khai một luồng demo tự động gồm 10 bước chính:

| Bước | Nội dung |
|---|---|
| 1 | Kiểm tra backend qua API dashboard overview |
| 2 | Load danh sách shipper lên bản đồ |
| 3 | Reset và bắt đầu simulation |
| 4 | Tìm 3 shipper gần warehouse nhất |
| 5 | Dispatch shipper về warehouse |
| 6 | Test Orders API |
| 7 | Gán random delivery orders cho shipper |
| 8 | Test nhiều loại incident |
| 9 | Chuyển sang dashboard thống kê realtime |
| 10 | Theo dõi đến khi orders hoàn tất và incidents đã được biểu diễn |

Luồng demo này phù hợp để trình bày toàn bộ pipeline từ backend đến frontend vì mỗi bước đều có API hoặc event realtime tương ứng. Người xem có thể quan sát:

- Marker shipper di chuyển trên bản đồ.
- Trạng thái shipper thay đổi qua từng phase.
- Order được gán cho shipper.
- Sự cố được áp dụng lên shipper.
- Dashboard cập nhật theo dữ liệu mới.
- Demo chỉ hoàn tất khi hệ thống đã chạy qua luồng nghiệp vụ chính.

---

### 4.1.5. Các API chính trong kịch bản mô phỏng

#### a. Kiểm tra backend

```http
GET /health
GET /dashboard/overview
GET /dashboard/fleet-stats
```

Các API này dùng để kiểm tra backend còn hoạt động, lấy số liệu tổng quan và cập nhật dashboard.

#### b. Quản lý shipper

```http
GET /shippers
GET /shippers/{shipper_id}
```

Frontend sử dụng các API này để load danh sách shipper và xem chi tiết từng shipper.

#### c. Điều phối mô phỏng

```http
POST /simulation/reset
POST /simulation/start
GET  /simulation/state
GET  /simulation/nearest?top_n=3
POST /simulation/dispatch
```

Nhóm API này tạo ra phần lõi của demo điều phối. Hệ thống reset trạng thái, bắt đầu simulation, chọn shipper gần kho và dispatch họ về warehouse.

#### d. Gán đơn hàng

```http
POST /simulation/assign-delivery
```

API này tạo đơn hàng mới và gán cho shipper đang chờ tại warehouse. Payload có dạng:

```json
{
  "shipper_id": "SHIPPER_ID",
  "dest_lat": 10.8214,
  "dest_lon": 106.6843,
  "destination_text": "District 1 - Random delivery",
  "items_count": 3
}
```

Sau khi gán thành công, backend broadcast event:

```json
{
  "type": "delivery_assigned",
  "shipper_id": "SHIPPER_ID",
  "order_id": "ORD-...",
  "dest_lat": 10.8214,
  "dest_lon": 106.6843
}
```

#### e. Xử lý sự cố

```http
POST /simulation/incident/apply
POST /simulation/incident/resolve/{shipper_id}
```

Ví dụ payload apply incident:

```json
{
  "shipper_id": "SHIPPER_ID",
  "incident_type": "HEAVY_RAIN",
  "rain_level": "HEAVY"
}
```

Các loại sự cố được hỗ trợ trong logic mô phỏng:

| Loại sự cố | Ý nghĩa |
|---|---|
| `TRAFFIC_JAM` | Kẹt xe, làm giảm tốc độ di chuyển |
| `HEAVY_RAIN` | Mưa lớn, làm tăng thời gian giao |
| `CUSTOMER_ABSENT` | Khách vắng, có thể retry hoặc tìm đơn phù hợp khác |
| `VEHICLE_BREAKDOWN` | Xe hỏng, cần xử lý hoặc thay shipper |
| `LOST_CONNECTION` | Mất tín hiệu GPS, shipper tạm thời offline |

---

## 4.2. Kết quả demo thực tế

### 4.2.1. Kết quả quan sát từ luồng realtime

Khi chạy demo, hệ thống thể hiện được một số kết quả chính:

1. **Frontend kết nối được backend**
   - API dashboard trả về dữ liệu tổng quan.
   - Trạng thái backend có thể kiểm tra qua health check.

2. **Danh sách shipper được load thành công**
   - Frontend gọi `/shippers`.
   - Marker shipper được hiển thị trên bản đồ.
   - Người dùng có thể chọn shipper để xem thông tin.

3. **Simulation có thể reset và start**
   - Khi gọi `/simulation/reset`, trạng thái cũ được xoá.
   - Khi gọi `/simulation/start`, simulation engine bắt đầu phát sinh cập nhật vị trí.

4. **Hệ thống tìm được shipper gần warehouse**
   - API `/simulation/nearest?top_n=3` trả về danh sách shipper gần kho.
   - Đây là bước quan trọng để tối ưu điều phối ban đầu.

5. **Dispatch shipper về warehouse**
   - Các shipper được chọn chuyển sang trạng thái đi về kho.
   - Vị trí được cập nhật realtime trên bản đồ.
   - Frontend nhận event khi shipper đến kho.

6. **Gán đơn hàng thành công**
   - Sau khi shipper đến warehouse, frontend gọi `/simulation/assign-delivery`.
   - Backend tạo order và gán cho shipper.
   - Trạng thái shipper chuyển sang giao hàng.
   - Frontend hiển thị thông tin order tương ứng.

7. **Xử lý sự cố trong quá trình giao**
   - Frontend apply các incident như kẹt xe, mưa lớn, hư xe, khách vắng.
   - Backend cập nhật trạng thái nội bộ của shipper.
   - WebSocket broadcast sự kiện để frontend phản ánh thay đổi.

8. **Dashboard realtime hoạt động**
   - Khi chuyển sang tab thống kê, dashboard đọc dữ liệu từ backend.
   - Các chỉ số fleet, shipper và order được cập nhật theo trạng thái hiện tại.

Như vậy, demo đã kiểm chứng được chuỗi nghiệp vụ từ lúc bắt đầu simulation đến khi dispatch, gán đơn, xử lý sự cố và theo dõi realtime.

---

### 4.2.2. Luồng xử lý GPS realtime

Backend có một service chính là `GPSService`, chịu trách nhiệm xử lý các bản tin GPS đi vào hệ thống. Luồng xử lý GPS được thiết kế theo 9 bước:

1. **Validate GPS data**
   - Kiểm tra `shipper_id`, `lat`, `lon`.

2. **Create tracking event**
   - Tạo bản ghi tracking event với thông tin vị trí, tốc độ, heading, ETA.

3. **Compute speed and heading**
   - Tính tốc độ di chuyển dựa trên vị trí trước đó.
   - Tính hướng di chuyển.

4. **Linear interpolation**
   - Làm mượt vị trí hiển thị bằng nội suy tuyến tính.

5. **Fetch active order and compute ETA**
   - Tìm đơn hàng active của shipper.
   - Tính ETA đến điểm giao.

6. **Save to MongoDB**
   - Lưu tracking event vào database theo dạng append-only.

7. **Cascade update**
   - Cập nhật trạng thái GPS của shipper.
   - Cập nhật ETA của order nếu có.

8. **WebSocket broadcast**
   - Gửi dữ liệu realtime cho frontend.

9. **Decision engine**
   - Kiểm tra các rule cảnh báo như delay hoặc idle.

Luồng này cho thấy hệ thống không chỉ hiển thị marker trên bản đồ, mà còn có pipeline xử lý dữ liệu tương đối đầy đủ, bao gồm tính tốc độ, tính hướng, tính ETA, lưu event và broadcast realtime.

---

### 4.2.3. WebSocket events quan trọng

Trong demo, backend dùng WebSocket endpoint:

```text
ws://localhost:8000/ws
```

Frontend nhận các loại event chính:

| Event | Ý nghĩa |
|---|---|
| `initial_state` | Trạng thái ban đầu khi frontend vừa kết nối |
| `bulk_gps_update` | Cập nhật vị trí nhiều shipper theo thời gian thực |
| `shipper_arrived` | Shipper được dispatch đã đến warehouse |
| `all_arrived_at_warehouse` | Tất cả shipper được dispatch đã đến warehouse |
| `delivery_assigned` | Order đã được gán cho shipper |
| `delivery_completed` | Shipper đã giao xong đơn |
| `simulation_completed` | Simulation hoàn tất |
| `incident_applied` | Incident được áp dụng trong simulation |
| `incident_resolved` | Incident đã được giải quyết |
| `customer_notification` | Thông báo delay hoặc sự cố cho khách hàng |
| `route_updated` | Route được cập nhật khi có tình huống cần reroute |

Các event này giúp frontend cập nhật giao diện mà không cần polling liên tục. Đây là điểm quan trọng của một hệ thống realtime.

---

### 4.2.4. Kết quả xử lý sự cố

Trong demo hiện tại, hệ thống có thể mô phỏng nhiều loại sự cố. Mỗi loại sự cố làm thay đổi trạng thái vận hành của shipper theo cách khác nhau.

#### a. Kẹt xe (`TRAFFIC_JAM`)

Khi apply sự cố kẹt xe, tốc độ di chuyển của shipper bị giảm. Điều này làm ETA tăng lên và có thể tạo ra cảnh báo delay. Hệ thống có thể broadcast event cập nhật route hoặc thông báo đến frontend.

#### b. Mưa lớn (`HEAVY_RAIN`)

Mưa lớn làm giảm tốc độ giao hàng theo mức độ mưa. Trong payload demo, `rain_level` có thể là `LIGHT`, `MEDIUM` hoặc `HEAVY`. Với mức `HEAVY`, thời gian giao dự kiến sẽ tăng rõ hơn.

#### c. Khách vắng (`CUSTOMER_ABSENT`)

Đây là tình huống phổ biến trong giao hàng thực tế. Khi khách vắng, hệ thống có thể tăng số lần retry hoặc đưa đơn vào trạng thái xử lý đặc biệt. Trong phần simulation engine, có logic liên quan đến retry khách vắng và danh sách đơn pending để hỗ trợ xử lý tiếp.

Trường hợp lý tưởng:

- Nếu còn đơn phù hợp gần vị trí hiện tại, shipper có thể tiếp tục nhận đơn khác.
- Nếu không còn đơn phù hợp, shipper có thể chuyển về trạng thái chờ hoặc idle.

#### d. Xe hỏng (`VEHICLE_BREAKDOWN`)

Khi xe hỏng, shipper không thể tiếp tục giao bình thường. Hệ thống đánh dấu incident có độ nghiêm trọng cao. Trong logic simulation, tình huống này có thể dẫn đến việc chờ xử lý hoặc điều phối shipper thay thế.

#### e. Mất kết nối (`LOST_CONNECTION`)

Khi mất kết nối, trạng thái tín hiệu của shipper chuyển sang offline. Đây là tình huống quan trọng vì trong thực tế GPS có thể bị mất do lỗi mạng, tắt thiết bị hoặc mất tín hiệu.

---

## 4.3. Phân tích kết quả và đối chiếu

### 4.3.1. Đánh giá theo test case

Dựa trên demo thực tế trong repo, có thể chia các test case chính như sau:

#### Test Case 1: Khởi động simulation thành công

**Input:**

```http
POST /simulation/reset
POST /simulation/start
```

**Kỳ vọng:**

- Simulation engine reset trạng thái cũ.
- Hệ thống chuyển sang phase mới.
- Frontend tiếp tục nhận GPS updates.

**Kết quả quan sát:**

- Auto Demo Panel có thể gọi reset và start.
- Các bước tiếp theo như tìm shipper gần kho và dispatch có thể thực hiện.

**Đánh giá:**

Test case đạt yêu cầu, chứng minh backend simulation có thể khởi động và phục vụ luồng realtime.

---

#### Test Case 2: Tìm shipper gần kho

**Input:**

```http
GET /simulation/nearest?top_n=3
```

**Kỳ vọng:**

- Backend trả về 3 shipper gần warehouse.
- Danh sách có `shipper_id` và thông tin khoảng cách.

**Kết quả quan sát:**

- Frontend nhận danh sách nearest shippers.
- Danh sách này được dùng trực tiếp cho bước dispatch.

**Đánh giá:**

Test case đạt yêu cầu, thể hiện hệ thống có thể chọn shipper tối ưu cho bước điều phối ban đầu.

---

#### Test Case 3: Dispatch shipper về warehouse

**Input:**

```http
POST /simulation/dispatch
```

Payload:

```json
{
  "shipper_ids": ["SHIPPER_1", "SHIPPER_2", "SHIPPER_3"]
}
```

**Kỳ vọng:**

- Shipper chuyển trạng thái sang hướng về warehouse.
- Frontend thấy shipper di chuyển trên bản đồ.
- Khi đến kho, backend phát event `shipper_arrived`.

**Kết quả quan sát:**

- Luồng dispatch được Auto Demo gọi sau khi chọn nearest shippers.
- Backend có WebSocket event để thông báo shipper đến warehouse.

**Đánh giá:**

Test case đạt yêu cầu đối với phần điều phối mô phỏng.

---

#### Test Case 4: Gán đơn giao hàng

**Input:**

```http
POST /simulation/assign-delivery
```

Payload:

```json
{
  "shipper_id": "SHIPPER_ID",
  "dest_lat": 10.8214,
  "dest_lon": 106.6843,
  "destination_text": "District 1 - Random delivery #1",
  "items_count": 3
}
```

**Kỳ vọng:**

- Backend tạo order.
- Gán order cho shipper.
- Shipper chuyển trạng thái giao hàng.
- Frontend nhận event `delivery_assigned`.
- UI hiển thị thông tin đơn hàng.

**Kết quả quan sát:**

- Auto Demo đã có bước gán random delivery orders cho shipper.
- Các destination được chọn trong khu vực TP.HCM.
- Sau khi gán, demo tiếp tục sang bước test incidents.

**Đánh giá:**

Test case đạt yêu cầu về luồng gán đơn cơ bản.

---

#### Test Case 5: Apply incident

**Input:**

```http
POST /simulation/incident/apply
```

Payload ví dụ:

```json
{
  "shipper_id": "SHIPPER_ID",
  "incident_type": "HEAVY_RAIN",
  "rain_level": "HEAVY"
}
```

**Kỳ vọng:**

- Backend cập nhật trạng thái incident của shipper.
- Frontend nhận event thông báo incident.
- Nếu incident ảnh hưởng route hoặc ETA, UI phản ánh thay đổi.

**Kết quả quan sát:**

- Auto Demo test nhiều incident type.
- Một số incident được resolve lại để kiểm tra flow phục hồi.

**Đánh giá:**

Test case đạt yêu cầu đối với phần mô phỏng tình huống bất thường.

---

#### Test Case 6: Resolve incident

**Input:**

```http
POST /simulation/incident/resolve/{shipper_id}
```

**Kỳ vọng:**

- Incident của shipper được xoá hoặc đánh dấu resolved.
- Shipper phục hồi trạng thái vận hành nếu có thể.
- Frontend nhận event `incident_resolved`.

**Kết quả quan sát:**

- Auto Demo gọi resolve đối với các incident có thể phục hồi.
- Backend có endpoint resolve incident riêng trong simulation router.

**Đánh giá:**

Test case đạt yêu cầu ở mức demo. Tuy nhiên, nên chuẩn hoá thêm giữa luồng `/incidents` và `/simulation/incident/*` để tránh trùng logic.

---

### 4.3.2. Ma trận bao phủ tính năng

| Nhóm chức năng | Mức độ hoàn thiện | Bằng chứng trong repo/demo | Nhận xét |
|---|---:|---|---|
| Clean Architecture 4 lớp | 100% | `domain`, `application`, `infrastructure`, `presentation` | Cấu trúc rõ, dễ bảo trì |
| Backend REST API | 100% | Routers: shippers, orders, dashboard, simulation, incidents | Đủ API cho demo |
| WebSocket realtime | 100% | `/ws`, `ws_manager`, simulation broadcast | Phù hợp yêu cầu realtime |
| GPS processing pipeline | 100% | `GPSService.process_gps_stream()` 9 bước | Có validate, compute, save, broadcast |
| Simulation engine | 100% | `simulation_engine.py` | Có phase, route, delivery target, incident |
| Tìm shipper gần kho | 100% | `/simulation/nearest` | Dùng cho dispatch ban đầu |
| Dispatch về warehouse | 100% | `/simulation/dispatch` | Có event khi đến kho |
| Gán đơn hàng | 100% | `/simulation/assign-delivery` | Tạo order và assign shipper |
| Xử lý 5 loại sự cố | 100% ở mức simulation | `TRAFFIC_JAM`, `HEAVY_RAIN`, `CUSTOMER_ABSENT`, `VEHICLE_BREAKDOWN`, `LOST_CONNECTION` | Logic mô phỏng đã có |
| Dashboard realtime | 90% | Dashboard API + frontend stats | Đủ demo, có thể bổ sung biểu đồ nâng cao |
| ETA/AI prediction | 50% | Có `lstm_predictor.py`, `train_lstm.py` | Framework đã có, demo vẫn thiên về heuristic |
| Persistence order/incident | 70% | MongoDB repositories + một phần in-memory trong simulation | Cần thống nhất dữ liệu simulation và DB |
| Security/Auth | 0–20% | CORS mở, chưa thấy JWT | Cần bổ sung trước khi production |
| Test automation | 50% | AutoDemoPanel browser test | Cần thêm unit/integration tests backend |

Nhìn chung, các chức năng cốt lõi phục vụ demo realtime đã đạt mức hoàn thiện cao. Phần còn hạn chế chủ yếu nằm ở production readiness như bảo mật, test tự động, persistence đầy đủ và AI ETA.

---

### 4.3.3. Đối chiếu với mục tiêu ban đầu

| Mục tiêu | Kết quả đạt được |
|---|---|
| Theo dõi shipper realtime | Đạt |
| Hiển thị bản đồ và vị trí shipper | Đạt |
| Tìm shipper gần warehouse | Đạt |
| Dispatch shipper về kho | Đạt |
| Gán đơn giao hàng | Đạt |
| Broadcast trạng thái realtime | Đạt |
| Xử lý sự cố giao hàng | Đạt ở mức simulation |
| Dự báo ETA thông minh | Đạt một phần |
| Dashboard thống kê | Đạt mức demo |
| Sẵn sàng production | Chưa, cần bổ sung security, persistence, monitoring |

Từ bảng đối chiếu có thể thấy hệ thống đã đáp ứng tốt mục tiêu của một MVP/demo. Hệ thống có thể chạy end-to-end, mô phỏng được các bước nghiệp vụ chính và thể hiện rõ đặc trưng realtime. Tuy nhiên, nếu triển khai thực tế, cần đầu tư thêm vào các thành phần bảo mật, dữ liệu thật, bản đồ thật và kiểm thử.

---

## 4.4. Đánh giá hiệu năng và chi phí vận hành

### 4.4.1. Đánh giá hiệu năng

Trong phạm vi demo, hệ thống cho thấy khả năng xử lý realtime tốt nhờ các yếu tố sau:

- Backend dùng FastAPI bất đồng bộ.
- MongoDB dùng Motor async driver.
- WebSocket giúp frontend nhận update nhanh thay vì polling liên tục.
- Simulation engine chạy background task.
- Frontend React cập nhật marker và dashboard theo event.

Các điểm mạnh:

1. **Độ trễ thấp trong demo**
   - Với số lượng shipper mô phỏng hiện tại, frontend có thể cập nhật vị trí liên tục.
   - WebSocket giúp giảm overhead so với REST polling.

2. **Pipeline GPS rõ ràng**
   - Mỗi GPS event được xử lý qua các bước cố định.
   - Dễ mở rộng thêm rule hoặc AI model.

3. **Khả năng mở rộng theo chiều ngang**
   - Backend có thể containerize qua Docker.
   - MongoDB, Redis, Kafka được mô tả trong stack.
   - Có thể tách simulation, ingestion và API thành services riêng nếu mở rộng.

Tuy nhiên, các con số như throughput, tỷ lệ thành công 90%, tiết kiệm 94% chi phí hoặc xử lý 50+ sự cố/giờ nên được xem là **ước lượng/giả định đánh giá**, không nên trình bày như số đo production nếu chưa có benchmark tự động hoặc log đo đạc chính thức.

---

### 4.4.2. Ước lượng lợi ích vận hành

So với cách điều phối thủ công, hệ thống tự động có các lợi ích tiềm năng:

- Giảm thời gian tìm shipper phù hợp.
- Giảm thao tác thủ công khi dispatch.
- Tự động cập nhật trạng thái giao hàng.
- Phát hiện hoặc biểu diễn sự cố nhanh hơn.
- Có thể cảnh báo delay realtime.
- Có nền tảng để tối ưu route và ETA trong tương lai.

Ở mức MVP, lợi ích rõ nhất là khả năng **tự động hoá luồng điều phối và giám sát**. Khi triển khai thực tế với dữ liệu thật, hệ thống có thể tiếp tục được đo bằng các KPI:

| KPI | Cách đo đề xuất |
|---|---|
| API response time | Log middleware hoặc APM |
| WebSocket latency | Timestamp server-client |
| Tỷ lệ giao thành công | Số order delivered / tổng order |
| Tỷ lệ reroute thành công | Số lần reroute có order thay thế / tổng reroute |
| Thời gian xử lý sự cố | Từ lúc incident tạo đến lúc resolve |
| ETA accuracy | Sai số giữa ETA dự đoán và thời gian giao thực tế |
| Uptime | Monitoring service |

---

## 4.5. Hạn chế hiện tại

Mặc dù demo đạt được nhiều chức năng quan trọng, hệ thống vẫn còn một số hạn chế cần lưu ý.

### 4.5.1. Bảo mật

Hiện tại backend chưa thể hiện cơ chế xác thực đầy đủ như JWT, phân quyền role hoặc API key. CORS cũng đang mở rộng trong môi trường demo. Điều này phù hợp khi chạy local nhưng chưa phù hợp nếu triển khai Internet public.

Cần bổ sung:

- JWT authentication.
- Role-based access control.
- Rate limiting.
- HTTPS/SSL.
- Kiểm soát CORS theo domain frontend.

---

### 4.5.2. Persistence giữa simulation và database

Một phần dữ liệu simulation được quản lý trong memory của simulation engine. Điều này giúp demo nhanh và linh hoạt, nhưng có thể gây mất trạng thái nếu server restart.

Cần cải thiện:

- Đồng bộ đầy đủ trạng thái simulation với MongoDB.
- Lưu pending orders và incident states vào database.
- Tạo migration hoặc seed data rõ ràng.
- Thêm cơ chế resume simulation nếu backend restart.

---

### 4.5.3. Tích hợp bản đồ và routing thực tế

Demo có sử dụng route/graph mô phỏng và có logic liên quan OSRM. Tuy nhiên, để triển khai thực tế cần tích hợp bản đồ đầy đủ hơn.

Cần bổ sung:

- OSRM hoặc Google Maps Directions API.
- Dữ liệu đường thật theo khu vực vận hành.
- Traffic realtime.
- Tối ưu route theo thời gian và tình trạng đường.

---

### 4.5.4. ETA/AI chưa hoàn thiện

Repo có các file liên quan LSTM như `lstm_predictor.py` và `train_lstm.py`, nhưng ở mức demo, ETA vẫn còn thiên về heuristic. Điều này hợp lý vì mô hình AI cần dữ liệu lịch sử đủ lớn và được đánh giá bằng metric rõ ràng.

Cần bổ sung:

- Dataset GPS/order thực tế.
- Pipeline train/evaluate model.
- Metric như MAE, RMSE cho ETA.
- Model serving ổn định.
- Fallback heuristic khi model không đủ confidence.

---

### 4.5.5. Kiểm thử tự động

Auto Demo Panel hỗ trợ kiểm thử trên browser, nhưng hệ thống vẫn cần thêm test ở backend.

Cần bổ sung:

- Unit test cho `simulation_engine.py`.
- Unit test cho `GPSService`.
- Integration test cho API simulation.
- WebSocket test.
- Test case riêng cho từng incident type.
- Load test với nhiều shipper/order hơn.

---

## 4.6. Kết luận chương

Qua quá trình chạy mô phỏng và đối chiếu với code trong repo, có thể kết luận rằng hệ thống Smart Logistics đã đạt được mục tiêu của một MVP realtime logistics tracking system. Hệ thống có thể mô phỏng đội shipper, tìm shipper gần kho, dispatch về warehouse, gán đơn hàng, theo dõi trạng thái giao hàng, xử lý nhiều loại sự cố và cập nhật realtime lên frontend.

Điểm mạnh của hệ thống nằm ở kiến trúc rõ ràng, có phân lớp theo Clean Architecture, backend bất đồng bộ, frontend realtime và simulation engine có khả năng biểu diễn các tình huống logistics phổ biến. Đặc biệt, việc sử dụng WebSocket giúp hệ thống phản ánh trạng thái gần như ngay lập tức trên giao diện, phù hợp với yêu cầu của bài toán theo dõi giao hàng thời gian thực.

Tuy nhiên, hệ thống hiện vẫn nên được xem là bản demo/MVP. Để triển khai thực tế, cần tiếp tục hoàn thiện bảo mật, persistence, routing thực tế, mô hình ETA/AI và bộ kiểm thử tự động. Đây là các hướng phát triển quan trọng giúp hệ thống chuyển từ mô phỏng học thuật sang ứng dụng vận hành thực tế.

---

# KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

## 1. Kết luận

Qua quá trình xây dựng và chạy mô phỏng, đề tài đã triển khai được một hệ thống Smart Logistics có khả năng mô phỏng quy trình giao hàng chặng cuối theo thời gian thực. Hệ thống bao gồm các chức năng chính như quản lý shipper, theo dõi GPS, gán đơn hàng, điều phối shipper về kho, xử lý sự cố và hiển thị dashboard realtime.

Về mặt kỹ thuật, hệ thống đã chứng minh được khả năng kết hợp giữa backend FastAPI, MongoDB, WebSocket và frontend React/Leaflet để tạo thành một pipeline realtime hoàn chỉnh. Mỗi thay đổi về vị trí hoặc trạng thái của shipper đều có thể được phát thành event và cập nhật lên giao diện.

Về mặt nghiệp vụ, hệ thống đã mô phỏng được các tình huống thường gặp trong logistics như kẹt xe, mưa lớn, khách vắng, xe hỏng và mất kết nối. Điều này giúp demo không chỉ dừng lại ở việc hiển thị vị trí, mà còn thể hiện được cách hệ thống phản ứng khi phát sinh ngoại lệ.

Tổng thể, hệ thống đạt được mục tiêu của một MVP phục vụ nghiên cứu và demo. Đây là nền tảng tốt để tiếp tục mở rộng thành hệ thống logistics thông minh hơn trong tương lai.

---

## 2. Hướng phát triển

### Giai đoạn 1: Hoàn thiện nền tảng production

Trong giai đoạn đầu, cần tập trung vào các yếu tố nền tảng để hệ thống có thể triển khai an toàn hơn:

- Thêm JWT authentication.
- Thêm phân quyền người dùng.
- Cấu hình HTTPS/SSL.
- Giới hạn CORS theo domain.
- Thêm logging và monitoring.
- Chuẩn hoá file cấu hình môi trường.

### Giai đoạn 2: Hoàn thiện persistence và dữ liệu

Ở giai đoạn tiếp theo, cần đồng bộ tốt hơn giữa simulation engine và database:

- Lưu đầy đủ trạng thái order, shipper, incident vào MongoDB.
- Lưu pending orders thay vì chỉ quản lý trong memory.
- Thêm lịch sử thay đổi trạng thái.
- Thêm seed data và migration script.
- Cho phép resume simulation sau khi restart backend.

### Giai đoạn 3: Tích hợp bản đồ và dữ liệu thực tế

Để nâng độ chính xác của route và ETA, cần tích hợp dữ liệu bản đồ thực:

- OSRM hoặc Google Maps Directions API.
- OpenStreetMap road network.
- Traffic realtime.
- Dữ liệu khu vực giao hàng thực tế.
- Tối ưu route theo thời gian và điều kiện đường.

### Giai đoạn 4: Nâng cấp AI/ML

Khi có dữ liệu lịch sử đủ lớn, hệ thống có thể phát triển mô hình ETA thông minh:

- Thu thập dữ liệu GPS/order thực tế.
- Huấn luyện LSTM hoặc mô hình time-series phù hợp.
- Đánh giá bằng MAE/RMSE.
- Dự đoán delay theo traffic, thời tiết, incident.
- Tự động đề xuất reroute hoặc reassign.

### Giai đoạn 5: Mở rộng ứng dụng người dùng

Sau khi backend ổn định, có thể phát triển thêm các ứng dụng phục vụ vận hành thực tế:

- Mobile app cho shipper bằng React Native.
- Portal cho khách hàng theo dõi đơn hàng.
- Admin dashboard nâng cao.
- Analytics dashboard cho quản lý.
- Notification qua email/SMS/push notification.

---

## 3. KPI đề xuất cho giai đoạn tiếp theo

| KPI | Mục tiêu đề xuất |
|---|---|
| API response time | < 500ms |
| WebSocket latency | < 1s |
| ETA error | < 10 phút khi có dữ liệu thật |
| Uptime | > 99% |
| Tỷ lệ giao thành công | > 90% |
| Tỷ lệ reroute thành công | > 80% |
| Test coverage backend core | > 80% |
| Incident resolve time | Giảm ít nhất 50% so với xử lý thủ công |

Các KPI này cần được đo bằng log thực tế hoặc công cụ monitoring thay vì chỉ ước lượng trong demo. Khi có dữ liệu thực, nhóm có thể đánh giá chính xác hơn hiệu quả vận hành và khả năng mở rộng của hệ thống.

---

## 4. Kết luận chung

Smart Logistics hiện đã có nền tảng kỹ thuật tốt cho một hệ thống logistics realtime. Demo trong repo cho thấy hệ thống có thể chạy được luồng end-to-end từ simulation, dispatch, assign delivery, incident handling đến dashboard realtime. Nếu tiếp tục hoàn thiện các phần còn thiếu như bảo mật, dữ liệu thực, routing thực tế và AI ETA, hệ thống có tiềm năng mở rộng thành một nền tảng hỗ trợ điều phối giao hàng thông minh trong môi trường thực tế.