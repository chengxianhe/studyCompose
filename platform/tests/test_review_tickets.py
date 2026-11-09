from concurrent.futures import ThreadPoolExecutor

from govplatform.review.tickets import FormTickets


def test_concurrent_replay_only_consumed_once() -> None:
    tickets = FormTickets()
    ticket = tickets.issue("/actions/start/test", "snapshot")
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(
            executor.map(
                lambda _: tickets.consume(ticket, "/actions/start/test", "snapshot"),
                range(20),
            )
        )
    assert sum(results) == 1


def test_ticket_is_bound_to_action_and_snapshot() -> None:
    tickets = FormTickets()
    ticket = tickets.issue("/actions/start/test", "snapshot")
    assert not tickets.consume(ticket, "/actions/start/other", "snapshot")
    assert not tickets.consume(ticket, "/actions/start/test", "changed")
    assert tickets.consume(ticket, "/actions/start/test", "snapshot")
