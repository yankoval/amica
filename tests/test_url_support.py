import os
import pytest
from unittest.mock import patch, MagicMock
from amica_generator import is_url, ensure_local, generate_amica_vdf
import urllib.error

def test_is_url():
    assert is_url("http://example.com/test.json")
    assert is_url("https://example.com/test.json")
    assert is_url("https:\\\\storage.yandexcloud.net\\test.json")
    assert not is_url("C:\\path\\to\\file.json")
    assert not is_url("/usr/local/bin/file.json")

@patch("urllib.request.urlopen")
def test_ensure_local_mangled_url(mock_urlopen, tmp_path):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b'mangled data'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    mangled_url = "https:\\\\example.com\\path\\data.json"
    normalized_url = "https://example.com/path/data.json"
    cache_dir = tmp_path / ".amica_cache_mangled"

    local_path = ensure_local(mangled_url, cache_dir=str(cache_dir))

    assert os.path.exists(local_path)
    mock_urlopen.assert_called_once_with(normalized_url)

@patch("urllib.request.urlopen")
def test_ensure_local_download(mock_urlopen, tmp_path):
    # Setup mock response
    mock_response = MagicMock()
    mock_response.read.return_value = b'{"key": "value"}'
    mock_response.__enter__.return_value = mock_response
    mock_urlopen.return_value = mock_response

    url = "https://example.com/data.json"
    cache_dir = tmp_path / ".amica_cache"

    # First call - should download
    local_path = ensure_local(url, cache_dir=str(cache_dir))

    assert os.path.exists(local_path)
    with open(local_path, "rb") as f:
        assert f.read() == b'{"key": "value"}'
    mock_urlopen.assert_called_once_with(url)

    # Second call - should use cache
    mock_urlopen.reset_mock()
    local_path_2 = ensure_local(url, cache_dir=str(cache_dir))
    assert local_path == local_path_2
    mock_urlopen.assert_not_called()

@patch("urllib.request.urlopen")
def test_ensure_local_error(mock_urlopen, tmp_path):
    mock_urlopen.side_effect = urllib.error.URLError("Network error")
    url = "https://example.com/error.json"
    cache_dir = tmp_path / ".amica_cache"

    with pytest.raises(ValueError, match="Could not download file from URL"):
        ensure_local(url, cache_dir=str(cache_dir))

@patch("urllib.request.urlopen")
@patch("amica_generator.calculate_md5")
@patch("amica_generator.count_csv_rows")
@patch("xml.etree.ElementTree.parse")
def test_generate_amica_vdf_with_urls(mock_et_parse, mock_count, mock_md5, mock_urlopen, tmp_path):
    # Mock for inputs
    mock_response_template = MagicMock()
    mock_response_template.read.return_value = b"<root><DataSource><SourcePath></SourcePath><DataMd5></DataMd5></DataSource></root>"
    mock_response_template.__enter__.return_value = mock_response_template

    mock_response_csv = MagicMock()
    mock_response_csv.read.return_value = b"header\nrecord1"
    mock_response_csv.__enter__.return_value = mock_response_csv

    mock_response_json = MagicMock()
    mock_response_json.read.return_value = b'{"key": "value"}'
    mock_response_json.__enter__.return_value = mock_response_json

    mock_response_mapping = MagicMock()
    mock_response_mapping.read.return_value = b'[{"key": "placeholder"}]'
    mock_response_mapping.__enter__.return_value = mock_response_mapping

    # Success response for PUT
    mock_response_put = MagicMock()
    mock_response_put.getcode.return_value = 200
    mock_response_put.__enter__.return_value = mock_response_put

    mock_urlopen.side_effect = [
        mock_response_template,
        mock_response_csv,
        mock_response_json,
        mock_response_mapping,
        mock_response_put
    ]

    mock_md5.return_value = "MD5HASH"
    mock_count.return_value = 1

    mock_tree = MagicMock()
    mock_root = ET.Element("Vdf")
    mock_ds = ET.SubElement(mock_root, "DataSource")
    ET.SubElement(mock_ds, "SourcePath")
    ET.SubElement(mock_ds, "DataMd5")
    mock_tree.getroot.return_value = mock_root
    mock_et_parse.return_value = mock_tree

    # Run generator with URLs
    # We need to make sure cache doesn't interfere with mocks
    cache_dir = tmp_path / ".amica_cache_test"
    with patch("amica_generator.ensure_local", side_effect=lambda x: ensure_local(x, cache_dir=str(cache_dir))):
        generate_amica_vdf(
            base_template_path="https://ex.com/t.vdf",
            new_csv_path="https://ex.com/d.csv",
            static_json_path="https://ex.com/s.json",
            mapping_json_path="https://ex.com/m.json",
            output_vdf_path="https://ex.com/out.vdf"
        )

    # Verify PUT was called
    assert mock_urlopen.call_count == 5
    last_call_args = mock_urlopen.call_args[0][0]
    assert last_call_args.full_url == "https://ex.com/out.vdf"
    assert last_call_args.method == "PUT"

import xml.etree.ElementTree as ET
