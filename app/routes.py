from app import app
from flask import  render_template, request, redirect, url_for
from bs4 import BeautifulSoup
import pandas as pd
import numpy
import requests
import json
import os
from app import utils

@app.route('/')
def index():
    return render_template("index.html.jinja")

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

                    opinions = pd.from_dict(all_opinions)

                    if not os.path.exists('app/data/stats'):
                        os.mkdir('app/data/stats')

                    with open(f'app/data/stats/{product_id}.json', 'w', encoding='UTF-8') as jsonfile:
                        
                        json.dump(stats, jsonfile, indent=4, ensure_ascii=False)


                return redirect(url_for('product', product_id=product_id))
        
            error = "Produkt istnieje, ale  nie ma opinii"
            return render_template('extract.html.jinja', error=error)
    
    error = 'Blędny kod produktu, bądź produkt nie istnieje'
    return render_template("extract.html.jinja")

@app.route('/products')
def products():
    products = [filename.split(".")[0] for filename in os.listdir('app/data/opinions')]
    return render_template("products.html.jinja", products = products)

@app.route('/author')
def author():
    return render_template("author.html.jinja")


@app.route('/product/<product_id>')
def product(product_id):
    return render_template('product.html.jinja', product_id = product_id)