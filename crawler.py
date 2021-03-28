import os
import time
import uuid
import traceback
import random

from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from logger import make_logger
from collections import defaultdict
from lxml.html import fromstring
import requests
import shutil

from db import RemainTaskRow, Post, PostImages, DatabaseHelper


class InstagramCrawler:
    def __init__(self):
        self.DRIVER_PATH = './driver/chromedriver'
        self.INSTA_ID = 'sooiso@hanmail.net'
        self.INSTA_PASSWD = 'gh767600'
        self.image_dir = './images'

        self.db = DatabaseHelper()
        self.logger = make_logger('instagram')
        self.load_driver()

    def load_driver(self):
        options = webdriver.ChromeOptions()

        options.add_argument("headless")
        options.add_argument("window-size=730x1600")
        options.add_argument("disable-gpu")
        options.add_argument("lang=ko_KR")
        options.add_argument(
            "user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/74.0.3729.169 Safari/537.36"
        )

        self.driver = webdriver.Chrome(self.DRIVER_PATH, options=options)
        self.driver.implicitly_wait(time_to_wait=10)

    def insta_login(self):
        self.driver.get('https://www.instagram.com/')
        username_box = self.driver.find_element_by_xpath('//input[@name="username"]')
        username_box.send_keys(self.INSTA_ID)

        passwd_box = self.driver.find_element_by_xpath('//input[@name="password"]')
        passwd_box.send_keys(self.INSTA_PASSWD)
        passwd_box.send_keys(Keys.RETURN)
        time.sleep(5)

    def influencer_info(self):
        if self.driver.get_window_size()['width'] > 735:
            self.driver.set_window_size(730, 1600)
        ul = self.driver.find_elements_by_xpath("//ul")[-1]
        influencer_info = ul.find_elements_by_xpath('.//li')

        result = defaultdict(int)
        for key, idx in [("post", 0), ("follower", 1), ("follew", 2)]:
            info_text = influencer_info[idx].text
            num_post = info_text.split('\n')[1].replace(',', '')
            result[key] = num_post
        return result

    def run_crawling_user_page(self, instagram_id):
        self.driver.get('https://www.instagram.com/' + instagram_id)
        time.sleep(5)
        crawled_post_id = self.db.select_remain_task_url_list_in_instagram_id(instagram_id)
        crawled_post_id = set(crawled_post_id)

        influencer_info = self.influencer_info()
        num_post = int(influencer_info['post'])

        self.logger.info('Crawling Instagram User [%s], [%d / %d]' % (instagram_id, len(crawled_post_id), num_post))
        if len(crawled_post_id) == num_post:
            return
        self.get_post_url_list(instagram_id, crawled_post_id, num_post)

    def get_post_url_list(self, instagram_id, crawled_post_id, num_post):
        self.driver.execute_script("window.scrollTo(0, 0)")
        time.sleep(5)

        while num_post > len(crawled_post_id):
            post_area = self.driver.find_elements_by_xpath("//article/div[1]/div[1]/div")
            for row in post_area:
                for elem in row.find_elements_by_xpath("./div"):
                    for post in elem.find_elements_by_xpath('./a'):
                        post_id = post.get_attribute('href')
                        if post_id in crawled_post_id:
                            continue

                        remain_task_row = RemainTaskRow(instagram_id=instagram_id, url=post_id)
                        self.db.insert_to_remain_task(remain_task_row)

                        crawled_post_id.add(post_id)
            self.logger.info('progress %d / %d' % (len(crawled_post_id), num_post))
            self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")
            time.sleep(3)
        return list(crawled_post_id)

    def close_post(self):
        cancel_btn = self.driver.find_element_by_xpath('/html/body/div[5]/div[3]/button')
        cancel_btn.click()

    def crawling_post(self):
        task_list = self.db.select_remain_task_where_is_processed_false(10)

        for task in task_list:
            self.driver.get(task.url)

            post = self.get_post_info()
            post_id = self.db.insert_post(post)
            post.id = post_id
            self.crawling_post_images(post)

            self.db.update_task_is_processed_set_true(task.id)

    def crawling_post_images(self, post):
        image_list = set()

        def get_post_image():
            images = self.driver.find_elements(By.XPATH,
                                               '/html/body/div[1]/section/main/div/div[1]/article/div[2]/div/div[1]/div[2]/div/div/div/ul/li')
            for img in images:
                if not img.get_attribute('class'):
                    continue
                li_img = img.find_elements(By.XPATH, './div/div/div//img')
                image_list.add(li_img[0].get_attribute('src'))

        def save_image_and_click_next():
            elem = self.driver.find_element(By.XPATH,
                                            '/html/body/div[1]/section/main/div/div[1]/article/div[2]/div/div[1]/div[2]/div')
            buttons = elem.find_elements(By.XPATH, './button')

            get_post_image()
            buttons[-1].click()
            time.sleep(1)
            return len(buttons)

        button_div_box = self.driver.find_element(By.XPATH,
                                        '/html/body/div[1]/section/main/div/div[1]/article/div[2]/div/div[1]/div[2]/div')
        buttons_box = button_div_box.find_elements(By.XPATH, './button')
        if len(buttons_box) == 0:
            return

        is_first = True
        while True:
            num_btn = save_image_and_click_next()

            if is_first:
                is_first = False
                continue

            if num_btn == 1:
                break

        self.save_images(image_list, post)

    def save_images(self, image_list, post):
        for i, src in enumerate(image_list):
            filename = uuid.uuid4().hex + '.jpg'
            path = os.path.join(self.image_dir, filename)

            resp = requests.get(src, stream=True)
            with open(path, 'wb') as f:
                resp.raw.decode_content = True
                shutil.copyfileobj(resp.raw, f)
            del resp
            post_image = PostImages(post_id=post.id, file_path=path)
            self.db.insert_post_image(post_image)

    def get_post_info(self):
        parser = fromstring(self.driver.page_source)
        instagram_id_box = parser.xpath(
            '/html/body/div[1]/section/main/div/div[1]/article/header/div[2]/div[1]/div[1]/a')
        instagram_id = instagram_id_box[0].text
        location_info_box = parser.xpath(
            '/html/body/div[1]/section/main/div/div[1]/article/header/div[2]/div[2]/div[2]/a')
        location_info = location_info_box[0].text
        contents_box = parser.xpath(
            '/html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span')
        contents = contents_box[0].text_content()
        tags_box = parser.xpath(
            '/html/body/div[1]/section/main/div/div[1]/article/div[3]/div[1]/ul/div/li/div/div/div[2]/span/a')
        tags = ','.join([tag.text for tag in tags_box])
        post = Post(location=location_info, contents=contents, tags=tags, instagram_id=instagram_id)
        return post

    def run(self, id_list):
        try:
            self.insta_login()
        except:
            self.logger.error('instagram login error')
            self.logger.error(traceback.format_exc())
            return

        for instagram_id in id_list:
            try:
                self.run_crawling_user_page(instagram_id)
            except:
                self.logger.error('Error instagram id : ' + instagram_id)
                self.logger.error(traceback.format_exc())
            time.sleep(random.randint(30, 60))

    def __del__(self):
        if self.driver:
            self.driver.close()

crawler = InstagramCrawler()

# id_list = ['shalala_sso', 'panajjjjang', 'oreo_ming', 'ssunny2113', 'misik_holic', 'mat_poleon', 'mat_thagoras',
#            'songchelin_guide', 'bitterpan_i', 'naegung_tasty', 'soju_anju_', 'hdk_chef', 'dduziny_chelin',
#            'travellerjun', 'mattamyoung', 'my_chaan']
# crawler.run(id_list)

crawler.crawling_post()
