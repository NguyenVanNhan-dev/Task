# Cài đặt 
## 1. Cài thư viện
```bash
pip install selenium webdriver-manager gspread google-auth
```
## 2. Cấu hình Google Sheet
- Tạo Service Account trên Google Cloud
- Download file JSON credentials
- Share Google Sheet cho email service account
- Update đường dẫn tới Google Sheet :
```bash
Credentials.from_service_account_file("path_to_json.json")
```
## 3. Cấu hình tài khoản LinkedIn
```bash 
USERNAME = "your_email"
PASSWORD = "your_password"
```
## 4. Cấu hình Google Sheet
```bash 
SHEET_ID_OR_URL = "your_google_sheet_url"
INPUT_TAB_NAME = "Sheet1"
```
# Cách chạy
- Bước 1 : Tải Visual Studio Code từ link : https://code.visualstudio.com/thank-you?dv=win64user
- Bước 2 : Tải Python từ link : https://www.python.org/downloads/release/python-3110/
- Bước 3 : Chạy câu lệnh sau :
```bash
python Crawl_LinkedIn_Profiles_2.py
```
