


async def test_truncation_repair_emits_redacted_audit(caplog) -> None:
    stt = _ScriptedSTT(
        [
            "Please use simple words.",
            "Please use simple words.",
            "by expressing yourself in simple, precise language.",
        ]
    )
    pipe, _events = _session_pipeline(stt, _paused_recording())

    caplog.set_level(logging.DEBUG, logger="jarvis.speech.pipeline")
    await _run_session(pipe)

    messages = [
        record.getMessage()
        for record in caplog.records
        if "dictation truncation audit:" in record.getMessage()
    ]
    assert any("original=Please use simple words." in message for message in messages)
    assert any("piece=1/2" in message and "text=Please use simple words." in message for message in messages)
    assert any("piece=2/2" in message and "text=by expressing yourself in simple, precise language." in message for message in messages)
    assert any("replaced=True" in message for message in messages)
