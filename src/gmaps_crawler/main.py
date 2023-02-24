import logging
import time
import random
from enum import IntEnum

from selenium.webdriver.common.action_chains import ActionChains, ScrollOrigin
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings
from drivers import create_driver
from entities import Place
from storages import get_storage

SIDE_BAR_RESTAURANT_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[2]/div/div[1]/div/div/div[2]/div[1]/div[{}]/div/a"
RESTAURANT_NAME_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[1]/h1/span[2]"
RESTAURANT_MENU_XPATH = "//a[@aria-label='Menu']"
RESTAURANT_ADDRESS_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[9]/div[4]/button/div[1]/div[2]/div[1]"
RESTAURANT_NUM_REVIEW_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[2]/div/div[1]/div[2]/span[2]/span[1]/span"
# MENU_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[9]/div[7]/a"
RATING_XPATH = "/html/body/div[3]/div[9]/div[9]/div/div/div[1]/div[3]/div/div[1]/div/div/div[2]/div[2]/div[1]/div[1]/div[2]/div/div[1]/div[2]/span[1]/span/span[1]"

BASE_URL = "https://www.google.com/maps/search/{search}/@24.136807,120.684875,14z/data=!3m1!4b1?hl=en"
SEARCH = "健康餐盒"
FINAL_URL = BASE_URL.format(search=SEARCH)

driver = create_driver()
logger = logging.getLogger(__name__)
                            

class PlaceDetailRegion(IntEnum):
    TRAITS = 1
    ADDRESS_EXTRA = 2


class ExtraRegionChild(IntEnum):
    ADDRESS = 0
    HOURS = 1
    EXTRA_ATTRS_START = 3


def find_elements_by_attribute(tag: str, attr_name: str, attr_value: str) -> list[WebElement]:
    query = f"{tag}[{attr_name}='{attr_value}']"
    elements = driver.find_elements(By.CSS_SELECTOR, query)
    return elements


def find_element_by_attribute(tag: str, attr_name: str, attr_value: str) -> WebElement:
    return find_elements_by_attribute(tag, attr_name, attr_value)[0]


def find_element_by_aria_label(tag: str, attr_value: str) -> WebElement:
    return find_element_by_attribute(tag, "aria-label", attr_value)


class GMapsNavigator:
    PLACES_PER_SCROLL = 7
    SECONDS_BEFORE_SCROLL = 1

    def __init__(self) -> None:
        self.place_idx = 0
        self.page = 1

    def _get_places_wrapper(self) -> list[WebElement]:
        search_label = SEARCH.replace("+", " ")
        wrapper = find_element_by_aria_label("div", f"Results for {search_label}")
        return [el for el in wrapper.find_elements(By.XPATH, "*") if el.is_displayed()]

    def _scroll_to_bottom(self, times: int):
        """
        We need to scroll the list div to bottom to load the next places,
        it wouldn't work to calculate the index of a div that is not visible (loaded) yet.

        Google Maps displays 7 places at a time.
        """
        time.sleep(self.SECONDS_BEFORE_SCROLL)

        for _ in range(times):
            anchor_el = driver.find_element(By.CLASS_NAME, "section-scrollbox").find_element(By.CLASS_NAME, "noprint")
            ActionChains(driver).move_to_element(anchor_el).perform()

    def _turn_page(self):
        next_page_arrow = driver.find_element(By.XPATH, "//button[contains(@aria-label, 'Next page')]")
        next_page_arrow.click()

    @property
    def has_next_place(self) -> bool:
        return True  # TODO: Find out how to decide when to turn page

    def focus_and_get_next_place_element(self) -> WebElement:
        times_to_scroll = self.place_idx // self.PLACES_PER_SCROLL
        self._scroll_to_bottom(times_to_scroll)

        place_divs_with_dividers = self._get_places_wrapper()
        div_idx = self.place_idx * 2
        selected_div = place_divs_with_dividers[div_idx]
        self.place_idx += 1

        logger.info("Crawling place n #%03d", self.place_idx)

        ActionChains(driver).move_to_element(selected_div).perform()
        return selected_div

    def __iter__(self):
        return self

    def __next__(self) -> WebElement:
        if self.has_next_place:
            return self.focus_and_get_next_place_element()

        raise StopIteration()


