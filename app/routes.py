#import

from app import app
from flask import  render_template, request, redirect, url_for, send_file
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
import requests
import json
import os
import io
from app import utils


#routes


#index
@app.route('/')
def index():
    return render_template("index.html.jinja")


#extract
@app.route('/extract', methods=['POST', "GET"])
def extract():
    if request.method == 'POST':
        product_id = request.form.get('product_id')

        url = f'https://www.ceneo.pl/{product_id}'
        response = requests.get(url)

        if response.status_code == requests.codes['ok']:

            page_dom = BeautifulSoup(response.text, 'html.parser')
            opinions_count = utils.extract(page_dom, '.product-review__link > span')

            if opinions_count:

                product_name = utils.extract(page_dom, 'h1')
                url          = f'https://www.ceneo.pl/{product_id}/opinie-1'
                all_opinions = []

                while (url):

                    response    = requests.get(url)
                    page_dom    = BeautifulSoup(response.text, 'html.parser')
                    opinions    = page_dom.select('div.js_product-review')

                    for opinion in opinions:
                            single_opinion = {

                                key : utils.extract(opinion, *value)
                                    for key, value in utils.selectors.items()

                            }
                            
                            all_opinions.append(single_opinion) 

                    try:
                        url = 'https://www.ceneo.pl/'+utils.extract(page_dom, 'a.pagination__next', 'href')
                    except TypeError:
                        url = None

                    if not os.path.exists('app/data'):
                        os.mkdir('app/data')

                    if not os.path.exists('app/data/opinions'):
                        os.mkdir('app/data/opinions')

                    with open(f'app/data/opinions/{product_id}.json', 'w', encoding='UTF-8') as jsonfile:
                        
                        json.dump(all_opinions, jsonfile, indent=4, ensure_ascii=False)

                    opinions = pd.DataFrame.from_dict(all_opinions)

                    opinions.rating = opinions.rating.apply(lambda r: r.split("/")[0].replace(",", "."), ).astype(float)
                    opinions.recommendation = opinions.recommendation.apply(lambda r: "Brak" if r is None else r)

                    stats = {
                        "product_id"            : product_id,
                        "product_name"          : product_name,
                        "opinions_count"        : opinions.shape[0],
                        "pros_count"            : int(opinions.pros.apply(lambda p: 1 if p else 0).sum()),
                        "cons_count"            : int(opinions.cons.apply(lambda c: 1 if c else 0).sum()),
                        "avg_rating"            : opinions.rating.mean(),
                        "rating_distribution"   : opinions.rating.value_counts().reindex(np.arange(0, 5.5, 0.5), fill_value=0).to_dict(),
                        "recommendation_distrb" : opinions.recommendation.value_counts().reindex(["Polecam", "Nie polecam", "Brak"], fill_value=0).to_dict()
                    }

                    if not os.path.exists("app/data/stats"):
                        os.mkdir("app/data/stats")

                    with open(f"app/data/stats/{product_id}.json", "w", encoding="UTF-8") as jfile:
                        json.dump(stats, jfile, indent=6, ensure_ascii=False)

                return redirect(url_for('product', product_id=product_id))
        
            error = "Produkt istnieje, ale  nie ma opinii"
            return render_template('extract.html.jinja', error=error)
    
    error = 'Błędny kod produktu, bądź produkt nie istnieje'
    return render_template("extract.html.jinja")


#products
@app.route('/products')
def products():

    products_list = [filename.split(".")[0] for filename in os.listdir('app/data/opinions')]
    products      = []

    for product_id in products_list:

        with open(f"app/data/stats/{product_id}.json", "r", encoding="UTF-8") as jfile:
            products.append(json.load(jfile))

    return render_template("products.html.jinja", products = products)


#author
@app.route('/author')
def author():
    return render_template("author.html.jinja")


#product
@app.route('/product/<product_id>')
def product(product_id):

    opinions_list    = [filename.split(".")[0] for filename in os.listdir('app/data/opinions')]
    product_opinions = []

    for i in opinions_list: 
        if i == product_id: 

            with open(f"app/data/opinions/{product_id}.json", "r", encoding="UTF-8") as jfile:
                product_opinions.append(json.load(jfile))

    return render_template('product.html.jinja', product_id = product_id, product_opinions = product_opinions[0])


#wykresy
@app.route('/product/chart/<product_id>')
def chart(product_id):

    opinions_list    = [filename.split(".")[0] for filename in os.listdir('app/data/opinions')]
    product_opinions = []

    for i in opinions_list: 
        if i == product_id: 

            with open(f"app/data/opinions/{product_id}.json", "r", encoding="UTF-8") as jfile:
                product_opinions.append(json.load(jfile))

    recomms_good = 0
    recomms_bad = 0
    rating_1 = 0
    rating_2 = 0
    rating_3 = 0
    rating_4 = 0
    rating_5 = 0

    for l in product_opinions[0]:
        
        for key, value in l.items():
            if key == "recommendation":
                if value == "Polecam":
                    recomms_good += 1
                else:
                    recomms_bad += 1
            if key == "rating":
                if int(value[0]) == 5:
                    rating_5 += 1
                if int(value[0]) == 4:
                    rating_4 += 1
                if int(value[0]) == 3:
                    rating_3 += 1
                if int(value[0]) == 2:
                    rating_2 += 1
                if int(value[0]) == 1:
                    rating_1 += 1



    return render_template("chart.html.jinja", product_id = product_id, product_opinions=product_opinions[0], recomms_bad=recomms_bad, recomms_good=recomms_good, rating_1=rating_1, rating_2=rating_2, rating_3=rating_3, rating_4=rating_4, rating_5=rating_5)


#download json
@app.route('/product/download_json/<product_id>')
def download_json(product_id):
    
    return send_file(f'data/opinions/{product_id}.json', 'text/json', as_attachment=True)

#download csv
@app.route('/product/download_csv/<product_id>')
def download_csv(product_id):

    opinions = pd.read_json(f'app/data/opinions/{product_id}.json')
    buffer   = io.BytesIO(opinions.to_csv(sep = ';', decimal = ',', index = False).encode())

    return send_file(buffer, 'text/csv', as_attachment=True, download_name=f"{product_id}.csv")

#download xlsx
@app.route('/product/download_xlsx/<product_id>')
def download_xlsx(product_id):
    pass