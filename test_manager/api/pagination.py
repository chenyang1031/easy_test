"""
共享分页配置

统一的分页类，各 ViewSet 从此文件引用，避免重复定义。
"""
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100
