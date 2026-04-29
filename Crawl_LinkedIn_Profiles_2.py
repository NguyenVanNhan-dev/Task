# @title 🚀 FINAL FIX: Title & Location (Deep Scan Mode)
import os
import time
import pickle
import random
import gspread
import re
import json
import requests
from google.auth import default
from google import auth

from IPython.display import Image, display

# Selenium Imports
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from google.oauth2.service_account import Credentials
import gspread
# --- CẤU HÌNH ---
SHEET_ID_OR_URL = 'https://docs.google.com/spreadsheets/d/1OhjIaXVwbO3x_Iu07h3s5fJzzXO1SezOw1K_Hl7LtOc/edit?gid=0#gid=0'
INPUT_TAB_NAME = "Sheet1"

# TÀI KHOẢN
USERNAME = os.environ.get("LINKEDIN_USER")
PASSWORD = os.environ.get("LINKEDIN_PASS")
if not USERNAME or not PASSWORD:
    print("❌ LỖI: Không tìm thấy LINKEDIN_USER hoặc LINKEDIN_PASS trong môi trường!")
    # Đừng chạy tiếp nếu thiếu thông tin quan trọng
COOKIES_FILE = 'linkedin_cookies.pkl'
CREDENTIALS_FILE = 'linkedin_credentials.pkl'
# --- 1. SETUP DRIVER ---
def setup_driver():
    options = webdriver.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

# --- 2. KẾT NỐI GOOGLE SHEET ---
def connect_google_sheet():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]

        creds = Credentials.from_service_account_file(
    "vivid-layout-492502-m1-ec6b14b41e28.json",
    scopes=scope
)

        gc = gspread.authorize(creds)

        sh = gc.open_by_url(SHEET_ID_OR_URL) \
            if "http" in SHEET_ID_OR_URL \
            else gc.open_by_key(SHEET_ID_OR_URL)

        print("✅ Kết nối Google Sheet thành công")
        return sh

    except Exception as e:
        print(f"⚠️ Lỗi kết nối Sheet: {e}")
        return None
def get_missive_linkedin_code():
    MISSIVE_API_KEY = os.environ.get("MISSIVE_API_KEY")
    HEADERS = {
        "Authorization": f"Bearer {MISSIVE_API_KEY}",
        "Content-Type": "application/json",
    }
    # Fix lỗi 400 bằng cách lấy inbox cá nhân hoặc shared
    # Bạn có thể thử thay "personal" bằng "shared" nếu không ra kết quả
    PARAMS = {"limmit": 20, "inbox": "true"}

    try:
        response = requests.get(
            "https://public.missiveapp.com/v1/conversations", 
            headers=HEADERS, 
            params=PARAMS
        )
        
        if response.status_code != 200:
            return None

        conversations = response.json().get("conversations", [])
        
        for c in conversations:
            # 1. Kiểm tra xem có đúng là email từ LinkedIn không
            authors = c.get("authors", [])
            is_linkedin = any(a.get("name") == "LinkedIn" for a in authors)
            
            if is_linkedin:
                subject = c.get("latest_message_subject", "")
                # 2. Dùng Regex lấy đúng 6 số (an toàn hơn split)
                import re
                match = re.search(r'\b\d{6}\b', subject)
                if match:
                    return match.group(0)
                    
        return None
    except Exception as e:
        print(f"Lỗi: {e}")
        return None

    except Exception as e:
        print(f"❌ Lỗi kết nối API: {e}")
        return None
# --- 3. LOGIN ---
def login_linkedin(driver):
    """
    Hàm đăng nhập LinkedIn tổng hợp:
    Kiểm tra Cookies -> Đăng nhập Password -> Xử lý OTP -> Lưu lại Cookies mới.
    """
    print("INFO: Đang truy cập LinkedIn...")
    driver.get("https://www.linkedin.com/login")
    time.sleep(2)

    # 1. Kiểm tra và tải Cookies nếu trùng khớp thông tin đăng nhập
    credentials_changed = True
    if os.path.exists(CREDENTIALS_FILE):
        with open(CREDENTIALS_FILE, "rb") as f:
            old_creds = pickle.load(f)
            if old_creds.get('username') == USERNAME and old_creds.get('password') == PASSWORD:
                credentials_changed = False

    if not credentials_changed and os.path.exists(COOKIES_FILE):
        print("INFO: Đang thử đăng nhập bằng Cookies...")
        with open(COOKIES_FILE, "rb") as f:
            for cookie in pickle.load(f):
                try: driver.add_cookie(cookie)
                except: pass
        driver.refresh()
        time.sleep(5)

        if "feed" in driver.current_url or driver.find_elements(By.CLASS_NAME, 'global-nav__me-photo'):
            print("INFO: Đăng nhập thành công bằng Cookies!")
            return True

    # 2. Nếu Cookies thất bại hoặc đổi tài khoản -> Đăng nhập bằng Password
    print("INFO: Tiến hành đăng nhập bằng tài khoản và mật khẩu...")
    try:
        WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(5)

        # --- 3. Xử lý xác thực mã PIN (OTP) tự động qua Missive API ---
        try:
            # Kiểm tra xem có trường nhập mã pin không (LinkedIn dùng ID này cho trang xác thực)
            pin_field = driver.find_elements(By.ID, "input__email_verification_pin")
            
            if pin_field:
                print("⚠️ CẢNH BÁO: LinkedIn yêu cầu mã xác thực từ Email!")
                print("📡 Đang tự động quét mã OTP từ Missive API...")

                otp_code = None
                # Thử lấy mã 5 lần, mỗi lần cách nhau 10 giây để đợi mail về
                for attempt in range(1, 6):
                    print(f"🔄 Thử lấy mã lần {attempt}...")
                    otp_code = get_missive_linkedin_code() # Gọi hàm dùng API Key của bạn
                    
                    if otp_code:
                        print(f"✅ Đã tìm thấy mã OTP: {otp_code}")
                        break
                    
                    if attempt < 5:
                        time.sleep(10) # Đợi mail đổ về inbox
                
                if otp_code:
                    pin_field[0].send_keys(otp_code)
                    # Tìm nút submit (ID thường là email-pin-submit-button)
                    try:
                        driver.find_element(By.ID, "email-pin-submit-button").click()
                        print("🚀 Đã điền mã và nhấn gửi!")
                        time.sleep(5)
                    except:
                        print("❌ Không tìm thấy nút Submit OTP.")
                else:
                    print("🛑 LỖI: Đã thử 5 lần nhưng không lấy được mã OTP từ API.")
                    # Bạn có thể chọn dừng chương trình hoặc chụp ảnh màn hình tại đây

        except Exception as e:
            print(f"INFO: Không phát hiện yêu cầu OTP hoặc lỗi xử lý: {e}")

        # 4. Kiểm tra đăng nhập thành công và Lưu Cookies/Credentials
        if "feed" in driver.current_url or driver.find_elements(By.CLASS_NAME, 'global-nav__me-photo'):
            with open(COOKIES_FILE, "wb") as f:
                pickle.dump(driver.get_cookies(), f)
            with open(CREDENTIALS_FILE, "wb") as f:
                pickle.dump({"username": USERNAME, "password": PASSWORD}, f)
            print("INFO: Đăng nhập thành công và đã cập nhật Cookies mới!")
            return True
        else:
            print("ERROR: Đăng nhập thất bại. Vui lòng kiểm tra lại tài khoản hoặc giao diện web.")
            return False

    except Exception as e:
        print(f"ERROR: Lỗi trong quá trình đăng nhập: {e}")
        return False

# --- 4. CRAWL PROFILE (HÀM FIX TRIỆT ĐỂ) ---
def crawl_profile(driver, raw_url):
    try:
        url = raw_url.strip()
        driver.get(url)

        print(f"--- Processing: {url}")
        time.sleep(random.uniform(5, 7))
        page_source = driver.page_source
        if "This page doesn’t exist" in page_source or "Page not found" in driver.title:
            print(f"⚠️ Cảnh báo: Hồ sơ không tồn tại (404).")
            return {
                "Name": "No Profile",
                "Title": "",
                "Location": "",
                "Connection": "",
                "Company": ""
            }, "NOT_FOUND"


        # Cuộn trang nhiều lần để kích hoạt dữ liệu ẩn
        for _ in range(3):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1)

        if any(x in driver.current_url for x in ["login", "authwall", "checkpoint", "challenge"]):
            print("Debug: Auth wall detected.")
            # Chụp screenshot
            filename = f"authwall_{int(time.time())}.png"
            driver.save_screenshot(filename)

            # Hiển thị ảnh trong Colab
            from IPython.display import Image, display
            display(Image(filename))
            return None, "AUTH_WALL"

        data_js = driver.execute_script("""

        const txt = (sel) => document.querySelector(sel)?.innerText.trim() || "";

        const sideBarElements = Array.from(document.querySelectorAll('div[role="button"]'))
            .map(el => el.innerText.trim())
            .filter(t => t.length > 3 && !t.includes('connection') && !t.includes('follower') && !t.includes('kết nối'));

        const lines = Array.from(document.querySelectorAll('p'))
            .map(el => el.innerText.trim())
            .filter(t => t.length > 0);

        const title = lines.find(t => t.includes(" at ") || t.length > 20) || "";
        let loc = "";

        const contactAnchor = document.querySelector('a[href*="contact-info"]');
        if (contactAnchor) {
            const parentText = contactAnchor.closest('div')?.innerText || "";

            loc = parentText
                .split('·')[0]          // bỏ phần sau dấu chấm
                .replace('Contact info', '')
                .trim();
        }
        return {
            name: txt('h1.text-heading-xlarge') || txt('div[data-display-contents="true"] h2') || txt('h2') || "",
            title,
            location : loc || txt('span.text-body-small.inline.t-black--light.break-words') || txt('span[class*="location"]') || "",
            company_list: sideBarElements.slice(0, 2).join(" | ") || "",
            connection_raw: document.body.innerText
        };
        """)

        name = data_js.get('name', '')
        title = data_js.get('title', '')
        location = data_js.get('location', '')
        company = data_js.get('company_list', '')
        conn_source = data_js.get('connection_raw', '')

        # # Fallback: Nếu vẫn trống công ty, thử lấy từ Title (thường sau dấu "at")
        # if not company and " at " in title:
        #     company = title.split(" at ")[-1].split("|")[0].strip()

        print(f"Debug: Extracted Name: {name}")
        print(f"Debug: Extracted Companies: {company}")

        connection = ""
        match = re.search(r'([\d,\.\+]+)\s*(connections|kết nối|followers|người theo dõi)', conn_source, re.I)
        if match:
            number = match.group(1)
            connection = f"{number} connections"

        print(f"Debug: Stats - Title: {len(title)} chars, Loc: {len(location)} chars, Comp: {len(company)} chars")

        return {
            "Name": name, "Title": title, "Location": location, "Connection": connection, "Company": company
        }, "Success"

    except Exception as e:
        print(f"Debug: Error at {url} - {str(e)}")
        return None, str(e)

