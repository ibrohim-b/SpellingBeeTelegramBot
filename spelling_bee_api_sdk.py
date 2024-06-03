import os
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()


class SpellingBeeSdk:
    def __init__(self):
        self.base_url = os.getenv("spelling_bee_api_address")

    def get_random_word(self, user_id: int):
        response = requests.get(f"{self.base_url}/words/get_random_word?user_id={user_id}")
        if response.status_code == 200:
            return Word(**response.json())
        else:
            return None

    def user_exists(self, user_id: int):
        response = requests.get(f"{self.base_url}/users/user_exists?user_id={user_id}")
        if response.status_code == 200:
            return bool(response.json())
        return False

    def user_has_name(self, user_id: int):
        response = requests.get(f"{self.base_url}/users/user_has_name?user_id={user_id}")
        if response.status_code == 200:
            return bool(response.json())
        return False

    def create_user(self, user_id: int, user_name: str):
        requests.post(f'{self.base_url}/users/create_user?user_id={user_id}&user_name={user_name}')

    def update_user_name(self, user_id: int, user_name: str):
        requests.put(f'{self.base_url}/users/update_name?user_id={user_id}&user_name={user_name}')

    def add_suggestion(self, word_id: int, user_id: int):
        requests.post(f'{self.base_url}/suggestions/add_suggestion?word_id={word_id}&user_id={user_id}')

    def update_suggestion(self, word_id: int, user_id: int, passed: int):
        requests.put(
            f"{self.base_url}/suggestions/update_suggestion?word_id={word_id}&user_id={user_id}&passed={passed}")

    def get_total_words_passed_count(self, user_id: int):
        response = requests.get(f"{self.base_url}/statistics/get_total_words_passed_count?user_id={user_id}")
        if response.status_code == 200:
            return int(response.json())
        return 0

    def get_total_words_count(self):
        response = requests.get(f"{self.base_url}/statistics/get_total_words_count")
        if response.status_code == 200:
            return int(response.json())
        return 0

    # get top list of users by words passed count
    def get_top_list_of_users(self):
        response = requests.get(f"{self.base_url}/statistics/get_top_list_of_users")
        if response.status_code == 200:
            return [User(**user) for user in response.json()]
        return []


@dataclass
class Definition:
    definition: str
    example: Optional[str]


@dataclass
class Meaning:
    part_of_speech: str
    definitions: [Definition]
    synonyms: [str]
    antonyms: [str]

    def __post_init__(self):
        self.definitions = [Definition(**definition) for definition in self.definitions]


@dataclass
class ExtraInfo:
    phonetics: [str]
    audio: Optional[str]
    meanings: [Meaning]

    def __post_init__(self):
        self.meanings = [Meaning(**meaning) for meaning in self.meanings]


@dataclass
class Word:
    word_id: int
    word_spell: str
    word_translation: str
    extra_info: ExtraInfo | None

    def __str__(self):
        return f"Word(word_id = {self.word_id}, word = {self.word_spell}, word_translation = {self.word_translation})"

    def __post_init__(self):
        self.extra_info = ExtraInfo(**self.extra_info) if self.extra_info else None


@dataclass
class User:
    user_id: int
    user_name: str
    passed: int


if __name__ == '__main__':
    spelling_bee_api_sdk = SpellingBeeSdk()
    print(spelling_bee_api_sdk.user_exists(142264444))
    r = spelling_bee_api_sdk.get_random_word(142264444)
    print(r)
    print(r.extra_info)
    # print(r.extra_info.audio)
    # print(r.extra_info.phonetics)
    # print(r.extra_info.meanings[0].part_of_speech)