class GMapsPlacesCrawler:
    MIN_BUSINESS_HOURS_LENGTH = 3
    WAIT_SECONDS_RESTAURANT_TITLE = 10

    def __init__(self) -> None:
        self.storage = get_storage()
        self.navigator = GMapsNavigator()

    def hit_back(self):
        elements = find_elements_by_attribute("button", "aria-label", "Back")
        for el in elements:
            if el.is_displayed():
                el.click()
                break

    def get_places(self):
        for place_div in self.navigator:
            place_div.click()
            self.get_place_details()

    def wait_restaurant_title_show(self):
        WebDriverWait(driver, self.WAIT_SECONDS_RESTAURANT_TITLE).until(
            EC.presence_of_element_located((By.XPATH, '//h1[text() != ""]'))
        )

    def get_place_details(self):
        self.wait_restaurant_title_show()

        # DATA



        restaurant_name = self.get_restaurant_name()
        logger.info("Crawling data for restaurant %s", restaurant_name)

        address = self.get_address()
        place = Place(restaurant_name, address)

        if self.expand_hours():
            place.business_hours = self.get_business_hours()

        # TRAITS
        place.extra_attrs = self.get_place_extra_attrs()
        traits_handler = self.get_region(PlaceDetailRegion.TRAITS)
        traits_handler.click()
        place.traits = self.get_traits()

        # REVIEWS
        place.rate, place.reviews = self.get_review()

        # PHOTOS
        place.photo_link = self.get_image_link()

        logger.info("Storing place ")
        self.storage.save(place)
        self.hit_back()

    def get_region(self, region: PlaceDetailRegion) -> WebElement:
        """
        Regions are sections inside the place details, often:
            0: ActionButtons e.g. Directions / Save
            1: DeliveryOptions e.g. Takeway / Delivery
            2: Address
            3: Popular Times
        """
        regions = find_elements_by_attribute("div", "role", "region")
        return regions[region]

    def get_extra_region_child(self, region_child: ExtraRegionChild) -> WebElement:
        extra_region = self.get_region(PlaceDetailRegion.ADDRESS_EXTRA)
        children = extra_region.find_elements(By.XPATH, "*")
        return children[region_child]

    def expand_hours(self) -> bool:
        try:
            find_element_by_aria_label("img", "Hours").click()
        except Exception:
            # Maybe it's a "complex" view with more data:
            # driver.find_element(By.XPATH, "//*[img[contains(@src, 'schedule_gm')]]").click()
            return False
        else:
            return True

    def get_restaurant_name(self) -> str:
        return driver.find_element(By.TAG_NAME, "h1").text

    def get_address(self) -> str:
        element = self.get_extra_region_child(ExtraRegionChild.ADDRESS)
        return element.text

    def get_place_extra_attrs(self):
        """
        May contain many random attributes, some are common like:
        - web address
        - phone number
        - plus code
        """
        region = self.get_region(PlaceDetailRegion.ADDRESS_EXTRA)
        children = region.find_elements(By.XPATH, "*")

        result = {}
        for child in children[ExtraRegionChild.EXTRA_ATTRS_START :]:
            key = child.find_element(By.TAG_NAME, "button").get_attribute("aria-label")
            result[key] = child.text

        return result

    def get_review(self) -> tuple[str, str]:
        review_wrapper = driver.find_element(By.XPATH, "//div[button[contains(text(), 'review')]]")
        rate, reviews = review_wrapper.text.split("\n")
        return rate, reviews

    def get_traits(self) -> dict[str, list[str]]:
        all_divs = driver.find_element(By.CLASS_NAME, "section-scrollbox").find_elements(By.XPATH, "*[text() != '']")
        result = {}
        for div in all_divs:
            category, *items = div.text.split("\n")
            result[category] = items

        self.hit_back()
        self.wait_restaurant_title_show()
        return result

    def get_business_hours(self) -> dict[str, str]:
        element = self.get_extra_region_child(ExtraRegionChild.HOURS)

        def get_first_line(raw):
            return raw.split("\n")[0]

        all_dates_times = [
            get_first_line(x.text)
            for x in element.find_elements(By.XPATH, "//tr/*")
            if len(x.text) > self.MIN_BUSINESS_HOURS_LENGTH
        ]

        return {all_dates_times[x]: all_dates_times[x + 1] for x in range(0, len(all_dates_times), 2)}

    def get_image_link(self) -> str:
        cover_img = driver.find_element(By.XPATH, "//img[@decoding='async']")
        return cover_img.get_property("src")

