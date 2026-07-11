from scripts.national_station_selection import candidates, score, select_state


def station_line(station_id, state, name, elevation="10.0"):
    return f"{station_id:<11} {35.0:8.4f} {-90.0:9.4f} {elevation:>6} {state:<2} {name:<30}"


def inventory_line(station_id, element, first, last):
    return f"{station_id:<11} {35.0:8.4f} {-90.0:9.4f} {element:<4} {first:4d} {last:4d}"


def test_candidates_require_overlapping_tmax_and_tmin_and_are_sorted():
    stations = "\n".join([station_line("USW00000002", "AL", "TWO"), station_line("USW00000001", "AL", "ONE")])
    inventory = "\n".join([
        inventory_line("USW00000001", "TMAX", 1950, 2025),
        inventory_line("USW00000001", "TMIN", 1960, 2024),
        inventory_line("USW00000002", "TMAX", 2000, 2025),
    ])
    found = candidates(stations, inventory)
    assert [item.id for item in found] == ["USW00000001"]
    assert (found[0].first_year, found[0].last_year) == (1960, 2024)


def test_selection_is_deterministic_and_role_balanced():
    stations = []
    inventory = []
    roles = {}
    role_names = ["urban"] * 10 + ["rural"] * 10 + ["coverage"] * 5
    for number, role in enumerate(role_names):
        station_id = f"USW{number:08d}"
        stations.append(station_line(station_id, "AL", station_id, str(number * 20)))
        inventory.extend([inventory_line(station_id, "TMAX", 1960, 2025), inventory_line(station_id, "TMIN", 1960, 2025)])
        roles[station_id] = role
    pool = candidates("\n".join(stations), "\n".join(inventory))
    first = select_state(pool, roles, "AL", current_year=2026)
    second = select_state(list(reversed(pool)), roles, "AL", current_year=2026)
    assert first == second
    assert len(first) == 20
    assert {role: sum(item["role"] == role for item in first) for role in roles.values()} == {"urban": 8, "rural": 8, "coverage": 4}
    assert score(pool[0], "urban", 2026) > 0
