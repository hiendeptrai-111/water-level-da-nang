**TRƯỜNG ĐẠI HỌC KIẾN TRÚC ĐÀ NẴNG**

**KHOA CÔNG NGHỆ THÔNG TIN**

**TÀI LIỆU ĐẶC TẢ CHỨC NĂNG WEBSITE**

> **Hệ thống dự báo mực nước và nguy cơ xả lũ đập thủy điện tích hợp theo dõi thời tiết và hỗ trợ cứu hộ khẩn cấp (SOS) tại thành phố Đà Nẵng**

*Phiên bản: 1.0 (bản nháp để rà soát)*

Sinh viên thực hiện: Trần Văn Hiền

**Đà Nẵng, 10/2026**

# 1. GIỚI THIỆU

## 1.1. Mục đích tài liệu

Tài liệu mô tả toàn bộ chức năng của website thuộc đồ án, bao gồm các vai trò người dùng, quyền hạn, mô tả chi tiết từng chức năng, danh sách màn hình và các yêu cầu chung. Tài liệu dùng để rà soát và thống nhất phạm vi trước khi lập trình, đồng thời làm cơ sở cho Chương 3 (Phân tích và thiết kế hệ thống) của báo cáo.

## 1.2. Phạm vi hệ thống

Hệ thống phục vụ vùng hạ du bốn hồ thủy điện lớn tại thành phố Đà Nẵng: A Vương, Đăk Mi 4, Sông Bung 4 và Sông Tranh 2. Website gồm ba nhóm chức năng chính, liên kết với nhau theo luồng dự báo – cảnh báo – ứng cứu:

- **Dự báo và cảnh báo:** hiển thị số liệu vận hành bốn hồ, mực nước dự kiến sau 1, 3 và 6 giờ, và mức cảnh báo được tính tự động mỗi giờ từ mô hình đã xây dựng.

- **Theo dõi thời tiết:** thông tin mưa và thời tiết theo từng phường, xã vùng hạ du.

- **SOS và điều phối cứu hộ:** người dân gửi tín hiệu cầu cứu kèm vị trí; admin tiếp nhận, được gợi ý đội cứu hộ theo thời gian tiếp cận thực tế và phân công xử lý.

Hệ thống đóng vai trò hỗ trợ ra quyết định, không thay thế quy trình chỉ huy của cơ quan chức năng và không thay thế việc gọi điện đến các số khẩn cấp.

## 1.3. Thuật ngữ

*Bảng 1. Thuật ngữ sử dụng trong tài liệu*

| **Thuật ngữ**               | **Giải thích**                                                                                                                           |
|-----------------------------|------------------------------------------------------------------------------------------------------------------------------------------|
| MNDBT                       | Mực nước dâng bình thường của hồ chứa                                                                                                    |
| Ngưỡng quy định             | Mực nước cao nhất trước lũ và mực nước đón lũ thấp nhất của từng hồ, thay đổi theo thời kỳ trong mùa lũ (Quyết định 1865/QĐ-TTg, Điều 6) |
| Mực nước mục tiêu điều hành | Mực nước hồ phải đạt theo chỉ đạo của thành phố trong từng đợt mưa lũ, có thời điểm bắt đầu và hạn hoàn thành                            |
| Tầm dự báo                  | Khoảng thời gian dự báo về phía trước: 1 giờ, 3 giờ, 6 giờ                                                                               |
| Mức cảnh báo                | Bình thường, Theo dõi, Cảnh báo (tự động) và Khẩn cấp (do admin phát)                                                                    |
| SOS                         | Tín hiệu cầu cứu khẩn cấp do người dân gửi qua website                                                                                   |
| Thời gian tiếp cận (ETA)    | Thời gian ước tính để đội cứu hộ đến nơi, có xét đến các đoạn đường bị ngập                                                              |
| Điểm ngập                   | Vị trí đường bị ngập do người dân hoặc đội cứu hộ báo cáo, dùng cho việc tính tuyến đường                                                |
| Dữ liệu nghi ngờ            | Số liệu vận hành bất thường (ví dụ nhảy hơn 0,8 m trong 1 giờ), chờ xác nhận ở giờ sau                                                   |

# 2. ĐỐI TƯỢNG SỬ DỤNG VÀ PHÂN QUYỀN

## 2.1. Các vai trò

*Bảng 2. Các vai trò người dùng*

| **Vai trò** | **Mô tả**                                                                                                                            | **Cách có tài khoản**                                      |
|-------------|--------------------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------|
| Người dân   | Người sống hoặc đang có mặt tại vùng hạ du; xem thông tin, gửi SOS, báo điểm ngập                                                    | Tự đăng ký                                                 |
| Đội cứu hộ  | Tài khoản của một đội cứu hộ; nhận và thực hiện nhiệm vụ, tự nhận SOS khi chưa được phân công                                        | Admin tạo, mỗi tài khoản gắn với một đội                   |
| Admin       | Quản trị hệ thống và điều hành: theo dõi cảnh báo, phát cảnh báo khẩn cấp, điều phối SOS, duyệt điểm ngập, thống kê, quản lý dữ liệu | Tạo khi cài đặt hệ thống; admin có thể tạo thêm admin khác |

Người chưa đăng nhập không phải một vai trò, nhưng vẫn xem được các thông tin công khai: tổng quan hồ chứa, dự báo, thời tiết, cảnh báo và bản đồ điểm ngập đã duyệt.

Tài khoản đội cứu hộ và admin không được tự đăng ký, nhằm tránh việc người lạ tự nhận là cứu hộ để xem thông tin cá nhân của người gặp nạn, hoặc phát cảnh báo giả.

## 2.2. Ma trận phân quyền

*Bảng 3. Quyền truy cập theo vai trò*

