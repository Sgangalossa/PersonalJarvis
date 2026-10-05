def test_account_rebind_does_not_rescan_unchanged_transcript(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data = tmp_path / "data"
    home = tmp_path / "home"
    _write(_claude_path(home), [_claude_line(uuid="u1", msg_id="msg_a")])

    monkeypatch.setattr(
        "jarvis.costs.cli_usage_index._account_id_for_root",
        lambda agent, root: "claude:first",
    )
    refresh(data_dir=data, home=home)

    monkeypatch.setattr(
        "jarvis.costs.cli_usage_index._account_id_for_root",
        lambda agent, root: "claude:second",
    )

    def fail_scan(*_args, **_kwargs):
        pytest.fail("account-only refresh must not rescan an unchanged transcript")

    monkeypatch.setattr("jarvis.costs.cli_usage_index._scan", fail_scan)
    refresh(data_dir=data, home=home)

    (turn,) = _all(data)
    assert turn.account_id == "claude:second"


