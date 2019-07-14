import re
import os
import spacy
import urllib
from bs4 import BeautifulSoup
import operator
import PyPDF2
import nltk
from nltk.corpus import stopwords
import string
from nltk.tokenize import word_tokenize
from nameparser.parser import HumanName
from nltk.corpus import wordnet


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
                if (name in person):
                    person_names.remove(person)
                    break

    return (person_names)


def getKeyWords(text):
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
    nlp = spacy.load('xx_ent_wiki_sm')
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
    for key, val in sorted_person:
        print(key, val)
        i += 1
        if i == 5:
            break
    print('\n\nORGANIZATION----\n')
    i = 0
    for key, val in sorted_orgs:
        print(key, val)
        i += 1
        if i == 5:
            break


if __name__ == '__main__':
    # C:\Users\Lenovo\Desktop\Inam\FoodSecurityChap1_Vira.pdf
    nltk.download('wordnet')
    choice = input('MENU\n1.URL\n2.PDF\nChoice: ')

    if choice == '1':
        url = input('\nPlease enter URL: ')
        html = urllib.request.urlopen(url).read()
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
        getKeyWords(text)

    if choice == '2':
        pdf = input('Enter path to the PDF file: ')
        pdfFileObj = open(pdf, 'rb')
        text = ''
        pdfReader = PyPDF2.PdfFileReader(pdfFileObj)
        for i in range(pdfReader.numPages):
            pageObj = pdfReader.getPage(i)
            text += pageObj.extractText()
        spaced = re.sub(r"\r\n", " ", text)
        getKeyWords(spaced)
        pdfFileObj.close()
