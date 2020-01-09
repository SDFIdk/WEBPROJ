from werkzeug.routing import BaseConverter


class IntFloatConverter(BaseConverter):
    """
    Creates a new datatype for use in flask routes.

    Shamelessly stolen from
    https://github.com/pallets/werkzeug/issues/1645#issuecomment-532829939
    """

    regex = r"-?(?:\d+(?:\.(?:\d+)?)?|\.\d+)"

    def to_python(self, value):
        try:
            return int(value)
        except ValueError:
            return float(value)
