import json
import os
import shutil
import sys
import xml.etree.ElementTree as ET
from time import sleep
import re

import requests
from requests.exceptions import ConnectionError
from imgurpython.helpers.error import ImgurClientError
from requests_oauthlib import OAuth1Session
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys

# Names for all of the folders that the images are saved to.
main_folder = ""
folders = {'imgur': 'Imgur', 'deviant': 'DeviantArt', 'direct': 'Other', 'tumblr': 'Tumblr', 'gfycat': 'Gfycat'}


def save_file(path, content):
    if not os.path.exists(path):
        with open(path, 'wb') as f:
            f.raw.decode_content = True
            shutil.copyfileobj(content, f)
            f.close()
            return True
    else:
        return False


# The folder where the subfolders and text files are
def set_folder(path):
    global main_folder
    main_folder = path


# Checks the required folders in the folders variable and creates them when needed
def check_folders():
    global folders
    created = 0
    if main_folder == "" or not os.path.exists(main_folder):
        print('Could not get folder: ', main_folder)
        sys.exit()
    for key in folders:
        folder = main_folder + "\\" + folders[key]
        print(folder)
        if not os.path.exists(folder):
            os.mkdir(folder)
            created += 1
        folders[key] = folder
    if created > 0:
        print("Created ", created, " folders")
    print('\n')


class Imgur(object):

    max_images = 50
    max_size = 157286400  #In bytes
    url = "imgur.com"

    def __init__(self, imgurclient=None):
        self.imgurclient = imgurclient

    #Get the Imgur image. Exceptions return False, otherwise True
    def get(self, url, filename):
        self.url = url
        imgurclient = self.imgurclient
        if imgurclient is None:
            raise ImgurClientError
        try:
            link = url.split("/")
            if "i.imgur.com" in link:
                img_id = link[-1].split(".")[0]
                print("Image id:", img_id)
                image = imgurclient.get_image(image_id=img_id)
                return self.download(image)
            elif "a" in link:
                if link[-1] == "gallery":
                    album_id = link[-2]
                else:
                    album_id = link[-1]
                if "#" in album_id:
                    album_id = album_id.split("#")[0]
                print("Image id:", album_id)
                album = imgurclient.get_album(album_id)
                images = imgurclient.get_album_images(album_id)
                return self.download(images, self.album_name(album), filename)
            elif "imgur.com" in link:
                img_id = link[-1].split('.')[0]
                if img_id == "new":
                    img_id = link[-2]
                if len(img_id) == 5:
                    print("Image id:", img_id)
                    album = imgurclient.get_album(img_id)
                    images = imgurclient.get_album_images(img_id)
                    return self.download(images, self.album_name(album), filename)
                elif img_id is not None:
                    print("Image id:", img_id)
                    image = imgurclient.get_image(img_id)
                    return self.download(image)
                else:
                    return False
            else:
                print(link)
                return False

        except ImgurClientError as e:
            print(e.error_message)
            print(e.status_code)
            return False

    def download(self, images, album_name=None, file=None):

        # Called for images. Returns True on success and False otherwise
        def download_image(image_obj, folder="", i=""):
            nonlocal moved
            r = requests.get(image_obj.link, stream=True)
            if r.status_code == 200:
                imgur = folders['imgur']
                if folder != "":
                    folder = "\\" + folder
                path = imgur + folder
                if not os.path.exists(path):
                    os.mkdir(path)
                if file is not None and moved is False:
                    os.rename(main_folder + '\\' + file, path + file)
                    moved = True
                elif album_name is not None and file is None and moved is False:
                    with open(path + 'Link.txt', 'a') as f:
                        f.write(self.url)
                    moved = True
                if i != "":
                    i += " "
                path = path + "\\" + i + image_obj.id + "." + image_obj.type.replace("image/", "")
                print(path)
                return save_file(path, r.raw)
            else:
                return False

        # Checks if it's an album or a single image
        if type(images) is list:
            amount = len(images)
            if amount > self.max_images:
                print("Too many images: ", amount)
                size = self.get_size(images)
                if size > self.max_size:
                    print("Too big:", size)
                    return "Images " + str(amount) + " Size " + str(size / 1000000) + "MB " + album_name
            folder_name = album_name + "\\"
            index = ["%.2d" % i for i in range(1, amount+1)]
            moved = False
            print(folder_name)
            value = False
            for idx, image in enumerate(images):
                value = download_image(image, folder=folder_name, i=index[idx])
            return value
        else:
            title = ""
            if images.title is not None:
                title = images.title
            return download_image(images, i=title)

    @staticmethod
    # Returns album name if available
    def album_name(album):
        if album.title is None:
            print(album.id)
            return album.id
        else:
            print(album.title + " " + album.id)
            return album.title + " " + album.id

    def set_max_images(self, amount):
        self.max_images = amount

    def set_max_size(self, size):
        self.max_size = size

    @staticmethod
    def get_size(images):
        size = 0
        for image in images:
            size += image.size
        return size


