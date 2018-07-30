
class FitbitApiWarning(Warning):
    pass


class FitbitApiException(Exception):

    @classmethod
    def build_from_response(cls, response_dict):
        if 'errorType' in response_dict and 'message' in response_dict:
            errors = [response_dict]
        else:
            errors = response_dict.get('errors', [])
        if not errors:
            raise ValueError("Response did not have any errors.")
        if len(errors) == 1:
            error = errors[0]
            return cls(error['errorType'], error['message'])
        else:
            raise ValueError("TODO: Implement this handling.")


class FitbitApiLimitExceededException(FitbitApiException):

    error_type = None

    def __str__(self):
        return '%s: %s' % (self.__class__.__qualname__, super().__str__())