class GMapCrawlerFfE():

    def __init__(self):
        self.data = []
        self.index = 3
        self.count = 1

        # pass
    
    def get_click_side_bar_menu(self, index):
        try:
            side_bar = driver.find_element(By.XPATH, SIDE_BAR_RESTAURANT_XPATH.format(index))
            side_bar.click()
        except Exception:
            # Maybe it's a "complex" view with more data:
            # driver.find_element(By.XPATH, "//*[img[contains(@src, 'schedule_gm')]]").click()
            return (False, None)
        else:
            return (True, side_bar)

    def get_restaurant_name(self):
        try:
            name = driver.find_element(By.XPATH, RESTAURANT_NAME_XPATH)
        except Exception:
            # Maybe it's a "complex" view with more data:
            # driver.find_element(By.XPATH, "//*[img[contains(@src, 'schedule_gm')]]").click()
            return (False, None)
        else:
            return (True, name.text)

    def get_restaurant_menu(self):
        try:
            menu = driver.find_element(By.XPATH, RESTAURANT_MENU_XPATH)
        except:
            return (False, None)
        else:
            return (True, menu.text)


    def get_restaurant_num_review(self):
        try:
            num_review = driver.find_element(By.XPATH, RESTAURANT_NUM_REVIEW_XPATH)
        except:
            return (False, None)
        else:
            return (True, num_review.text)

    def get_restaurant_rating(self):
        try:
            rating = driver.find_element(By.XPATH, RATING_XPATH)
        except:
            return (False, None)
        else:
            return (True, rating.text)

    def get_restaurant_address(self):
        try:
            address = driver.find_element(By.XPATH, RESTAURANT_ADDRESS_XPATH)
        except:
            return (False, None)
        else:
            return (True, address.text)

    def get_places(self):
        # if self.get_click_side_bar_menu(self.index):
        while self.get_click_side_bar_menu(self.index)[0]:
            res_name = self.get_restaurant_name()[1]
            res_address = self.get_restaurant_address()[1]
            res_rating = self.get_restaurant_rating()[1]
            res_num_review = self.get_restaurant_num_review()[1]
            res_menu = self.get_restaurant_menu()[1]

            logger.info("[bold pink] == name: {}, address: {}, rating: {}, res_num_review: {}, res_menu: {} ==[/]".format(res_name, res_address, res_rating, res_num_review, res_menu), extra={"markup": True})
            if self.count * 10 + 3 == self.index:
                self.scroll_down(self.get_click_side_bar_menu(self.index)[1])
                self.count += 1
                rn = random.randint(1,10)
                logger.info("[bold blue] == sleep {} second for scroll down ==[/]".format(rn), extra={"markup": True})
                time.sleep(5)
            self.index += 2
            rn = random.randint(1,5)
            logger.info("[bold blue] == sleep {} second for get next side bar ==[/]".format(rn), extra={"markup": True})
            time.sleep(rn)


        
    def scroll_down(self, iframe):

        scroll_origin = ScrollOrigin.from_element(iframe)
        ActionChains(driver).scroll_from_origin(scroll_origin, 0, 500).perform()

if __name__ == "__main__":
    logger.info("[bold yellow]== * Running Gmaps Crawler ==[/]", extra={"markup": True})
    logger.info("[yellow]Settings:[/yellow] %s", settings.dict(), extra={"markup": True})

    driver.get(FINAL_URL)
    crawler = GMapCrawlerFfE()
    crawler.get_places()
