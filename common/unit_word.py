#!coding=utf-8
from typing import List
import time
from pydantic import BaseModel


class WordPoolModel(BaseModel):
    id: str
    word: str
    nature: str


class UnitStat:
    flags_head = [u'་', u'།']
    flags_last = [
        u'་', u'།', u'འི་', u'འི།', u'འུ་', u'འུ།', u'འོ་', u'འོ།', u'ས་', u'ས།'
    ]
    color_num = 6

    def __init__(self, word_pool: List[WordPoolModel]):
        self.word_pool = word_pool

    def color_divide(self, vals: List[int]):
        vals.sort(reverse=True)
        _tmp_length = int(len(vals) / self.color_num)
        colouration_result = {}
        for x in range(len(vals)):
            # 是否整除不影响结果
            if x < _tmp_length:
                colouration_result[vals[x]] = 0
            elif x < 2 * _tmp_length:
                colouration_result[vals[x]] = 1
            elif x < 3 * _tmp_length:
                colouration_result[vals[x]] = 2
            elif x < 4 * _tmp_length:
                colouration_result[vals[x]] = 3
            elif x < 5 * _tmp_length:
                colouration_result[vals[x]] = 4
            else:
                colouration_result[vals[x]] = 5
        return colouration_result

    def word_extend(self, word: str) -> List:
        # 去掉末尾的 ་
        _tmp = word.split(u'་')
        _word = u'་'.join(_tmp[:-1])

        flags_head = self.flags_head
        flags_last = self.flags_last
        words = []
        if word == u'འི་':
            words.append(['', u'འི', flags_head[1]])
            words.append(['', u'འི', flags_head[0]])
        elif word == u'འི།':
            words.append(['', u'འི', flags_head[1]])
            words.append(['', u'འི', flags_head[0]])

        elif word == u'འུ་':
            words.append(['', u'འུ', flags_head[1]])
            words.append(['', u'འུ', flags_head[0]])
        elif word == u'འུ།':
            words.append(['', u'འུ', flags_head[1]])
            words.append(['', u'འུ', flags_head[0]])

        elif word == u'འོ་':
            words.append(['', u'འོ', flags_head[1]])
            words.append(['', u'འོ', flags_head[0]])
        elif word == u'འོ།':
            words.append(['', u'འོ', flags_head[1]])
            words.append(['', u'འོ', flags_head[0]])
        else:
            for _head in flags_head:
                for _last in flags_last:
                    words.append([_head, _word, _last])
        # print(words)
        return words

    def word_count(self, text: str, word: str, index: str) -> (int, str):
        count = 0
        _html = text
        # 计算单词的extend
        word_extend = self.word_extend(word)
        for _word in word_extend:
            _word_index = f"{_word[0]}{_word[1]}{_word[2]}"
            count += text.count(_word_index)  # 1/3的时间
            _word_new = f'{_word[0]}[{index}]{_word[2]}'
            _html = _html.replace(_word_index, _word_new)  # 1/3的时间
        return count, _html

    def run(self, source: str):
        source = source.replace(' ', '')
        source = source.replace(u'༌', u'་')  # 肉眼不可见，显示一样，其实不一样
        _temp = []
        tmp_list = source.splitlines()
        for _line in tmp_list:
            _temp.append(u"->་%s" % _line)

        text = '\n'.join(_temp)

        count_vals = []
        result = []

        # 遍历词库进行统计
        for _item in self.word_pool:
            # start = time.time()
            count, new_text = self.word_count(text, _item.word, _item.id)
            if count <= 0:
                continue
            result.append({'word': _item.word, 'nature': _item.nature, 'count': count, 'word_index': _item.id})
            count_vals.append(count)
            text = new_text
        # 统计结果
        # 出现的次数，用于颜色动态划分
        color = self.color_divide(list(set(count_vals)))
        for item in result:
            item['color'] = color.get(item['count'])
        print(text)
        return result, text


if __name__ == '__main__':
    import pymongo

    myclient = pymongo.MongoClient("mongodb://192.168.0.61:37017")
    mydb = myclient["tibetan"]
    db_data = mydb['word_stat_dict'].aggregate([{'$match': {'type': 'stat', 'is_exclude': False}},
                                                {'$project': {'_id': 0, 'id': 1, 'word': 1, 'nature': 1,
                                                              'length': {'$strLenCP': "$word"}}},
                                                {'$sort': {'length': -1}}
                                                ])
    word_pool = [WordPoolModel(**item) for item in db_data]
    start = time.time()
    u = UnitStat(word_pool=word_pool)
    with open('./data/0a1cf472a154d6ab9044a352329db162.txt', 'r') as f:
        source = f.read()
    u.run(source)
    print(time.time() - start)
    # resp = u.word_extend('ཀ་ཀོ་ལ་')
    # for r in resp:
    #     print(''.join(r))
    # import re
    # data = '''བཅོམ་ལྡན་འདས་ ཀྱི་ ཡེ་ཤེས་ རྒྱས་པ འི་ མདོ་སྡེ་ རིན་པོ་ཆེ་ མཐའ་ཡས་པ་ མཐ ར་ ཕྱིན་པ་ ཞེས་ བྱ་བ་ ཐེག་པ་ ཆེན་པོ འི་ མདོ །[151a][151a.1] ཞིག་ གོང་ ན་ ཞི་བ་ ཉིད་ དང་ །   གྱ་ནོམ་པ་ ཉིད་ ཡོད་ དོ་ སྙམ་ ནས་ དེ ས་ བསམས་ ཏེ་ རྟོག་པ་ མེད་པ འི་ བསམ་གཏན་ ཐོབ་ ནས་ དེ་ འདི་ སྙམ་ དུ་ གྱུར་ ཏེ །   གང་ རྟོག་པ་ དང་ དཔྱོད་པ་ དག་ མི་ འབྱུང་བ་ འདི་ ནི །   མྱ་ངན་ ལ ས་ འདས་པ་ ཡིན་ ཏེ །   འདི་ ནི་ ཞི་བ འོ །   ། འདི་ ནི་ གྱ་ནོམ་པ འོ །   ། གང་ རྟོག་པ་ དང་ དཔྱོད་ [151a.2] པ་ དག་ མེད་པ་ དེ་ཡང་ དང་ ཡང་ དུ་ སྐྱེ་བ ར་ མི་ འཇུག་ ལ་ཉེ་ བར་ ལེན་པ་ ཅུང་ཟད་ ཀྱང་ མེད་ དེ་ འདི་ ནི་ ཕུང་པོ་ ལྷག་མ་ མེད་པ འི་ དབྱིངས་ སུ་ མྱ་ངན་ ལ ས་ འད འོ་ སྙམ་ ནས་ དེ་ ཏིང་ངེ་འཛིན་ དེ་ལས་ ལངས་ ནས །   སྲོག་ཆགས་ འབུམ་ཕྲག་ དྲུག་ བཟོད་པ་ འདི་ ལ་ བཙུད་ དོ །   ། དེ་དག་ ཀྱང་ འདི་ སྙམ་ དུ་ གྱུར་ ཏེ །   རྟོག་པ་ དང་ [151a.3] དཔྱོད་པ་ འདི་དག་ སྤངས་ ན་ དེ འི་ སྐྱེ་བ་ མི་ འཇུག་ སྟེ་ དེ་ཡང་ དང་ ཡང་ དུ་ སྐྱེ་བ་ མི་ འཇུག་པ་ འདི་ ནི་ མྱ་ངན་ ལ ས་ འདའ་བ་ ཐོབ་བོ་ སྙམ་ མོ །   ། དེ་ལྟར་ བཟོད་པ་ དང་ སྣང་བ་ ལ་ དགའ་བ་ དེ་དག་ ལ་ འོད་གསལ་ གྱི་ གཞལ་མེད་ ཁང་ དག་ བྱུང་བ ར་ གྱུར་ ཏོ །   ། དེ་ལྟར་ གཞལ་མེད་ ཁང་ དེ་དག་ མཐོང་ ནས་ འདི་ སྙམ་ [151a.4] དུ་ གྱུར་ ཏེ །  '''
    # print(re.sub(r"།(\s*)།", r"།།\r\n", data))
