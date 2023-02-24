import logging
import time
from enum import IntEnum

from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.action_chains import ScrollOrigin
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from drivers import create_driver
from entities import Place
from storages import get_storage


BASE_URL = "https://www.google.com/maps/search/{search}/@25.0078177,121.6292181,14z/data=!3m1!4b1?hl=en"
SEARCH = "健康餐盒"
FINAL_URL = BASE_URL.format(search=SEARCH)
INDEX = 3
COUNT = 1
SIDE_BAR_RESTAURANT_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[{}]/div/a"


RESTAURANT_NAME_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]"
RESTAURANT_MENU_XPATH = "//a[@aria-label='Menu']"
RESTAURANT_ADDRESS_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[9]/div[4]/button/div[1]/div[2]/div[1]"
RESTAURANT_NUM_REVIEW_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[2]/div/div[1]/div[2]/span[2]/span[1]/span"
# MENU_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[9]/div[7]/a"
RATING_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[2]/div/div[1]/div[2]/span[1]/span/span[1]"

driver = create_driver()
driver.get(FINAL_URL)

# print(driver.find_element(By.CLASS_NAME, "hfpxzc"))

# elements = driver.find_elements(By.CLASS_NAME, "hfpxzc").text
# driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
# time.sleep(3)
# elements = driver.find_element(By.XPATH, '/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[3]/div/a')



# SIDE_BAR_RESTAURANT_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[{}]/div/a".format(INDEX)

point = driver.find_element(By.XPATH, SIDE_BAR_RESTAURANT_XPATH.format(3))

restaurant_href = point.get_attribute("href")
restaurant_location = restaurant_href
point.click()

restaurant_name = driver.find_element(By.XPATH, RESTAURANT_NAME_XPATH)
def scroll_down(iframe):

    scroll_origin = ScrollOrigin.from_element(iframe)
    ActionChains(driver)\
        .scroll_from_origin(scroll_origin, 0, 500)\
        .perform()
scroll_down(point)

# restaurant name
print(restaurant_name.text)

# driver.find_element(By.ID , RESTAURANT_NAME_XPATH)
restaurant_menu = driver.find_element(By.XPATH, RESTAURANT_MENU_XPATH)
print(restaurant_menu.get_attribute("href"))






# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]

# restaurant_xpath = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]"
# print(driver.find_element(By.XPATH, RESTAURANT_NAME_XPATH).text)

# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]
# ActionChains(driver).scroll_to_element(iframe).perform()

# iframe = driver.find_element(By.TAG_NAME, "iframe")
# scroll_origin = ScrollOrigin.from_element(iframe)
# ActionChains(driver)\
#     .scroll_from_origin(scroll_origin, 0, 200)\
#     .perform()

time.sleep(3)
# total_height = int(driver.execute_script("return document.body.scrollHeight"))
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div
# print(total_height)
# for i in range(1, total_height, 4):
#    driver.execute_script("window.scrollTo(0, {});".format(i))
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]
# resname = driver.find_element(By.XPATH, '/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]').text
# print(resname)
# elements = driver.find_element(By.XPATH, '/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[51]/div/a')
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[5]/div/a
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[7]/div/a
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[41]/div/a
# print(elements)
# for e in elements:
#     print(e.text)

# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[9]/div[8]/a/div[1]/div[2]/div[1]
# /html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[13]/div/a