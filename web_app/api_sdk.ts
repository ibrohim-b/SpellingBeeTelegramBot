interface Definition {
    definition: string
    example: string | null
}

interface Meaning {
    partOfSpeech: string
    definitions: Array<Definition>
    synonyms: Array<string>
    antonyms: Array<string>
}

interface ExtraInfo {
    phonetics: Array<string>
    audio: string | null
    meanings: Array<Meaning>
}

interface Word {
    word_id: number
    word_spell: string
    word_translation: string
    extra_info: ExtraInfo | null
}


class APISDK {

    private static instance: APISDK | null = null;
    api_url: string = "http://159.223.180.158:8000"

    private constructor() {
    }

    public static getInstance(): APISDK {
        if (APISDK.instance === null) {
            APISDK.instance = new APISDK();
        }
        return APISDK.instance;
    }

    async getRandomWord(user_id: number): Promise<Word | null> {
        const response = await fetch(`${(this.api_url)}`);
        if (response.ok) {
            const data = await response.json();
            return data;
        } else {
            return null;
        }
    }
}