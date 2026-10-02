from pathlib import Path

from agent_workspace.pap_conformance import (
    ConformanceStatus,
    load_conformance_cases,
    main,
    run_conformance_suite,
)


FIXTURES_DIR = Path(__file__).parent / "fixtures" / "pap_conformance"


def test_pap_conformance_cases_load_from_upstream_fixtures():
    schema_cases = load_conformance_cases(FIXTURES_DIR / "schema-validation.yaml")
    layout_cases = load_conformance_cases(FIXTURES_DIR / "layout-validation.yaml")

    assert [case.name for case in schema_cases] == [
        "Accept valid agent.md",
        "Reject missing protocol_version",
        "Accept valid memory tiers and schema evolution",
    ]
    assert [case.name for case in layout_cases] == [
        "Accept default layout structure",
        "Reject missing critical files",
    ]


def test_pap_schema_conformance_runner_tracks_las_deviations(tmp_path):
    results = run_conformance_suite(FIXTURES_DIR / "schema-validation.yaml", tmp_path)
    result_by_name = {result.name: result for result in results}

    assert result_by_name["Reject missing protocol_version"].status == ConformanceStatus.PASSED
    assert result_by_name["Accept valid memory tiers and schema evolution"].status == ConformanceStatus.PASSED
    assert result_by_name["Accept valid agent.md"].status == ConformanceStatus.DEVIATION
    assert "tools" in result_by_name["Accept valid agent.md"].deviation


def test_pap_layout_conformance_runner_tracks_ambiguous_layout_cases(tmp_path):
    results = run_conformance_suite(FIXTURES_DIR / "layout-validation.yaml", tmp_path)

    assert len(results) == 2
    assert {result.status for result in results} == {ConformanceStatus.DEVIATION}
    assert all(result.deviation for result in results)


def test_pap_conformance_runner_main_accepts_tracked_deviations():
    exit_code = main(
        [
            str(FIXTURES_DIR / "schema-validation.yaml"),
            str(FIXTURES_DIR / "layout-validation.yaml"),
        ]
    )

    assert exit_code == 0
