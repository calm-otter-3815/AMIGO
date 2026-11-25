import numpy as np

from baselines import greedy_jar


def test_select():
    fine = np.array([[1, 0, 0], [0, .3, .3]])
    coarse = np.full(3, .5)
    omega = np.zeros((3, 3))
    omega[0, 2] = omega[2, 0] = .5
    assert greedy_jar.select(fine, coarse, omega, 2) == [0, 2]
    # a pick never changes the earlier ones, so a smaller k is a cut of a larger one
    assert greedy_jar.select(fine, coarse, omega, 3)[:2] == greedy_jar.select(fine, coarse, omega, 2)
