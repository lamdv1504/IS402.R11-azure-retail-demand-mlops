# QUY ĐỊNH GIT & GITHUB CHO NHÓM

### 1. Trước khi bắt đầu công việc

Bắt buộc cập nhật nhánh `main` mới nhất trước khi tạo nhánh mới.

```bash
git switch main
git pull origin main
git switch -c feat/ten-task
```

### 2. Trong quá trình làm việc

- Mỗi task phải tạo một nhánh riêng.
- Không được code hoặc push trực tiếp lên `main`.
- Chỉ commit những file liên quan đến task.
- Không tự ý chỉnh sửa hoặc xóa code của thành viên khác.

### 3. Sau khi hoàn thành task

```bash
git add .
git commit -m "feat: mo ta cong viec"
git push -u origin feat/ten-task
```

### 4. Quy định Merge

- Tạo Pull Request từ nhánh đang làm vào `main`.
- **Bắt buộc yêu cầu tài khoản `@lamdv1504` Review.**
- Chỉ được Merge khi đã được Approve.
- Nếu có yêu cầu chỉnh sửa thì phải sửa trước khi Merge.

### 5. Hạn chế Conflict

- Luôn `pull` nhánh `main` mới nhất trước khi tạo nhánh làm việc.
- Các thành viên cần trao đổi trước nếu cùng chỉnh sửa một file hoặc chức năng.
- Hạn chế để nhánh tồn tại quá lâu mà không cập nhật code.
- Trước khi tạo Pull Request, nên cập nhật thay đổi mới nhất từ `main` vào nhánh đang làm:

```bash
git fetch origin
git merge origin/main
```

- Không tự ý ghi đè hoặc xóa thay đổi của thành viên khác.

### 6. Xử lý khi xảy ra Conflict

**Bước 1:** Xác định các file bị conflict.

```bash
git status
```

**Bước 2:** Mở file bị conflict trong VS Code, kiểm tra và lựa chọn nội dung phù hợp.

- `Accept Current Change`: Giữ thay đổi hiện tại.
- `Accept Incoming Change`: Giữ thay đổi được merge vào.
- `Accept Both Changes`: Giữ cả hai thay đổi nếu phù hợp.

**Bước 3:** Chỉnh sửa lại code, xóa các dấu conflict nếu còn và kiểm tra chương trình.

**Bước 4:** Sau khi giải quyết xong, commit và push:

```bash
git add .
git commit -m "fix: resolve merge conflicts"
git push
```

**Lưu ý:**
- Nếu không chắc chắn cách xử lý, phải trao đổi với thành viên liên quan.
- Không được xóa code của người khác chỉ để giải quyết conflict.
- Phải kiểm tra lại chức năng sau khi xử lý conflict.
- Nếu conflict phát sinh khi merge `main` vào nhánh làm việc, chỉ hoàn tất merge sau khi đã giải quyết các file xung đột.

### 7. Sau khi Merge

- Xóa nhánh đã hoàn thành nếu không còn cần sử dụng.
- Trước khi làm task tiếp theo, phải quay về `main`, pull code mới nhất và tạo nhánh mới.

---

### Quy trình chung

**Pull main → Tạo nhánh → Code → Commit → Push → Cập nhật main nếu cần → Pull Request → Review → Approve → Merge main**

**Nguyên tắc quan trọng:** Không push trực tiếp lên `main`, không tự ý ghi đè code và không merge khi chưa được `@lamdv1504` Approve.