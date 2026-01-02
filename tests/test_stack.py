import unittest
from stack import is_similar_filename


class TestIsSimilarFilename(unittest.TestCase):

    def test_simple_jpg_raw(self):
        self.assertTrue(
            is_similar_filename([
                "IMG123.JPG",
                "IMG123.RAW"
            ])
        )
        self.assertTrue(
            is_similar_filename([
                "IMG123.JPG",
                "IMG123.DNF"
            ])
        )

    def test_simple_jpg_raw_mixed_case(self):
        self.assertTrue(
            is_similar_filename([
                "IMG123.JPG",
                "IMG123.raw"
            ])
        )
        self.assertFalse(
            is_similar_filename([
                "IMG123.JPG",
                "img123.raw"
            ])
        )

    def test_pixel_variants(self):
        self.assertTrue(
            is_similar_filename([
                "PXL_20250615_143621025.RAW-02.ORIGINAL.dng",
                "PXL_20250615_143621025.RAW-01.COVER.jpg"
            ])
        )

    def test_same_extension(self):
        self.assertFalse(
            is_similar_filename([
                "IMG123.JPG",
                "IMG123.JPG"
            ])
        )

    def test_same_extension_mixed_case(self):
        self.assertFalse(
            is_similar_filename([
                "IMG123.JPG",
                "IMG123.jpg"
            ])
        )

    def test_different_files(self):
        self.assertFalse(
            is_similar_filename([
                "IMG123.JPG",
                "IMG124.RAW"
            ])
        )

    def test_unrelated_suffixes(self):
        self.assertTrue(
            is_similar_filename([
                "DSC0001-edit.tif",
                "DSC0001.jpg"
            ])
        )

    def test_length_error(self):
        with self.assertRaises(ValueError):
            is_similar_filename(["IMG123.JPG"])

        with self.assertRaises(ValueError):
            is_similar_filename([
                "IMG123.JPG",
                "IMG123.RAW",
                "extra.png"
            ])


if __name__ == "__main__":
    unittest.main()
