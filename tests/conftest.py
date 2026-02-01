"""Pytest fixtures for ComfyUI batch image processing tests."""

import os
import tempfile

import pytest
from PIL import Image


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
def temp_real_image_dir():
    """
    Create a temporary directory with actual image files.

    Creates real PNG images (100x100 solid colors) for testing
    image loading functionality. Named to test natural sort order.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create real images with names that test natural sort
        images = [
            ("img1.png", "red"),
            ("img2.png", "green"),
            ("img10.png", "blue"),
        ]
        for filename, color in images:
            filepath = os.path.join(tmpdir, filename)
            img = Image.new("RGB", (100, 100), color=color)
            img.save(filepath)

        yield tmpdir


@pytest.fixture
def temp_mixed_image_dir():
    """
    Create a temp directory with mixed image types and a non-image file.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        # Real images
        Image.new("RGB", (50, 50), color="red").save(os.path.join(tmpdir, "test1.png"))
        Image.new("RGB", (50, 50), color="blue").save(os.path.join(tmpdir, "test2.jpg"))

        # Non-image file
        with open(os.path.join(tmpdir, "readme.txt"), "w") as f:
            f.write("not an image")

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


@pytest.fixture
def temp_output_dir():
    """Create a temporary output directory for save tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir
