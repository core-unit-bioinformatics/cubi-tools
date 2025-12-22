
import abc
import enum
import re


class YesOrNo(enum.Enum):
    no = 0
    n = 0
    nay = 0
    yes = 1
    y = 1
    yay = 1


class Sanitizer(abc.ABC):

    def __init__(self, check: str) -> None:
        self.regexp = re.compile(check)
        return None

    def fail(self, tested_input):
        err_msg = (
            f"Failed to validate user input >>> {tested_input} <<< "
            f"with regular expression: {self.regexp.pattern}"
        )
        raise ValueError(err_msg)

    @abc.abstractmethod
    def validate(self, user_input):
        raise NotImplementedError


class LiteralSanitizer(Sanitizer):

    def validate(self, user_input):
        fail = self.regexp.match(user_input) is None
        if fail:
            self.fail(user_input)
        return user_input


class UserAnswer(Sanitizer):

    def __init__(self):
        yes_no_options = "(" + "|".join(YesOrNo.__members__) + ")"
        self.regexp = re.compile(yes_no_options)
        return None

    def validate(self, user_input):
        norm_input = user_input.lower()
        fail = self.regexp.match(norm_input) is None
        if fail:
            self.fail(norm_input)
        return norm_input

    def is_positive(self, user_input):
        _ = self.validate(user_input)
        answer = bool(YesOrNo[user_input].value)
        return answer

    def is_negative(self, user_input):
        return not self.is_positive(user_input)


class IntSanitizer(Sanitizer):

    def validate(self, user_input):
        fail = self.regexp.match(str(user_input)) is None
        if fail:
            self.fail(user_input)
        return user_input


class CommaListSanitizer(Sanitizer):

    def validate(self, user_input):
        values = [v.strip() for v in user_input.split(",")]
        fails = []
        for value in values:
            fail = self.regexp.match(value) is None
            if fail:
                fails.append(value)
        if fails:
            self.fail(",".join(fails))
        # note here that we are not returning
        # the comma-sep string
        return values

