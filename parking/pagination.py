from django.conf import settings
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Page query: ?page=2
    Optional: ?page_size=10 (capped at max_page_size)
    """

    page_size = settings.REST_FRAMEWORK.get("PAGE_SIZE", 20)
    page_size_query_param = "page_size"
    max_page_size = 100
