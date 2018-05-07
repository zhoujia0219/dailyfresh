# import os
# import django
#
#
# os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dailyfresh.settings")
# django.setup()


from celery import Celery
from django.core.mail import send_mail
from django.template import loader

from apps.goods.models import GoodsCategory, IndexSlideGoods, IndexPromotion, IndexCategoryGoods
from dailyfresh import settings

# app = Celery('celery_tasks.tasks', broker='redis://127.0.0.1:6379/1')
app = Celery('dailyfresh', broker='redis://127.0.0.1:6379/1')

@app.task
def send_active_mail(username, receiver, token):

    subject = '天天生鲜用户激活'
    message = ''
    sender = settings.EMAIL_FROM
    receivers = [receiver]

    html_message = ('<h2>尊敬的 %s, 感谢注册天天生鲜</h2>' 
                    '<p>请点击此链接激活您的帐号: ' 
                    '<a href="http://127.0.0.1:8000/users/active/%s">'
                    'http://127.0.0.1:8000/users/active/%s</a>'
                    )% (username, token, token)

    send_mail(subject, message, sender, receivers, html_message=html_message)

@app.task
def generate_static_index_html():
    categories = GoodsCategory.objects.all()
    slide_skus = IndexSlideGoods.objects.all().order_by('index')
    promotions = IndexPromotion.objects.all().order_by('index')

    for category in categories:
        # 查询某一类别下的文字类别商品
        text_skus = IndexCategoryGoods.objects.filter(
            category=category, display_type=0).order_by('index')
        # 查询某一类别下的图片类别商品
        img_skus = IndexCategoryGoods.objects.filter(
            category=category, display_type=1).order_by('index')
        # 动态地给类别新增实例属性
        category.text_skus = text_skus
        # 动态地给类别新增实例属性
        category.img_skus = img_skus

    cart_count = 0

    context = {
        'categories': categories,
        'slide_skus': slide_skus,
        'promotions': promotions,
        'cart_count': cart_count,
    }

    template = loader.get_template('index.html')
    html_str = template.render(context)

    path = '/home/python/Desktop/static/index.html'

    with open(path, 'w') as file:
        file.write(html_str)