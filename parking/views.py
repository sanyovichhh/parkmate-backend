from django.shortcuts import render, get_object_or_404
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from .models import Parking, User, Booking
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    ParkingSerializer,
    BookingSerializer
)


def home(request):
    return render(request, 'index.htm')


# Authentication endpoints


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def register(request):
    """
    Register a new user.
    POST /api/parkmate/register
    """
    serializer = UserRegistrationSerializer(data=request.data)
    if serializer.is_valid():
        user = serializer.save()
        return Response({
            'user': UserSerializer(user).data,
            'message': 'User registered successfully'
        }, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def login(request):
    """
    Login user.
    POST /api/parkmate/login
    Body: {"email": "...", "password": "..."}
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = authenticate(request, username=email, password=password)
    if user:
        return Response({
            'user': UserSerializer(user).data,
            'message': 'Login successful'
        }, status=status.HTTP_200_OK)
    else:
        return Response(
            {'error': 'Invalid credentials'},
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
def logout_view(request):
    """
    Logout user.
    POST /api/parkmate/logout
    """
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


# User management endpoints

@api_view(['GET'])
def get_user(request, user_id):
    """
    Get user information.
    GET /api/parkmate/users/{user_id}
    Accessible only for admins and the user themselves.
    """
    user = get_object_or_404(User, id=user_id)
    
    # Get authenticated user from token/session
    auth_user_id = request.headers.get('X-User-Id')
    if auth_user_id:
        try:
            auth_user = User.objects.get(id=int(auth_user_id))
            # Check permission: admin or self
            if not auth_user.is_admin and auth_user.id != user.id:
                return Response(
                    {'error': 'You do not have permission to access this user'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except (User.DoesNotExist, ValueError):
            pass
    
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
def delete_user(request, user_id):
    """
    Delete a user.
    DELETE /api/parkmate/users/{user_id}
    Accessible only for admins and the user themselves.
    """
    user = get_object_or_404(User, id=user_id)
    
    # Get authenticated user from token/session
    auth_user_id = request.headers.get('X-User-Id')
    if auth_user_id:
        try:
            auth_user = User.objects.get(id=int(auth_user_id))
            # Check permission: admin or self
            if not auth_user.is_admin and auth_user.id != user.id:
                return Response(
                    {'error': 'You do not have permission to delete this user'},
                    status=status.HTTP_403_FORBIDDEN
                )
        except (User.DoesNotExist, ValueError):
            pass
    
    user.delete()
    return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)


# Parking endpoints

@api_view(['GET', 'POST'])
def parking_list_create(request):
    """
    Create a new parking or get all parkings.
    POST /api/parkmate/parking - Create parking
    GET /api/parkmate/parking - Get all parkings
    """
    if request.method == 'POST':
        serializer = ParkingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:  # GET
        parkings = Parking.objects.all()
        serializer = ParkingSerializer(parkings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_parking(request, parking_id):
    """
    Get specific parking.
    GET /api/parkmate/parking/{parking_id}
    """
    parking = get_object_or_404(Parking, parking_id=parking_id)
    serializer = ParkingSerializer(parking)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_parking(request, parking_id):
    """
    Update a parking.
    PUT /api/parkmate/parking/{parking_id}
    """
    parking = get_object_or_404(Parking, parking_id=parking_id)
    serializer = ParkingSerializer(parking, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_parking(request, parking_id):
    """
    Delete a parking.
    DELETE /api/parkmate/parking/{parking_id}
    """
    parking = get_object_or_404(Parking, parking_id=parking_id)
    parking.delete()
    return Response({'message': 'Parking deleted successfully'}, status=status.HTTP_200_OK)


# Booking endpoints

@api_view(['GET', 'POST'])
def booking_list_create(request):
    """
    Create a new booking or get all bookings.
    POST /api/parkmate/bookings - Create booking
    GET /api/parkmate/bookings - Get all bookings (Admin: all, User: own)
    """
    if request.method == 'POST':
        # Get user from header
        auth_user_id = request.headers.get('X-User-Id')
        if auth_user_id:
            try:
                user = User.objects.get(id=int(auth_user_id))
                request.user_obj = user
            except (User.DoesNotExist, ValueError):
                return Response(
                    {'error': 'Invalid user authentication'},
                    status=status.HTTP_401_UNAUTHORIZED
                )
        else:
            return Response(
                {'error': 'User authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        serializer = BookingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:  # GET
        auth_user_id = request.headers.get('X-User-Id')
        if auth_user_id:
            try:
                user = User.objects.get(id=int(auth_user_id))
                if user.is_admin:
                    bookings = Booking.objects.all()
                else:
                    bookings = Booking.objects.filter(user_id=user)
            except (User.DoesNotExist, ValueError):
                bookings = Booking.objects.none()
        else:
            bookings = Booking.objects.all()
        
        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def get_booking(request, booking_id):
    """
    Get specific booking.
    GET /api/parkmate/bookings/{booking_id}
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check permission
    auth_user_id = request.headers.get('X-User-Id')
    if auth_user_id:
        try:
            user = User.objects.get(id=int(auth_user_id))
            if not user.is_admin:
                # Check if user owns the booking
                if booking.user_id != user:
                    return Response(
                        {'error': 'You do not have permission to access this booking'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        except (User.DoesNotExist, ValueError):
            pass
    
    serializer = BookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_booking(request, booking_id):
    """
    Update a booking.
    PUT /api/parkmate/bookings/{booking_id}
    Owner or admin only.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check permission
    auth_user_id = request.headers.get('X-User-Id')
    if auth_user_id:
        try:
            user = User.objects.get(id=int(auth_user_id))
            if not user.is_admin:
                # Check if user owns the booking
                if booking.user_id != user:
                    return Response(
                        {'error': 'You do not have permission to update this booking'},
                        status=status.HTTP_403_FORBIDDEN
                    )
            request.user_obj = user
        except (User.DoesNotExist, ValueError):
            return Response(
                {'error': 'Invalid user authentication'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    serializer = BookingSerializer(booking, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
def delete_booking(request, booking_id):
    """
    Delete a booking.
    DELETE /api/parkmate/bookings/{booking_id}
    Owner or admin only.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check permission
    auth_user_id = request.headers.get('X-User-Id')
    if auth_user_id:
        try:
            user = User.objects.get(id=int(auth_user_id))
            if not user.is_admin:
                # Check if user owns the booking
                if booking.user_id != user:
                    return Response(
                        {'error': 'You do not have permission to delete this booking'},
                        status=status.HTTP_403_FORBIDDEN
                    )
        except (User.DoesNotExist, ValueError):
            return Response(
                {'error': 'Invalid user authentication'},
                status=status.HTTP_401_UNAUTHORIZED
            )
    
    booking.delete()
    return Response({'message': 'Booking deleted successfully'}, status=status.HTTP_200_OK)
