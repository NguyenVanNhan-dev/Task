# @title 🚀 FINAL FIX: Title & Location (Deep Scan Mode)
import os
import time
import pickle
import random
import gspread
import re
import json
import undetected_chromedriver as uc
from google.auth import default

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
COOKIES_FILE = 'linkedin_cookies.pkl'
SHEET_ID_OR_URL = 'https://docs.google.com/spreadsheets/d/1OhjIaXVwbO3x_Iu07h3s5fJzzXO1SezOw1K_Hl7LtOc/edit?gid=0#gid=0'
INPUT_TAB_NAME = "Sheet1"

# TÀI KHOẢN
USERNAME = os.environ.get("LINKEDIN_USER")
PASSWORD = os.environ.get("LINKEDIN_PASS")

# --- 1. SETUP DRIVER ---
def setup_driver():
    options = uc.ChromeOptions()
    options.add_argument('--headless=new')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])

    driver = uc.Chrome(options=options, version_main=None)
    driver.set_page_load_timeout(90)
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
# --- 3. LOGIN ---
def login_with_cookies(driver):
    driver.get("https://www.linkedin.com")
    time.sleep(3)
    
    # Lấy cookies từ GitHub Secret (được truyền qua biến môi trường)
    cookies_json = os.environ.get("LINKEDIN_COOKIES")
    
    if cookies_json:
        cookies = json.loads(cookies_json)
        for cookie in cookies:
            # Loại bỏ thuộc tính 'sameSite' nếu có để tránh lỗi Selenium
            if 'sameSite' in cookie:
                del cookie['sameSite']
            try:
                driver.add_cookie(cookie)
            except:
                pass
        
        driver.get("https://www.linkedin.com/feed/")
        time.sleep(5)
        
        if "feed" in driver.current_url or "checkpoint" not in driver.current_url:
            print("✅ Đăng nhập bằng Cookie thành công!")
            return True
            
    print("❌ Cookie hết hạn hoặc không hợp lệ. Đang thử Login bằng Pass...")
    return False # Nếu fail thì mới chạy tiếp hàm login_linkedin cũ của bạn
def login_linkedin(driver):
    driver.get("https://www.linkedin.com/login")
    if os.path.exists(COOKIES_FILE):
        with open(COOKIES_FILE, "rb") as f:
            for cookie in pickle.load(f):
                try: driver.add_cookie(cookie)
                except: pass
        driver.refresh()
        time.sleep(5)
    if "feed" in driver.current_url: return True

    try:
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "username"))).send_keys(USERNAME)
        driver.find_element(By.ID, "password").send_keys(PASSWORD)
        driver.find_element(By.XPATH, "//button[@type='submit']").click()
        time.sleep(10)
        with open(COOKIES_FILE, "wb") as f:
            pickle.dump(driver.get_cookies(), f)
        return True
    except: return False

# --- 4. CRAWL PROFILE (HÀM FIX TRIỆT ĐỂ) ---
def crawl_profile(driver, raw_url):
    try:
        url = raw_url.strip()
        driver.get(url)

        print(f"--- Processing: {url}")
        time.sleep(random.uniform(10, 16))
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
        for _ in range(4):
            driver.execute_script("window.scrollBy(0, 500);")
            time.sleep(1.5)

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
    urls = ws.col_values(1)

    driver = setup_driver()
    if not login_with_cookies(driver): return

    for i in range(1, len(urls)):
        url = urls[i]
        if "linkedin.com/in/" not in url: continue

        print(f"🔄 Đang xử lý: {url}")
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
        if count >= MAX_PROFILE:
            print("reached max limit")
            break

        time.sleep(random.randint(15, 28))

    driver.quit()

if __name__ == "__main__":
    main()
    print("✅ Done!")
