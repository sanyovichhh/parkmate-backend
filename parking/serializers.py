from rest_framework import serializers
from .models import Parking, User, Booking
from django.contrib.auth.hashers import make_password, check_password


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'password', 'password_confirm', 'is_admin', 'date_joined')
        read_only_fields = ('id', 'date_joined')
        extra_kwargs = {
            'email': {'required': True},
            'first_name': {'required': True},
            'last_name': {'required': True},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords don't match"})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        user = User.objects.create_user(password=password, **validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'is_admin', 'date_joined')
        read_only_fields = ('id', 'date_joined')


class ParkingSerializer(serializers.ModelSerializer):
    class Meta:
        model = Parking
        fields = '__all__'
        read_only_fields = ('parking_id',)

    def create(self, validated_data):
        # Auto-generate parking_id if not provided
        if 'parking_id' not in validated_data or validated_data.get('parking_id') is None:
            last_parking = Parking.objects.order_by('-parking_id').first()
            validated_data['parking_id'] = (last_parking.parking_id + 1) if last_parking else 1
        return super().create(validated_data)


class BookingSerializer(serializers.ModelSerializer):
    parking = ParkingSerializer(source='parking_id', read_only=True)
    user = UserSerializer(source='user_id', read_only=True)
    parking_id = serializers.IntegerField(write_only=True)
    user_id = serializers.IntegerField(write_only=True, required=False)

    class Meta:
        model = Booking
        fields = ('booking_id', 'parking_id', 'user_id', 'start_time', 'end_time', 'parking', 'user')
        read_only_fields = ('booking_id',)

    def validate(self, attrs):
        start_time = attrs.get('start_time')
        end_time = attrs.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time"})
        
        # Check if parking exists
        parking_id = attrs.get('parking_id')
        if parking_id:
            try:
                Parking.objects.get(parking_id=parking_id)
            except Parking.DoesNotExist:
                raise serializers.ValidationError({"parking_id": "Parking does not exist"})
        
        return attrs

    def create(self, validated_data):
        # Auto-generate booking_id if not provided
        if 'booking_id' not in validated_data or validated_data.get('booking_id') is None:
            last_booking = Booking.objects.order_by('-booking_id').first()
            validated_data['booking_id'] = (last_booking.booking_id + 1) if last_booking else 1
        
        # Get parking object from parking_id
        parking_id = validated_data.pop('parking_id')
        parking = Parking.objects.get(parking_id=parking_id)
        validated_data['parking_id'] = parking
        
        # Set user_id from request if not provided
        request = self.context.get('request')
        if request and hasattr(request, 'user_obj') and request.user_obj:
            validated_data['user_id'] = request.user_obj
        
        # Remove user_id from validated_data if it was passed as integer (we use request.user_obj instead)
        validated_data.pop('user_id', None)
        
        return super().create(validated_data)
