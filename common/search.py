from elasticsearch import Elasticsearch
from config import ES_NAME, ES_PASSWD, ES_PORT, ES_URL

#
# es = Elasticsearch(['es-cn-0pp0wdtno00026tz5.elasticsearch.aliyuncs.com'], http_auth=('elastic', 'N+8atre&lt'),
#                    port=9200)
es = Elasticsearch([ES_URL], port=ES_PORT)


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
