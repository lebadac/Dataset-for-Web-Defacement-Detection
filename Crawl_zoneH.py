import random
import time
from fake_useragent import UserAgent
from selenium.webdriver.common.by import By
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import pandas as pd
from colorama import Fore, Style

# Load unique notifiers from CSV
notifiers_df = pd.read_csv("Notifier3.csv")
unique_notifiers = notifiers_df['Notifier'].unique()

# Set up Chrome options with user-agent rotation and incognito mode
ua = UserAgent()  # Generate a random user-agent
opt = Options()
opt.add_argument('--no-sandbox')
opt.add_argument('--disable-dev-shm-usage')
opt.add_argument('--incognito')
opt.add_argument(f'user-agent={ua.random}')

# Optional proxy setup (comment out if not needed)
# PROXY = "http://your_proxy_address:port"
# opt.add_argument(f'--proxy-server={PROXY}')

driver = webdriver.Chrome(options=opt)

# Function to wait for manual CAPTCHA input
def wait_for_manual_captcha_input():
    print(Fore.RED + "CAPTCHA detected. Please solve it manually in the browser. Press Enter here when done." + Style.RESET_ALL)
    input()  # Wait for user to press Enter after solving CAPTCHA

# Function to save data to CSV
def save_data_to_csv(data):
    if data:
        df = pd.DataFrame(data)
        df.to_csv("zone_h_notifiers_datasets.csv", index=False, encoding="utf-8")
        print(Fore.GREEN + "Data saved to zone_h_notifiers_datasetss.csv" + Style.RESET_ALL)

# Scrape data from each notifier's page
def scrape_notifier_data(notifier):
    data = []
    page = 1

    while page <= 50:  # Stop after page 50
        try:
            # Randomize user-agent and delay
            opt.add_argument(f'user-agent={ua.random}')
            driver.get(f'https://zone-h.org/archive/notifier={notifier}/page={page}')
            time.sleep(random.uniform(1, 2))  # Random delay between requests

            SrcePage = driver.page_source

            # Handle CAPTCHA if detected
            if "If you often get this captcha when gathering data" in SrcePage:
                save_data_to_csv(data)  # Save progress before waiting
                wait_for_manual_captcha_input()
                SrcePage = driver.page_source  # Reload page source after CAPTCHA is solved

            # Check for 403 Forbidden error
            if "403 Forbidden" in SrcePage:
                print(Fore.RED + "403 Forbidden detected. Waiting before retrying..." + Style.RESET_ALL)
                time.sleep(60)  # Wait for 1 minute before retrying
                continue

            # Parse HTML
            soup = BeautifulSoup(SrcePage, 'html.parser')
            parenter = soup.find('table', {'id': 'ldeface'})

            # Stop if no table is found for this notifier
            if not parenter:
                print(Fore.YELLOW + f"No table found on page {page} for notifier {notifier}. Moving to next notifier..." + Style.RESET_ALL)
                break

            rows = parenter.find_all('tr')[1:]  # Skip header row

            # Flag to check if all rows are null for this page
            all_rows_null = True

            # Extract data and check for null-only rows
            for row in rows:
                columns = row.find_all('td')
                if len(columns) < 9:
                    continue

                # Extract data
                date = columns[0].text.strip()
                notifier_name = columns[1].text.strip()
                h_status = columns[2].text.strip() or "N/A"
                m_status = columns[3].text.strip() or "N/A"
                r_status = columns[4].text.strip() or "N/A"
                location = columns[5].find('img')['title'] if columns[5].find('img') else "N/A"
                domain = columns[7].text.strip()
                os = columns[8].text.strip()
                view = columns[9].find('a')['href'] if columns[9].find('a') else "N/A"

                # Check if this row has any non-null data
                if any(value != "N/A" and value for value in [date, notifier_name, h_status, m_status, r_status, location, domain, os]):
                    all_rows_null = False
                    data.append({
                        "Notifier": notifier_name,
                        "Date": date,
                        "H": h_status,
                        "M": m_status,
                        "R": r_status,
                        "Location": location,
                        "Domain": domain,
                        "OS": os,
                        "View": f'https://zone-h.org{view}'
                    })

            # If all rows were null, stop scraping this notifier
            if all_rows_null:
                print(Fore.YELLOW + f"All data on page {page} for notifier {notifier} is null. Moving to next notifier..." + Style.RESET_ALL)
                break

            print(Fore.GREEN + f"Page {page} for notifier {notifier} scraped successfully." + Style.RESET_ALL)
            page += 1  # Move to the next page

        except Exception as e:
            print(Fore.RED + f"An error occurred on page {page} for notifier {notifier}: {e}" + Style.RESET_ALL)
            save_data_to_csv(data)  # Save progress on error
            break

    return data

if __name__ == "__main__":
    print(Fore.GREEN + "\nStarting Notifier Scraping ..." + Style.RESET_ALL)
    time.sleep(1)

    all_data = []

    try:
        # Loop through each notifier and scrape their pages
        for notifier in unique_notifiers:
            notifier_data = scrape_notifier_data(notifier)
            all_data.extend(notifier_data)
            save_data_to_csv(all_data)  # Save progress after each notifier

    except Exception as e:
        print(Fore.RED + f"An error occurred: {e}. Saving data collected so far..." + Style.RESET_ALL)

    finally:
        # Final save to CSV after all notifiers are processed or if interrupted
        save_data_to_csv(all_data)
        print(Fore.GREEN + "Final data successfully saved to zone_h_notifiers_datasets.csv" + Style.RESET_ALL)

        # Close the browser
        driver.quit()
