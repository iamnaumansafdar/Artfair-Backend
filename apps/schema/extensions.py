from drf_spectacular.utils import OpenApiAuthenticationExtension

class KnoxTokenAuthenticationScheme(OpenApiAuthenticationExtension):
    """
    Custom authentication scheme for Knox token authentication in Swagger/OpenAPI.
    """
    target_class = "knox.auth.TokenAuthentication"  # Knox authentication class
    name = "BearerAuth"  # Name referenced in the OpenAPI schema
    schema = {
        "type": "http",
        "scheme": "Bearer",
    }

