from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from time import sleep
import requests, shutil, os


class Deviantart(object):
    def __init__(self, chrome):
        self.driver = chrome

    def get_image(self, file_path):
        driver = self.driver
        with open(file_path) as f:
            file_content = f.readline()
            f.close()
        driver.get(file_content)
        filename = file_content.split("/")[-1]
        sleep(5)
        value = self.click_download()
        if value:
            image_url = self.close_tab()
            success = self.download_image(image_url, filename)
            if success:
                os.rename(file_path, 'E:/Dropbox/Images/DeviantArt/' + filename + "\\" + filename + ".txt")
                return True
            else:
                return False

    def click_download(self):
        driver = self.driver
        try:
            elem = driver.find_element_by_xpath('//*[contains(concat( " ", @class, " " ), '
                                                'concat( " ", "dev-page-download", " " ))]')
            ActionChains(driver) \
                .key_down(Keys.CONTROL) \
                .click(elem) \
                .key_up(Keys.CONTROL) \
                .perform()
            return True
        except NoSuchElementException:
            try:
                elem = driver.find_element_by_xpath('//*[(@id = "dDLButton")]')
                elem.click()
                return True
            except NoSuchElementException:
                print("Shit")
                return False

    def close_tab(self):
        driver = self.driver
        url = driver.current_url
        windows = driver.window_handles
        for w in windows:
            driver.switch_to.window(w)
            if url == driver.current_url:
                driver.close()
        return driver.current_url

    def download_image(self, url, image_name):
        r = requests.get(url, stream=True)
        print(url)
        if r.status_code == 200:
            path = os.path.normpath('E:/Dropbox/Images/DeviantArt')
            path += "\\" + image_name
            if not os.path.exists(path):
                os.mkdir(path)
            path += "\\" + image_name + url.split(".")[-2]
            print(path)
            with open(path, 'wb') as f:
                f.raw.decode_content = True
                shutil.copyfileobj(r.raw, f)
                f.close()
                return True
        else:
            return False
