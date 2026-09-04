"""The paper's nine equations as native Word math.

Each builder returns a list of OMML elements for one equation. Numbering
matches the manuscript: (1) federated objective through (9) ECE.
"""
from paper.omml import (run as r, op, sub, sup, subsup, frac, nary, func,
                        delim, brk)


def _theta():
    return r("\u03b8")


def eq1_objective():
    """min_theta  sum_k w_k L_k(theta)"""
    return [
        sub(op("min"), _theta()), op(" "),
        nary("\u2211", [sub(r("k"), r(""))] if False else [r("k")], [],
             [sub(r("w"), r("k")), op(" "),
              sub(r("L"), r("k")), delim([_theta()])]),
    ]


def eq2_distance():
    """D_k = 1/2 sum_c |pi_k(c) - pibar(c)|"""
    return [
        sub(r("D"), r("k")), op(" = "),
        frac([op("1")], [op("2")]),
        nary("\u2211", [r("c")], [],
             [op("\u2502"), sub(r("\u03c0"), r("k")), delim([r("c")]),
              op(" \u2212 "), r("\u03c0\u0304"), delim([r("c")]),
              op("\u2502")]),
    ]


def eq3_quality():
    """q_k = 1 / (1 + L_k)"""
    return [
        sub(r("q"), r("k")), op(" = "),
        frac([op("1")], [op("1 + "), sub(r("L"), r("k"))]),
    ]


def eq4_score():
    """s_k = alpha log n_k - beta D_k + gamma log q_k

    Operators carry no manual padding: Word spaces binary operators in a
    math run itself, and the extra spaces pushed the number onto its own
    line.
    """
    return [
        sub(r("s"), r("k")), op("="),
        r("α"), func("log", [sub(r("n"), r("k"))]),
        op("−"), r("β"), sub(r("D"), r("k")),
        op("+"), r("γ"), func("log", [sub(r("q"), r("k"))]),
    ]


def eq5_softmax():
    """w_k = exp(s_k - s*) / sum_j exp(s_j - s*),  s* = max_j s_j"""
    return [
        sub(r("w"), r("k")), op(" = "),
        frac([func("exp", [delim([sub(r("s"), r("k")), op(" \u2212 "),
                                  sup(r("s"), op("\u22c6"))])])],
             [nary("\u2211", [sub(r("j"), r("")) if False else r("j")],
                   [r("K")],
                   [func("exp", [delim([sub(r("s"), r("j")), op(" \u2212 "),
                                        sup(r("s"), op("\u22c6"))])])])]),
    ]


def eq6_aggregation():
    """theta^{t+1} = sum_k w_k theta_k^{t+1}"""
    return [
        sup(_theta(), [op("t + 1")][0]), op(" = "),
        nary("\u2211", [op("k = 1")], [r("K")],
             [sub(r("w"), r("k")), op(" "),
              subsup(_theta(), r("k"), op("t + 1"))]),
    ]


def eq7_fedavg():
    """w_k = n_k / sum_j n_j  (the FedAvg weights, recovered at b=g=0)"""
    return [
        sub(r("w"), r("k")), op(" = "),
        frac([sub(r("n"), r("k"))],
             [nary("∑", [r("j")], [], [sub(r("n"), r("j"))])]),
    ]


def eq8_dpsgd():
    """g~_t = 1/B sum_{i in B_t} clip(grad L_i(theta_t), C) + N(0, sigma^2 C^2 I)"""
    return [
        sub(r("g\u0303"), r("t")), op(" = "),
        frac([op("1")], [r("B")]),
        nary("\u2211", [r("i"), op(" \u2208 "), sub(r("B"), r("t"))], [],
             [func("clip", [op("\u2207"), sub(r("L"), r("i")),
                            delim([sub(_theta(), r("t"))]),
                            op(", "), r("C")])]),
        brk(),
        op("+ "), r("\U0001d4a9"),
        delim([op("0, "), sup(r("\u03c3"), op("2")),
               sup(r("C"), op("2")), r("I")]),
    ]


def eq9_ece():
    """ECE = sum_{m=1}^{M} (|B_m|/N) |A(B_m) - C(B_m)|

    A and C stand for the accuracy and confidence of a bin; the sentence
    after the display names them. Spelling them out ran past the column
    and split the absolute value across two lines.
    """
    return [
        op("ECE"), op("="),
        nary("\u2211", [op("m=1")], [r("M")],
             [frac([delim([sub(r("B"), r("m"))], left="|", right="|")],
                   [r("N")]),
              delim([r("A"), delim([sub(r("B"), r("m"))]),
                     op("\u2212"),
                     r("C"), delim([sub(r("B"), r("m"))])],
                    left="|", right="|")]),
    ]


EQUATIONS = {
    "eq1_objective.png": eq1_objective,
    "eq2_distance.png": eq2_distance,
    "eq3_quality.png": eq3_quality,
    "eq4_score.png": eq4_score,
    "eq5_softmax.png": eq5_softmax,
    "eq6_aggregation.png": eq6_aggregation,
    "eq9_fedavg_special.png": eq7_fedavg,
    "eq7_dpsgd.png": eq8_dpsgd,
    "eq8_ece.png": eq9_ece,
}
