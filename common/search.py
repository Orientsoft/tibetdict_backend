from elasticsearch import Elasticsearch
from config import ES_NAME, ES_PASSWD, ES_PORT, ES_URL

es = Elasticsearch([ES_URL], http_auth=(ES_NAME, ES_PASSWD), port=ES_PORT)


def query_es(index: str, queryObj: dict, start: int = 0, size: int = 10):
    query = {
        "from": start,
        "size": size,
        "sort": [{"createdAt": "desc"}],
        "query": queryObj,
        # "highlight": {
        #     "boundary_max_scan": 40,
        #     "fields": {
        #         "content": {"force_source": True, "type": "plain", "fragment_size": 150, "number_of_fragments": 5}
        #     }
        # },
        # "_source": ["highlight", "id"],

    }
    result = es.search(index=index, body=query)
    return result


def get_one_file_content_from_es(index: str, file_id: str, size: int):
    query = {
        "size": size,
        "sort": [{"seq": "asc"}],
        "query": {"bool": {
            "must": [
                {"term": {"id": file_id}},
            ]
        }},
    }
    result = es.search(index=index, body=query)
    return result


def bulk(index: str, body: list):
    es.indices.create(index=index, ignore=400)
    result = es.bulk(body=body, request_timeout=60)
    return result


def delete_es_by_fileid(index, id):
    query = {"query": {"term": {"id": id}}}
    res = es.delete_by_query(index=index, body=query)
    print(res)


'''
curl -XPUT "192.168.0.20:9201/tibetan-content/_settings" -H 'Content-Type: application/json' -d' {
    "index" : {
        "highlight.max_analyzed_offset" : 600000000
    }
}
'

DELETE tibetan-content-dev

PUT tibetan-content-dev/_settings
{
    "index" : {
        "highlight.max_analyzed_offset" : 600000000
    }
}
'''

if __name__ == '__main__':
    import time

    Obj = {
        "bool": {
            "must": [
                {"match_phrase": {"content": 'གྱ་ནོམ་པ'}},
                {"term": {"user_id": 'b95d552e5add11ebb13ca0a4c56447ad'}},
            ]
        }
    }
    # print(query_es('tibetan-content-dev', Obj))
    start = time.time()
    # print(query_es_file_content('tibetan-content-dev', 'གྱ་ནོམ་པ', '6146f1047c8f11eb97b2080027ce4314'))
    # print(time.time() - start)
    # delete_es_by_fileid('tibetan-content-dev','f8e9d6867d5f11ebbe5d080027ce4314')
    print(get_one_file_content_from_es('tibetan-content', '422a6210863a11ebba21cef0e539f272',5))
