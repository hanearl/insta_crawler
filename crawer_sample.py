import csv
import time
import random

from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup


class Parser:
    def __init__(self, driver_path='./data/chromedriver'):
        self.driver = webdriver.Chrome(driver_path)

    def parse_board_list(self, page=0):
        self.driver.get('https://m.bobaedream.co.kr/board/new_writing/national/'+str(page))
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        board = soup.find("ul", class_="rank").find_all('div', class_='info')
        return [bbs.find('a').attrs['href'] for bbs in board]

    def __parse_board(self, soup):
        board = Board()
        article_tit = soup.find('header', class_='article-tit')
        board.title = article_tit.find("div", class_='title').find('h3').text

        util = article_tit.find("div", class_="util")
        board.date = util.find('time').text
        board.like = util.find('span', class_='data3').text
        board.hit = util.find('span', class_='data4').text
        board.writer = article_tit.find('div', class_='util2').find('span').text

        article_body = soup.find('div', class_='article-body')
        board.content = article_body.text

        board.images = article_body.find_all('img')

        replies = []
        for r in soup.find_all('div', class_='con_area'):
            reply = Reply()
            reply.content = r.find('div', class_='reply').text

            r_info = r.find('div', class_='util').find_all('span')
            reply.writer = r_info[0].text
            reply.date = r_info[1].text
            replies.append(reply)
        board.replies = replies

        return board

    def parse_board(self, url):
        self.driver.get(url)
        soup = BeautifulSoup(self.driver.page_source, 'html.parser')
        return self.__parse_board(soup)

    def __del__(self):
        self.driver.close()

p = Parser()
b_list = p.parse_board_list(1)
print(b_list)
mobile_url = 'https://m.bobaedream.co.kr'

print(p.parse_board(mobile_url + b_list[0]))