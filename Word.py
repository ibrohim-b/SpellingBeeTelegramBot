class Word:
    def __init__(self, word_id: str, word: str, word_translation: str) -> None:
        self.word_id = word_id
        self.word_spell = word
        self.word_translation = word_translation

    def __str__(self):
        return f"Word(word_id = {self.word_id}, word = {self.word_spell}, word_translation = {self.word_translation})"
