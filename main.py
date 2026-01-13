import time
import pandas as pd
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# --- HELPER TO CLEAN NASTY CHARACTERS ---
def clean_text(text):
    """
    Scrubbing the dirty characters so Excel doesn't cry.
    """
    if not isinstance(text, str):
        return text
    # Remove non-printable characters (ASCII 0-31 except tab/newline)
    return re.sub(r'[\x00-\x1F\x7F]+', '', text).strip()

# --- CLOUD SETTINGS ---
options = webdriver.ChromeOptions()
options.add_argument('--headless=new') 
options.add_argument('--start-maximized') 
options.add_argument('--window-size=1920,1080')
options.add_argument('--disable-blink-features=AutomationControlled') 
options.add_argument('--no-sandbox') 
options.add_argument('--disable-dev-shm-usage') 
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-gpu') 
options.add_argument('--disable-backgrounding-occluded-windows')
options.add_argument('--disable-renderer-backgrounding')
options.add_argument('--disable-popup-blocking') 
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# --- START ---
print("Bootleg Chat: Паля гумите...")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

all_data = []
output_filename = "bg_medics_dynamic.xlsx" 

def get_text_safe(element, xpath):
    try:
        val = element.find_element(By.XPATH, xpath).text.strip()
        return val if val else "-"
    except:
        return "-"

def get_attr_safe(element, attr):
    try:
        val = element.get_attribute(attr)
        return val if val else "-"
    except:
        return "-"

def save_to_excel(data, filename):
    if not data: return
    try:
        df = pd.DataFrame(data)
        df.to_excel(filename, index=False)
        # Няма да принтим "Saved" всеки път, че конзолата ще стане на салата
    except Exception as e:
        print(f"   [ERROR] Мамка му, не можах да запиша файла: {e}")

print("Bootleg Chat: Атака...")

# --- OUTER LOOP: REGIONS ---
for r in range(23, 29): 
    region_code = f"{r:02d}"
    page_num = 1 
    
    print(f"\n========================================")
    print(f"🏥 ЗАПОЧВАМЕ РЕГИОН: {region_code}")
    print(f"========================================")

    # --- INNER LOOP: PAGES ---
    while True:
        target_url = f"https://blsbg.eu/bg/medics/unionlist/{region_code}?UIN_page={page_num}"
        
        print(f"  > Отварям стр. {page_num} за регион {region_code}...")
        
        try:
            driver.get(target_url)
        except Exception:
            time.sleep(2)
            try:
                driver.get(target_url)
            except:
                print("  ! Отказвам се от тая страница.")
                break 

        if "404" in driver.title or "Page not found" in driver.page_source:
            print(f"  🏁 Регион {region_code} приключи.")
            break

        try:
            rows = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, "//table//tr[td]"))
            )
        except TimeoutException:
            if "Няма намерени" in driver.page_source:
                print(f"  🏁 Регион {region_code} е празен.")
                break
            else:
                print("  ! Timeout. Refresh...")
                driver.refresh()
                try:
                    rows = WebDriverWait(driver, 10).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//table//tr[td]"))
                    )
                except:
                    print("  ! Пак греда. Скип.")
                    break

        # --- DATA COLLECTION ---
        summary_text = "-"
        is_last_page = False
        
        try:
            summary_element = driver.find_element(By.CSS_SELECTOR, "div.summary")
            summary_text = clean_text(summary_element.text)
            
            match = re.search(r'-(\d+)\s+от\s+(\d+)', summary_text)
            if match:
                current_end = int(match.group(1))
                total_records = int(match.group(2))
                percentage = (current_end / total_records) * 100
                print(f"    [Info] Прогрес: {percentage:.2f}% ({current_end}/{total_records})")
                if current_end >= total_records:
                    is_last_page = True
        except NoSuchElementException:
            pass

        for row in rows:
            try:
                uin = get_text_safe(row, "./td[1]")
                
                try:
                    img = row.find_element(By.CSS_SELECTOR, "img.expand")
                    adr = get_attr_safe(img, "adr")
                    gadr = get_attr_safe(img, "gadr")
                    tel = get_attr_safe(img, "tel")
                    wrk = get_attr_safe(img, "wrk")
                    spec_attr = get_attr_safe(img, "spec")
                except NoSuchElementException:
                    adr = gadr = tel = wrk = spec_attr = "-"

                name = get_text_safe(row, "./td[3]")
                spec_text = get_text_safe(row, "./td[4]")

                data_row = {
                    "Region Code": clean_text(region_code),
                    "UIN": clean_text(uin),
                    "Address (Hidden)": clean_text(adr),
                    "G Address (Hidden)": clean_text(gadr),
                    "Phone": clean_text(tel),
                    "Workplace": clean_text(wrk), 
                    "Specialty (Hidden)": clean_text(spec_attr),
                    "Name": clean_text(name),
                    "Specialty (Visible)": clean_text(spec_text),
                    "Source URL": target_url,
                    "Summary Info": summary_text
                }
                all_data.append(data_row)
            except Exception:
                continue
        
        # --- SAVE EVERY SINGLE DAMN TIME ---
        save_to_excel(all_data, output_filename)
        # -----------------------------------

        if is_last_page:
            print(f"  🏁 Достигнахме края на Регион {region_code}.")
            break 
        
        page_num += 1

save_to_excel(all_data, output_filename)
driver.quit()
print(f"Готово, Гащник! Всички {len(all_data)} записчовци са вътре.")