| **Nhóm chức năng**                               | **Chưa đăng nhập** | **Người dân** | **Đội cứu hộ** | **Admin** |
|--------------------------------------------------|--------------------|---------------|----------------|-----------|
| Xem tổng quan hồ chứa, dự báo, thời tiết         | ✓                  | ✓             | ✓              | ✓         |
| Xem cảnh báo công khai                           | ✓                  | ✓             | ✓              | ✓         |
| Gửi SOS                                          | ✓ (\*)             | ✓             | –              | –         |
| Theo dõi SOS của mình                            | –                  | ✓             | –              | –         |
| Báo điểm ngập                                    | –                  | ✓             | ✓              | ✓         |
| Nhận cảnh báo tự động mức Theo dõi               | –                  | –             | –              | ✓         |
| Nhận cảnh báo tự động mức Cảnh báo               | –                  | –             | ✓              | ✓         |
| Phát / kết thúc cảnh báo Khẩn cấp                | –                  | –             | –              | ✓         |
| Xem vị trí SOS đang mở                           | –                  | –             | ✓              | ✓         |
| Xem số điện thoại người gửi SOS                  | –                  | –             | ✓ (\*\*)       | ✓         |
| Phân công, chuyển giao SOS                       | –                  | –             | –              | ✓         |
| Tự nhận SOS chưa được phân công                  | –                  | –             | ✓              | –         |
| Cập nhật trạng thái cứu hộ                       | –                  | –             | ✓              | ✓         |
| Duyệt điểm ngập                                  | –                  | –             | –              | ✓         |
| Thống kê, xuất báo cáo                           | –                  | –             | –              | ✓         |
| Quản lý người dùng, đội cứu hộ, danh mục, ngưỡng | –                  | –             | –              | ✓         |
| Tình trạng dữ liệu, mô hình, nhật ký hệ thống    | –                  | –             | –              | ✓         |

*(\*) Gửi SOS không cần đăng nhập nhưng bắt buộc nhập số điện thoại. (\*\*) Chỉ hiện sau khi đội đã nhận hoặc được giao SOS đó; trước đó đội chỉ thấy vị trí và mức ưu tiên.*

<img src="media/cb5cb5e14f6f4872220b69e7f67d5b377832ae0d.png" style="width:5.83333in;height:2.67708in" />

*Hình 1. Các nhóm trang theo vai trò người dùng*

# 3. DANH SÁCH CHỨC NĂNG

*Bảng 4. Tổng hợp chức năng*

| **Mã** | **Tên chức năng**             | **Vai trò chính**     | **Ưu tiên** |
|--------|-------------------------------|-----------------------|-------------|
| CN01   | Đăng ký tài khoản             | Chưa đăng nhập        | Cao         |
| CN02   | Đăng nhập                     | Tất cả                | Cao         |
| CN03   | Quên mật khẩu                 | Tất cả                | Trung bình  |
| CN04   | Hồ sơ cá nhân                 | Đã đăng nhập          | Trung bình  |
| CN05   | Đăng xuất                     | Đã đăng nhập          | Cao         |
| CN06   | Tổng quan hồ chứa             | Tất cả                | Cao         |
| CN07   | Chi tiết và dự báo từng hồ    | Tất cả                | Cao         |
| CN08   | Tải dữ liệu hồ chứa           | Admin                 | Thấp        |
| CN09   | Xem cảnh báo khu vực          | Tất cả                | Cao         |
| CN10   | Cảnh báo tự động              | Admin, Đội cứu hộ     | Cao         |
| CN11   | Phát cảnh báo khẩn cấp        | Admin                 | Cao         |
| CN12   | Lịch sử cảnh báo              | Admin                 | Trung bình  |
| CN13   | Thời tiết theo phường/xã      | Tất cả                | Cao         |
| CN14   | Bản đồ mưa                    | Tất cả                | Thấp        |
| CN15   | Gửi SOS                       | Người dân             | Cao         |
| CN16   | Theo dõi SOS của tôi          | Người dân             | Cao         |
| CN17   | Bản đồ và danh sách SOS       | Admin                 | Cao         |
| CN18   | Gợi ý và phân công đội cứu hộ | Admin                 | Cao         |
| CN19   | Nhiệm vụ và tự nhận SOS       | Đội cứu hộ            | Cao         |
| CN20   | Báo điểm ngập                 | Người dân, Đội cứu hộ | Trung bình  |
| CN21   | Duyệt điểm ngập               | Admin                 | Trung bình  |
| CN22   | Thống kê và xuất báo cáo      | Admin                 | Thấp        |
| CN23   | Quản lý người dùng            | Admin                 | Cao         |
| CN24   | Quản lý hồ chứa và ngưỡng     | Admin                 | Trung bình  |
| CN25   | Quản lý phường/xã hạ du       | Admin                 | Trung bình  |
| CN26   | Quản lý đội cứu hộ            | Admin                 | Cao         |
| CN27   | Tình trạng dữ liệu và mô hình | Admin                 | Trung bình  |
| CN28   | Nhật ký hệ thống              | Admin                 | Thấp        |

# 4. MÔ TẢ CHI TIẾT CHỨC NĂNG

## 4.1. Nhóm tài khoản

### CN01. Đăng ký tài khoản

**Người dùng:** Người chưa có tài khoản (đăng ký thành Người dân).

**Mô tả:** Người dân tạo tài khoản để gửi SOS nhanh hơn, theo dõi SOS và nhận cảnh báo khẩn cấp cho phường/xã nơi ở.

**Dữ liệu nhập:**

*Bảng 5. Dữ liệu đăng ký*

| **Trường**        | **Bắt buộc** | **Ràng buộc**                                                                                                                            |
|-------------------|--------------|------------------------------------------------------------------------------------------------------------------------------------------|
| Họ và tên         | Có           | 2–100 ký tự                                                                                                                              |
| Số điện thoại     | Có           | 10 chữ số, bắt đầu bằng 0, không trùng tài khoản khác                                                                                    |
| Email             | Có           | Đúng định dạng, không trùng; phải xác thực trước khi đăng nhập                                                                           |
| Mật khẩu          | Có           | Tối thiểu 8 ký tự, có cả chữ và số                                                                                                       |
| Nhập lại mật khẩu | Có           | Trùng với mật khẩu                                                                                                                       |
| Phường/xã nơi ở   | Có           | Chọn từ ô chọn gồm 94 phường, xã, đặc khu của Đà Nẵng (Nghị quyết 1659/NQ-UBTVQH15); các xã vùng hạ du xếp lên đầu; không cho nhập tự do |
| Số nhà, thôn/tổ   | Không        | Tối đa 255 ký tự                                                                                                                         |
| Vị trí nhà        | Không        | Ghim trên bản đồ, giúp đội cứu hộ tìm nhà nhanh                                                                                          |
| Đồng ý điều khoản | Có           | Đồng ý cho hệ thống dùng vị trí khi gửi SOS và báo điểm ngập                                                                             |

**Quy tắc xử lý:**

- Kiểm tra dữ liệu ở cả giao diện và máy chủ; báo lỗi ngay dưới từng trường.

