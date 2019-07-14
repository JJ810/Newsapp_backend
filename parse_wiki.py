from time import sleep
import random
from bs4 import BeautifulSoup
import requests

session_requests = requests.session()

desktop_agents = [
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/602.2.14 (KHTML, like Gecko) Version/10.0.1'
    ' Safari/602.2.14',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98'
    ' Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_6) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.98'
    ' Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.71 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/54.0.2840.99 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:50.0) Gecko/20100101 Firefox/50.0']

# email_body_url = input("Please Enter Racecard url with date: ")

dictionary = {}


def random_headers():
    return {'User-Agent': random.choice(desktop_agents)}


def get_wiki_result_dic(keyword):
    try:
        url = "https://en.wikipedia.org/wiki/" + keyword
        description = ""
        image_url = ""
        dictionary_my = {'keyword': keyword.replace("_", " ")}
        print("Going To:", url)
        result = session_requests.get(url, headers=random_headers())
        print(result.ok, result.status_code)
        if result.ok and result.status_code == 200:
            soup = BeautifulSoup(result.text, 'lxml')
            main_div = soup.find('div', attrs={'id': 'mw-content-text', 'lang': 'en', 'class': 'mw-content-ltr'})

            # Find all paragraphs

            full_para = ""
            try:
                paras = main_div.find_all('p')
                for para in paras:
                    full_para += para.text
                # print(full_para)
                try:
                    x = full_para.split('.')
                    # split paragraphs on bases of dot
                    description = x[0]
                    description = description.replace("\n", "").replace("\xa0", "")
                except Exception as e:
                    print(e)
            except Exception as e:
                print(e)
            # find image_url
            try:
                table = main_div.find('table', attrs={"class": "infobox"})
                try:
                    refs = table.find_all('a')
                    for ref in refs:
                        if str(ref['href']).lower().__contains__("wiki/file:"):
                            href = ref.find('img').get('srcset')
                            href = href.split(",")
                            href[0] = href[0].replace("1.5x", "")
                            link = ('https:' + href[0])
                            image_url = link
                            break
                except:
                    pass
                    # break
            except Exception as e:
                print(e)
            if description and description.strip(" ").__len__() > 0:
                dictionary_my['description'] = description.strip(" ")

            if image_url is not None and image_url.strip(" ").__len__() > 0:
                dictionary_my['image_url'] = image_url.strip(" ")

            print(dictionary_my)
    except Exception as e:
        dictionary_my = {}
        print(e)
    finally:
        return dictionary_my


# if __name__ == "__main__":
#     get_wiki_result_dic("San_Francisco")
