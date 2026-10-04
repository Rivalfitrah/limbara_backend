from math import asin, cos, radians, sin, sqrt

EARTH_RADIUS_KM = 6371.0088


def haversine_km(latitude_a: float, longitude_a: float, latitude_b: float, longitude_b: float) -> float:
    delta_latitude = radians(latitude_b - latitude_a)
    delta_longitude = radians(longitude_b - longitude_a)
    latitude_a_rad = radians(latitude_a)
    latitude_b_rad = radians(latitude_b)

    haversine = sin(delta_latitude / 2) ** 2 + cos(latitude_a_rad) * cos(latitude_b_rad) * sin(delta_longitude / 2) ** 2
    return 2 * EARTH_RADIUS_KM * asin(sqrt(haversine))