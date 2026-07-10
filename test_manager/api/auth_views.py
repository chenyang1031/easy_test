"""
认证 API 视图 — 为 Vue SPA 提供 JSON 登录/注册/用户信息接口。

使用 Django session + SessionAuthentication，通过 cookie 维持登录状态。
前端 http.js 自动携带 csrftoken cookie，无需额外处理。
"""
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from rest_framework import permissions, serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView


# ========================================================================
#  序列化器
# ========================================================================

class RegisterSerializer(serializers.ModelSerializer):
    """用户注册序列化器（与 auth_views.CustomUserCreationForm 对齐）"""
    password = serializers.CharField(write_only=True, min_length=8)
    password2 = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(required=True)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'password2']

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('该用户名已被占用')
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('该邮箱已被注册')
        return value

    def validate(self, data):
        if data['password'] != data['password2']:
            raise serializers.ValidationError({'password2': '两次输入的密码不一致'})
        return data

    def create(self, validated_data):
        validated_data.pop('password2')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
        )
        return user


class UserDetailSerializer(serializers.ModelSerializer):
    """用户详细信息序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name',
                  'date_joined', 'last_login']


class UserProfileSerializer(serializers.ModelSerializer):
    """用户个人资料编辑序列化器"""
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def validate_email(self, value):
        user = self.instance
        if User.objects.filter(email__iexact=value).exclude(pk=user.pk).exists():
            raise serializers.ValidationError('该邮箱已被其他用户使用')
        return value


# ========================================================================
#  视图
# ========================================================================

class AuthLoginView(APIView):
    """
    POST /api/v1/auth/login/

    使用用户名和密码登录，成功后建立 session。
    请求体: { "username": "...", "password": "..." }
    响应 200: { "detail": "登录成功", "user": { ... } }
    响应 401: { "detail": "用户名或密码不正确" }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username', '').strip()
        password = request.data.get('password', '')

        if not username or not password:
            return Response(
                {'detail': '请输入用户名和密码'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return Response({
                'detail': '登录成功',
                'user': UserDetailSerializer(user).data,
            })
        return Response(
            {'detail': '用户名或密码不正确'},
            status=status.HTTP_401_UNAUTHORIZED,
        )


class AuthLogoutView(APIView):
    """
    POST /api/v1/auth/logout/

    退出登录，清除当前 session。
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response({'detail': '已退出登录'})


class AuthUserView(APIView):
    """
    GET /api/v1/auth/user/

    获取当前登录用户的详细信息。
    用于 SPA 刷新页面时恢复登录状态。
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserDetailSerializer(request.user).data)


class AuthRegisterView(APIView):
    """
    POST /api/v1/auth/register/

    创建新用户并自动登录。
    请求体: { "username": "...", "email": "...", "password": "...", "password2": "..." }
    响应 201: { "detail": "注册成功", "user": { ... } }
    响应 400: { "field_name": ["错误信息"] }
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        user = serializer.save()
        login(request, user)
        return Response(
            {
                'detail': '注册成功',
                'user': UserDetailSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class AuthProfileView(APIView):
    """
    GET /api/v1/auth/profile/       → 获取个人资料（同 AuthUserView）
    PUT /api/v1/auth/profile/       → 更新个人资料（first_name, last_name, email）
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserDetailSerializer(request.user).data)

    def put(self, request):
        serializer = UserProfileSerializer(
            instance=request.user,
            data=request.data,
            partial=True,
        )
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response({
            'detail': '个人资料已更新',
            'user': UserDetailSerializer(request.user).data,
        })


class AuthPasswordChangeView(APIView):
    """
    POST /api/v1/auth/password-change/

    修改当前用户密码。
    请求体: { "old_password": "...", "new_password": "...", "new_password2": "..." }
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        old = request.data.get('old_password', '')
        new_pw = request.data.get('new_password', '')
        new_pw2 = request.data.get('new_password2', '')

        if not old or not new_pw or not new_pw2:
            return Response(
                {'detail': '请填写所有密码字段'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not request.user.check_password(old):
            return Response(
                {'detail': '旧密码不正确'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(new_pw) < 8:
            return Response(
                {'detail': '新密码长度不能少于 8 个字符'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if new_pw != new_pw2:
            return Response(
                {'detail': '两次输入的新密码不一致'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(new_pw)
        request.user.save()

        # 重新登录以保持当前 session 有效
        login(request, request.user)
        return Response({'detail': '密码修改成功'})