class Gfycat(object):

    # Gets the gfycat gif and saves it. Returns True on success
    def get_image(self, url):
        gfy_api = 'https://gfycat.com/cajax/get/'
        r = requests.get(gfy_api + url)
        json = r.json()
        if json.get('error') is None:
            gif_stuff = json.get('gfyItem')
            if gif_stuff is None:
                return False
            else:
                url = gif_stuff.get('gifUrl')
                if url is None:
                    return False
                else:
                    name = gif_stuff.get('gfyName')
                    title = gif_stuff.get('title')
                    if title is not None:
                        name = title + " " + gif_stuff.get('gfyName')
                    return self.download_image(url, name)

    @staticmethod
    # Downloads the image
    def download_image(url, name):
            r = requests.get(url, stream=True)
            if r.status_code == 200:
                path = folders['gfycat']
                path = path + "\\" + name + ".gif"
                print(path)
                return save_file(path, r.raw)
            else:
                return False


class DirectLink(object):

    @staticmethod
    # Downloads images using the phantomJS browser
    def download_image(url, file_path, driver):
        def download():
            nonlocal path_folder, r
            if r.status_code == 200:
                path = folders['direct']
                name = ''.join(image_name.split(".")[:-1])
                if name == "":
                    name = ''.join(image_name.split("."))
                path_folder = path + "\\" + name
                if not os.path.exists(path_folder):
                    os.mkdir(path_folder)
                path = path_folder + "\\" + re.sub('[<>:\\"\|?\*]', '', r.url.split('/')[-1])
                print(path)
                if os.path.isfile(path):
                    return False
                if save_file(path, r.raw):
                    return True
                else:
                    return False
            else:
                return False
        image_name = url.split('/')[-1]
        image_name = re.sub('[<>:\\"\|?\*]', '', image_name)
        print(url)
        try:
            r = requests.get(url, stream=True)
        except ConnectionError as e:
            print(e)
            return False
        print(image_name)
        if file_path is not None:
            filename = file_path.split("\\")[-1]
        path_folder = ""
        if "image" in r.headers['Content-Type']:
            print('direct link')
            value = download()
            if value and file_path is not None:
                os.rename(file_path, path_folder + "\\" + filename)
            elif value:
                with open(path_folder + '\\Link.txt', 'a') as link:
                    link.write(url)
            return value
        else:
            driver.get(url)
            images = driver.find_elements_by_tag_name('img')
            if len(images) > 20 and file_path is not None:
                os.rename(file_path, folders['other'] + "\\Too many images\\" + filename)
                return False
            else:
                for image in images:
                    src = image.get_attribute('src')
                    print(src)
                    if src is None:
                        src = image.get_attribute('data-src')
                        if src is None:
                            return False
                    r = requests.get(src, stream=True)
                    print(r.url)
                    value = download()
                print(value, file_path, path_folder)
                if value and file_path is not None:
                    os.rename(file_path, path_folder + "\\" + filename)
                elif value:
                    print(path_folder+'\\Link.txt')
                    with open(path_folder + '\\Link.txt', 'a') as link:
                        link.write(url)
                return value