- Mật khẩu được băm trước khi lưu, không lưu dạng gốc.

- Giới hạn số lần đăng ký từ cùng một địa chỉ mạng để chống tạo tài khoản hàng loạt.

- Sau khi đăng ký, hệ thống gửi email xác thực; đường dẫn có hiệu lực 24 giờ, có nút gửi lại. Chưa xác thực thì chưa đăng nhập được. Điều này không cản trở tình huống khẩn cấp vì gửi SOS không cần đăng nhập.

**Kết quả:** Tạo tài khoản vai trò Người dân ở trạng thái chờ xác thực; sau khi bấm đường dẫn trong email, người dân đăng nhập được.

### CN02. Đăng nhập

**Người dùng:** Tất cả vai trò.

**Mô tả:** Đăng nhập bằng số điện thoại hoặc email kèm mật khẩu.

**Quy tắc xử lý:**

- Xác thực bằng JWT: mã truy cập hết hạn sau 30 phút, mã làm mới hết hạn sau 7 ngày; giao diện tự làm mới khi mã truy cập hết hạn.

- Sai mật khẩu 5 lần liên tiếp: tạm khoá đăng nhập 15 phút.

- Thông báo lỗi chung "Thông tin đăng nhập không đúng", không tiết lộ tài khoản có tồn tại hay không.

- Tài khoản bị khoá bởi admin không đăng nhập được.

- Tài khoản chưa xác thực email: báo cần xác thực, kèm nút gửi lại email.

**Kết quả:** Chuyển đến trang phù hợp vai trò: Người dân về trang chủ, Đội cứu hộ về trang Nhiệm vụ, Admin về Bảng điều khiển.

### CN03. Quên mật khẩu

**Người dùng:** Mọi tài khoản (đều có email).

**Mô tả:** Nhập email để nhận đường dẫn đặt lại mật khẩu.

**Quy tắc xử lý:**

- Đường dẫn chỉ dùng một lần và hết hạn sau 30 phút.

- Luôn hiển thị cùng một thông báo dù email có tồn tại hay không.

**Kết quả:** Người dùng đặt mật khẩu mới; mọi phiên đăng nhập cũ bị đăng xuất.

### CN04. Hồ sơ cá nhân

**Người dùng:** Người dùng đã đăng nhập.

**Mô tả:** Xem và sửa thông tin cá nhân, đổi mật khẩu, cài đặt nhận thông báo.

**Thông tin hiển thị:**

- Họ tên, số điện thoại, email, phường/xã nơi ở, địa chỉ.

- Số điện thoại người thân để đội cứu hộ liên hệ khi không gọi được cho người gửi SOS.

- Cài đặt thông báo: nhận trên website, nhận qua email.

**Quy tắc xử lý:**

- Đổi mật khẩu phải nhập mật khẩu cũ.

- Đổi số điện thoại phải kiểm tra không trùng.

- Đổi email phải xác thực lại email mới.

### CN05. Đăng xuất

**Người dùng:** Người dùng đã đăng nhập.

**Mô tả:** Huỷ phiên làm việc, xoá mã đăng nhập trên trình duyệt và vô hiệu hoá mã làm mới ở máy chủ.

## 4.2. Nhóm hồ chứa và dự báo

### CN06. Tổng quan hồ chứa

**Người dùng:** Tất cả vai trò.

**Mô tả:** Trang hiển thị tình trạng bốn hồ trên cùng một màn hình, tự tải lại mỗi 5 phút.

**Thông tin hiển thị:**

- Mỗi hồ một thẻ: tên hồ, mực nước hiện tại, khoảng cách đến MNDBT, lưu lượng đến, lưu lượng xả (qua máy và qua tràn).

- Huy hiệu mức cảnh báo theo màu: xanh (Bình thường), vàng (Theo dõi), cam (Cảnh báo), đỏ (Khẩn cấp).

- Thời điểm của số liệu; nếu số liệu cũ hơn 2 giờ thì hiện dòng "Dữ liệu chưa được cập nhật".

- Biểu tượng "Cần xác nhận dữ liệu" khi giờ mới nhất có số liệu nghi ngờ.

- Với người dân: một câu giải thích dễ hiểu, ví dụ "Mực nước hồ A Vương đang dâng, theo dõi thông báo của chính quyền địa phương".

### CN07. Chi tiết và dự báo từng hồ

**Người dùng:** Tất cả vai trò.

**Mô tả:** Trang riêng của từng hồ với biểu đồ và kết quả dự báo.

**Thông tin hiển thị:**

- Biểu đồ mực nước 7 ngày qua, nối tiếp 3 điểm dự báo sau 1, 3 và 6 giờ (nét đứt), kèm đường ngang ngưỡng quy định của thời kỳ hiện tại và mực nước mục tiêu điều hành nếu đang có chỉ đạo.

- Biểu đồ lưu lượng đến và lưu lượng xả; biểu đồ cột lượng mưa lưu vực theo giờ.

- Bảng dự báo: tầm dự báo, mực nước dự kiến, mức cảnh báo, so sánh với ngưỡng quy định và mực nước mục tiêu điều hành.

- Chọn khoảng thời gian xem lịch sử (tối đa 90 ngày một lần).

- Ghi chú cố định: "Kết quả dự báo mang tính tham khảo, hỗ trợ ra quyết định", kèm phiên bản và ngày huấn luyện mô hình.

**Quy tắc xử lý:**

- Mực nước dự kiến lấy từ mô hình hồi quy tuyến tính; mức cảnh báo tính theo quy tắc phối hợp Baseline, phương án A và phương án B như kết quả đánh giá ở Chương 4.

- Các ngưỡng là ngưỡng phục vụ vận hành và đón lũ, không phải ngưỡng mất an toàn của đập. Giao diện ghi rõ tên từng loại ngưỡng và không tô đỏ chỉ vì mực nước vượt ngưỡng; mức cảnh báo chỉ do mô hình và quy tắc ở mục 4.3 quyết định.

- Khi số liệu giờ mới nhất bị thiếu thì không hiển thị dự báo, chỉ ghi "Chưa đủ dữ liệu để dự báo".

### CN08. Tải dữ liệu hồ chứa

**Người dùng:** Admin.

**Mô tả:** Xuất số liệu vận hành, lượng mưa và kết quả dự báo của một hồ trong khoảng thời gian chọn ra file CSV hoặc Excel.

## 4.3. Nhóm cảnh báo

