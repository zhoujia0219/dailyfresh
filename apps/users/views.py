import re

from django.contrib.auth import authenticate, login, logout
from django.core.mail import send_mail
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django_redis import get_redis_connection
from itsdangerous import TimedJSONWebSignatureSerializer, SignatureExpired

from apps.goods.models import GoodsSKU
from apps.orders.models import OrderInfo, OrderGoods
from apps.users.models import User, Address
from dailyfresh import settings
from celery_tasks.tasks import send_active_mail
from utils.common import LoginRequiredMixin


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

        # return HttpResponse('登录成功，进入登录界面')
        return redirect(reverse('users:login'))

    @staticmethod
    def send_active_mail(username, email, token):
        """发送激活邮件"""
        subject = '天天生鲜激活邮件'  # 标题，必须指定
        message = ''  # 正文
        from_email = settings.EMAIL_FROM  # 发件人
        recipient_list = [email]  # 收件人
        # 正文 （带有html样式）
        html_message = ('<h3>尊敬的%s：感谢注册天天生鲜</h3>'
                        '请点击以下链接激活您的帐号:<br/>'
                        '<a href="http://127.0.0.1:8000/users/active/%s">'
                        'http://127.0.0.1:8000/users/active/%s</a>'
                        ) % (username, token, token)

        send_mail(subject, message, from_email, recipient_list,
                  html_message=html_message)


class ActiveView(View):

    def get(self, request, token:str):

        try:
            s = TimedJSONWebSignatureSerializer(settings.SECRET_KEY)
            info = s.loads(token)
            user_id = info['confirm']
        except SignatureExpired:
            return HttpResponse('激活链接已过期')

        User.objects.filter(id=user_id).update(is_active=True)

        return redirect(reverse('users:login'))


class LoginView(View):

    def get(self, request):
        return render(request, 'login.html')

    def post(self, request):

        username = request.POST.get('username')
        password = request.POST.get('password')

        if not all([username, password]):  # all 一个参数 列表
            return render(request, 'login.html', {'errmsg': '请求参数不完整'})

        user = authenticate(username=username, password=password)

        if user is None:
            return render(request, 'login.html', {'errmsg': '用户名密码不正确'})

        if not user.is_active:
            return render(request, 'login.html', {'errmsg': '注册账号未激活'})

        login(request, user)

        remember = request.POST.get('remember')

        if remember != 'on':
            request.session.set_expiry(0)
        else:
            request.session.set_expiry(None)

        # 登录成功后，要跳转到next指向的界面
        next = request.GET.get('next')
        if next:
            # 如果要进入的是确认订单界面，则登录成功后，跳转到购物车界面即可
            if next == '/orders/place':
                response = redirect('/cart')
            else:
                response = redirect(next)
            return response
        else:
            # 为空，则默认跳转到首页
            # return redirect('/index')
            # 注意： urls.py文件中，urlpatterns是一个列表，不要使用{}
            return redirect(reverse('goods:index'))

class LogoutView(View):

    def get(self, request):
        logout(request)

        return redirect(reverse('goods:index'))


class UserInfoView(LoginRequiredMixin, View):

    def get(self, request):

        strict_redis = get_redis_connection()
        # 读取所有的商品id,返回一个 列表
        # history_1 = [3, 1, 2]
        key = 'history_%s' % request.user.id
        # 最多只取出5个商品id: [3, 1, 2]
        sku_ids = strict_redis.lrange(key, 0, 4)
        print(sku_ids)

        # 顺序有问题： 根据商品id，查询出商品对象
        # select * from df_goods_sku where id in [3,1,2]
        # skus = GoodsSKU.objects.filter(id__in=sku_ids)
        # 解决：
        skus = []  # 保存查询出来的商品对象
        for sku_id in sku_ids:  # sku_id: bytes
            try:
                sku = GoodsSKU.objects.get(id=int(sku_id))
                skus.append(sku)
            except:
                pass
        # 查询登录用户最新添加的地址，并显示出来
        try:
            address = request.user.address_set.latest('create_time')
            print(address)
        except Exception as a:
            print(a)
            address = ""
        data = {
            'which_page': 1,
            'address': address,
            'skus': skus,
        }
        return render(request, 'user_center_info.html', data)


class UserOrderView(LoginRequiredMixin, View):

    def get(self, request, page_no):

        # 查询当前登录用户所有的订单(降序排列)
        orders = OrderInfo.objects.filter(
            user=request.user).order_by('-create_time')
        for order in orders:
            # 查询某个订单下所有的商品
            order_skus = OrderGoods.objects.filter(order=order)
            for order_sku in order_skus:
                # 循环每一个订单商品，计算小计金额
                order_sku.amount = order_sku.price * order_sku.count

            # 新增三个实例属性
            # 订单状态
            order.status_desc = OrderInfo.ORDER_STATUS.get(order.status)
            # 实付金额
            order.total_pay = order.trans_cost + order.total_amount
            # 订单商品
            order.order_skus = order_skus

        # 创建分页对象
        # 参数2：每页显示两条
        paginator = Paginator(orders, 1)
        # 获取page对象
        try:
            page = paginator.page(page_no)
        except EmptyPage:  # 没有获取到分页
            page = paginator.page(1)
        data = {
            'which_page': 2,
            'page': page,
            'page_range': paginator.page_range,  # 页码列表[1,2,3,4]
        }

        return render(request, 'user_center_order.html', data)


class UserAddressView(LoginRequiredMixin, View):
    def get(self, request):

        # 查询登录用户最新添加的地址，并显示出来
        try:
            # address = Address.objects.filter(
            #     user=request.user).order_by('-create_time')[0]
            address = request.user.address_set.latest('create_time')
        except:
            address = None

        print("address:", address)

        context = {
            'which_page': 3,
            'address': address,
        }
        return render(request, 'user_center_site.html', context)

    def post(self, request):
        print("1")
        # 获取post请求参数
        receiver = request.POST.get('receiver')
        print("3", receiver)

        detail = request.POST.get('detail')
        print("4", detail)

        zip_code = request.POST.get('zip_code')
        print("5")

        mobile = request.POST.get('mobile')
        print("2", mobile)
        # del request.session['_auth_user_id']

        # 合法性校验
        if not all([receiver, detail, mobile]):
            return render(request, 'user_center_site.html',
                          {'errmsg': '参数不能为空'})

        print(3)

        # 新增一个地址
        Address.objects.create(
            receiver_name=receiver,
            receiver_mobile=mobile,
            detail_addr=detail,
            zip_code=zip_code,
            user=request.user,
        )
        print("3")
        # 添加地址成功，回到当前界面，刷新数据：/users/address
        return redirect(reverse('users:address'))


        # login_required(views.address)
        # @login_required


def address(request):
    """进入用户地址界面"""
    context = {
        'which_page': 3,
    }
    return render(request, 'user_center_site.html', context)

