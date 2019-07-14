# coding: utf-8

# pip install sumy
from sumy.parsers.plaintext import PlaintextParser
from sumy.parsers.html import HtmlParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.nlp.stemmers import Stemmer
from sumy.utils import get_stop_words
import io
import re
import spacy
import PyPDF2
import nltk
from nltk.corpus import stopwords
import string
from nltk.tokenize import word_tokenize
from nltk.corpus import wordnet
import urllib
from bs4 import BeautifulSoup

SENTENCES_COUNT = 2


def simple_check():
    SUMMARY_SENTENCES_COUNT = 5
    LANGUAGE = "english"
    URL = "https://qz.com/1367800/ubernomics-is-ubers-semi-secret-internal-economics-department/"
    parser = HtmlParser.from_url(URL, Tokenizer(LANGUAGE))
    document = parser.document
    stemmer = Stemmer(LANGUAGE)

    from sumy.summarizers.luhn import LuhnSummarizer

    LHS = LuhnSummarizer(stemmer)
    LHS.stop_words = get_stop_words(LANGUAGE)
    print("\nSummary using Luhn Summarizer")
    print("*******************************")
    for sentence in LHS(document, SUMMARY_SENTENCES_COUNT):
        print(sentence)

    html = urllib.request.urlopen(URL).read()
    soup = BeautifulSoup(html, features='html.parser')
    print(soup.prettify())


def get_data_list(URL, file_type=""):
    SUMMARY_SENTENCES_COUNT = 5
    sentences = []
    try:
        LANGUAGE = "english"
        # parser = None
        if file_type == "txt":
            parser = HtmlParser.from_string(URL, None, Tokenizer(LANGUAGE))
        elif file_type == "pdf":
            content = read_pdf(URL)
            parser = HtmlParser.from_string(content, None, Tokenizer(LANGUAGE))
        else:
            parser = HtmlParser.from_url(URL, Tokenizer(LANGUAGE))

        document = parser.document
        stemmer = Stemmer(LANGUAGE)

        from sumy.summarizers.luhn import LuhnSummarizer

        LHS = LuhnSummarizer(stemmer)
        LHS.stop_words = get_stop_words(LANGUAGE)
        print("\nSummary using Luhn Summarizer")
        print("*******************************")
        for sentence in LHS(document, SUMMARY_SENTENCES_COUNT):
            sentences.append(str(sentence))
    except Exception as e:
        print(str(e))
    finally:
        return sentences


def get_human_names(text):
    tokens = nltk.tokenize.word_tokenize(text)
    pos = nltk.pos_tag(tokens)
    sentt = nltk.ne_chunk(pos, binary=False)
    person_list = []
    person = []
    name = ""
    for subtree in sentt.subtrees(filter=lambda t: t.label() == 'PERSON'):
        for leaf in subtree.leaves():
            person.append(leaf[0])
        if len(person) > 1:
            for part in person:
                name += part + ' '
            if name[:-1] not in person_list:
                person_list.append(name[:-1])
            name = ''
        person = []
    person_names = person_list
    for person in person_list:
        person_split = person.split(" ")
        for name in person_split:
            if wordnet.synsets(name):
                if name in person:
                    person_names.remove(person)
                    break
    return person_names


def getKeyWords(text):
    dic = {}
    try:
        names = get_human_names(text)

        tokens = word_tokenize(text)
        table = str.maketrans('', '', string.punctuation)
        stripped = [w.translate(table) for w in tokens]
        words = [word for word in stripped if word.isalpha()]
        newWords = []
        for word in words:
            if word.isupper():
                newWords.append(word)
            else:
                word = word.lower()
                newWords.append(word)

        stop_words = set(stopwords.words('english'))
        words = [w for w in newWords if not w in stop_words]

        newWords = []
        ind = False
        for word in words:
            if len(word) > 1:
                if ind:
                    word = word.capitalize()
                    word = word + ','
                newWords.append(word)
                ind = False
            if len(word) == 1:
                newWords.append(word + '.')
                ind = True
        words = newWords

        text = ' '.join(words)
        # names = get_human_names(text)
        # input()
        # print("1")
        import traceback
        import sys

        try:
            spacy.prefer_gpu()
            nlp = spacy.load('xx_ent_wiki_sm')
        except Exception:
            print(traceback.format_exc())

        # print("2")
        organizations = {}
        person = {}
        doc = nlp(text)
        for name in names:
            if name in person:
                person[name] += 1
            else:
                person[name] = 1
        for ent in doc.ents:
            if ent.label_ == 'ORG':
                if ent.text in organizations:
                    organizations[ent.text] += 1
                else:
                    organizations[ent.text] = 1
        sorted_person = sorted(person.items(), key=lambda kv: kv[1], reverse=True)
        sorted_orgs = sorted(organizations.items(), key=lambda kv: kv[1], reverse=True)
        print('PERSON----\n')
        i = 0
        people_list = []
        for key, val in sorted_person:
            print(key, val)
            people_list.append(str(key) + " " + str(val))
            i += 1
            if i == SENTENCES_COUNT:
                break
        print('\n\nORGANIZATION----\n')
        i = 0
        organization_list = []
        for key, val in sorted_orgs:
            print(key, val)
            organization_list.append(str(key) + " " + str(val))
            i += 1
            if i == SENTENCES_COUNT:
                break
        dic = {'people': people_list, 'organization': organization_list}
    except Exception as e:
        dic = {'people': [], 'organization': []}
        print(str(e))
    finally:
        return dic


def get_keywords_dic(URL, file_type=""):
    try:
        text = URL
        if file_type == "":
            html = urllib.request.urlopen(URL).read()
            soup = BeautifulSoup(html, features='html.parser')
            # kill all script and style elements
            for script in soup(["script", "style"]):
                script.extract()  # rip it out
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            # break multi-headlines into a line each
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            # drop blank lines
            text = ' '.join(chunk for chunk in chunks if chunk)
        elif file_type == "pdf":
            text = read_pdf(URL)
        return getKeyWords(text)
    except Exception as e:
        print(str(e))


def read_pdf(pdf):
    pdf_content = io.BytesIO(pdf)
    text = ''
    pdfReader = PyPDF2.PdfFileReader(pdf_content)
    for i in range(pdfReader.numPages):
        pageObj = pdfReader.getPage(i)
        text += pageObj.extractText()
    spaced = re.sub(r"\r\n", " ", text)
    return spaced
    # print(spaced)
    # getKeyWords(spaced)

# print(get_keywords_dic("https://qz.com/1367800/ubernomics-is-ubers-semi-secret-internal-economics-department/"))