Hệ thống có bốn mức cảnh báo. Ba mức đầu được tính tự động mỗi giờ. Mức Khẩn cấp chỉ do admin phát sau khi xác nhận, vì kết quả đánh giá cho thấy mô hình chưa vượt quy tắc quán tính một cách có ý nghĩa thống kê, nên quyết định gửi báo động đến toàn dân cần có con người kiểm tra.

*Bảng 6. Các mức cảnh báo*

| **Mức**     | **Cách sinh ra**                                    | **Ai nhận**                                   | **Hình thức**                                         |
|-------------|-----------------------------------------------------|-----------------------------------------------|-------------------------------------------------------|
| Bình thường | Tự động                                             | –                                             | Hiển thị trên trang                                   |
| Theo dõi    | Tự động (phương án B), hoặc khi có dữ liệu nghi ngờ | Admin                                         | Bảng điều khiển, email                                |
| Cảnh báo    | Tự động (Baseline hoặc phương án A)                 | Admin, đội cứu hộ; người dân xem trên trang   | Bảng điều khiển, email, biểu ngữ trên trang           |
| Khẩn cấp    | Admin phát thủ công                                 | Người dân đăng ký tại các phường/xã được chọn | Thông báo trên website, email, biểu ngữ đỏ toàn trang |

### CN09. Xem cảnh báo khu vực

**Người dùng:** Tất cả vai trò.

**Mô tả:** Trang liệt kê các cảnh báo đang có hiệu lực; người dân đã đăng nhập thấy cảnh báo của phường/xã mình lên đầu.

**Thông tin hiển thị:**

- Mức cảnh báo, hồ liên quan, các phường/xã bị ảnh hưởng, nội dung, thời điểm phát, hiệu lực đến.

- Hướng dẫn hành động ngắn theo mức (ví dụ di chuyển đồ đạc lên cao, chuẩn bị sơ tán).

- Số điện thoại khẩn cấp luôn hiển thị.

### CN10. Cảnh báo tự động

**Người dùng:** Admin, đội cứu hộ.

**Mô tả:** Mỗi giờ, sau khi chạy dự báo, nếu mức của một hồ tăng lên Theo dõi hoặc Cảnh báo thì hệ thống tạo thông báo. Admin nhận cả hai mức; đội cứu hộ chỉ nhận mức Cảnh báo, để không bị làm phiền bởi các tín hiệu theo dõi.

**Quy tắc xử lý:**

- Chỉ thông báo khi mức tăng hoặc khi mức Cảnh báo kéo dài thêm mỗi 3 giờ, tránh gửi lặp mỗi giờ.

- Thông báo nêu rõ: hồ, tầm dự báo, mực nước dự kiến, lý do (mô hình nào báo), có dữ liệu nghi ngờ hay không.

- Người nhận bấm "Đã xem" để đánh dấu đã tiếp nhận; hệ thống lưu ai xem lúc nào.

### CN11. Phát cảnh báo khẩn cấp

**Người dùng:** Admin.

**Mô tả:** Soạn và phát cảnh báo khẩn cấp đến người dân các phường/xã bị ảnh hưởng.

**Dữ liệu nhập:**

*Bảng 7. Dữ liệu phát cảnh báo khẩn cấp*

| **Trường**          | **Bắt buộc** | **Ràng buộc**                                                                                        |
|---------------------|--------------|------------------------------------------------------------------------------------------------------|
| Hồ liên quan        | Có           | Chọn một hoặc nhiều hồ                                                                               |
| Phường/xã ảnh hưởng | Có           | Hệ thống gợi ý theo bảng hồ – phường/xã (Phụ lục B), xếp vùng hạ du gần lên đầu; admin thêm hoặc bớt |
| Nội dung            | Có           | Chọn mẫu soạn sẵn rồi sửa; tối đa 1.000 ký tự                                                        |
| Hiệu lực đến        | Có           | Thời điểm kết thúc dự kiến; có thể kết thúc sớm                                                      |

**Quy tắc xử lý:**

- Trước khi gửi hiện màn hình xác nhận: số người nhận dự kiến và nội dung xem trước.

- Mọi lần phát, sửa, kết thúc đều ghi vào nhật ký hệ thống.

**Kết quả:** Biểu ngữ đỏ hiện trên toàn website; người dân tại các phường/xã được chọn nhận thông báo trên website và email.

### CN12. Lịch sử cảnh báo

**Người dùng:** Admin.

**Mô tả:** Tra cứu các cảnh báo đã sinh ra hoặc đã phát, lọc theo hồ, mức, khoảng thời gian; xem chi tiết dự báo tại thời điểm cảnh báo.

## 4.4. Nhóm thời tiết

### CN13. Thời tiết theo phường/xã

**Người dùng:** Tất cả vai trò.

**Mô tả:** Xem thời tiết hiện tại và dự báo của một phường/xã; mặc định là phường/xã nơi ở với người dân đã đăng nhập.

**Thông tin hiển thị:**

- Hiện tại: nhiệt độ, lượng mưa giờ qua, gió.

- Mưa tích lũy 24 giờ qua.

- Dự báo mưa theo giờ cho 24, 48 và 72 giờ tới (biểu đồ cột).

- Biểu tượng "Mưa lớn" khi lượng mưa dự báo vượt ngưỡng hiển thị do admin cấu hình. Đây là thông tin tham khảo, không phải cảnh báo chính thức.

**Quy tắc xử lý:**

- Dữ liệu lấy từ Open-Meteo theo tọa độ trung tâm của phường/xã, cập nhật mỗi giờ và lưu đệm để không gọi lại liên tục.

### CN14. Bản đồ mưa

**Người dùng:** Tất cả vai trò.

**Mô tả:** Bản đồ các phường/xã hạ du, tô màu theo lượng mưa tích lũy 24 giờ qua hoặc dự báo 24 giờ tới; bấm vào một phường/xã để mở CN13.

## 4.5. Nhóm SOS

### CN15. Gửi SOS

**Người dùng:** Người dân; người chưa đăng nhập (bắt buộc nhập số điện thoại).

**Mô tả:** Màn hình tối giản với một nút SOS lớn màu đỏ, tối ưu cho điện thoại.

**Dữ liệu nhập:**

*Bảng 8. Dữ liệu gửi SOS*

