from elasticsearch import Elasticsearch
from config import ES_NAME, ES_PASSWD, ES_PORT, ES_URL

es = Elasticsearch([ES_URL], http_auth=(ES_NAME, ES_PASSWD), port=ES_PORT)


def query_es(index: str, keyword: str, num: int = 10):
    query = {
        "query": {
            "match_phrase": {
                "content": keyword
            }
        },
        "highlight": {
            "fields": {
                "content": {}
            }
        },
        "_source": ["highlight", "id"],
    }
    result = es.search(index=index, body=query, size=num, timeout=60)
    return result


def bulk(index: str, body: list):
    es.indices.create(index=index, ignore=400)
    result = es.bulk(body=body, request_timeout=60)
    return result
