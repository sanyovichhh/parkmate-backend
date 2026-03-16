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
        email = validated_data.pop('email')
        user = User.objects.create_user(email=email, password=password, **validated_data)
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
        parking_id = attrs.get('parking_id')

        if start_time and end_time and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time"})

        if not parking_id:
            raise serializers.ValidationError({"parking_id": "Parking is required"})

        # Ensure parking exists
        try:
            parking = Parking.objects.get(parking_id=parking_id)
        except Parking.DoesNotExist:
            raise serializers.ValidationError({"parking_id": "Parking does not exist"})

        # Capacity check: count overlapping bookings for this parking
        if start_time and end_time:
            overlapping = Booking.objects.filter(
                parking_id=parking,
                start_time__lt=end_time,
                end_time__gt=start_time,
            ).count()

            if overlapping >= parking.amount_of_spots:
                raise serializers.ValidationError({
                    "non_field_errors": [
                        "No available spots for this parking in the selected time range."
                    ]
                })

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
        
        # Remove user_id if it was passed as integer (we'll set it from request)
        validated_data.pop('user_id', None)
        
        # Set user_id from request (user_obj is set in the view)
        request = self.context.get('request')
        if request and hasattr(request, 'user_obj') and request.user_obj:
            validated_data['user_id'] = request.user_obj
        elif request and hasattr(request, 'user') and request.user.is_authenticated:
            validated_data['user_id'] = request.user
        else:
            raise serializers.ValidationError({"user_id": "User authentication required"})
        
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        # Convert parking_id from integer to Parking instance if provided
        if 'parking_id' in validated_data:
            parking_id = validated_data.pop('parking_id')
            parking = Parking.objects.get(parking_id=parking_id)
            validated_data['parking_id'] = parking
        
        # Remove user_id if it was passed (we don't allow changing the user)
        validated_data.pop('user_id', None)
        
        # Update the instance
        return super().update(instance, validated_data)