| **Trường**       | **Bắt buộc**          | **Ràng buộc**                                                                          |
|------------------|-----------------------|----------------------------------------------------------------------------------------|
| Vị trí           | Có                    | Tự lấy GPS kèm độ chính xác; nếu không lấy được thì chọn trên bản đồ hoặc nhập địa chỉ |
| Số điện thoại    | Có nếu chưa đăng nhập | Tự điền với Người dân                                                                  |
| Số người cần cứu | Không                 | Chọn nhanh: 1, 2–4, 5 trở lên                                                          |
| Nhóm cần ưu tiên | Không                 | Chọn nhiều: người già, trẻ nhỏ, người bệnh, người bị thương, phụ nữ mang thai          |
| Mức nước         | Không                 | Chọn: ngang gối, ngang ngực, ngập tầng 1, phải lên mái                                 |
| Ghi chú          | Không                 | Tối đa 300 ký tự                                                                       |
| Ảnh              | Không                 | Tối đa 1 ảnh, tự nén nhỏ trước khi gửi                                                 |

**Quy tắc xử lý:**

- Nhấn giữ nút 3 giây để gửi, tránh bấm nhầm; có nút huỷ trong 5 giây sau khi gửi.

- Gửi ngay vị trí và số điện thoại trước; các thông tin thêm được gửi bổ sung sau, để SOS đi được cả khi mạng yếu.

- Mạng lỗi: tự gửi lại nhiều lần và hiện rõ trạng thái "Đang gửi lại".

- Mỗi tài khoản hoặc số điện thoại chỉ có 1 SOS đang mở; gửi tiếp thì cập nhật vào SOS cũ.

- Giới hạn tần suất theo thiết bị và địa chỉ mạng để chống gửi tràn.

- Mức ưu tiên được tính tự động từ mức nước, nhóm cần ưu tiên, thời gian chờ và mức cảnh báo hiện tại của khu vực.

- Luôn hiển thị số điện thoại khẩn cấp và lời nhắc: nếu gọi được điện thoại thì hãy gọi ngay.

**Kết quả:** Hiện mã SOS và trạng thái "Đã gửi". SOS xuất hiện ngay trên bản đồ điều phối.

<img src="media/a190b8d00603d8c42e3c3d54f08ce95d69998096.png" style="width:5.83333in;height:2.10417in" />

*Hình 2. Luồng trạng thái của một SOS*

### CN16. Theo dõi SOS của tôi

**Người dùng:** Người dân (người chưa đăng nhập xem bằng mã SOS và số điện thoại).

**Mô tả:** Xem trạng thái SOS đang mở và lịch sử các SOS đã gửi.

**Thông tin hiển thị:**

- Trạng thái hiện tại theo luồng ở Hình 2, thời điểm từng bước.

- Đội cứu hộ đã được phân công và thời gian tiếp cận ước tính.

**Quy tắc xử lý:**

- Người dân được cập nhật vị trí, bổ sung thông tin, hoặc huỷ SOS khi đã an toàn.

## 4.6. Nhóm điều phối cứu hộ

### CN17. Bản đồ và danh sách SOS

**Người dùng:** Admin.

**Mô tả:** Màn hình điều phối gồm bản đồ và danh sách, tự cập nhật mỗi 30 giây.

**Thông tin hiển thị:**

- Bản đồ: SOS tô màu theo mức ưu tiên, vị trí các đội cứu hộ, các điểm ngập đã duyệt.

- Danh sách SOS sắp theo mức ưu tiên và thời gian chờ; lọc theo trạng thái, phường/xã.

- Chi tiết một SOS: thông tin người gửi, nút gọi điện, ảnh, lịch sử xử lý.

**Quy tắc xử lý:**

- Admin bấm "Tiếp nhận" để chuyển SOS sang trạng thái Đã tiếp nhận; tránh hai người cùng xử lý một SOS.

- Có thể đánh dấu SOS trùng lặp hoặc gộp các SOS ở cùng một vị trí.

### CN18. Gợi ý và phân công đội cứu hộ

**Người dùng:** Admin.

**Mô tả:** Hệ thống gợi ý đội cứu hộ phù hợp nhất cho một SOS dựa trên thời gian tiếp cận thực tế.

**Quy tắc xử lý:**

- Mạng lưới đường lấy từ OpenStreetMap, tính tuyến bằng OSRM.

- Đoạn đường có điểm ngập đã duyệt: mức "xe máy không qua được" thì tăng thời gian đi; mức "ô tô không qua được" trở lên thì chặn với đội đi đường bộ.

- Đội có ca nô được xét riêng, không phụ thuộc đường bộ.

- Hiện 3 đội tốt nhất đang rảnh, kèm thời gian tiếp cận ước tính và tuyến đường trên bản đồ.

- Hệ thống chỉ gợi ý; admin chọn và bấm "Phân công". Không tự động phân công.

- Nếu sau 15 phút chưa có admin phân công, các đội đang rảnh gần nhất nhận thông báo để tự nhận SOS (xem CN19). Admin vẫn có thể chuyển SOS sang đội khác bất cứ lúc nào.

**Kết quả:** SOS chuyển sang Đang di chuyển; đội được giao nhận thông báo nhiệm vụ.

### CN19. Nhiệm vụ và tự nhận SOS

**Người dùng:** Đội cứu hộ.

**Mô tả:** Giao diện cho điện thoại, gồm hai danh sách: nhiệm vụ đã được giao, và các SOS đang chờ nhận ở gần đội.

**Thông tin hiển thị:**

- Nhiệm vụ đã giao: vị trí người cần cứu, tuyến đường gợi ý, nút gọi điện, số người và nhóm cần ưu tiên.

- SOS chờ nhận: vị trí, mức ưu tiên, thời gian chờ và thời gian tiếp cận ước tính từ vị trí của đội; chưa hiện số điện thoại.

**Quy tắc xử lý:**

- Bấm "Nhận" để tự nhận một SOS chưa được phân công; hệ thống khoá để hai đội không nhận trùng. Sau khi nhận, số điện thoại người gửi mới hiện ra.

- Mỗi đội chỉ nhận thêm khi đang ở trạng thái Rảnh.

- Cập nhật trạng thái: Đã đến nơi, Đã cứu, Không liên lạc được; có thể trả lại nhiệm vụ kèm lý do.

- Gửi vị trí của đội khi đang mở trang, để bản đồ điều phối luôn đúng.

- Đội đặt trạng thái của mình: Rảnh, Đang làm nhiệm vụ, Nghỉ.

## 4.7. Nhóm điểm ngập

### CN20. Báo điểm ngập

**Người dùng:** Người dân, đội cứu hộ, admin.

