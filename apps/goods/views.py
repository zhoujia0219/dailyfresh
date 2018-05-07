from django.core.cache import cache
from django.core.paginator import Paginator, EmptyPage
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.views.generic import View
from django_redis import get_redis_connection
from redis import StrictRedis


from apps.goods.models import GoodsCategory, IndexSlideGoods, IndexPromotion, IndexCategoryGoods, GoodsSKU

from apps.users.models import User
from apps.users.views import UserAddressView


class BaseCartView(View):

    def get_cart_count(self, request):

        cart_count = 0
        if request.user.is_authenticated():
            strict_redis = get_redis_connection()
            user_id = request.user.id
            # key = 'cart_%s' % user_id
            key = 'cart_%s' % request.user.id

            # cart_dict = strict_redis.hgetall(key)
            vals = strict_redis.hvals(key)

            # for c in cart_dict.values():
            for count in vals:
                # cart_count += int(c)
                cart_count += int(count)

        return cart_count


class IndexView(BaseCartView):

    def get(self, request):

        context = cache.get('index_html_data')
        # user = User()
        # user.is_authenticated()
        if context is None:
            print('首页缓存为空，读取数据库数据')
            categories = GoodsCategory.objects.all()
            slide_skus = IndexSlideGoods.objects.all().order_by('index')
            promotions = IndexPromotion.objects.all().order_by('index')[0:2]


            for category in categories:
                text_skus = IndexCategoryGoods.objects.filter(category=category, display_type=0).order_by('index')
                img_skus = IndexCategoryGoods.objects.filter(category=category, display_type=1).order_by('index')

                category.text_skus = text_skus
                category.img_skus= img_skus


            context = {
                'categories': categories,
                'slide_skus': slide_skus,
                'promotions': promotions,
            }

            cache.set('index_html_data', context, 60*30)

        else:
            print('缓存不为空，使用缓存')

        cart_count = self.get_cart_count(request)

        # context.update(cart_count=cart_count)
        context.update({'cart_count': cart_count})
        return render(request, 'index.html', context)


class DetailView(View):

    # /goods/商品id
    def get(self, request, sku_id):

        # 查询商品详情信息
        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoesNotExist:
            # 查询不到商品则跳转到首页
            # return HttpResponse('商品不存在')
            return redirect(reverse('goods:index'))

        # 获取所有的类别数据
        categories = GoodsCategory.objects.all()

        # 获取最新推荐
        new_skus = GoodsSKU.objects.filter(
            category=sku.category).order_by('-create_time')[0:2]

        # 查询其它规格的商品
        other_skus = sku.spu.goodssku_set.exclude(id=sku.id)

        # 获取购物车中的商品数量
        cart_count = 0
        # 如果是登录的用户
        if request.user.is_authenticated():
            # 获取用户id
            user_id = request.user.id
            # 从redis中获取购物车信息
            redis_conn = get_redis_connection("default")
            # 如果redis中不存在，会返回None
            cart_dict = redis_conn.hgetall("cart_%s" % user_id)
            for val in cart_dict.values():
                cart_count += int(val)    # 转成int再作累加

            # 保存用户的历史浏览记录
            # history_用户id: [3, 1, 2]
            # 移除现有的商品浏览记录
            key = 'history_%s' % request.user.id
            redis_conn.lrem(key, 0, sku.id)
            # 从左侧添加新的商品浏览记录
            redis_conn.lpush(key, sku.id)
            # 控制历史浏览记录最多只保存3项(包含头尾)
            redis_conn.ltrim(key, 0, 2)

        # 定义模板数据
        context = {
            'categories': categories,
            'sku': sku,
            'new_skus': new_skus,
            'cart_count': cart_count,
            'other_skus': other_skus,
        }

        # 响应请求,返回html界面
        return render(request, 'detail.html', context)


class ListView(BaseCartView):

    def get(self, request, category_id, page_num):

        sort = request.GET.get('sort')
        try:
            category = GoodsCategory.objects.get(id=category_id)
        except GoodsCategory.DoesNotExist:
            return redirect(reverse('goods:index'))
        categories = GoodsCategory.objects.all()

        try:
            new_skus = GoodsCategory.objects.filter(category=category).order_by('-craete_time')[0:2]
        except:
            new_skus = None

        if sort == 'price':
            skus = GoodsSKU.objects.filter(category=category).order_by('price')
        elif sort =='hot':
            skus = GoodsSKU.objects.filter(category=category).order_by('hot')
        else:
            skus = GoodsSKU.objects.filter(category=category)
            sort = 'default'

        paginator = Paginator(skus, 2)
        try:
            page = Paginator.page(page_num)
        except EmptyPage:
            page = Paginator.page(1)


        cart_count = self.get_cart_count(request)

        context = {
            'category': category,
            'categories': categories,

            # 'skus': skus,
            'page': page,
            'page_range': paginator.page_range,

            'new_skus': new_skus,
            'cart_count': cart_count,
            'sort': sort,
        }
        return render(request, 'list.html', context)