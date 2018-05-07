from django.contrib.auth.models import AbstractUser
from django.db import models
from itsdangerous import TimedJSONWebSignatureSerializer
from tinymce.models import HTMLField

from dailyfresh import settings
from utils.models import BaseModel


class User(BaseModel, AbstractUser):

    class Meta:
        db_table = 'df_user'


    def generate_active_token(self):

        serializer = TimedJSONWebSignatureSerializer(settings.SECRET_KEY, 3600*24)
        token = serializer.dumps({'confirm': self.id})
        return token.decode()


class Address(BaseModel):

    receiver_name = models.CharField(max_length=20, verbose_name='收件人')
    detail_addr = models.CharField(max_length=250, verbose_name='详细地址')
    receiver_mobile = models.CharField(max_length=13, verbose_name='电话号码')
    zip_code = models.CharField(max_length=6, verbose_name='邮编')
    is_default = models.BooleanField(default=False, verbose_name='是否默认地址')
    user = models.ForeignKey(User, verbose_name='所属用户')

    class Meta:
        db_table = 'df_address'


class TestModel(models.Model):

    name = models.CharField(max_length=20)

    goods_detail = HTMLField(default='', verbose_name='商品详情')