**Mô tả:** Báo một vị trí đường bị ngập để phục vụ việc tính tuyến đường cứu hộ.

**Dữ liệu nhập:**

*Bảng 9. Dữ liệu báo điểm ngập*

| **Trường** | **Bắt buộc** | **Ràng buộc**                                                      |
|------------|--------------|--------------------------------------------------------------------|
| Vị trí     | Có           | Mặc định vị trí hiện tại, chỉnh được trên bản đồ                   |
| Mức ngập   | Có           | Đi lại được; xe máy không qua được; ô tô không qua được; chỉ ca nô |
| Ảnh        | Không        | Tối đa 1 ảnh                                                       |

**Quy tắc xử lý:**

- Báo của người dân ở trạng thái Chờ duyệt; báo của đội cứu hộ và admin được dùng ngay.

- Điểm ngập tự hết hạn sau 12 giờ nếu không có ai xác nhận lại.

### CN21. Duyệt điểm ngập

**Người dùng:** Admin.

**Mô tả:** Duyệt, từ chối hoặc sửa mức ngập của các báo cáo; gộp các báo cáo gần nhau. Chỉ điểm ngập đã duyệt mới được dùng để tính tuyến đường và hiển thị công khai (không kèm thông tin người báo).

## 4.8. Nhóm thống kê

### CN22. Thống kê và xuất báo cáo

**Người dùng:** Admin.

**Thông tin hiển thị:**

- Số SOS theo ngày và theo phường/xã; tỷ lệ đã cứu, huỷ, trùng lặp.

- Thời gian từ lúc gửi đến lúc tiếp nhận, và đến lúc đội tới nơi (trung bình và trung vị).

- Số cảnh báo theo mức và theo hồ.

- Xuất Excel hoặc CSV theo khoảng thời gian chọn.

## 4.9. Nhóm quản trị hệ thống

### CN23. Quản lý người dùng

**Người dùng:** Admin.

**Mô tả:** Tạo tài khoản đội cứu hộ và admin; khoá hoặc mở khoá tài khoản; đổi vai trò; gắn tài khoản cứu hộ với đội; đặt lại mật khẩu.

### CN24. Quản lý hồ chứa và ngưỡng

**Người dùng:** Admin.

**Mô tả:** Quản lý hai bảng riêng biệt, không ghi đè lên nhau (chi tiết ở Phụ lục A).

**Thông tin hiển thị:**

- Bảng ngưỡng quy định: mực nước cao nhất trước lũ và mực nước đón lũ thấp nhất của từng hồ theo từng thời kỳ (từ ngày – đến ngày), nạp sẵn theo Quyết định 1865/QĐ-TTg.

- Bảng chỉ đạo điều hành: mỗi lần thành phố có công văn yêu cầu hồ đạt một mực nước, admin thêm một dòng gồm hồ, loại yêu cầu (không vượt / hạ về), mực nước mục tiêu, thời điểm bắt đầu, hạn hoàn thành, số và ngày văn bản.

**Quy tắc xử lý:**

- Hệ thống tự chọn ngưỡng quy định theo ngày hiện tại và hiển thị các chỉ đạo đang còn hiệu lực.

- Không xoá chỉ đạo cũ; chỉ đánh dấu hết hiệu lực, để giữ lịch sử điều hành.

- Mọi thay đổi được ghi nhật ký hệ thống.

### CN25. Quản lý phường/xã hạ du

**Người dùng:** Admin.

**Mô tả:** Danh mục phường/xã: tên, tọa độ trung tâm (dùng cho thời tiết), ranh giới (tuỳ chọn, dùng cho bản đồ) và bảng liên kết với từng hồ kèm loại vùng: khu vực đập, hạ du gần, hạ du đồng bằng (Phụ lục B). Bảng này dùng để gợi ý khi phát cảnh báo khẩn cấp và để xếp ô chọn địa chỉ khi đăng ký.

### CN26. Quản lý đội cứu hộ

**Người dùng:** Admin.

**Mô tả:** Tên đội, căn cứ, số thành viên, số điện thoại, loại phương tiện (xe cứu hộ, xe máy, ca nô), các phường/xã thường phụ trách.

### CN27. Tình trạng dữ liệu và mô hình

**Người dùng:** Admin.

**Thông tin hiển thị:**

- Lần cập nhật dữ liệu hồ chứa và dữ liệu mưa gần nhất, lỗi gần nhất nếu có.

- Số giờ thiếu dữ liệu trong 7 ngày qua; các giờ có dữ liệu nghi ngờ.

- Phiên bản mô hình, ngày huấn luyện, khoảng dữ liệu đã dùng.

### CN28. Nhật ký hệ thống

**Người dùng:** Admin.

**Mô tả:** Ghi lại các thao tác quan trọng: đăng nhập của admin và đội cứu hộ, phát và kết thúc cảnh báo khẩn cấp, tiếp nhận và phân công SOS, duyệt điểm ngập, sửa ngưỡng, thay đổi phân quyền. Nhật ký chỉ được thêm, không được sửa hay xoá.

# 5. DANH SÁCH MÀN HÌNH

*Bảng 10. Các màn hình và đường dẫn*

| **Đường dẫn**                        | **Màn hình**                                            | **Vai trò**               | **Chức năng**    |
|--------------------------------------|---------------------------------------------------------|---------------------------|------------------|
| /                                    | Trang chủ: tổng quan hồ chứa, cảnh báo đang có, nút SOS | Tất cả                    | CN06, CN09       |
| /dang-ky, /dang-nhap, /quen-mat-khau | Tài khoản                                               | Chưa đăng nhập            | CN01–CN03        |
| /tai-khoan                           | Hồ sơ cá nhân                                           | Đã đăng nhập              | CN04             |
| /ho-chua/:ma                         | Chi tiết và dự báo hồ                                   | Tất cả                    | CN07             |
| /canh-bao                            | Cảnh báo khu vực                                        | Tất cả                    | CN09             |
| /thoi-tiet, /thoi-tiet/ban-do        | Thời tiết, bản đồ mưa                                   | Tất cả                    | CN13, CN14       |
| /sos                                 | Gửi SOS                                                 | Người dân, chưa đăng nhập | CN15             |
| /sos/cua-toi                         | Theo dõi SOS                                            | Người dân                 | CN16             |
| /diem-ngap/bao-cao                   | Báo điểm ngập                                           | Người dân, Đội cứu hộ     | CN20             |
| /cuu-ho/nhiem-vu                     | Nhiệm vụ và SOS chờ nhận                                | Đội cứu hộ                | CN19             |
| /admin                               | Bảng điều khiển: cảnh báo, tình trạng dữ liệu           | Admin                     | CN10, CN27       |
| /admin/sos                           | Điều phối SOS                                           | Admin                     | CN17, CN18       |
| /admin/canh-bao                      | Phát và lịch sử cảnh báo                                | Admin                     | CN11, CN12       |
| /admin/diem-ngap                     | Duyệt điểm ngập                                         | Admin                     | CN21             |
| /admin/thong-ke                      | Thống kê, tải dữ liệu                                   | Admin                     | CN08, CN22       |
| /admin/nguoi-dung, /admin/doi-cuu-ho | Người dùng, đội cứu hộ                                  | Admin                     | CN23, CN26       |
| /admin/danh-muc, /admin/nhat-ky      | Hồ chứa, ngưỡng, phường/xã, nhật ký                     | Admin                     | CN24, CN25, CN28 |

