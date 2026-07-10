"""Mock 数据管理 API ViewSet"""

from rest_framework import serializers, viewsets, permissions, status
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from rest_framework.response import Response
from django.http import HttpResponse
from django.contrib.auth.models import User
import json

from test_manager.models import MockData
from test_manager.gen_data import auto_gen_data
from .pagination import StandardResultsSetPagination


class MockDataSerializer(serializers.ModelSerializer):
    """Mock 数据序列化器"""
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)
    data_count = serializers.SerializerMethodField()

    class Meta:
        model = MockData
        fields = [
            'id', 'aim', 'data', 'description',
            'created_at', 'updated_at', 'created_by_name',
            'data_count',
        ]
        read_only_fields = ['created_at', 'updated_at']

    def get_data_count(self, obj):
        try:
            data = json.loads(obj.data)
            return len(data) if isinstance(data, list) else 1
        except (json.JSONDecodeError, TypeError):
            return 0


class MockDataViewSet(viewsets.ModelViewSet):
    """Mock 数据管理：生成、查看、删除、导出"""

    queryset = MockData.objects.all()
    serializer_class = MockDataSerializer
    permission_classes = [permissions.IsAuthenticated]
    pagination_class = StandardResultsSetPagination
    filter_backends = [SearchFilter]
    search_fields = ['aim', 'description']

    def get_queryset(self):
        return MockData.objects.filter(created_by=self.request.user).order_by('-created_at')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=False, methods=['post'])
    def generate(self, request):
        """生成 Mock 数据并保存"""
        field_defs = request.data.get('field_defs', [])
        num = int(request.data.get('num', 10))
        aim = request.data.get('aim', '')
        description = request.data.get('description', '')

        if not field_defs:
            return Response({'error': '字段定义不能为空'}, status=status.HTTP_400_BAD_REQUEST)
        if num < 1 or num > 10000:
            return Response({'error': '生成条数范围为 1~10000'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            generated_json = auto_gen_data(fields=field_defs, num=num)
        except Exception as e:
            return Response({'error': f'数据生成失败: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)

        mock_data = MockData.objects.create(
            aim=aim,
            data=generated_json,
            description=description,
            created_by=request.user,
        )

        serializer = self.get_serializer(mock_data)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['get'])
    def export(self, request, pk=None):
        """导出 Mock 数据为 JSON 文件下载"""
        mock_data = self.get_object()
        try:
            data = json.loads(mock_data.data)
        except (json.JSONDecodeError, TypeError):
            data = mock_data.data

        json_str = json.dumps(data, ensure_ascii=False, indent=2)
        filename = f"mock_data_{mock_data.id}.json"
        response = HttpResponse(json_str, content_type='application/json')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response
