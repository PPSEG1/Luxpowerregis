from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import TimeoutException, UnexpectedAlertPresentException
import time
from datetime import datetime

def register_luxpower(customer_username, customer_email, dongle_sn, dongle_pin):
    driver = None
    try:
        # ==============================================================
        # ⚙️ ตั้งค่าบอท (ซ่อนหน้าจอ 100%)
        # ==============================================================
        options = webdriver.ChromeOptions()
        options.add_argument('--headless=new') # 🥷 เปิดโหมดซ่อนหน้าจอ (ไม่เด้งให้รำคาญตา)
        options.add_argument('--disable-gpu') # ป้องกันจอแครช
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--window-size=1920,1080') # จำลองขนาดหน้าจอให้บอทมองเห็นปุ่มครบ
        
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        wait = WebDriverWait(driver, 15)

        # --- 🛠️ ฟังก์ชันผู้ช่วย ---
        def safe_fill(element_id, target_text):
            el = wait.until(EC.presence_of_element_located((By.ID, element_id)))
            driver.execute_script("arguments[0].value = '';", el)
            el.clear()
            el.send_keys(target_text)
            time.sleep(0.3) 

        def accept_alert_if_present():
            try:
                WebDriverWait(driver, 3).until(EC.alert_is_present())
                alert = driver.switch_to.alert
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
                            elif "dismatch" in text.lower() or "mismatch" in text.lower():
                                return "Dongle PIN หรือข้อมูลไม่ถูกต้อง"
                            return f"ระบบปฏิเสธข้อมูล: {text}"
            except UnexpectedAlertPresentException:
                try:
                    driver.switch_to.alert.accept()
                except:
                    pass
            return None

        # ==========================================
        # STEP 1: Login (ในฐานะ Autohome Admin)
        # ==========================================
        print("\n⏳ [1/5] กำลังเข้าสู่ระบบแอดมิน (Autohome)...")
        driver.get("https://server.luxpowertek.com/") 
        wait.until(EC.presence_of_element_located((By.ID, "account")))
        
        safe_fill("account", "autohome.team")
        safe_fill("password", "am249197")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click() 
        wait.until(EC.url_contains("WManage"))
        time.sleep(2)

        # ==========================================
        # STEP 2: Add User (สร้างบัญชีลูกค้า)
        # ==========================================
        print(f"⏳ [2/5] กำลังสร้างบัญชีให้ลูกค้า: {customer_username}...")
        driver.get("https://server.luxpowertek.com/WManage/web/system/user/add/VIEWER")
        wait.until(EC.presence_of_element_located((By.ID, "account")))
        
        safe_fill("account", customer_username)
        safe_fill("password", "am123456789")
        safe_fill("repeatPassword", "am123456789")
        safe_fill("email", customer_email)
        Select(driver.find_element(By.ID, "timezone")).select_by_value("EAST7")
        
        driver.find_element(By.ID, "addButton").click()
        alert_text = accept_alert_if_present()
        time.sleep(2) 
        
        error_msg = check_for_danger_alerts()
        
        is_user_exist = False
        if alert_text and ("exist" in alert_text.lower() or "already" in alert_text.lower()):
            is_user_exist = True
        elif error_msg and "ซ้ำ" in error_msg:
            is_user_exist = True
            
        if is_user_exist:
            print("   ↳ ⚠️ บัญชีนี้เคยสมัครไว้แล้ว! กำลังข้ามไปขั้นตอนถัดไป...")
        else:
            if error_msg: raise Exception(f"[สร้างบัญชี] {error_msg}")

        # ==========================================
        # STEP 3: Logout แอดมิน & Login เข้าบัญชีลูกค้า
        # ==========================================
        print("\n🔄 [3/5] กำลังล็อกเอาท์แอดมิน และล็อกอินเข้าสู่บัญชีลูกค้า...")
        driver.delete_all_cookies() 
        driver.get("https://server.luxpowertek.com/") 
        
        wait.until(EC.presence_of_element_located((By.ID, "account")))
        safe_fill("account", customer_username)
        safe_fill("password", "am123456789")
        driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click() 
        time.sleep(3) # รอให้หน้าเว็บประมวลผลการล็อกอิน
        
        login_alert = accept_alert_if_present()
        if login_alert and ("error" in login_alert.lower() or "fail" in login_alert.lower() or "wrong" in login_alert.lower() or "incorrect" in login_alert.lower()):
            raise Exception(f"ไม่สามารถล็อกอินเข้าบัญชีลูกค้าได้ (รหัสผ่านอาจถูกเปลี่ยน): {login_alert}")

        # ⚠️ ดักจับหน้า Reset Password
        if len(driver.find_elements(By.ID, "resetPasswordButton")) > 0:
            print("   ↳ ⚠️ ระบบบังคับยืนยันรหัสผ่านใหม่ กำลังจัดการ...")
            safe_fill("password", "am123456789")
            safe_fill("repeatPassword", "am123456789")
            driver.find_element(By.ID, "resetPasswordButton").click()
            time.sleep(2)
            accept_alert_if_present()
            time.sleep(2)
            
            # ล็อกอินใหม่อีกรอบ
            if len(driver.find_elements(By.ID, "account")) > 0:
                print("   ↳ กำลังล็อกอินเข้าสู่ระบบอีกครั้ง...")
                safe_fill("account", customer_username)
                safe_fill("password", "am123456789")
                driver.find_element(By.CSS_SELECTOR, "button[type='submit']").click()
                time.sleep(3)

        # ⚠️ ให้เวลาเว็บลูกค้าเตรียม Dashboard 5 วินาทีเต็มๆ ป้องกันบอทช็อค
        print("   ↳ กำลังรอให้เว็บโหลดข้อมูลผู้ใช้ใหม่จนสมบูรณ์...")
        time.sleep(5)

        # ==========================================
        # STEP 4: Add Plant (ในฐานะลูกค้า)
        # ==========================================
        print(f"⏳ [4/5] กำลังสร้างไซต์งาน (ในชื่อของลูกค้า)...")
        driver.get("https://server.luxpowertek.com/WManage/web/config/plant/add")
        wait.until(EC.presence_of_element_located((By.ID, "name")))
        
        safe_fill("name", customer_email)
        today_date = datetime.now().strftime("%Y-%m-%d") 
        driver.execute_script(f"document.getElementById('createDate').value = '{today_date}';")
        safe_fill("nominalPower", "5000")
        
        Select(driver.find_element(By.ID, "continent")).select_by_value("ASIA")
        time.sleep(0.5)
        Select(driver.find_element(By.ID, "region")).select_by_value("SOUTHEAST_ASIA")
        time.sleep(0.5)
        Select(driver.find_element(By.ID, "country")).select_by_value("THAILAND")
        time.sleep(0.5)
        Select(driver.find_element(By.ID, "timezone")).select_by_value("EAST7")
        
        driver.find_element(By.ID, "addButton").click()
        alert_text = accept_alert_if_present()
        time.sleep(2) 
        
        error_msg = check_for_danger_alerts()
        
        is_plant_exist = False
        if alert_text and ("exist" in alert_text.lower() or "already" in alert_text.lower()):
            is_plant_exist = True
        elif error_msg and "ซ้ำ" in error_msg:
            is_plant_exist = True
            
        if is_plant_exist:
            print("   ↳ ⚠️ ไซต์งานนี้ถูกสร้างไว้แล้ว! กำลังข้ามไปหน้า Add Dongle...")
        else:
            if error_msg: raise Exception(f"[สร้างไซต์งาน] {error_msg}")

        # ==========================================
        # STEP 5: Add Dongle (ข้ามได้ถ้าไม่ใส่)
        # ==========================================
        if dongle_sn and dongle_pin:
            print(f"⏳ [5/5] กำลังไปที่หน้า Station เพื่อเพิ่ม Dongle (S/N: {dongle_sn})...")
            driver.get("https://server.luxpowertek.com/WManage/web/config/plant")
            time.sleep(3) # รอหน้าโหลด
            
            wait.until(EC.element_to_be_clickable((By.XPATH, "(//button[contains(., 'Station Management')])[1]"))).click()
            wait.until(EC.element_to_be_clickable((By.XPATH, "(//a[contains(text(), 'Add Dongle')])[1]"))).click()
            wait.until(EC.visibility_of_element_located((By.ID, "serialNumAddModal")))
            
            safe_fill("serialNumAddModal", dongle_sn)
            safe_fill("verifyCodeAddModal", dongle_pin)
            
            driver.find_element(By.ID, "addDatalogModalSubmit").click()
            alert_text = accept_alert_if_present()
            time.sleep(2) 
            
            error_msg = check_for_danger_alerts()
            if error_msg: raise Exception(f"[ผูก Dongle] {error_msg}")
            if alert_text and ("fail" in alert_text.lower() or "error" in alert_text.lower() or "exist" in alert_text.lower() or "already" in alert_text.lower()):
                raise Exception(f"[ผูก Dongle] อุปกรณ์นี้ถูกใช้งานไปแล้ว หรือมีข้อผิดพลาด: {alert_text}")
        else:
            print("⏭️ [5/5] ไม่มีข้อมูล Dongle - ข้ามขั้นตอนการเพิ่มอุปกรณ์")

        # ==========================================
        # พิมพ์ข้อความสรุปงานบน Terminal
        # ==========================================
        print("\n" + "="*50)
        print(f"🎉 เสร็จสมบูรณ์! จัดการบัญชีและไซต์งานให้ลูกค้าเรียบร้อยแล้ว")
        print("-" * 50)
        print("📌 สรุปข้อมูลการเข้าใช้งาน")
        print(f"Username: {customer_username}")
        print(f"Password: am123456789")
        if dongle_sn:
            print(f"Dongle S/N: {dongle_sn}")
        print("\n✅ ลูกค้านำยูเซอร์ไปใช้งานได้เลยครับ")
        print("="*50 + "\n")

    except Exception as e:
        print("\n" + "❌ "*20)
        print(f"เกิดข้อผิดพลาดtiger0084@gmail.com: {str(e)}")
        print("❌ "*20 + "\n")

    finally:
        if driver:
            driver.quit()