# 6. YÊU CẦU PHI CHỨC NĂNG

## 6.1. Bảo mật

- Mật khẩu băm bằng thuật toán mặc định của Django; không ghi mật khẩu vào nhật ký.

- Phân quyền kiểm tra ở API phía máy chủ, không chỉ ẩn nút trên giao diện.

- Dùng HTTPS khi triển khai; cấu hình CORS chỉ cho phép địa chỉ của frontend.

- Giới hạn tần suất với đăng nhập, đăng ký, gửi SOS và báo điểm ngập.

## 6.2. Quyền riêng tư

- Số điện thoại người gửi SOS chỉ admin và đội đã nhận SOS đó xem được; các đội khác chỉ thấy vị trí và mức ưu tiên để nhận nhiệm vụ.

- Điểm ngập hiển thị công khai không kèm thông tin người báo.

- Ẩn danh hoá SOS đã đóng sau 90 ngày (cấu hình được): xoá số điện thoại và ảnh, đổi tọa độ chính xác thành tên phường/xã; vẫn giữ thời điểm, phường/xã, thời gian xử lý và kết quả để thống kê.

## 6.3. Hiệu năng và độ tin cậy

- Trang tổng quan tải dưới 2 giây trong điều kiện mạng thông thường.

- Dữ liệu hồ chứa, mưa và dự báo cập nhật mỗi giờ; trang tổng quan tự tải lại mỗi 5 phút, màn hình điều phối mỗi 30 giây.

- Khi nguồn dữ liệu lỗi, vẫn hiển thị số liệu gần nhất kèm thông báo dữ liệu cũ; không hiển thị dự báo khi thiếu số liệu giờ mới nhất.

- Chức năng SOS hoạt động độc lập với module dự báo: nếu dự báo lỗi, SOS vẫn gửi và điều phối được.

## 6.4. Giao diện

- Tiếng Việt, hỗ trợ tốt trên điện thoại (ưu tiên với trang SOS, cảnh báo và nhiệm vụ cứu hộ).

- Chữ đủ lớn, độ tương phản cao, nút SOS dễ thấy và dễ bấm.

- Màu sắc mức cảnh báo thống nhất trên mọi màn hình, kèm chữ để không phụ thuộc hoàn toàn vào màu.

# 7. CÔNG NGHỆ SỬ DỤNG

*Bảng 11. Công nghệ dự kiến*

| **Thành phần**   | **Công nghệ**                                                                    |
|------------------|----------------------------------------------------------------------------------|
| Backend, API     | Python, Django, Django REST Framework, xác thực JWT                              |
| Cơ sở dữ liệu    | PostgreSQL (SQLite khi phát triển)                                               |
| Frontend         | React (Vite), React Router, Recharts (biểu đồ), Leaflet với bản đồ OpenStreetMap |
| Mô hình dự báo   | Các module đã đóng gói: xu_ly_du_lieu.py, du_bao.py; scikit-learn, XGBoost       |
| Nguồn dữ liệu    | Cổng thông tin PCTT Đà Nẵng (số liệu vận hành hồ), Open-Meteo (mưa và thời tiết) |
| Tính tuyến đường | OSRM trên dữ liệu OpenStreetMap                                                  |
| Chạy định kỳ     | Lệnh quản trị Django chạy mỗi giờ bằng cron (hoặc Celery Beat)                   |
| Gửi thông báo    | Thông báo trong website và email qua SMTP                                        |

# 8. KẾ HOẠCH TRIỂN KHAI THEO GIAI ĐOẠN

*Bảng 12. Thứ tự triển khai đề xuất*

| **Giai đoạn**        | **Nội dung**                                                                  | **Chức năng**               |
|----------------------|-------------------------------------------------------------------------------|-----------------------------|
| 1\. Nền tảng         | Tài khoản, phân quyền 3 vai trò, quản lý người dùng                           | CN01–CN05, CN23, CN28       |
| 2\. Dự báo           | Nạp dữ liệu, cập nhật mỗi giờ, trang hồ chứa, cảnh báo tự động                | CN06–CN10, CN12, CN24, CN27 |
| 3\. Thời tiết        | Danh mục phường/xã, thời tiết, bản đồ mưa                                     | CN13, CN14, CN25            |
| 4\. SOS và điều phối | Gửi và theo dõi SOS, đội cứu hộ, điểm ngập, gợi ý đội theo thời gian tiếp cận | CN15–CN21, CN26             |
| 5\. Hoàn thiện       | Cảnh báo khẩn cấp, gửi email, thống kê, kiểm thử toàn hệ thống                | CN11, CN22                  |

Trong phạm vi đồ án, dữ liệu điểm ngập và vị trí các đội cứu hộ được tạo ở mức mô phỏng để trình diễn chức năng điều phối; thông báo được gửi qua website và email, việc gửi tin nhắn SMS hoặc Zalo là hướng phát triển.

# 9. CÁC QUYẾT ĐỊNH ĐÃ CHỐT

*Bảng 13. Các quyết định thiết kế đã thống nhất*

