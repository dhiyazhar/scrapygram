import os
import csv

from requests import Session, Response
from json import dumps
from dotenv import load_dotenv
from time import sleep
from datetime import datetime
from time import time

from comment.helpers import logging

class Comment:
    def __init__(self, cookie: str = None) -> None:
        if not cookie:
            return logging.error('cookie required !')

        self.__min_id: str = None
        self.__all_comments: list = []  

        self.__result: dict = {
            "username": None,
            "full_name": None,
            "caption": None,
            "date_now": None,
            "create_at": None,
            "post_url": None,
            "comments": []  
        }
        
        self.__requests : Session = Session()
        self.__requests.headers.update({
            "Cookie": cookie,
            "User-Agent": "Instagram 126.0.0.25.121 Android (23/6.0.1; 320dpi; 720x1280; samsung; SM-A310F; a3xelte; samsungexynos7580; en_GB; 110937453)"
        })

    def __format_date(self, milisecond: int) -> str:
        try:
            return datetime.fromtimestamp(milisecond).strftime("%Y-%m-%dT%H:%M:%S")
        except:
            return datetime.fromtimestamp(milisecond / 1000).strftime("%Y-%m-%dT%H:%M:%S")


    def __dencode_media_id(self, post_id: str) -> int:
        alphabet: str = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_'
        media_id: int = 0

        for char in post_id:
            media_id = media_id * 64 + alphabet.index(char)

        return media_id

    def __build_params(self) -> dict:
        return {
            "can_support_threading": True,
            "sort_order": "popular",
            **({"min_id": self.__min_id} if self.__min_id else {})
        }
    
    def __get_reply_comment(self, comment_id: str):
        min_id: str = ''
        child_comments: list = []

        while True:
            response: Response = self.__requests.get(f'https://www.instagram.com/api/v1/media/{self.__media_id}/comments/{comment_id}/child_comments/?min_id={min_id}').json()

            child_comments.extend([
                {
                    "username": comment["user"]["username"],
                    "full_name": comment["user"]["full_name"],
                    "comment": comment["text"],
                    "create_time": self.__format_date(comment["created_at"]),
                    "avatar": comment["user"]["profile_pic_url"],
                    "total_like": comment["comment_like_count"],
                } for comment in response['child_comments']
            ])

            if(not response['has_more_head_child_comments']): break
            
            min_id: str = response['next_min_child_cursor'] 

            sleep(1)
        return child_comments

    def __filter_comments(self, response: dict) -> None:
        for comment in response['comments']:
            logging.info(comment['text'])

            comment_data = {
                "username": comment["user"]["username"],
                "full_name": comment["user"]["full_name"],
                "comment": comment["text"],
                "create_time": self.__format_date(comment["created_at"]),
                "avatar": comment["user"]["profile_pic_url"],
                "total_like": comment["comment_like_count"],
                "total_reply": comment["child_comment_count"],
                "replies": self.__get_reply_comment(comment['pk']) if comment['child_comment_count'] else []
            }

            self.__all_comments.append(comment_data)  # Append to the accumulated comments list
            sleep(1)

        if 'next_min_id' in response:
            self.__min_id = response['next_min_id']
        else:
            return True

        self.__min_id = response['next_min_id'] 

        
    def excecute(self, post_id: str):
        self.__media_id = self.__dencode_media_id(post_id)
        while True:
            response: Response = self.__requests.get(
                f'https://www.instagram.com/api/v1/media/{self.__media_id}/comments/',
                params=self.__build_params()
            )

            if response.status_code != 200:
                return

            data: dict = response.json()

            if not self.__result['comments']:
                self.__result["username"]: str = data["caption"]["user"]["username"]
                self.__result["full_name"]: str = data["caption"]["user"]["full_name"]
                self.__result["caption"]: str = data["caption"]["text"]
                self.__result["date_now"]: str = self.__format_date(round(time() * 1000))
                self.__result["create_at"]: str = self.__format_date(data["caption"]["created_at"])
                self.__result["post_url"]: str = f"https://instagram.com/p/{post_id}"

            if self.__filter_comments(data):
                break

        # Populate self.__result['comments'] with the accumulated comments
        self.__result['comments'] = self.__all_comments

        return self.__result

    def to_csv(self, output_file: str, post_id: str):
        csv_file_path = f'{output_file}.csv'
        with open(csv_file_path, mode='w', newline='', encoding='utf-8') as csv_file:
            fieldnames = ['username', 'full_name', 'comment', 'create_time', 'avatar', 'total_like', 'total_reply', 'replies']
            writer = csv.DictWriter(csv_file, fieldnames=fieldnames)

            writer.writeheader()
            for comment in self.__result['comments']:
                writer.writerow({
                    'username': comment['username'],
                    'full_name': comment['full_name'],
                    'comment': comment['comment'],
                    'create_time': comment['create_time'],
                    'avatar': comment['avatar'],
                    'total_like': comment['total_like'],
                    'total_reply': comment['total_reply'],
                    'replies': comment['replies']
                })

        logging.info(f'Output CSV data: {csv_file_path}')


# testing
if(__name__ == '__main__'):
    load_dotenv() 
    cookie = os.getenv("COOKIE") 

    comment: Comment = Comment(cookie)
    # comment.excecute('C1ACfnvh4KE')
    # comment.excecute('C1Ww1LChZhN')
    data: dict = comment.excecute('Cm2cJmABD1p')
    with open('test_data.json', 'w') as file:
        file.write(dumps(data, indent=2, ensure_ascii=False))