# ----------------------------------------
# ส่วนรับข้อมูลจากหน้า Terminal
# ----------------------------------------
if __name__ == "__main__":
    print("\n" + "="*50)
    print(" 🚀 Autohome Solarcell - สร้างบัญชี & แอด Dongle (โหมดนินจา ซ่อนหน้าจอ)")
    print("="*50)
    
    user_email = input("📩 1. พิมพ์ 'อีเมล' ลูกค้า: ").strip()
    
    if not user_email:
        print("\n❌ ไม่พบอีเมล ยกเลิกการทำงาน!")
    else:
        auto_username = user_email.split('@')[0]
        
        print("\n" + "-" * 50)
        print("🛑 ตัวเลือกเสริม: ใส่ Dongle เลยไหม? (ถ้ายังไม่มี ให้กด Enter ข้ามไปเลย)")
        dongle_sn = input("📡 2. พิมพ์ 'S/N' ของ Dongle (กด Enter เพื่อข้าม): ").strip()
        
        dongle_pin = ""
        if dongle_sn:
            dongle_pin = input("🔑 3. พิมพ์ 'PIN' ของ Dongle: ").strip()
            
        print("\n" + "-" * 50)
        print("🤖 กำลังเริ่มทำงานอยู่เบื้องหลัง กรุณารอสักครู่... (ห้ามปิดหน้าต่าง)")
        print("-" * 50)
        
        register_luxpower(auto_username, user_email, dongle_sn, dongle_pin)
