from elasticsearch import Elasticsearch
from config import ES_NAME, ES_PASSWD, ES_PORT, ES_URL

es = Elasticsearch([ES_URL], http_auth=(ES_NAME, ES_PASSWD), port=ES_PORT)


def query_es(index: str, keyword: str, start: int = 0, size: int = 10):
    query = {
        "from": start,
        "size": size,
        "sort": [{"createdAt": "desc"}],
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
    result = es.search(index=index, body=query)
    return result


def bulk(index: str, body: list):
    es.indices.create(index=index, ignore=400)
    result = es.bulk(body=body, request_timeout=60)
    return result
'''
curl -XPUT "192.168.0.20:9201/tibetan-content/_settings" -H 'Content-Type: application/json' -d' {
    "index" : {
        "highlight.max_analyzed_offset" : 600000000
    }
}
'
'''