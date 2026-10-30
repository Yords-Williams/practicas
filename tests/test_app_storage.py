from app_storage import user_data_path


def test_user_data_path_migrates_legacy_file_and_preserves_existing_target(
    tmp_path, monkeypatch
):
    import app_storage

    legacy_dir = tmp_path / "legacy"
    data_dir = tmp_path / "user-data"
    legacy_dir.mkdir()
    legacy_file = legacy_dir / "cameras_config.json"
    legacy_file.write_text('[{"name": "Legacy"}]', encoding="utf-8")
    monkeypatch.chdir(legacy_dir)
    monkeypatch.setattr(app_storage, "APP_DATA_DIR", data_dir)

    migrated_path = user_data_path("cameras_config.json")

    assert migrated_path == str(data_dir / "cameras_config.json")
    assert (data_dir / "cameras_config.json").read_text(encoding="utf-8") == (
        '[{"name": "Legacy"}]'
    )

    legacy_file.write_text("[]", encoding="utf-8")
    assert user_data_path("cameras_config.json") == migrated_path
    assert (data_dir / "cameras_config.json").read_text(encoding="utf-8") == (
        '[{"name": "Legacy"}]'
    )
