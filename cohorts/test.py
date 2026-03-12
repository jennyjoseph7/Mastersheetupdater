import unittest
from unittest.mock import patch
from utility import UtilityMixin


class TestUtilityMixin(unittest.TestCase):

    SAMPLE_PDF = "https://d24ohqpcwj3ww1.cloudfront.net/gryd_file_system/media/document/bde3c8c1-5053-47cf-8b2a-fbe8c1b8dc4f-68e8b8e4_SwiftTechnicalSpecification.pdf"
    SAMPLE_WEBSITE = "https://www.google.com"
    
    def setUp(self):
        self.util = UtilityMixin()

    def test_strict_url_validator_valid(self):
        url = "https://www.google.com"
        self.assertTrue(self.util.strict_url_validator(url))

    def test_strict_url_validator_invalid(self):
        url = "not_a_url"
        self.assertFalse(self.util.strict_url_validator(url))

    def test_fetch_brochure_content_real(self):
        result = self.util.fetch_brochure_content(self.SAMPLE_PDF)
        self.assertIsInstance(result, dict)

    @patch.object(UtilityMixin, "fetch_brochure_content")
    def test_fetch_brochure_content(self, mock_fetch):
        mock_fetch.return_value = {"page_content": "dummy"}
        expected_keys = ["page_content"]
        result = self.util.fetch_brochure_content(
            brochure_url=self.SAMPLE_PDF
            )

        self.assertIsInstance(result, dict)
        self.assertIn("page_content", result)
        for key in expected_keys:
            self.assertIn(key , result)

    @patch.object(UtilityMixin, "fetch_product_details_from_website")
    def test_fetch_product_details_from_website(self, mock_fetch):
        mock_fetch.return_value = {"page_content": "dummy"}
        expected_keys = ["page_content"]
        result = self.util.fetch_product_details_from_website(self.SAMPLE_WEBSITE)
        self.assertIsInstance(result, dict)
        self.assertIn("page_content", result)
        for key in expected_keys:
            self.assertIn(key , result)


if __name__ == "__main__":
    unittest.main()
