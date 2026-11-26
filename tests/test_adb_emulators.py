from toolscripts.adb import emulators


def test_find_emulator_serial_matches_the_avd_name(monkeypatch):
    monkeypatch.setattr(
        emulators, "list_devices", lambda: ["R5CT1234", "emulator-5554", "emulator-5556"]
    )
    names = {"emulator-5554": "Pixel_8\nOK\n", "emulator-5556": "Pixel_9\r\nOK\r\n"}
    monkeypatch.setattr(emulators, "capture", lambda cmd, check: names[cmd[2]])

    assert emulators.find_emulator_serial("Pixel_9") == "emulator-5556"
    assert emulators.find_emulator_serial("Tablet") is None


def test_kill_emulator_waits_until_adb_drops_it(monkeypatch):
    listed = [["emulator-5554"], ["emulator-5554"], []]
    sent = []
    monkeypatch.setattr(emulators, "try_run", lambda cmd: sent.append(cmd) or True)
    monkeypatch.setattr(emulators, "list_devices", lambda: listed.pop(0))
    monkeypatch.setattr(emulators.time, "sleep", lambda s: None)

    assert emulators.kill_emulator("emulator-5554") is True
    assert sent == [["adb", "-s", "emulator-5554", "emu", "kill"]]


def test_kill_emulator_gives_up_after_the_timeout(monkeypatch):
    monkeypatch.setattr(emulators, "try_run", lambda cmd: True)
    monkeypatch.setattr(emulators, "list_devices", lambda: ["emulator-5554"])
    monkeypatch.setattr(emulators.time, "sleep", lambda s: None)

    assert emulators.kill_emulator("emulator-5554", timeout_s=0) is False
