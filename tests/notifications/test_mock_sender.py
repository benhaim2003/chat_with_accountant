from app.notifications.mock_sender import MockSender


class TestMockSender:
    def test_send_returns_true(self) -> None:
        sender = MockSender()
        assert sender.send("+972501111111", "Hello!") is True

    def test_send_logs_phone_and_message(self, caplog) -> None:
        import logging
        sender = MockSender()
        with caplog.at_level(logging.INFO):
            sender.send("+972501111111", "Test message")
        assert "+972501111111" in caplog.text
        assert "Test message" in caplog.text
