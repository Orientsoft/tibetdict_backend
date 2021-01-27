from fastapi import HTTPException
from starlette.status import HTTP_400_BAD_REQUEST
from config import database_name, word_stat_dict_collection_name, work_history_collection_name
from collections import Counter
from common.upload import MinioUploadPrivate
from loguru import logger
import traceback


# import time


class WordCount:
    def __init__(self, conn, word_type: str = 'stat', color_total: int = 6):
        self.content = None
        self.conn = conn
        self.word_type = word_type
        self.word_stat_in_content = None
        self.color_total = color_total
        # self.time = time.time()

    async def get_content(self, _id):
        # start_time = time.time()
        result = await self.conn[database_name][work_history_collection_name].find_one({'id': _id})
        self.content = MinioUploadPrivate().get_object(full_path=result['parsed']).decode(encoding='utf-8')
        # logger.info('get_content used: %s' % str(start_time - self.time))

    def split_and_count_file_content(self, split: str = ' '):
        '''
        文档内容已经以空格进行过分词，所以根据空格分隔content为list，并轮询进行计数
        :return: 组装成一个字符为key，该字符计数为value的字典
        '''
        # start_time = time.time()
        logger.info(self.content)
        content_list = self.content.split(split)
        # Counter的结果类型继承dict的属性
        self.word_stat_in_content = Counter(content_list)
        # 若content为空字符串，报"后台异常"
        if not self.word_stat_in_content:
            raise HTTPException(status_code=HTTP_400_BAD_REQUEST, detail='40010')
        # logger.info('split_and_count_file_content used: %s' % str(start_time - self.time))
        return self.word_stat_in_content

    def colouration(self, word_stat_in_content):
        '''
        动态染色，无具体色号，共6种，以int类型标注
        :return: 频率为key，颜色编号为value的字典
        '''
        if not word_stat_in_content:
            logger.info(
                'function "colouration" in class "WordCount" do not find self.word_stat_\
                in_content and run function "split_and_count_file_content"')
            self.split_and_count_file_content()
        colouration_result = {}
        # start_time = time.time()
        # 得到每种频率
        frequency = list(set(word_stat_in_content.values()))
        logger.info(len(frequency))
        frequency.sort(reverse=True)
        step = len(frequency) / self.color_total
        for x in range(len(frequency)):
            # 是否整除不影响结果
            if x < step:
                colouration_result[frequency[x]] = 0
            elif x < 2 * step:
                colouration_result[frequency[x]] = 1
            elif x < 3 * step:
                colouration_result[frequency[x]] = 2
            elif x < 4 * step:
                colouration_result[frequency[x]] = 3
            elif x < 5 * step:
                colouration_result[frequency[x]] = 4
            else:
                colouration_result[frequency[x]] = 5
        # logger.info('colouration used: %s' % str(start_time - self.time))
        return colouration_result

    async def word_count(self, _id):
        '''
        根据文档已经统计出的词进行查询，得到List[BaseModel]，遍历该列表
        :return: [{'word': str, 'nature': str, 'count': int, 'color': str, 'word_index': str}]
        '''
        try:
            if not self.content:
                logger.info('run "get_content"')
                await self.get_content(_id=_id)
            if not self.word_stat_in_content:
                logger.info(
                    'function "word_count" in class "WordCount" do not find self.word_stat_in_content \
                    and run function "split_and_count_file_content"')
                self.split_and_count_file_content()
            colouration_result = self.colouration(word_stat_in_content=self.word_stat_in_content)
            # start_time = time.time()
            query = {
                'word': {'$in': list(self.word_stat_in_content.keys())},
                'type': self.word_type
            }
            # 此时查出来的的list都是有效数据
            result = self.conn[database_name][word_stat_dict_collection_name].find(query)
            data_word_stat_dict = [x async for x in result]
            result = []
            for x in data_word_stat_dict:
                result.append({
                    'word': x['word'],
                    'nature': x['nature'],
                    'count': self.word_stat_in_content[x['word']],
                    'color': colouration_result[self.word_stat_in_content[x['word']]],
                })
            # logger.info('word_count used: %s' % str(start_time - self.time))
            result.sort(key=lambda x: x['count'], reverse=True)
            return result
        except Exception as e:
            traceback.print_exc()
            logger.error(e)
            return None
