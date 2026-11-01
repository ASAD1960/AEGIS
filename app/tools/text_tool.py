"""
AEGIS Text Analysis Tool

Performs basic text analysis operations.
"""


class TextAnalysisTool:

    def analyze(self, text):

        if not isinstance(text, str):
            raise TypeError("Input must be a string.")

        if not text.strip():
            raise ValueError("Text cannot be empty.")

        words = text.split()

        sentences = [
            sentence
            for sentence in text.replace("!", ".").replace("?", ".").split(".")
            if sentence.strip()
        ]

        return {
            "word_count": len(words),
            "character_count": len(text),
            "sentence_count": len(sentences),
        }