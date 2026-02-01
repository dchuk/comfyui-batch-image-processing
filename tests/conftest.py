"""Pytest fixtures for ComfyUI batch image processing tests."""

import os
import tempfile

import pytest


@pytest.fixture
def temp_image_dir():
    """
    Create a temporary directory with test image files.

    Yields the path to the temporary directory. Files are created
    with various naming patterns for testing natural sort.

    Note: These are placeholder files (not actual images) for sorting tests.
    Image loading tests will need real image fixtures.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files with various naming patterns
        test_files = [
            "img1.png",
            "img2.png",
            "img10.png",
            "photo001.jpg",
            "photo01.jpg",
            "photo1.jpg",
            "banana.png",
            "apple.png",
            "cherry.png",
        ]
        for filename in test_files:
            filepath = os.path.join(tmpdir, filename)
            with open(filepath, "w") as f:
                f.write("placeholder")

        yield tmpdir


@pytest.fixture
def comfyui_mock():
    """
    Mock for ComfyUI execution context.

    Placeholder fixture for future tests that need to mock
    ComfyUI's execution environment.
    """
    # Placeholder - will be expanded when testing actual node execution
    return {}
