#!/usr/bin/python
# -*- coding:utf-8 -*-


def colouration(word_stat_in_content, num: int = 6):
    '''
    动态染色，无具体色号，共6种，以int类型标注
    :return: 频率为key，颜色编号为value的字典
    '''
    colouration_result = {}
    # start_time = time.time()
    # 得到每种频率
    frequency = list(set(word_stat_in_content.values()))
    frequency.sort(reverse=True)
    step = len(frequency) / num
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
