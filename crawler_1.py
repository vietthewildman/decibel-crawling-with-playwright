import asyncio
import json
import pandas as pd
import re
from bs4 import BeautifulSoup
import os
from playwright.async_api import async_playwright

async def save_cookies(cookies):
    with open("cookies.json", "w") as file:
        json.dump(cookies, file)

async def load_cookies():
    with open("cookies.json", "r") as file:
        return json.load(file)

# DEFINE VARIABLES
    # Date Range
date_range = ['01/09/2023', '30/09/2023']
# error_message = 'Low Interaction Time'
# total_results = 805
# error_message = 'Unresponsive Clicks'
# total_results = 453
error_message = 'Unresponsive clicks on interactive UI elements'
total_results = 171
    # Login Page
username_input = '#field-1'
next_button = '//html/body/div[1]/div/div[2]/form/div[2]/button/canvas'
password_input = '#field-3'
login_button = '//html/body/div[1]/div/div[2]/form/div[2]/button'
    # Main Page
discover_button = '#app > div.main-layout.fill > div.sidebar.react-container.relative > div > section > div > nav > div > ul > li:nth-child(3) > div > div > button'
    # Target Page
target_page = 'https://portal.decibel.com/PageDiscovery'
exp_issues_button = '//*[@id="ui-id-6"]'
date_range_selector = 'li.curseg.dates a'
date_range_from = '#reportStart'
date_range_end = '#reportEnd'
date_range_submit_button = '//*[@id="main"]/div[3]/div/div[2]/div/div/div/form/div[2]/div/button'
# next_results_button = '//*[@id="main"]/div[3]/div/div[3]/div[2]/div/div/div/div[2]/div/div[2]/nav/ul/li[7]/span/button'
next_results_button = '#main > div.main-content > div > div.report-main > div.inner > div > div > div > div.content.no-pad.stack-item.slideInFromRight.animated > div > div:nth-child(2) > nav > ul > li.next > span'
    # Regex: page still contains Thai 
url_pattern = re.compile(r'nissan\.co\.th.*')

async def login(page):
    temp_ = True
    while temp_:
        element_1 = await page.query_selector(username_input)
        element_2 = await page.query_selector(discover_button)
        if element_1 or element_2:
            temp_ = False  
    if element_1 and await element_1.is_visible():
        # Wait for the login input -> input -> enter -> click next
        await page.wait_for_selector('#field-1', timeout=10000)
        await page.type('#field-1', "email@com") #userID
        await page.keyboard.press("Enter")
        await page.click('//html/body/div[1]/div/div[2]/form/div[2]/button/canvas')
        # Wait for the pw input -> input -> enter -> click login button
        await page.wait_for_selector('#field-3', timeout=10000)
        await page.type('#field-3', "password") #userPW
        await page.keyboard.press("Enter")
        await page.click('//html/body/div[1]/div/div[2]/form/div[2]/button')
        # Save Cookies
        cookies = await page.context.cookies()
        with open('cookies.json', 'w') as f:
            json.dump(cookies, f)

    else:
        print('Already Logged In!')

async def navigate_to_target(page):
        # Wait for discover_button -> navigate -> wait Exp Issues button -> Click
        await page.goto(target_page)
        await page.wait_for_selector(exp_issues_button)
        await page.click(exp_issues_button)

async def change_date_range(page):
        # Click on Date Range Selector
        await page.wait_for_selector(date_range_selector)
        await page.click(date_range_selector)
        # From
        await page.wait_for_selector(date_range_from)
        await page.fill(date_range_from, date_range[0])
        # End
        await page.wait_for_selector(date_range_end)
        await page.fill(date_range_end, date_range[1])
        # Click submit
        await page.click(date_range_submit_button)

async def crawl_data(page):        
        # (1) click on Action button
        td_elements = await page.query_selector_all('td.no-break')
        for td in td_elements:
            if (await td.text_content()).lower() == error_message.lower():
                # Find and click the link within the same table row
                await td.eval_on_selector('xpath=../td[contains(@class, "action")]//a', 'a => a.click()')
                break  # Exit the loop if the link has been clicked

        # (2) Crawl Data

        col1_data = []
        col2_data = []
        col3_data = []
        col4_data = []
        count_ = 1
        
            # (a) Navigate to next page
                # Find total pages need to crawl
        if (total_results//50*50) < total_results:
            total_pages =  total_results//50 + 1
        else:
            total_pages == total_results / 50
        
                # Navigate to the next page
        count_ = 1
        await page.wait_for_selector(next_results_button)    
                # Loop next pages
        while count_ <= total_pages:
                # Check if 1st page
            if count_ > 1:
                await page.wait_for_selector(next_results_button)
                await page.click(next_results_button)

            # print(f"We are at page {count_}")

            # (b) Use Beautiful Soup 4 to get data
                # Get HTML Content 
            page_html = await page.evaluate('() => document.body.outerHTML')

                # Parse the HTML content with BeautifulSoup
            soup = BeautifulSoup(page_html, 'html.parser')

                # Find all tables with the specified class
            tables = soup.find_all('table', {'class': 'visitors-report contribution-table'})

                # Select the 2nd table ([1] since indexing is 0-based)
            table = tables[1]

                # Get all rows (<tr>) in <tbody>
            rows = table.find('tbody').find_all('tr')

            for row in rows:

                # Check if the row has enough data
                if len(row.find_all('td')) > 2:

                # Get Data
                    relative = url_pattern.search(row.find('td', {'class': 'relative'}).get_text(strip=True)).group()
                    score = row.find('td', {'class': 'score'}).get_text(strip=True)
                    status1 = row.find('td', {'class': 'status'}).get_text(strip=True).split()[0]
                    status2 = row.find('td', {'class': 'status'}).get_text(strip=True).split()[1][1:-1]  

                # Append data to lists
                    col1_data.append(relative)
                    col2_data.append(score)
                    col3_data.append(status1)
                    col4_data.append(status2) 


            count_ += 1

            # (c) Compile into a dataframe
        df = pd.DataFrame({
            'page_url': col1_data,
            'dxs_score': col2_data,
            'sessions': col3_data,
            'percentage':col4_data
        })
                # Remove duplicated row: keep only the one with higest sessions
        df = df.sort_values(by=['page_url', 'sessions'], ascending=[True, False])
        df = df.drop_duplicates(subset='page_url', keep='first')
        df = df.sort_values(by='sessions', ascending=False).reset_index(drop=True)
        return df

async def main():
    path = 'C:\\Users\\hoang\\AppData\\Local\\Google\\Chrome\\User Data\\Default\\decibel_crawler'
    async with async_playwright() as pw:

        browser_context = await pw.chromium.launch_persistent_context(path, headless=False)
        page = await browser_context.new_page()

        # Load Cookies
        try: 
            with open('cookies.json', 'r') as f:
                cookies = json.load(f)
            await page.context.add_cookies(cookies)
        except Exception:
            pass

        # Login
        await page.goto('https://portal.decibel.com')
        await page.wait_for_timeout(5000) 
        await login(page)

        # Wait for main page fully loaded
        await page.wait_for_selector(discover_button)

        # Navigate to the target page
        await navigate_to_target(page)
        await page.wait_for_timeout(2000)

        # Change Date ranage
        await change_date_range(page)
        await page.wait_for_timeout(2000) 

        # Crawl data
        df = await crawl_data(page)
        await page.wait_for_timeout(2000) 

        # Clean up: close the context
        await browser_context.close()

        df.to_csv(f'{error_message}.csv', index=False)



# Run the script
if __name__ == "__main__":
    asyncio.run(main())