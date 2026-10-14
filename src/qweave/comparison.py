"""Sampling intervals for frozen-circuit Bell comparisons."""
from math import log, sqrt

from scipy.stats import binomtest

from .measurements import BASES, measured_bell_fidelity


def fidelity_difference(reference_counts, candidate_counts, *, confidence=0.95):
    """Conservative pointwise CI for candidate F minus reference F.

    Six Clopper-Pearson parity-probability intervals with Bonferroni alpha/6
    cover the difference jointly. Conditional counts use their actual accepted
    denominators. No assumption that D's conditional and marginal estimates are
    independent is made: each is compared separately with independent C shots.
    """
    if not 0 < confidence < 1:
        raise ValueError('confidence must lie strictly between zero and one')
    if any(sum(counts[basis].values()) == 0
           for counts in (reference_counts, candidate_counts) for basis in BASES):
        return {'difference': None, 'interval': None, 'confidence': confidence}
    low = high = 0.
    for counts, method_sign in ((candidate_counts, 1), (reference_counts, -1)):
        for basis, sign in zip(BASES, (1, -1, 1)):
            n = sum(counts[basis].values())
            even = counts[basis].get('00', 0) + counts[basis].get('11', 0)
            interval = binomtest(even, n).proportion_ci(
                confidence_level=1-(1-confidence)/6, method='exact')
            coefficient = method_sign * sign / 2
            low += coefficient * (interval.low if coefficient > 0 else interval.high)
            high += coefficient * (interval.high if coefficient > 0 else interval.low)
    return dict(difference=measured_bell_fidelity(candidate_counts)-measured_bell_fidelity(reference_counts),
                interval=(low, high), confidence=confidence,
                method='six Bonferroni-adjusted exact Clopper-Pearson parity intervals',
                scope='sampling uncertainty for this frozen-circuit comparison, not calibration uncertainty')


def acceptance_summary(accepted, attempted):
    """Hoeffding covers mean acceptance even if basis probabilities differ."""
    if attempted <= 0 or not 0 <= accepted <= attempted:
        raise ValueError('Invalid acceptance counts')
    p = accepted / attempted
    epsilon = sqrt(log(40)/(2*attempted))
    return dict(accepted=accepted, attempted=attempted, fraction=p,
                interval=(max(0., p-epsilon), min(1., p+epsilon)),
                interval_method='95% Hoeffding interval for mean attempted-shot acceptance')
