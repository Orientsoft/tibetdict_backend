from elasticsearch import Elasticsearch
from config import ES_NAME, ES_PASSWD, ES_PORT, ES_URL

#
# es = Elasticsearch(['es-cn-0pp0wdtno00026tz5.elasticsearch.aliyuncs.com'], http_auth=('elastic', 'N+8atre&lt'),
#                    port=9200)
es = Elasticsearch([ES_URL], http_auth=(ES_NAME, ES_PASSWD), port=ES_PORT)


def query_es(keyword: str, num: int = 10):
    query = {
        "query": {
            "match_phrase": {
                "attachment.content": keyword
            }
        },
        "highlight": {
            "fields": {
                "attachment.content": {}
            }
        }
    }
    result = es.search(index="tibetan-corpus-docx", body=query, size=num)
    return result


def bulk(index: str, body: list):
    es.indices.create(index=index, ignore=400)
    result = es.bulk(body=body, request_timeout=60)
    return result
