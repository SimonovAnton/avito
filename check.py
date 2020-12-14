import aiohttp
import asyncio
from datetime import datetime
from aiohttp import ClientResponse
from db import *


#   Creating a URL for the Avito GET request. Arguments - query:str, search region:int.
def create_message(query: str, region_id: int) -> str:
    message = 'https://m.avito.ru/api/9/items?key=af0deccbgcgidddjgnvljitntccdduijhdinfgjgfjir&'
    message += 'locationId={0}&query={1}'.format(region_id, query)
    return message


#   Sends GET requests to Avito. Returns responses in json format.
async def get_to_avito(message_avito: str) -> ClientResponse.json:
    async with aiohttp.ClientSession() as session:
        async with session.get(message_avito) as response:
            return await response.json()


#   Returns a list of unique query + region_id pairs from the requests table.
def select_items(con: connection) -> list:
    cursor = con.cursor()
    message = '''SELECT ID, QUERY, REGION_ID FROM requests ;'''
    cursor.execute(message)
    con.commit()
    items = []
    for row in cursor:
        item = [row[0], row[1], row[2]]
        items.append(item)
    cursor.close()
    return items


#   For each request, it adds a new row to the items_count table with a timestamp and the count of ads on Avito.
async def update(request_id: int, query: str, region_id: int, con: connection) -> None:
    response = await get_to_avito(create_message(query, region_id))
    count = response['result']['mainCount']
    time_now = datetime.utcnow()
    cursor = con.cursor()
    message = '''INSERT INTO items_count (TIME, COUNT, REQUEST_ID) 
                VALUES ('{0}', {1}, {2})
                ON CONFLICT DO NOTHING;'''.format(time_now.strftime('%Y.%m.%d %H:%M:%S.%f'), count, request_id)
    cursor.execute(message)
    con.commit()
    cursor.close()
    return None


#   Run awaitable objects (adding the current count of ads) in the sequence concurrently.
async def go_around(con: connection) -> None:
    items = [update(request_id, query, region_id, con) for request_id, query, region_id in select_items(con)]
    await (asyncio.gather(*items))
    await asyncio.sleep(0.1)
    return None


#   Run the program.
def main(con: connection) -> None:
    asyncio.run(go_around(con))
    pass


if __name__ == '__main__':
    create_db()
    create_items_count()
    con = db_connection()
    main(con)
