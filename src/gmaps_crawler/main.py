from cmath import log
import logging
import time
import random
from enum import IntEnum

from selenium.webdriver.common.action_chains import ActionChains, ScrollOrigin
from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from config import settings, fileconfig
from drivers import create_driver
# from entities import Place
from entities import GeoPlace, ResInfo
from storages import get_storage, MongoStorage
import dataclasses

FINAL_URL = fileconfig.base_url.format(search=fileconfig.search_word)

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
        self.error_count = 0
        self.index = 3
        self.count = 1
        self.storage = get_storage()
        # pass
    
    def get_click_side_bar_menu(self, index):
        try:
            side_bar = driver.find_element(By.XPATH, fileconfig.side_bar_res_xpath.format(index))
            side_bar.click()
        except Exception:
            # Maybe it's a "complex" view with more data:
            # driver.find_element(By.XPATH, "//*[img[contains(@src, 'schedule_gm')]]").click()
            return (False, None, None)
        else:
            return (True, side_bar, side_bar.get_attribute('href'))

    def get_restaurant_name(self):
        try:
            name = driver.find_element(By.XPATH, fileconfig.res_name_xpath)
            return (True, name.text)
        except Exception:
            # Maybe it's a "complex" view with more data:
            # driver.find_element(By.XPATH, "//*[img[contains(@src, 'schedule_gm')]]").click()
            return (False, None)
        # else:


    def get_restaurant_menu(self):
        try:
            menu = driver.find_element(By.XPATH, fileconfig.res_menu_xpath)
            return (True, menu.text)
        except:
            return (False, None)
        # else:
            


    def get_restaurant_num_review(self):
        try:
            num_review = driver.find_element(By.XPATH, fileconfig.res_num_review_xpath)
            return (True, num_review.text.replace('(', '').replace(')','').replace(' reviews', '').replace(' review', '').replace(' 則評論', ''))
        except:
            return (False, 0)
        # else:
            

    def get_restaurant_rating(self):
        try:
            rating = driver.find_element(By.XPATH, fileconfig.res_rating_xpath)
            return (True, float(rating.text))
        except:
            return (False, None)
        # else:


    def get_restaurant_address(self):
        try:
            address = driver.find_element(By.XPATH, fileconfig.res_address_xpath)
            return (True, address.text)
        except:
            return (False, None)
        # else:


    def get_places(self):
        # if self.get_click_side_bar_menu(self.index):
        while True:
            if self.error_count > 5:
                break
            (side_bar_exist_or_not, side_bar, href) = self.get_click_side_bar_menu(self.index)
            logger.info("[bold blue] == sleep {} second to load information ==[/]".format(2), extra={"markup": True})
            time.sleep(2)
            if side_bar_exist_or_not:
            
                name = self.get_restaurant_name()[1]
                
                if fileconfig.search_word not in name.upper():
                    self.error_count += 1
                    continue

                address = self.get_restaurant_address()[1]
                rating = self.get_restaurant_rating()[1]
                nums_of_review = self.get_restaurant_num_review()[1]
                menu_list = self.get_restaurant_menu()[1]
                # href = self.get_click_side_bar_menu(self.index)[2]
                location = GeoPlace()
                res = ResInfo(name, location, address, href, rating, nums_of_review, menu_list)
                # geo = GeoPlace()
                res.location.coordinates.append(float(str(res.href).split('!4d')[1].split('!')[0]))
                res.location.coordinates.append(float(str(res.href).split('!3d')[1].split('!4d')[0]))

                logger.info("[bold] == resinfo {} == [/]".format(res), extra={"markup": True})
                # logger.info("[bold] == resinfo {} == [/]".format(dataclasses.asdict(res)), extra={"markup": True})
                # logger.info("[bold pink] == name: {}, address: {}, rating: {}, res_num_review: {}, res_menu: {}, res_href: {}, res_lat: {}, res_lng: {}==[/]".format(res_name, res_address, res_rating, res_num_review, res_menu, res_href, res_lat, res_lng), extra={"markup": True})
                self.scroll_down(side_bar)

                rn = random.randint(1,5)
                logger.info("[bold blue] == sleep {} second for scroll down ==[/]".format(rn), extra={"markup": True})
                time.sleep(rn)
                logger.info("[bold blue] == count {}  ==[/]".format(self.count), extra={"markup": True})
                self.count += 1
                self.index += 2
                rn = random.randint(1,5)
                logger.info("[bold blue] == sleep {} second for get next side bar ==[/]".format(rn), extra={"markup": True})
                time.sleep(rn)
                
                self.data.append(dataclasses.asdict(res))
            else:
                break

        logger.info("[bold blue] == save data to mongo ==[/]".format(rn), extra={"markup": True})
        self.storage.save(self.data)

    def scroll_down(self, iframe):

        scroll_origin = ScrollOrigin.from_element(iframe)
        ActionChains(driver).scroll_from_origin(scroll_origin, 0, 1000).perform()

if __name__ == "__main__":
    logger.info("[bold yellow]== * Running Gmaps Crawler ==[/]", extra={"markup": True})
    logger.info("[yellow]Settings:[/yellow] %s", settings.dict(), extra={"markup": True})
    logger.info("[yellow]Settings:[/yellow] %s", vars(fileconfig), extra={"markup": True})
    driver.get(FINAL_URL)
    crawler = GMapCrawlerFfE()
    crawler.get_places()