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
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException

# --- НАСТРОЙКИ ЗА ОБЛАКА (HEADLESS GANGSTA MODE) ---
options = webdriver.ChromeOptions()

# НАЙ-ВАЖНОТО: Трябва да е headless, иначе GitHub ще го убие
options.add_argument('--headless=new') 

options.add_argument('--start-maximized') 
options.add_argument('--window-size=1920,1080') # Лъжем го, че имаме голям монитор
options.add_argument('--disable-blink-features=AutomationControlled') 
options.add_argument('--no-sandbox') 
options.add_argument('--disable-dev-shm-usage') 
options.add_argument('--ignore-certificate-errors')
options.add_argument('--disable-gpu') # Важно за Linux среди

# Флагове да не заспива (макар че в headless е по-лесно)
options.add_argument('--disable-backgrounding-occluded-windows')
options.add_argument('--disable-renderer-backgrounding')
options.add_argument('--disable-background-timer-throttling')
options.add_argument('--disable-popup-blocking') 

# Слагаме User-Agent, да не ни хванат веднага, че сме роботи
options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

# --- СТАРТИРАНЕ НА ДРАЙВЕРА С МЕНИДЖЪР ---
# Това инсталира Chrome драйвера автоматично в облака
print("Bootleg Chat: Инсталирам драйверчовци...")
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
        print(f"   [SAVE] Записах {len(data)} редчовци в Ексела.")
    except Exception as e:
        print(f"   [ERROR] Не можах да запиша файла: {e}")

print("Bootleg Chat: Минаваме на директна URL атака в облака...")

# --- ВЪНШЕН ЦИКЪЛ: РЕГИОНИ (02 до 30) ---
# ВНИМАНИЕ: В GitHub имаш лимит от 6 часа. Ако гръмне по време, намали рейнджа тук.
for r in range(2, 3): # was 2, 29
    region_code = f"{r:02d}"
    page_num = 1 
    
    print(f"\n========================================")
    print(f"🏥 ЗАПОЧВАМЕ РЕГИОН: {region_code}")
    print(f"========================================")

    # --- ВЪТРЕШЕН ЦИКЪЛ: СТРАНИЦИ ---
    while True:
        target_url = f"https://blsbg.eu/bg/medics/unionlist/{region_code}?UIN_page={page_num}"
        
        print(f"  > Отварям стр. {page_num} за регион {region_code}...")
        
        try:
            driver.get(target_url)
        except Exception as e:
            print(f"  ! Грешка при зареждане на URL: {e}. Пробвам пак...")
            time.sleep(2)
            try:
                driver.get(target_url)
            except:
                print("  ! Отказвам се от тая страница.")
                break 

        # Проверка за 404
        if "404" in driver.title or "Page not found" in driver.page_source:
            print(f"  🏁 Регион {region_code} даде 404 или е празен. Минаваме на следващия.")
            break

        # Чакаме таблицата
        try:
            rows = WebDriverWait(driver, 20).until( # Намалих малко тайм-аута за бързина
                EC.presence_of_all_elements_located((By.XPATH, "//table//tr[td]"))
            )
        except TimeoutException:
            if "Няма намерени" in driver.page_source:
                print(f"  🏁 Регион {region_code} е празен (няма записи).")
                break
            else:
                print("  ! Времето изтече. Таблицата не се появи. Пробваме рефреш...")
                driver.refresh()
                try:
                    rows = WebDriverWait(driver, 15).until(
                        EC.presence_of_all_elements_located((By.XPATH, "//table//tr[td]"))
                    )
                except:
                     print("  ! Пак греда. Скипваме региона.")
                     break

        # --- СЪБИРАНЕ НА ДАННИ ---
        is_last_page = False
        summary_text = "-"
        
        try:
            summary_element = driver.find_element(By.CSS_SELECTOR, "div.summary")
            summary_text = summary_element.text.strip()
            
            match = re.search(r'-(\d+)\s+от\s+(\d+)', summary_text)
            
            if match:
                current_end = int(match.group(1))
                total_records = int(match.group(2))
                
                percentage = (current_end / total_records) * 100
                print(f"    [Info] Прогрес: {percentage:.2f}% ({current_end}/{total_records})")
                
                if current_end >= total_records:
                    is_last_page = True
            else:
                pass
                
        except NoSuchElementException:
            # Ако няма summary, може да е само 1 страница или грешка
            pass

        # Скрейпинг на редовете
        new_rows_count = 0
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
                    "Region Code": region_code,
                    "UIN": uin,
                    "Address (Hidden)": adr,
                    "G Address (Hidden)": gadr,
                    "Phone": tel,
                    "Workplace": wrk,
                    "Specialty (Hidden)": spec_attr,
                    "Name": name,
                    "Specialty (Visible)": spec_text,
                    "Source URL": target_url,
                    "Summary Info": summary_text
                }
                all_data.append(data_row)
                new_rows_count += 1
            except Exception:
                continue
        
        # --- ПРОВЕРКА ЗА ИЗХОД ---
        if is_last_page:
            print(f"  🏁 Достигнахме края на Регион {region_code}.")
            # Записваме след всеки завършен регион за сигурност
            save_to_excel(all_data, output_filename) 
            break 
        
        page_num += 1
        
        # В облака може и без sleep, ама айде да не сме нахални
        # time.sleep(0.5) 

# Финален запис
save_to_excel(all_data, output_filename)
driver.quit()
print(f"Готово, Гащник! Всичко е в {output_filename}. На баба ти хвърчилото литна в облака!")