| **STT** | **Nội dung**               | **Quyết định**                                                                                            |
|---------|----------------------------|-----------------------------------------------------------------------------------------------------------|
| 1       | Gửi SOS khi chưa đăng nhập | Cho phép, bắt buộc nhập số điện thoại                                                                     |
| 2       | Đội cứu hộ tự nhận SOS     | Sau 15 phút chưa có admin phân công                                                                       |
| 3       | Phường/xã vùng hạ du       | Theo Phụ lục B, chia 3 loại vùng: khu vực đập, hạ du gần, hạ du đồng bằng                                 |
| 4       | Kênh thông báo             | Website và email                                                                                          |
| 5       | Ngưỡng mực nước            | Hai bảng riêng: ngưỡng quy định theo thời kỳ (Quyết định 1865) và mực nước mục tiêu theo chỉ đạo từng đợt |
| 6       | Lưu vị trí SOS             | Ẩn danh hoá sau 90 ngày kể từ khi đóng                                                                    |
| 7       | Đăng ký tài khoản          | Email bắt buộc và phải xác thực; phường/xã chọn từ ô chọn 94 đơn vị, không nhập tự do                     |

## Việc còn lại trước khi lập trình

- Kiểm tra trên bản đồ các xã đánh dấu (\*) trong Phụ lục B: lần theo dòng sông từ từng đập xuôi về hạ du, xác định xã nằm phía trên hay phía dưới đập.

- Đối chiếu lại bản gốc Quyết định 1865/QĐ-TTg trước khi nạp Bảng A.1 và A.2 vào hệ thống.

# PHỤ LỤC A. NGƯỠNG MỰC NƯỚC VẬN HÀNH

Hệ thống phân biệt hai loại ngưỡng và lưu ở hai bảng riêng. Ngưỡng quy định là mức cố định theo thời kỳ trong mùa lũ. Mực nước mục tiêu điều hành là yêu cầu cụ thể của thành phố cho từng đợt mưa lũ, có thể khác ngưỡng quy định mà không mâu thuẫn. Cả hai đều là ngưỡng phục vụ vận hành và đón lũ, không phải ngưỡng mất an toàn của đập.

*Bảng A.1. Mực nước cao nhất trước lũ (m), theo Quyết định 1865/QĐ-TTg, Điều 6*

| **Hồ**       | **01/9 – 15/11** | **16/11 – 15/12** |
|--------------|------------------|-------------------|
| A Vương      | 376              | 377 – 380         |
| Đăk Mi 4     | 255              | 256 – 258         |
| Sông Bung 4  | 217,5            | 218,5 – 222,5     |
| Sông Tranh 2 | 172              | 173 – 175         |

*Bảng A.2. Mực nước đón lũ thấp nhất (m), theo Quyết định 1865/QĐ-TTg, Điều 6*

| **Hồ**       | **01/9 – 15/11** | **16/11 – 15/12** |
|--------------|------------------|-------------------|
| A Vương      | 370              | 377               |
| Đăk Mi 4     | 251,5            | 256               |
| Sông Bung 4  | 216              | 218,5             |
| Sông Tranh 2 | 165              | 173               |

*Bảng A.3. Cấu trúc bảng chỉ đạo điều hành*

| **Trường**            | **Nội dung**                            |
|-----------------------|-----------------------------------------|
| Hồ                    | Hồ được yêu cầu                         |
| Loại yêu cầu          | Không vượt mức / Hạ về mức              |
| Mực nước mục tiêu (m) | Giá trị yêu cầu                         |
| Bắt đầu               | Thời điểm bắt đầu vận hành theo yêu cầu |
| Hạn hoàn thành        | Thời điểm phải đạt mực nước mục tiêu    |
| Văn bản               | Số, ngày văn bản và cơ quan ban hành    |

*Bảng A.4. Ví dụ dữ liệu chỉ đạo điều hành năm 2025*

| **Văn bản**                | **Đăk Mi 4**     | **A Vương**    | **Sông Tranh 2** | **Hạn**        |
|----------------------------|------------------|----------------|------------------|----------------|
| 131/PTDS, 26/10/2025       | Không vượt 253,5 | Không vượt 372 | Không vượt 168   | Từ 12:30 26/10 |
| 3542/UBND-PTDS, 05/11/2025 | Hạ về 251,5      | Hạ về 373      | Hạ về 169        | 22:00 06/11    |
| Chỉ đạo ngày 28/11/2025    | 256,2            | 378            | 173,2            | 06:30 01/12    |

# PHỤ LỤC B. PHƯỜNG/XÃ THEO TỪNG HỒ

Tên đơn vị hành chính theo Nghị quyết 1659/NQ-UBTVQH15 (hiệu lực từ 01/7/2025). Danh sách do đề tài đề xuất dựa trên vị trí đập và mạng lưới sông; admin có thể điều chỉnh. Các xã đánh dấu (\*) cần kiểm tra thêm trên bản đồ.

*Bảng B.1. Liên kết hồ – phường/xã theo loại vùng*

| **Hồ**       | **Khu vực đập**            | **Hạ du gần**                           | **Hạ du đồng bằng** |
|--------------|----------------------------|-----------------------------------------|---------------------|
| A Vương      | Đông Giang\*, Sông Kôn\*   | Bến Hiên, Sông Vàng\*                   | Nhánh Vu Gia        |
| Sông Bung 4  | Nam Giang                  | Bến Giằng                               | Nhánh Vu Gia        |
| Đăk Mi 4     | Khâm Đức                   | Thạnh Mỹ\*                              | Nhánh Vu Gia        |
| Sông Tranh 2 | Trà Tân, Trà Đốc, Trà My\* | Lãnh Ngọc, Phước Trà, Hiệp Đức, Việt An | Nhánh Thu Bồn       |

*Bảng B.2. Các phường/xã hạ du đồng bằng*

| **Nhóm**                                      | **Phường/xã**                                                                                                                         |
|-----------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------|
| Nhánh Vu Gia (A Vương, Sông Bung 4, Đăk Mi 4) | Thượng Đức, Hà Nha, Phú Thuận, Vu Gia, Đại Lộc                                                                                        |
| Nhánh Thu Bồn (Sông Tranh 2)                  | Nông Sơn, Quế Phước                                                                                                                   |
| Vùng hợp lưu (cả 4 hồ)                        | Gò Nổi, Điện Bàn Tây, phường Điện Bàn, Thu Bồn, Duy Xuyên, Nam Phước, Duy Nghĩa, phường Hội An, phường Hội An Tây, phường Hội An Đông |

Cảnh báo theo đơn vị xã rộng hơn vùng ngập thực tế, vì không phải toàn bộ diện tích một xã đều nằm trong hành lang thoát lũ. Đây là giới hạn của hệ thống; riêng chức năng SOS dùng tọa độ GPS nên không bị ảnh hưởng.
