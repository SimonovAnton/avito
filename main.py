from flask import Flask, render_template, request, json
from check import create_message
from datetime import datetime
from db import *
import requests

app = Flask(__name__)


#   GET request for Avito. Returns the count of ads for the given request. Argument - URL:str.
def get_count(message_avito: str) -> int:
    request_avito = requests.get(message_avito)
    count = request_avito.json()['result']['mainCount']
    return count


#   Makes a list of the first 5 ads on request (excludes VIP ads).
#   Returns None if there are less than 5 ads on request.
#   Argument - URL:str.
def get_top5(message_avito: str) -> list:
    request_avito = requests.get(message_avito)
    response = request_avito.json()

    top5 = [None for _ in range(5)]
    i = 0
    k = i

    while i < len(top5):
        try:
            if response['result']['items'][k]['type'] != 'vip':
                link = 'https://avito.ru' + response['result']['items'][k]['value']['uri_mweb']
                top5[i] = link
                i += 1
                k += 1
            else:
                k += 1
        except IndexError:
            break
        except KeyError:
            k += 1

    return top5


#   Server start page.Returns template.
@app.route('/')
def index():
    return render_template('start_page.html')


#   By using POST method accepts json containing query and region_id. Creates a row with the received data in the
#   requests table. Passes the count of ads currently in the items_count table. Returns json with the ID (request_id)
#   assigned to the current query + region_id pair.
@app.route('/add', methods=['POST'])
def add() -> json:
    try:
        data_add = request.data
        query = json.loads(data_add)['query']
        region_id = int(json.loads(data_add)['region_id'])

        message_avito = create_message(query, region_id)
        count = get_count(message_avito)

        cursor = con.cursor()

        try:
            cursor.execute(
                'INSERT INTO requests (QUERY, REGION_ID) VALUES (%(query)s, %(region_id)s) ON CONFLICT DO NOTHING;',
                {'query': query, 'region_id': region_id}
            )
        except Exception as e:
            con.rollback()
            response = app.response_class(
                response=json.dumps({'error': str(e)}),
                status=400,
                mimetype='application/json'
            )
            return response
        con.commit()

        try:
            cursor.execute(
                'SELECT ID FROM requests WHERE QUERY=%(query)s AND REGION_ID=%(region_id)s;',
                {'query': query, 'region_id': region_id}
            )
        except Exception as e:
            con.rollback()
            response = app.response_class(
                response=json.dumps({'error': str(e)}),
                status=400,
                mimetype='application/json'
            )
            return response

        request_id = int(cursor.fetchone()[0])

        time_now = datetime.utcnow()
        try:
            cursor.execute(
                '''INSERT INTO items_count (TIME, COUNT, REQUEST_ID) VALUES (%(time)s, %(count)s, %(region_id)s) 
                ON CONFLICT DO NOTHING;''',
                {'time': time_now.strftime('%Y.%m.%d %H:%M:%S'), 'count': count, 'region_id': request_id}
            )
        except Exception as e:
            con.rollback()
            response = app.response_class(
                response=json.dumps({'error': str(e)}),
                status=400,
                mimetype='application/json'
            )
            return response

        cursor.close()
        con.commit()

        answer = {'id': request_id}
        response = app.response_class(
            response=json.dumps(answer),
            status=200,
            mimetype='application/json'
        )
        return response

    except Exception as e:
        response = app.response_class(
            response=json.dumps({'error': str(e)}),
            status=400,
            mimetype='application/json'
        )
        return response


#   Using the POST method, accepts a json containing a query_id and a time range to display the count of ads.
#   Returns json with the timestamps and corresponding counts.
@app.route('/stat', methods=['POST'])
def stat() -> json:
    try:
        data_stat = request.data
        request_id = int(json.loads(data_stat)['request_id'])
        timestamp_fst = json.loads(data_stat)['timestamp_fst']
        timestamp_snd = json.loads(data_stat)['timestamp_snd']
        cursor = con.cursor()
        try:
            cursor.execute(
                '''SELECT TIME, COUNT FROM items_count WHERE REQUEST_ID=%(request_id)s AND 
                (TIME BETWEEN %(time_1)s AND %(time_2)s);''',
                {'request_id': request_id, 'time_1': timestamp_fst, 'time_2': timestamp_snd}
            )
        except Exception as e:
            con.rollback()
            response = app.response_class(
                response=json.dumps({'error': str(e)}),
                status=400,
                mimetype='application/json'
            )
            return response

        answer = {}
        for row in cursor:
            answer[str(row[0])] = row[1]
        cursor.close()
        con.commit()

        response = app.response_class(
            response=json.dumps(answer),
            status=200,
            mimetype='application/json'
        )
        return response

    except Exception as e:
        response = app.response_class(
            response=json.dumps({'error': str(e)}),
            status=400,
            mimetype='application/json'
        )
        return response


#   Using the POST method, accepts a json containing a query_id. Returns json with links to top 5 ads for current
#   query_id.  If count of ads less than 5, returns None for empty positions.
@app.route('/top', methods=['POST'])
def top() -> json:
    try:
        data_stat = request.data
        request_id = int(json.loads(data_stat)['request_id'])
        cursor = con.cursor()
        try:
            cursor.execute(
                'SELECT QUERY, REGION_ID FROM requests WHERE ID=%(request_id)s;',
                {'request_id': request_id}
            )
        except Exception as e:
            con.rollback()
            response = app.response_class(
                response=json.dumps({'error': str(e)}),
                status=400,
                mimetype='application/json'
            )
            return response

        query = ''
        region_id = 0

        for row in cursor:
            query = row[0]
            region_id = row[1]

        if (query == '') or (region_id == 0):
            response = app.response_class(
                response=json.dumps({'error': 'Bad request'}),
                status=400,
                mimetype='application/json'
            )
            return response

        con.commit()
        cursor.close()

        message_avito = create_message(query, region_id)
        top5 = get_top5(message_avito)

        answer = {}
        for _ in range(len(top5)):
            answer[str(_ + 1)] = top5[_]

        response = app.response_class(
            response=json.dumps(answer),
            status=200,
            mimetype='application/json'
        )
        return response

    except Exception as e:
        response = app.response_class(
            response=json.dumps({'error': str(e)}),
            status=400,
            mimetype='application/json'
        )
        return response


if __name__ == '__main__':
    try:
        create_db()
        con = db_connection()
        app.run(debug=True, host='0.0.0.0')
        db_disconnection(con)
    except Exception as e:
        print('Error while creating PostgreSQL table', e)
