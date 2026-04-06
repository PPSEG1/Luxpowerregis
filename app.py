from flask import Flask, render_template, request, jsonify
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
import time
import threading
from datetime import datetime

app = Flask(__name__)
bot_lock = threading.Lock() # ป้องกันคิวชนกัน

def register_luxpower_installer(customer_username, customer_email, dongle_sn, dongle_pin):
    driver = None
    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new') 
        options.add_argument('--disable-gpu') 
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080')
        
        prefs = {"profile.managed_default_content_settings.images": 2}
        options.add_experimental_option("prefs", prefs)
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        
        wait = WebDriverWait(driver, 15) 
        short_wait = WebDriverWait(driver, 3) 

        def safe_fill(element_id, target_text):
            el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
            driver.execute_script("arguments[0].value = '';", el)
            el.clear()
            el.send_keys(target_text)
            time.sleep(0.3) 

        def safe_select(element_id, target_value):
            for _ in range(10): 
                try:
                    select = Select(driver.find_element(By.ID, element_id))
                    select.select_by_value(target_value)
                    return 
                except:
                    time.sleep(0.5) 
            raise Exception(f"เว็บโหลดตัวเลือก '{target_value}' ในช่อง '{element_id}' ไม่ทันครับ")

        def accept_alert_if_present():
            try:
                alert = short_wait.until(EC.alert_is_present())
                alert_text = alert.text
                alert.accept()
                return alert_text
            except TimeoutException:
                return None 

        def check_for_danger_alerts():
            try:
                alerts = driver.find_elements(By.CSS_SELECTOR, ".alert-danger")
                for alert in alerts:
                    if alert.is_displayed():
                        text = alert.text.strip()
                        if text:
                            if "exists" in text.lower() or "already" in text.lower():
                                return "ข้อมูลนี้มีอยู่ในระบบแล้ว (ซ้ำ)"
                            return f"ระบบปฏิเสธข้อมูล: {text}"
            except:
                pass
            return None

        # STEP 1: Login
        driver.get("https://server.luxpowertek.com/") 
        wait.until(EC.presence_of_element_located((By.ID, "account")))
        safe_fill("account", "autohome.team")
        safe_fill("password", "am249197")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click() 
        wait.until(EC.url_contains("WManage"))
        time.sleep(2) 

        # STEP 2: Add User (INSTALLER)
        driver.get("https://server.luxpowertek.com/WManage/web/system/user/add/INSTALLER")
        wait.until(EC.presence_of_element_located((By.ID, "account")))
        time.sleep(1) 
        
        safe_fill("account", customer_username)
        safe_fill("password", "am123456789")
        safe_fill("repeatPassword", "am123456789")
        safe_fill("email", customer_email)
        safe_select("timezone", "EAST7")
        
        installer_code = f"AH{customer_username}99"[:25] 
        safe_fill("customerCode", installer_code)
        safe_select("techInfoType", "EMAIL")
        safe_fill("techInfo", customer_email)
        
        driver.find_element(By.ID, "addButton").click()
        alert_text = accept_alert_if_present() 
        time.sleep(2) 
        error_msg = check_for_danger_alerts()
        
        if alert_text and ("exist" in alert_text.lower() or "already" in alert_text.lower()):
            pass # ซ้ำไม่เป็นไร ข้ามได้
        elif error_msg and "ซ้ำ" in error_msg:
            pass
        elif error_msg:
            raise Exception(f"[สร้างบัญชี] {error_msg}")

        # STEP 3: Logout & Login As Installer
        driver.delete_all_cookies() 
        driver.get("https://server.luxpowertek.com/") 
        wait.until(EC.presence_of_element_located((By.ID, "account")))
        safe_fill("account", customer_username)
        safe_fill("password", "am123456789")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click() 
        time.sleep(3) 
        
        # ดักหน้า Reset Password
        reset_buttons = driver.find_elements(By.ID, "resetPasswordButton")
        if len(reset_buttons) > 0:
            safe_fill("password", "am123456789")
            safe_fill("repeatPassword", "am123456789")
            reset_buttons[0].click()
            accept_alert_if_present()
            time.sleep(2)
            if len(driver.find_elements(By.ID, "account")) > 0:
                safe_fill("account", customer_username)
                safe_fill("password", "am123456789")
                driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                time.sleep(3)

        try: wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".sidebar, .main-header, #menu")))
        except: pass
        time.sleep(2)

        # STEP 4: Add Plant
        driver.get("https://server.luxpowertek.com/WManage/web/config/plant/add")
        wait.until(EC.presence_of_element_located((By.ID, "name")))
        time.sleep(1)
        
        safe_fill("name", customer_email)
        today_date = datetime.now().strftime("%Y-%m-%d") 
        driver.execute_script(f"document.getElementById('createDate').value = '{today_date}';")
        safe_fill("nominalPower", "5000")
        
        safe_select("continent", "ASIA")
        safe_select("region", "SOUTHEAST_ASIA")
        safe_select("country", "THAILAND")
        safe_select("timezone", "EAST7")
        
        driver.find_element(By.ID, "addButton").click()
        alert_text = accept_alert_if_present() 
        time.sleep(2)
        error_msg = check_for_danger_alerts()
        
        if alert_text and ("exist" in alert_text.lower() or "already" in alert_text.lower()):
            pass
        elif error_msg and "ซ้ำ" in error_msg:
            pass
        elif error_msg: 
            raise Exception(f"[สร้างไซต์งาน] {error_msg}")

        # STEP 5: Add Dongle
        if dongle_sn and dongle_pin:
            driver.get("https://server.luxpowertek.com/WManage/web/config/plant")
            time.sleep(3) 
            wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[contains(., 'Station Management')])[1]"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "(//a[contains(text(), 'Add Dongle')])[1]"))).click()
            wait.until(EC.visibility_of_element_located((By.ID, "serialNumAddModal")))
            time.sleep(1)
            
            safe_fill("serialNumAddModal", dongle_sn)
            safe_fill("verifyCodeAddModal", dongle_pin)
            driver.find_element(By.ID, "addDatalogModalSubmit").click()
            alert_text = accept_alert_if_present() 
            time.sleep(2)
            
            error_msg = check_for_danger_alerts()
            if error_msg: raise Exception(f"[ผูก Dongle] {error_msg}")
            if alert_text and ("fail" in alert_text.lower() or "error" in alert_text.lower() or "exist" in alert_text.lower() or "already" in alert_text.lower()):
                raise Exception(f"[ผูก Dongle] มีข้อผิดพลาด: {alert_text}")

        # ข้อความตอบกลับไปที่หน้าเว็บ
        success_msg = (
            f"🎉 <b>เสร็จสมบูรณ์!</b> จัดการบัญชีช่างเรียบร้อย<br><br>"
            f"📌 <u>สรุปข้อมูลการเข้าใช้งาน</u><br>"
            f"User: <b>{customer_username}</b><br>"
            f"Pass: <b>am123456789</b><br>"
            f"Installer Code: <b>{installer_code}</b><br>"
        )
        if dongle_sn: success_msg += f"Dongle S/N: <b>{dongle_sn}</b><br>"
        success_msg += "<br>✅ ส่งมอบให้ช่างนำไปล็อกอินใช้งานได้เลยครับ"

        return {"status": "success", "message": success_msg}

    except Exception as e:
        return {"status": "error", "message": f"❌ <b>เกิดข้อผิดพลาด:</b><br>{str(e)}"}
    finally:
        if driver: driver.quit()

# API สำหรับรับข้อมูลจากหน้าเว็บ
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/run-bot', methods=['POST'])
def run_bot():
    if not bot_lock.acquire(blocking=False):
        return jsonify({"status": "error", "message": "⚠️ <b>คิวเต็ม!</b> มีคนอื่นกำลังใช้งานบอทอยู่ กรุณารอสักครู่แล้วกดใหม่ครับ"})
    try:
        email = request.form.get('email', '').strip()
        sn = request.form.get('sn', '').strip()
        pin = request.form.get('pin', '').strip()
        
        if not email: return jsonify({"status": "error", "message": "❌ กรุณากรอกอีเมล!"})
        if sn and not pin: return jsonify({"status": "error", "message": "❌ กรุณากรอก PIN ด้วยครับ!"})

        username = email.split('@')[0]
        result = register_luxpower_installer(username, email, sn, pin)
        return jsonify(result)
    finally:
        bot_lock.release()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)