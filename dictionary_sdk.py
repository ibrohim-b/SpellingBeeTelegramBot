import requests


class DictionaryClient():
    def __init__(self):
        self.base_url = "https://api.dictionaryapi.dev/api/v2/entries/en"

    def get_definition(self, word):
        response = requests.get(f"{self.base_url}/{word}")
        if response.status_code == 200:
            return DictionaryWord(response.json()[0])
        else:
            return None


class DictionaryWord:
    def __init__(self, response):
        self.word = response['word']
        self.response = response
        self.phonetics = []
        for phonetic in response['phonetics']:
            if 'text' in phonetic:
                self.phonetics.append(phonetic['text'])
        self.meanings = []
        for meaning in response['meanings']:
            self.meanings.append(Meaning(meaning))

    def __str__(self):
        return f"Word: {self.word}\nPhonetics: {self.phonetics}\nMeanings: {self.meanings}"


class Meaning:
    def __init__(self, meaning):
        self.part_of_speech = meaning['partOfSpeech']
        self.definitions = []
        for definition in meaning['definitions']:
            self.definitions.append(Definition(definition))
        self.synonyms = meaning['synonyms']
        self.antonyms = meaning['antonyms']

    def __str__(self):
        return f"Part of Speech: {self.part_of_speech}\nDefinitions: {self.definitions}\nSynonyms: {self.synonyms}\nAntonyms: {self.antonyms}"

class Definition():
    def __init__(self, _definition):
        self.definition = _definition['definition']
        self.example = None
        if 'example' in _definition:
            self.example = _definition['example']

    def __str__(self):
        return f"Definition: {self.definition}\nExample: {self.example}"


if __name__ == "__main__":
    client = DictionaryClient()
    hello = client.get_definition("hello")
    for meaning in hello.meanings:
        for definition in meaning.definitions:
            print(definition)
        print(meaning.synonyms)
        print(meaning.antonyms)
    print(hello.word)
