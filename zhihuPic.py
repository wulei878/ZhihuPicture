# -*-coding:utf-8 -*-

import requests

try:
    import cookielib
except:
    import http.cookiejar as cookielib
import re
import time
import os.path

try:
    from PIL import Image
except:
    pass

import multiprocessing
import socket
import sys

agent = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_3) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36'
headers = {
    "Host": "www.zhihu.com",
    "Referer": "https://www.zhihu.com/",
    'User-Agent': agent
}

# 使用登录cookie信息
session = requests.session()
session.cookies = cookielib.LWPCookieJar(filename='cookies')
try:
    session.cookies.load(ignore_discard=True)
except:
    print("Cookie 未能加载")


def get_xsrf():
    '''_xsrf 是一个动态变化的参数'''
    index_url = 'https://www.zhihu.com'
    # 获取登录时需要用到的_xsrf
    index_page = session.get(index_url, headers=headers)
    html = index_page.text
    pattern = r'name="_xsrf" value="(.*?)"'
    # 这里的_xsrf 返回的是一个list
    _xsrf = re.findall(pattern, html)
    return _xsrf[0]


# 获取验证码
def get_captcha():
    t = str(int(time.time() * 1000))
    captcha_url = 'https://www.zhihu.com/captcha.gif?r=' + t + "&type=login"
    print (captcha_url)
    r = session.get(captcha_url, headers=headers)
    with open('captcha.jpg', 'wb') as f:
        f.write(r.content)
        f.close()
    # 用pillow 的 Image 显示验证码
    # 如果没有安装 pillow 到源代码所在的目录去找到验证码然后手动输入
    try:
        im = Image.open('captcha.jpg')
        im.show()
        im.close()
    except:
        print(u'请到 %s 目录找到captcha.jpg 手动输入' % os.path.abspath('captcha.jpg'))
    captcha = input("please input the captcha\n>")
    return captcha


def isLogin():
    # 通过查看用户个人信息来判断是否已经登录
    url = "https://www.zhihu.com/settings/profile"
    login_code = session.get(url, headers=headers, allow_redirects=False).status_code
    if login_code == 200:
        return True
    else:
        return False


def login(secret, account):
    # 通过输入的用户名判断是否是手机号
    if re.match(r"^1\d{10}$", account):
        print("手机号登录 \n")
        post_url = 'https://www.zhihu.com/login/phone_num'
        postdata = {
            '_xsrf': get_xsrf(),
            'password': secret,
            'remember_me': 'true',
            'phone_num': account,
        }
    else:
        if "@" in account:
            print("邮箱登录 \n")
        else:
            print("你的账号输入有问题，请重新登录")
            return 0
        post_url = 'https://www.zhihu.com/login/email'
        postdata = {
            '_xsrf': get_xsrf(),
            'password': secret,
            'remember_me': 'true',
            'email': account,
        }
        # try:
        #     # 不需要验证码直接登录成功
        #     login_page = session.post(post_url, data=postdata, headers=headers)
        #     login_code = login_page.text
        #     print(login_page.status_code)
        #     print(login_code)
        # except:
        # 需要输入验证码后才能登录成功
    postdata["captcha"] = get_captcha()
    login_page = session.post(post_url, data=postdata, headers=headers)
    login_code = eval(login_page.text)
    print(login_code['msg'])
    session.cookies.save()


try:
    input = raw_input
except:
    pass


def getImageUrl(questionID):
    url = "https://www.zhihu.com/node/QuestionAnswerListV2"
    method = 'next'
    size = 10
    allImageUrl = []

    # 循环直至爬完整个问题的回答
    while (True):
        print ("===========offset: ", size)
        postdata = {
            'method': 'next',
            'params': '{"url_token":' + str(questionID) + ',"pagesize": "10",' + \
                      '"offset":' + str(size) + "}",
            '_xsrf': get_xsrf(),

        }
        size += 10
        page = session.post(url, headers=headers, data=postdata)
        ret = eval(page.text)
        listMsg = ret['msg']
        if not listMsg or size > 300:
            print ("图片URL获取完毕, 页数: ", (size - 10) / 10)
            return allImageUrl
        pattern = re.compile('data-original="(.*?)">', re.S)
        for pageUrl in listMsg:
            items = re.findall(pattern, pageUrl)
            for item in items:  # 这里去掉得到的图片URL中的转义字符'\\'
                imageUrl = item.replace("\\", "")
                allImageUrl.append(imageUrl)


def saveImagesFromUrl(filePath, questionID):
    imagesUrl = getImageUrl(questionID)
    print ("图片数: ", len(imagesUrl))
    p = multiprocessing.Pool(40)
    path = filePath + '/' + str(questionID)
    if not os.path.exists(path):
        os.makedirs(path)
    for item in imagesUrl:
        filenames = item.split('/')
        filename = filenames[len(filenames) - 1]
        p.apply_async(save_pic, args=(item, path + '/' + filename))
    p.close()
    p.join()


def save_pic(pic_url, filename):
    count = 0
    while True:
        try:
            print ('picture ', filename, ' begin...')
            ir = requests.get(pic_url, stream=True, timeout=30)
            if ir.status_code == 200:
                with open(filename, 'wb') as f:
                    for chunk in ir:
                        f.write(chunk)
        except socket.timeout:
            print ('timeout: ', filename, 'count: ', count)
            count += 1
        except Exception as e:
            print (filename, 'other fault: ', e)
            count += 1
        else:
            print ('picture ', filename, ' save successfully! it has tried to download', count, ' times')
            break


def checkLogin():
    if isLogin():
        print('您已经登录')
        ids = questionIDs.split(' ')
        print (ids)
        for id in ids:
            print (id)
            saveImagesFromUrl('Picture', id)
    else:
        account = input('请输入你的用户名\n>  ')
        secret = input("请输入你的密码\n>  ")
        login(secret, account)
        checkLogin()


if __name__ == '__main__':
    if len(sys.argv) < 2:
        questionIDs = input('请输入要爬取的问题id(如有多个id，请用空格隔开): ')
    checkLogin()
