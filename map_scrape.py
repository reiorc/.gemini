# 終わるまで12時間かかる
#

# for each 1-47
# https://www.mapion.co.jp/phonebook/M01012/47/
# 最初のulのliのhrefを取得し、アクセス
# paginationがあれば取得し、最後のpagination-link内の数値まで、"/phonebook/M01012/13108/8.html" 
# https://www.mapion.co.jp/phonebook/M01012/13108/1.htmlを1～8までforループ
# class="list-table"のtbodyのhrefをforで回す
# 最初のテーブルのtbodyのtd内テキストを全て取得しcsvに書き出し

# from os import wait
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs
import csv
import time
import re

headers = {
    "User-Agent": "Mozilla/5.0"
}

pref_count = 2

# output_file = open(f"scraped_data{pref_count}.csv", "w", newline="", encoding="utf-8")
output_file = open(f"scraped_data_all.csv", "w", newline="", encoding="utf-8")
csv_writer = csv.writer(output_file)

# 1. sample/1 ～ sample/47 までループ
#for i in range(1, 48):
for i in range(1,48):
    print(f"フェーズ{i}開始")
    url = f"https://www.mapion.co.jp/phonebook/M01012/{str(i).zfill(2)}"
    res = requests.get(url, headers=headers)
    soup = BeautifulSoup(res.content, "html.parser")

    # 2. 最初の ul の中の li > a のリンクを取得
    ul = soup.find_all("ul")[1]
    if not ul:
        continue
    for li in ul.find_all("li"):
        a_tag = li.find("a", href=True)
        if not a_tag:
            continue
        base_link = "https://www.mapion.co.jp" + a_tag["href"]  # https://www.example2.com/xxx/
        #base_link = "https://www.mapion.co.jp/phonebook/M01012/13364/"
        
        # 3. pagination のチェック
        sub_res = requests.get(base_link, headers=headers)
        sub_soup = BeautifulSoup(sub_res.content, "html.parser")

        pagination = sub_soup.find("p", class_="pagination")
        if pagination:
            pages = pagination.find_all("a", class_="pagination-link")
            if pages:
                if pages[-1].get_text() == "後へ":
                    last_page_num = int(pages[-2].get_text())
                else:
                    last_page_num = int(pages[-1].get_text())
            else:
                last_page_num = 1
        else:
            last_page_num = 1

        # 3-2. ページ番号に基づいてループ
        for page in range(1, last_page_num + 1):
            page_url = f"{base_link}{page}.html"
            page_res = requests.get(page_url, headers=headers)
            page_soup = BeautifulSoup(page_res.content, "html.parser")
            print(f"{page_url}の解析を開始")

            # 4. list-table 内の tbody の中の a[href]
            list_table = page_soup.find("table", class_="list-table")
            if not list_table:
                continue
            for a in list_table.find_all("a", href=True):
                detail_url = "https://www.mapion.co.jp" + a["href"]

                # 5. 詳細ページにアクセスしてテーブルの td を取得
                detail_res = requests.get(detail_url, headers=headers)
                detail_soup = BeautifulSoup(detail_res.content, "html.parser")

                first_table = detail_soup.find("table")
                if not first_table:
                    continue
                tds = first_table.find_all("td")

                # 辞書に変換
                # 結果を格納する辞書
                data = {}

                # 表の中の<tr>すべてを処理
                try:
                    for row in first_table.find_all("tr"):
                        th = row.find("th")
                        td = row.find("td")
                        if th and td:
                            key = th.text.strip()
                            value = td.get_text(separator="\n", strip=True)

                            # 特別な処理：住所 → 郵便番号と住所を分ける
                            if key == "住所":
                                zip_match = re.search(r"(〒?\d{3}-\d{4})", value)
                                if zip_match:
                                    data["郵便番号"] = zip_match.group(1).replace("〒","").replace("-","")
                                    address = value.replace(zip_match.group(1), "").strip()
                                    data["住所"] = address
                                else:
                                    data["住所"] = value  # 郵便番号が見つからない場合

                            elif key == "地図":
                                # <img>タグのsrcを取得
                                a = td.find('a')
                                loc = a['href'].split("/")[2].split(",") #/m2/43.08555107,140.81536992,16/poi=G6167817-001
                                # 緯度・経度を取得
                                data["緯度"]= loc[0]
                                data["経度"]= loc[1]

                            else:
                                data[key] = value
                    
                    disclaimers = detail_soup.findAll("p", class_="disclaimer")
                    if len(disclaimers) == 0:
                        gurunabi = ""
                    else:
                        if len(disclaimers[0].find_all("a", href=True)) >= 2:
                            gurunabi = disclaimers[0].find_all("a", href=True)[1]["href"]
                        else:
                            gurunabi = ""
                    data["ぐるなび"] = gurunabi

                    # 新しい行を作成
                    wanted_keys = [
        "名称", "よみがな", "郵便番号", "住所", "電話番号","最寄り駅","最寄り駅からの距離",
        "標高", "タグ", "緯度", "経度","ぐるなび"
    ]
                    new_row = [data.get(key, "") for key in wanted_keys]

                    #print("新しい列:", new_row)
                    #print("地図:", data["地図"])
                #['やまでんファーム株式会社', 'やまでんふぁーむ', '〒046-0511', '北海道余市郡赤井川村字日ノ出２０３', '0135-34-7890', '仁木駅', '仁木駅から\n直線距離で7113m', '海抜156m', 'カフェ', '', '']



                # row = [td.get_text(strip=True) for td in tds]
                # try:
                #     # <img>タグのsrc
                #     if ("海抜" in tds[6].get_text(strip=True)):
                #         row = [
                #             tds[0].get_text(strip=True), # 店名(漢字)
                #             tds[1].get_text(strip=True),  # 店名(ひらがな)
                #             tds[2].contents[0].replace("〒","").replace("-",""),  # 郵便番号
                #             tds[2].contents[2],  # 住所
                #             lat,  # 緯度
                #             lon,  # 経度
                #             tds[4].get_text(strip=True).replace("-",""),  # 
                #             "",
                #             "",
                #             tds[6].get_text(strip=True),  # 標高
                #             tds[9].get_text(strip=True),  #タグ
                #             gurunabi # ぐるなび
                #             ]
                #     else:
                #         row = [
                #             tds[0].get_text(strip=True), # 店名(漢字)
                #             tds[1].get_text(strip=True),  # 店名(ひらがな)
                #             tds[2].contents[0].replace("〒","").replace("-",""),  # 郵便番号
                #             tds[2].contents[2],  # 住所
                #             lat,  # 緯度
                #             lon,  # 経度
                #             tds[4].get_text(strip=True).replace("-",""),  # 
                #             tds[5].get_text(strip=True),  # 駅
                #             tds[6].get_text(strip=True),  # 駅からの距離
                #             tds[8].get_text(strip=True),  # 標高
                #             tds[11].get_text(strip=True),  #タグ
                #             gurunabi # ぐるなび
                #             ]
                    csv_writer.writerow(new_row)
                    #print(new_row)
                except:
                    print(tds[0])
                    print(detail_url)
                time.sleep(0.1)  # サーバーに負荷をかけないように

output_file.close()
print("完了しました。")

#https://www.mapion.co.jp/phonebook/M01012/01409/G6167817-001/
#ギャラリー珈琲巧房やまぶき,ぎゃらりーこーひーこうぼうやまぶき,〒046-0501北海道余市郡赤井川村 赤井川289,ギャラリー珈琲巧房やまぶきの大きい地図を見る,0135-34-6787,然別駅,然別駅から直線距離で7763m,ギャラリー珈琲巧房やまぶきへのアクセス・ルート検索,海抜139m,164 278 878*64,左の二次元コードを読取機能付きのケータイやスマートフォンで読み取ると簡単にアクセスできます。URLをメールで送る場合はこちら,コーヒー
#やまでんファーム株式会社,やまでんふぁーむ,〒046-0511北海道余市郡赤井川村字日ノ出２０３,やまでんファーム株式会社の大きい地図を見る,0135-34-7890,仁木駅,仁木駅から直線距離で7113m,やまでんファーム株式会社へのアクセス・ルート検索,海抜156m,164 369 037*81,左の二次元コードを読取機能付きのケータイやスマートフォンで読み取ると簡単にアクセスできます。URLをメールで送る場合はこちら,カフェ
