from django.urls import path
from .views import (
    home,
    register,
    login,
    logout_view,
    get_current_user,
    get_all_users,
    get_user,
    delete_user,
    parking_list_create,
    get_parking,
    parking_availability,
    update_parking,
    delete_parking,
    booking_list_create,
    get_booking,
    update_booking,
    delete_booking,
)

urlpatterns = [
    path('', home, name='home'),
    
    # Authentication endpoints
    path('register/', register, name='register'),
    path('login/', login, name='login'),
    path('logout/', logout_view, name='logout'),
    path('me/', get_current_user, name='get_current_user'),
    
    # User endpoints
    path('users/', get_all_users, name='get_all_users'),
    path('users/<int:user_id>/', get_user, name='get_user'),
    path('users/<int:user_id>/delete/', delete_user, name='delete_user'),
    
    # Parking endpoints
    path('parking/', parking_list_create, name='parking_list_create'),
    path('parking/<int:parking_id>/', get_parking, name='get_parking'),
    path('parking/<int:parking_id>/availability/', parking_availability, name='parking_availability'),
    path('parking/<int:parking_id>/update/', update_parking, name='update_parking'),
    path('parking/<int:parking_id>/delete/', delete_parking, name='delete_parking'),
    
    # Booking endpoints
    path('bookings/', booking_list_create, name='booking_list_create'),
    path('bookings/<int:booking_id>/', get_booking, name='get_booking'),
    path('bookings/<int:booking_id>/update/', update_booking, name='update_booking'),
    path('bookings/<int:booking_id>/delete/', delete_booking, name='delete_booking'),
]