import sqlite3

from gtts import gTTS

db = sqlite3.connect("./words.db")
cursorObj = db.cursor()


rows = cursorObj.execute("select word from words").fetchall()
for row in rows:
    word = row[0]
    print(word)
    tts = gTTS(word)
    tts.save(f'words_mp3/{word}.mp3')