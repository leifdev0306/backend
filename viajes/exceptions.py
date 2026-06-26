from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        response.data['status_code'] = response.status_code
    else:
        # Manejar errores no capturados
        response = Response(
            {'detail': 'Ocurrió un error inesperado.', 'status_code': 500},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )
    return response