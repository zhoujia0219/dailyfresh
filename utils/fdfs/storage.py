from django.core.files.storage import FileSystemStorage
from fdfs_client.client import Fdfs_client


class FdfsStorage(FileSystemStorage):

    def _save(self, name, content):
        # path = super()._save(name, content)

        client = Fdfs_client('utils/fdfs/client.conf')
        try:
            datas = content.read()
            dict_data = client.upload_by_buffer(datas)
            status = dict_data.get('Status')
            if status == 'Upload successed.':
                # 上传图片成功
                path = dict_data.get('Remote file_id')
            else:
                raise Exception('上传图片失败：%s' % status)

        except Exception as e:
            print(e)
            raise e

        return path

    def url(self, name):

        url = super().url(name)
        return 'http://127.0.0.1:8888/' + url
