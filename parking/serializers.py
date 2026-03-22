from rest_framework import serializers
from .models import Parking, User, Booking



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
    """
    Optional extra field `available_spots` when the view passes context['at'] (datetime).
    If `at` is not in context, `available_spots` is null (not computed).
    """
    available_spots = serializers.SerializerMethodField()

    class Meta:
        model = Parking
        fields = (
            'parking_id',
            'amount_of_spots',
            'address',
            'comment',
            'price',
            'available_spots',
        )
        read_only_fields = ('parking_id', 'available_spots')

    def get_available_spots(self, obj):
        at = self.context.get('at')
        if at is None:
            return None
        return obj.get_available_spots(at=at)

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
        instance = getattr(self, 'instance', None)

        # Support partial updates: fall back to current instance values
        start_time = attrs.get('start_time') or (instance.start_time if instance else None)
        end_time = attrs.get('end_time') or (instance.end_time if instance else None)
        parking_id = attrs.get('parking_id') or (instance.parking_id.parking_id if instance else None)

        if start_time is not None and end_time is not None and start_time >= end_time:
            raise serializers.ValidationError({"end_time": "End time must be after start time"})

        if not parking_id:
            raise serializers.ValidationError({"parking_id": "Parking is required"})

        # Ensure parking exists
        try:
            parking = Parking.objects.get(parking_id=parking_id)
        except Parking.DoesNotExist:
            raise serializers.ValidationError({"parking_id": "Parking does not exist"})

        # Capacity check: count overlapping bookings for this parking
        if start_time is not None and end_time is not None:
            overlapping_qs = Booking.objects.filter(
                parking_id=parking,
                start_time__lt=end_time,
                end_time__gt=start_time,
            )

            # On update, do not count current booking against itself
            if instance is not None:
                overlapping_qs = overlapping_qs.exclude(pk=instance.pk)

            overlapping = overlapping_qs.count()

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
