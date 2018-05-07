import re

from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render
from django.views.generic import View
from itsdangerous import TimedJSONWebSignatureSerializer, SignatureExpired

from apps.users.models import User
from dailyfresh import settings
from celery_tasks.tasks import send_active_mail


def register(request):
    return render(request, 'register.html')


def do_register(request):
    return HttpResponse('登陆成功，进入登陆界面')


class RegisterView(View):

    def get(self, request):
        return render(request, 'register.html')

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        email = request.POST.get('email')
        allow = request.POST.get('allow')
        # print("allow: ", allow)

        if not all([username, password, password2, email, allow]):
            return render(request, 'register.html', {'message': '参数不完整'})
        if password != password2:
            return render(request, 'register.html', {'message': '两次输入的密码不一致'})
        if allow != 'on':
            return render(request, 'register.html', {'message': '请勾选同意用户协议'})
        if not re.match('^[a-z0-9][\w.\-]*@[a-z0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'register.html', {'message': '请输入正确的邮箱'})

        try:
            user = User.objects.create_user(username=username,
                                            email=email,
                                            password=password)
            user.is_active = False
            user.save()
        except IntegrityError:
            return render(request, 'register.html', {'message': '用户名已存在'})

        # todo
        token = user.generate_active_token()
        # send_active_mail(username, email, token)
        # 异步发送激活邮件
        send_active_mail.delay(username, email, token)

        return HttpResponse('登陆成功，进入登陆界面')

class ActiveView(View):

    def get(self, request, token:str):

        try:
            s = TimedJSONWebSignatureSerializer(settings.SECRET_KEY)
            info = s.loads(token)
            user_id = info['confirm']
        except SignatureExpired:
            return HttpResponse('激活链接已过期')

        User.objects.filter(id=user_id).update(is_active=True)

        return HttpResponse('激活成功，进入登录界面')

class LoginRequiredView(View):
    """会作登录检测的类视图"""

    # 需要定义为一个类方法
    @classmethod
    def as_view(cls, **initkwargs):
        # 视图函数
        view_fun = super().as_view(**initkwargs)
        # 使用装饰器对视图函数进行装饰
        return login_required(view_fun)

# dailyfresh/utils/common.py文件
class LoginRequiredMixin(object):

    @classmethod
    def as_view(cls, **initkwargs):
         # super(): MRO搜索的下一个类
         # 会调用View的as_view方法, 并返回视图函数
         view_fun = super().as_view(**initkwargs)
         # 对视图函数进行装饰
         view_fun = login_required(view_fun)
         # 返回装饰后的视图函数
         return view_fun
