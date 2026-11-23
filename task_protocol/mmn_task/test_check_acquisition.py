"""Read-only discovery must find candidate files without editing the recording data."""

def test_find_treadmill_csv_in_nested_recording_folder(tmp_path):
    from task_protocol.mmn_task.check_acquisition import find_treadmill_files

    directory = tmp_path / 'recordings' / 'old_session'
    directory.mkdir(parents=True)
    source = directory / 'mouse_treadmill.csv'
    source.write_text('timestamp,speed\n1,5\n')
    (directory / 'unrelated.csv').write_text('unrelated')
    ignored = tmp_path / '.git'
    ignored.mkdir()
    (ignored / 'treadmill.txt').write_text('ignored')
    assert find_treadmill_files([tmp_path]) == [source]
    assert source.read_text() == 'timestamp,speed\n1,5\n'


def test_search_is_bounded(tmp_path):
    from task_protocol.mmn_task.check_acquisition import find_treadmill_files

    for number in range(10):
        (tmp_path / ('treadmill{}.csv'.format(number))).write_text('data')
    assert len(find_treadmill_files([tmp_path], limit=3)) == 3
