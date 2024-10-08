from rest_framework.viewsets import ModelViewSet
from rest_framework.permissions import IsAuthenticated
from .models import Project
from .serializers import ProjectSerializer
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate

class CustomLoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email')
        password = request.data.get('password')

        # Authenticate the user
        user = authenticate(request, username=email, password=password)

        if user is not None:
            # Use Simple JWT to get the tokens
            refresh = RefreshToken.for_user(user)
            
            # Or use TokenObtainPairSerializer to maintain consistency with TokenObtainPairView
            serializer = TokenObtainPairSerializer(data={
                'email': email,
                'password': password
            })
            try:
                if serializer.is_valid(raise_exception=True):
                     # Check if the user is a superuser
                    is_superuser = user.is_superuser
                    # Return response with tokens in cookies
                    response = Response({
                        'message': 'Login successful',
                        'email': email,  # Add the email to the response
                        'is_superuser': is_superuser  # Add the superuser status
                    })
                    response.set_cookie(
                        key='refresh_token',
                        value=str(serializer.validated_data['refresh']),
                        httponly=True,
                        secure=True,  # Only for HTTPS
                        samesite='Lax',
                    )
                    response.set_cookie(
                        key='access_token',
                        value=str(serializer.validated_data['access']),
                        httponly=True,
                        secure=True,  # Only for HTTPS
                        samesite='Lax',
                    )
                    return response
            except Exception as e:
                return Response({'error': str(e)}, status=401)

        return Response({'error': 'Invalid credentials'}, status=401)

class LogoutView(APIView):
    # permission_classes = [IsAuthenticated]

    def post(self, request):
        print('request: ', request)
        response = Response({'message': 'Logout successful'})
        
        # Clear tokens from cookies
        response.delete_cookie('refresh_token')
        response.delete_cookie('access_token')
        
        print('response:', response)
        return response


class ProjectViewSet(ModelViewSet):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer

