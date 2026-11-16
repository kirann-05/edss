from datetime import date, timedelta

import pytest

from app.domain.enums import Domain
from app.kpi.catalogue import CATALOGUE
from app.synthetic.generator import generate, nudge_to_total, split_total


class TestShape:
    def test_eight_departments_over_three_academic_years(self, dataset):
        assert len(dataset.departments) == 8
        assert dataset.periods == ("2023-24", "2024-25", "2025-26")
        assert dataset.current_period == "2025-26"
        assert {f.period_year for f in dataset.facts} == set(dataset.periods)

    def test_every_metric_in_the_catalogue_is_produced(self, dataset):
        assert {f.metric_key for f in dataset.facts} == set(CATALOGUE)

    def test_every_fact_carries_status_as_of_and_a_source_reference(self, dataset):
        for fact in dataset.facts:  # ingestion rule: rows without these are rejected
            assert fact.status is not None
            assert fact.as_of is not None
            assert fact.source_ref

    def test_no_two_facts_share_a_slot(self, dataset):
        slots = [(f.dept_code, f.metric_key, f.period_year, f.period_sub) for f in dataset.facts]
        assert len(slots) == len(set(slots))

    def test_every_fact_points_at_a_batch_of_its_own_domain_and_period(self, dataset):
        batches = {b.id: b for b in dataset.batches}
        for fact in dataset.facts:
            batch = batches[fact.batch_id]
            assert batch.domain is fact.domain
            assert batch.source_system_id == fact.source_system_id
        assert sum(b.row_count for b in dataset.batches) == len(dataset.facts)

    def test_every_publication_points_at_a_research_batch(self, dataset):
        batches = {b.id: b for b in dataset.batches}
        for paper in dataset.publications:
            assert batches[paper.batch_id].domain is Domain.RESEARCH

    def test_ids_are_unique_and_sequential(self, dataset):
        assert [f.id for f in dataset.facts] == list(range(1, len(dataset.facts) + 1))
        assert [p.id for p in dataset.publications] == list(range(1, len(dataset.publications) + 1))

    def test_closed_years_are_clean(self, dataset, ref):
        for fact in dataset.facts:
            if fact.period_year != dataset.current_period:
                assert fact.status.value in {"final", "audited"}, fact


class TestDeterminism:
    def test_same_seed_and_date_give_identical_data(self):
        a, b = generate(date(2026, 10, 1)), generate(date(2026, 10, 1))
        assert a == b

    def test_another_reference_date_shifts_as_of_but_not_the_figures(self):
        a, b = generate(date(2026, 10, 1)), generate(date(2026, 12, 1))
        assert [f.value for f in a.facts] == [f.value for f in b.facts]
        assert [f.status for f in a.facts] == [f.status for f in b.facts]
        shift = timedelta(days=61)
        assert all(fb.as_of - fa.as_of == shift for fa, fb in zip(a.facts, b.facts, strict=True))

    def test_the_seed_only_changes_publication_wording_not_the_numbers(self):
        a, b = generate(date(2026, 10, 1), seed=1), generate(date(2026, 10, 1), seed=2)
        assert [f.value for f in a.facts] == [f.value for f in b.facts]
        assert [p.title for p in a.publications] != [p.title for p in b.publications]


class TestHelpers:
    @pytest.mark.parametrize(
        ("total", "weights"),
        [
            (1250, [240, 60, 180, 120, 180, 120, 60]),
            (9200, [905, 330, 118]),
            (7, [1, 1, 1]),
            (0, [3, 4]),
        ],
    )
    def test_split_total_sums_exactly_and_keeps_proportion(self, total, weights):
        parts = split_total(total, weights)
        assert sum(parts) == total
        assert all(part >= 0 for part in parts)
        quotas = [total * w / sum(weights) for w in weights]
        assert all(abs(part - quota) < 1 for part, quota in zip(parts, quotas, strict=True))

    def test_split_total_with_no_weight_gives_zeros(self):
        assert split_total(10, [0, 0]) == [0, 0]

    def test_nudge_reaches_the_total_without_breaking_caps(self):
        result = nudge_to_total([8, 8, 8], 27, order=[0, 1, 2], cap=[10, 10, 10])
        assert sum(result) == 27
        assert max(result) <= 10

    def test_nudge_down_never_goes_negative(self):
        result = nudge_to_total([3, 0, 5], 4, order=[2, 0, 1])
        assert sum(result) == 4
        assert min(result) >= 0

    def test_nudge_that_cannot_reach_the_total_raises(self):
        with pytest.raises(ValueError, match="cannot reach"):
            nudge_to_total([10, 10], 25, order=[0, 1], cap=[10, 10])
