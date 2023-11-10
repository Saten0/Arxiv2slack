from datetime import datetime
import re
import requests
import pickle
import os
import deepl
import requests
import openai
import random
import time
import json

source_lang = 'EN'
target_lang = 'JA'
openai.api_key = "..." #ChatGPTのAPIキー
API_KEY = '' #DeepLのAPIキー


# webhook POST先URL
API_URL = "..." #IFTTTのHPから取得できる

#参考
#https://zenn.dev/ozushi/articles/ebe3f47bf50a86
#https://qiita.com/Hiroaki-K4/items/579014b41adc85fe919f
#この辺のコードをパクっている
#requestsで取ってきているが(パクっている)、arxivライブラリを使えば簡略化可能(面倒だしやってることは全く同じなのでまあいいか状態)


# 検索ワード
QUERY = '((abs:"tensor networks")+OR+(abs:"tensor network")+OR+(ti:"tensor networks")+OR+(ti:"tensor network"))'

def get_summary(title,result):
    system =  """```
以下の制約条件と、入力された論文のタイトル、概要をもとに最高の要約を出力してください。

制約条件:
・文章は簡潔にわかりやすく。
・箇条書きで3行で出力。
・重要なキーワードは取り逃がさない。
・要約した文章は日本語へ翻訳。

期待する出力フォーマット:
1.
2.
3.

```"""

    text = f"title: {title}\n Abstract: {result}"
    response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {'role': 'system', 'content': system},
                    {'role': 'user', 'content': text}
                ],
                temperature=0.25,
            )
    summary = response['choices'][0]['message']['content']
#    title, *body = summary.split('\n')
#    body = '\n'.join(body)
#    message = f"{body}\n"
    return summary

def parse(data, tag):
    # parse atom file
    # e.g. Input :<tag>XYZ </tag> -> Output: XYZ

    pattern = "<" + tag + ">([\s\S]*?)<\/" + tag + ">"
    if all:
        obj = re.findall(pattern, data)
    return obj


number = 5 # 何件拾ってくるか
#Arxivライブラリを使えば大幅簡略可能だが、やる事は一緒なのでやっていない
def search_and_send(query, start, ids, api_url):
    translator = deepl.Translator(API_KEY)
    while True:
        counter = 0
        url = 'http://export.arxiv.org/api/query?search_query=' + query + '&start=' + str(
            start) + '&max_results=' + number +'&sortBy=lastUpdatedDate&sortOrder=descending'
        # Get returned value from arXiv API
        data = requests.get(url).text
        # Parse the returned value
        entries = parse(data, "entry")
        for entry in entries:
            # Parse each entry
            url = parse(entry, "id")[0]
            if not (url in ids):
                print("exists")
                # parse
                title = parse(entry, "title")[0]
                title = title.replace('\n', '')
                abstract = parse(entry, "summary")[0]
                Authors = ', '.join(parse(entry, "name") )
                date = parse(entry, "published")[0]
                print(title)
                # abstの改行を取る
                abstract = abstract.replace('\n', '')

                # 日本語化 ★②の部分
                summary_result = get_summary(title,abstract)
                title_jap = translator.translate_text(title, source_lang=source_lang, target_lang=target_lang)
                abstract_jap = translator.translate_text(abstract, source_lang=source_lang, target_lang=target_lang)

                message1 = "\n".join(
                     ["<br>*Title:  " + title+"*<br>" +  title_jap.text,"<br><br>Authors: " + Authors, "<br><br>URL: " + url, "<br><br>Date: " + date ])         
                
                message2 = "\n".join(
                    ["<br><br>>Abstract: " + abstract]
                )
                message3 = "\n".join(
                    ["<br><br>>Abstract(日本語):" +  abstract_jap.text, "<br><br>Summary by ChatGPT(3.5):<br> " + summary_result]
                )
                # webhookへPost ★①の部分
                response = requests.post(api_url, data=json.dumps({"value1": message1}),headers={'Content-Type': 'application/json'})
                time.sleep(3)
                response = requests.post(api_url, data=json.dumps({"value1": message2}),headers={'Content-Type': 'application/json'})
                time.sleep(3)
                response = requests.post(api_url, data=json.dumps({"value1": message3}),headers={'Content-Type': 'application/json'})
                ids.append(url)
                counter = counter + 1
                if counter == number:
                    return 0
        if counter == 0 and len(entries) < number:
            requests.post(api_url, data={"value1": "Currently, there is no available papers"})
            return 0
        elif counter == 0 and len(entries) == number:
            # When there is no available paper and full query
            requests.post(api_url, data={"value1": "新しい論文はありません"})
            return 0


if __name__ == "__main__":
    print("Publish")
    # setup =========================================================
    # Set URL of API
    api_url = API_URL

    # Load log of published data
    if os.path.exists("/mnt/c/Users/Linra/Documents/tools_on_ubuntu/paper/published.pkl"):
        ids = pickle.load(open("/mnt/c/Users/Linra/Documents/tools_on_ubuntu/paper/published.pkl", 'rb'))
        #ここは自分が保存したところに設置(コマンド使って取得するのがいいかも)
    else:
        ids = []

    # Query for arXiv API
    query = QUERY


    # start =========================================================
    start = 0

    # Post greeting to your Slack
#    dt = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
#    requests.post(api_url, data={"value1": dt})

    # Call function
    search_and_send(query, start, ids, api_url)

    # Update log of published data
    pickle.dump(ids, open("/mnt/c/Users/Linra/Documents/tools_on_ubuntu/paper/published.pkl", "wb"))
    #ここも変えておくのがいいです