# --- 5. MAIN ---
def main():
    MAX_PROFILE = 20
    count = 0
    sh = connect_google_sheet()
    if not sh: return
    ws = sh.worksheet(INPUT_TAB_NAME)
    # Lấy toàn bộ dữ liệu của Sheet để kiểm tra (tránh gọi API nhiều lần)
    all_rows = ws.get_all_values()
    # all_rows[0] là header, dữ liệu bắt đầu từ index 1

    driver = setup_driver()
    if not login_linkedin(driver): return

    # Chạy từ dòng thứ 2 (index 1)
    for i in range(1, len(all_rows)):
        if count >= MAX_PROFILE:
            print("reached max limit")
            break
        row_data = all_rows[i]
        url = row_data[0].strip() if len(row_data) > 0 else ""

        # 1. KIỂM TRA URL TRỐNG
        if not url or "linkedin.com/in/" not in url:
            print(f"⏩ Dòng {i+1}: Bỏ qua do URL trống hoặc không hợp lệ.")
            continue

        # 2. KIỂM TRA DỮ LIỆU ĐÃ CÓ CHƯA (Cột G - Status thường là index 6)
        # Giả sử: Cột A(0):URL, B(1):Name, ..., G(6):Status
        if len(row_data) >= 7:
            status_existing = row_data[6]
            if status_existing in ["Success", "NOT_FOUND", "No Profile"]:
                print(f"⏭️ Dòng {i+1}: Đã có dữ liệu ({status_existing}), bỏ qua.")
                continue

        # Nếu vượt qua các kiểm tra trên thì mới tiến hành Crawl
        print(f"🔄 Đang xử lý dòng {i+1}: {url}")
        data, status = crawl_profile(driver, url)
        row = i + 1
        if data and data.get('Name') == "No Profile":
            # === TRƯỜNG HỢP PROFILE KHÔNG TỒN TẠI ===
            ws.update(range_name=f"B{row}:G{row}", values=[[
                "No Profile", "", "", "", "", ""
            ]])
            print(f"   ⚠️ Profile không tồn tại (NOT_FOUND)")

        elif data and data.get('Name') and data['Name'] != "No Profile":
            # === THÀNH CÔNG ===
            ws.update(range_name=f"B{row}:G{row}", values=[[
                data['Name'],
                data['Title'],
                data['Location'],
                data['Connection'],
                data['Company'],
                "Success"
            ]])
            print(f"   ✅ OK: {data['Name']}")

        else:
            # === LỖI KHÁC ===
            error_msg = f"Error: {status}"
            ws.update(range_name=f"B{row}:G{row}", values=[[
                "", "", "", "", "", error_msg
            ]])
            print(f"   ❌ {error_msg}")

            if status == "AUTH_WALL":
                print("🛑 Dừng do Auth Wall!")
                break

        count +=1


        time.sleep(random.randint(3, 6))

    driver.quit()

if __name__ == "__main__":
    main()
    print("✅ Done!")
