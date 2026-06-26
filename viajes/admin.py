from django.contrib import admin
from .models import AgencyProfile, Trip, Reservation

@admin.register(AgencyProfile)
class AgencyProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'phone', 'is_active')
    search_fields = ('user__username', 'user__email', 'phone')

@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ('origin', 'destination', 'departure_date', 'agency', 'price', 'available_seats', 'status')
    list_filter = ('status', 'departure_date', 'agency')
    search_fields = ('origin', 'destination')

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('user_name', 'user_carnet', 'trip', 'seats_reserved', 'status', 'created_at')
    list_filter = ('status', 'trip')
    search_fields = ('user_name', 'user_carnet')