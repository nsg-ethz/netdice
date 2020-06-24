import math

import numpy as np


class Prob:
    """
    Numerically stable probability in logspace.
    """

    def __init__(self, p):
        self.is_zero = p == 0
        if not self.is_zero:
            self.log_val = math.log(p)

    def val(self):
        if self.is_zero:
            return 0
        else:
            return math.exp(self.log_val)

    def invert(self):
        """
        :return: 1-p
        """
        if self.is_zero:
            return Prob(1)
        elif self.val() > 1.0:
            return Prob(0)
        else:
            return Prob(1 - self.val())

    def __add__(self, other):
        if self.is_zero:
            return other
        elif other.is_zero:
            return self
        else:
            p = Prob(0)
            p.log_val = np.logaddexp(self.log_val, other.log_val)
            p.is_zero = False
            return p

    def __mul__(self, other):
        if self.is_zero or other.is_zero:
            return Prob(0)
        else:
            p = Prob(0)
            p.log_val = self.log_val + other.log_val
            p.is_zero = False
            return p

    def __str__(self):
        return str(self.val())