class Deviantart(object):

    def __init__(self, chrome):
        self.driver = chrome

    # Gets the and downloads the image. Returns True on success
    def get_image(self, file_path, link):
        driver = self.driver
        driver.get(link)
        filename = link.split("/")[-1]
        sleep(5)
        value = self.click_download()
        if value:
            image_url = self.close_tab()
            print(image_url, filename)
            success = self.download_image(image_url, filename)
            renamed = folders['deviant'] + '\\' + filename + "\\" + filename + ".txt"
            if success and not os.path.isfile(renamed):
                if file_path is not None:
                    os.rename(file_path, renamed)
                else:
                    with open(renamed, 'a') as f:
                        f.write(link)
                return True
            else:
                return False
        else:
            return value

    # Clicks on the download link and opens it in a new tab. Returns True on success
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
                print("Something went wrong while trying to get the download link")
                return False

    # Closes the the current tab and leaves the full-sized image tab open.
    def close_tab(self):
        driver = self.driver
        url = driver.current_url
        windows = driver.window_handles
        for w in windows:
            driver.switch_to.window(w)
            if url == driver.current_url:
                driver.close()
        return driver.current_url

    @staticmethod
    # Downloads the image. Returns True on success
    def download_image(url, image_name):
        r = requests.get(url, stream=True)
        print(url)
        if r.status_code == 200:
            path = folders['deviant']
            path += "\\" + image_name
            if not os.path.exists(path):
                os.mkdir(path)
            path += "\\" + image_name + '.' + url.split(".")[-1]
            print(path)
            return save_file(path, r.raw)
        else:
            return False


class Tumblr(object):

    def __init__(self, key):
        self.api_key = key
        self.oauth = OAuth1Session(client_key=self.api_key)

    @staticmethod
    # Used to determine the post id
    def strisint(s):
        try:
            int(s)
            return True
        except ValueError:
            return False

    def download(self, url):
        r = requests.get(url)
        if 'image' in r.headers.get('Content-Type'):
            return 'DIRECTLINK'
        api = 'https://api.tumblr.com/v2/blog/'
        a = url.split("/")
        if self.strisint(a[-2]):
            post_id = a[-2]
        else:
            post_id = a[-1]
        print('Tumblr post id:', post_id)
        folder = a[-1]
        blog_name = a[2].split('.')[0]
        api += blog_name + '/posts?id=' + post_id
        r = self.oauth.get(api)
        try:
            json_file = json.loads(r.text)
            if json_file['meta']['status'] == 200:
                response = json_file['response']['posts'][0]
                images = response['photos']
                extra_images = response['caption']
            else:
                print("Error retrieving images")
                return False
        except (KeyError, TypeError) as e:
            print("Key error: ", e.args, json_file)
            return False
        index = ["%.2d" % i for i in range(1, len(images) + 1)]
        for idx, image in enumerate(images):
            url = image.get('original_size').get('url')
            if not self.download_image(url, folder, index[idx]):
                print('Download error', url, folder, idx)
                return False
        print(extra_images)
        if '<img' in extra_images:
            extra_images = '<extraimage>' + extra_images + '</extraimage>'
            tree = ET.fromstring(extra_images)
            for img in tree:
                i = img.find('img')
                if i is not None:
                    url = i.get('src')
                    print(url)
                    if not self.download_image(url, folder):
                        return False
        return True

    @staticmethod
    def download_image(url, folder, i=""):
        r = requests.get(url, stream=True)
        if r.status_code == 200:
            path = folders['tumblr'] + '\\' + folder
            if not os.path.exists(path):
                os.mkdir(path)
            if i != "":
                i += " "
            path += "\\" + i + url.split('/')[-1]
            print(path)
            return save_file(path, r.raw)
        else:
            print("Url error")
            return False
