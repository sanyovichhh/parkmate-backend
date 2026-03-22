from datetime import datetime
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth import authenticate
from django.contrib.auth import login as auth_login, logout as auth_logout
from .models import Parking, User, Booking
from .pagination import StandardResultsSetPagination
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    ParkingSerializer,
    BookingSerializer
)


def home(request):
    return render(request, 'index.htm')



def parse_at_query_param(request):
    """
    Read optional ?at= ISO datetime from query string.
    Returns (at, error_response). at is None if param missing; error_response is set on bad format.
    """
    at_str = request.query_params.get('at')
    if not at_str:
        return None, None
    try:
        at = datetime.fromisoformat(at_str.replace('Z', '+00:00'))
        if timezone.is_naive(at):
            at = timezone.make_aware(at)
        return at, None
    except ValueError:
        return None, Response(
            {'error': 'Invalid datetime for "at". Use ISO 8601, e.g. 2025-03-15T12:00:00'},
            status=status.HTTP_400_BAD_REQUEST,
        )


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
        auth_login(request._request, user)  # Create session - use underlying Django request
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
    No credentials (email/password) needed - only session cookie required.
    Just send the session cookie that was created during login.
    """
    auth_logout(request._request)  # Destroy session - use underlying Django request
    return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_current_user(request):
    """
    Get current authenticated user information.
    GET /api/parkmate/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data, status=status.HTTP_200_OK)


# User management endpoints

@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_user(request, user_id):
    """
    Get user information.
    GET /api/parkmate/users/{user_id}
    Accessible only for admins and the user themselves.
    """
    user = get_object_or_404(User, id=user_id)
    
    # Check permission: admin or self
    if not request.user.is_admin and request.user.id != user.id:
        return Response(
            {'error': 'You do not have permission to access this user'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserSerializer(user)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_user(request, user_id):
    """
    Delete a user.
    DELETE /api/parkmate/users/{user_id}
    Accessible only for admins and the user themselves.
    """
    user = get_object_or_404(User, id=user_id)
    
    # Check permission: admin or self
    if not request.user.is_admin and request.user.id != user.id:
        return Response(
            {'error': 'You do not have permission to delete this user'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    user.delete()
    return Response({'message': 'User deleted successfully'}, status=status.HTTP_200_OK)


# Parking endpoints

@api_view(['GET', 'POST'])
def parking_list_create(request):
    """
    Create a new parking or get all parkings.
    POST /api/parkmate/parking - Create parking (Admin only)
    GET /api/parkmate/parking - Get all parkings (Public)
    """
    if request.method == 'POST':
        # Check if user is authenticated and is admin
        if not request.user.is_authenticated:
            return Response(
                {'error': 'Authentication required'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        if not request.user.is_admin:
            return Response(
                {'error': 'Only admins can create parking places'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = ParkingSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:  # GET
        at, err = parse_at_query_param(request)
        if err is not None:
            return err
        parkings = Parking.objects.all().order_by("parking_id")
        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(parkings, request)
        serializer = ParkingSerializer(
            page,
            many=True,
            context={'request': request, 'at': at},
        )
        return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
def get_parking(request, parking_id):
    """
    Get specific parking.
    GET /api/parkmate/parking/{parking_id}
    Optional query: ?at=2025-03-15T12:00:00 — includes available_spots at that time.
    """
    at, err = parse_at_query_param(request)
    if err is not None:
        return err
    parking = get_object_or_404(Parking, parking_id=parking_id)
    serializer = ParkingSerializer(parking, context={'request': request, 'at': at})
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['GET'])
def parking_availability(request, parking_id):
    """
    Get number of available spots for a parking at a given time.
    GET /api/parkmate/parking/{parking_id}/availability/?at=2025-03-15T12:00:00
    Query param `at`: ISO 8601 datetime (optional; defaults to now).
    """
    parking = get_object_or_404(Parking, parking_id=parking_id)
    at, err = parse_at_query_param(request)
    if err is not None:
        return err
    if at is None:
        at = timezone.now()

    available = parking.get_available_spots(at=at)
    booked = parking.amount_of_spots - available
    return Response({
        'parking_id': parking.parking_id,
        'datetime': at.isoformat(),
        'total_spots': parking.amount_of_spots,
        'booked': booked,
        'available': available,
    }, status=status.HTTP_200_OK)


@api_view(['PUT'])
def update_parking(request, parking_id):
    """
    Update a parking.
    PUT /api/parkmate/parking/{parking_id}
    Admin only.
    """
    # Check if user is authenticated and is admin
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if not request.user.is_admin:
        return Response(
            {'error': 'Only admins can update parking places'},
            status=status.HTTP_403_FORBIDDEN
        )
    
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
    Admin only.
    """
    # Check if user is authenticated and is admin
    if not request.user.is_authenticated:
        return Response(
            {'error': 'Authentication required'},
            status=status.HTTP_401_UNAUTHORIZED
        )
    if not request.user.is_admin:
        return Response(
            {'error': 'Only admins can delete parking places'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    parking = get_object_or_404(Parking, parking_id=parking_id)
    parking.delete()
    return Response({'message': 'Parking deleted successfully'}, status=status.HTTP_200_OK)


# Booking endpoints

@api_view(['GET', 'POST'])
@permission_classes([permissions.IsAuthenticated])
def booking_list_create(request):
    """
    Create a new booking or get all bookings.
    POST /api/parkmate/bookings - Create booking
    GET /api/parkmate/bookings - Get all bookings (Admin: all, User: own)
    """
    if request.method == 'POST':
        request.user_obj = request.user
        serializer = BookingSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    else:  # GET
        if request.user.is_admin:
            bookings = Booking.objects.all().order_by("-start_time", "booking_id")
        else:
            bookings = Booking.objects.filter(user_id=request.user).order_by(
                "-start_time", "booking_id"
            )

        paginator = StandardResultsSetPagination()
        page = paginator.paginate_queryset(bookings, request)
        serializer = BookingSerializer(page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


@api_view(['GET'])
@permission_classes([permissions.IsAuthenticated])
def get_booking(request, booking_id):
    """
    Get specific booking.
    GET /api/parkmate/bookings/{booking_id}
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check permission: admin or owner
    if not request.user.is_admin and booking.user_id != request.user:
        return Response(
            {'error': 'You do not have permission to access this booking'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = BookingSerializer(booking)
    return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(['PUT'])
@permission_classes([permissions.IsAuthenticated])
def update_booking(request, booking_id):
    """
    Update a booking.
    PUT /api/parkmate/bookings/{booking_id}
    Owner or admin only.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check permission: admin or owner
    if not request.user.is_admin and booking.user_id != request.user:
        return Response(
            {'error': 'You do not have permission to update this booking'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    request.user_obj = request.user
    serializer = BookingSerializer(booking, data=request.data, partial=True, context={'request': request})
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['DELETE'])
@permission_classes([permissions.IsAuthenticated])
def delete_booking(request, booking_id):
    """
    Delete a booking.
    DELETE /api/parkmate/bookings/{booking_id}
    Owner or admin only.
    """
    booking = get_object_or_404(Booking, booking_id=booking_id)
    
    # Check permission: admin or owner
    if not request.user.is_admin and booking.user_id != request.user:
        return Response(
            {'error': 'You do not have permission to delete this booking'},
            status=status.HTTP_403_FORBIDDEN
        )
    
    booking.delete()
    return Response({'message': 'Booking deleted successfully'}, status=status.HTTP_200_OK)
