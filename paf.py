import time
from util import config_log_format, print_log, read_config
from DrissionPage import ChromiumPage, ChromiumOptions
import random
from txapi import detect_face
from loguru import logger


@logger.catch
def like_video():
    follow_eles = page.eles('tag=div@data-e2e=feed-follow-icon')
    for follow_ele in follow_eles:
        if follow_ele.states.is_in_viewport:
            follow_ele.click()
            page.wait(1)

    digg_eles = page.eles('tag=div@data-e2e=video-player-digg')
    for digg_ele in digg_eles:
        if digg_ele.states.is_in_viewport:
            digged_state = digg_ele.attr('data-e2e-state')
            if digged_state == 'video-player-no-digged':
                digg_ele.click()
                page.wait(1)

    feed_eles = page.eles('tag=div@data-e2e=feed-comment-icon')
    for feed_ele in feed_eles:
        if feed_ele.states.is_in_viewport:
            feed_ele.click()
            page.wait(1)

    input_main_eles = page.eles('tag=div@class:comment-input-inner-container')
    for input_main_ele in input_main_eles:
        if input_main_ele.states.is_in_viewport:
            input_main_ele.click()
            page.wait(1)
            input_ele = input_main_ele.ele('tag=div@class=DraftEditor-editorContainer')
            input_ele.input(comment)
            page.wait(1)

            submit_ele = input_main_ele.child(2).child(1).child(3)
            submit_ele.click()
            page.wait(1)

    close_ele0s = page.eles('tag=div@id=relatedVideoCard')
    for close_ele0 in close_ele0s:
        if close_ele0.states.is_in_viewport:
            close_ele1 = close_ele0.child(1).child(1).child(2)
            close_ele1.click()
            page.wait(1)


@logger.catch
def next_video():
    page.ele('tag=div@class=xgplayer-playswitch-next').click()
    page.wait(1)
    living_eles = page.eles('tag=span@text()=直播中', timeout=1)
    for living_ele in living_eles:
        if living_ele.states.is_in_viewport:
            print_log(f'直播，跳过~')
            return False

    ad_eles = page.eles('tag=span@text()=广告', timeout=1)
    for ad_ele in ad_eles:
        if ad_ele.states.is_in_viewport:
            print_log('广告，跳过~')
            return False

    follow_eles = page.eles('tag=div@data-e2e=feed-follow-icon')
    for follow_ele in follow_eles:
        if follow_ele.states.is_in_viewport:
            f_a_dict = follow_ele.child('tag=div').child('tag=div').attrs
            if 'hidden' in f_a_dict:
                print_log('关注过了，跳过~')
                return False

    account_name_eles = page.eles('tag=div@class=account-name')
    for account_name_ele in account_name_eles:
        if account_name_ele.states.is_in_viewport:
            print_log(f'正在播放 {account_name_ele.text} 的视频')
            page.wait(1)

            if len(SecretId) == 0 or len(SecretKey) == 0:
                print_log('未配置腾讯云的 SecretId 和 SecretKey，直接点赞评论')
                like_video()
                page.wait(2)
                return True

            b64 = page.get_screenshot(path='screenshots', name=f'{int(time.time())}.jpg', as_base64=True)
            res = detect_face(b64, SecretId, SecretKey)
            if res[0]:
                if res[1] == 1:
                    if res[2] >= beauty:
                        if age_low <= res[3] <= age_high:
                            print_log(f'性别：女, 颜值：{res[2]}, 年龄：{res[3]}，活捉一个小姐姐，点赞关注留言走一波~')
                            like_video()
                            page.wait(2)
                        else:
                            print_log(f'年龄：{res[3]}，不在年龄要求范围内，跳过~')
                    else:
                        print_log(f'颜值：{res[2]}，低于颜值要求，跳过~')
                else:
                    print_log(f'是个爷们儿，跳过~')
            else:
                print_log(f'人脸识别失败：{[res[1]]}')

    return True


if __name__ == '__main__':

    config_log_format('log')
    beauty, age_low, age_high, comment, SecretId, SecretKey = read_config()
    print_log('脚本开始~')
    print_log(f'颜值要求：{beauty}')
    print_log(f'年龄要求：{age_low}-{age_high}')

    co = ChromiumOptions(read_file=False)
    co.use_system_user_path()
    co.set_local_port(9222)
    co.set_timeouts(30, 30, 30)
    page = ChromiumPage(addr_or_opts=co)

    page.get('https://www.douyin.com/')
    page.wait(3)

    while True:
        r = next_video()
        if not r:
            page.wait(random.randint(5, 10))
