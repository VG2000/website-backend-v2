from django.http import JsonResponse

def json_response(message, status_txt, status):
    """
    Creates a standardized JSON response for use across multiple views.

    :param message: The message to include in the response
    :param status_txt: The status text ('success', 'error', etc.)
    :param status: The HTTP status code for the response
    :return: A JsonResponse object
    """
    return JsonResponse(
        {
            "message": message,
            "status_txt": status_txt,
        },
        status=status,
    )
