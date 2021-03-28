import psycopg2
import traceback
from logger import make_logger


class RemainTaskRow:
    id = None
    instagram_id = None
    url = None
    insert_date = None
    is_processed = None

    def __init__(self, instagram_id, url):
        self.instagram_id = instagram_id
        self.url = url

    def __init__(self, id, instagram_id, url):
        self.id = id
        self.instagram_id = instagram_id
        self.url = url

class Post:
    id = None
    location = None
    contents = None
    tags = None
    instagram_id = None

    def __init__(self, location, contents, tags, instagram_id):
        self.location = location
        self.contents = contents
        self.tags = tags
        self.instagram_id = instagram_id


class PostImages:
    id = None
    post_id = None
    file_path = None

    def __init__(self, post_id, file_path):
        self.post_id = post_id
        self.file_path = file_path

class DatabaseHelper:
    def __init__(self):
        conn_info = {'host': '192.168.219.110', 'dbname': 'insta_matzip', 'user': 'postgres',
                     'password': 'qwerqwer', 'port': '5432'}
        self.conn = psycopg2.connect(**conn_info)
        self.conn.autocommit = True
        self.cur = self.conn.cursor()
        self.logger = make_logger('db')

    def insert_to_remain_task(self, remain_task: RemainTaskRow):
        sql = "INSERT INTO remain_task (instagram_id, url, insert_date) VALUES ('%s', '%s', now());" % \
              (remain_task.instagram_id, remain_task.url)
        try:
            self.cur.execute(sql)
        except:
            self.logger.error('insert to remain taks error')
        finally:
            pass

    def select_remain_task_url_list_in_instagram_id(self, instagram_id):
        sql = "SELECT url FROM remain_task WHERE instagram_id = '%s';" % instagram_id
        try:
            self.cur.execute(sql)
            url_list = self.cur.fetchall()
        except:
            self.logger.error('select remain task url list Error')
            self.logger.error(traceback.format_exc())
            return []

        return [x[0] for x in url_list]

    def select_remain_task_where_is_processed_false(self, num_list=1000):
        sql = "SELECT id, instagram_id, url FROM remain_task WHERE is_processed is FALSE LIMIT %s;" % (num_list)
        try:
            self.cur.execute(sql)
            url_list = self.cur.fetchall()
        except:
            self.logger.error('select remain task where is_processed is False list Error')
            self.logger.error(traceback.format_exc())
            return []

        return [RemainTaskRow(x[0], x[1], x[2]) for x in url_list]

    def insert_post(self, post: Post):
        sql = "INSERT INTO post (location, contents, tags, instagram_id) VALUES ('%s', '%s', '%s', '%s') RETURNING id;" % \
              (post.location, post.contents, post.tags, post.instagram_id)
        try:
            self.cur.execute(sql)
            id = self.cur.fetchone()[0]
        except:
            self.logger.error('insert post Error')
            self.logger.error(traceback.format_exc())
            return None

        return id

    def insert_post_image(self, post_image: PostImages):
        sql = "INSERT INTO post_images (post_id, file_path) VALUES ('%s', '%s');" % \
              (post_image.post_id, post_image.file_path)
        try:
            self.cur.execute(sql)
        except:
            self.logger.error('insert post image Error')
            self.logger.error(traceback.format_exc())

    def update_task_is_processed_set_true(self, task_id):
        sql = "UPDATE remain_task SET is_processed = TRUE WHERE id = %d" % \
              (task_id)
        try:
            self.cur.execute(sql)
        except:
            self.logger.error('update task is_processed set true Error')
            self.logger.error(traceback.format_exc())

    def __del__(self):
        if self.cur:
            self.cur.close()
        if self.conn:
            self.conn.close()
