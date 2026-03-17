from flask import jsonify, Response

def failure_response(message: str) -> Response:
    """
    Returns a failure response in the form of string JSON.
    """
    resp_dict = {
        "success": False,
        "message": message
    }
    return jsonify(resp_dict)

def failure_response_param(param: str) -> Response:
    """
    Returns a failure response with the following message:
    Parameter '<param>' required
    """
    return failure_response(f"Parameter '{param}' required")

def verify_data_present(data: dict, parameters: list[str], omit: list[str] = []) -> None | tuple[Response, int]:
    for parameter in parameters:
        if parameter not in omit and parameter not in data:
            return failure_response_param(parameter), 400
    return None
