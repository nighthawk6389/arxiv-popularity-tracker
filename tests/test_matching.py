from arxiv_popularity.matching import (
    normalize_arxiv_id,
    extract_arxiv_id_from_url,
    normalize_title,
)


class TestNormalizeArxivId:
    def test_strips_version(self):
        assert normalize_arxiv_id("2401.12345v2") == "2401.12345"

    def test_no_version(self):
        assert normalize_arxiv_id("2401.12345") == "2401.12345"

    def test_old_format(self):
        assert normalize_arxiv_id("hep-th/9901001v1") == "hep-th/9901001"

    def test_strips_whitespace(self):
        assert normalize_arxiv_id("  2401.12345v3  ") == "2401.12345"


class TestExtractArxivIdFromUrl:
    def test_abs_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2401.12345") == "2401.12345"

    def test_abs_url_with_version(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/abs/2401.12345v2") == "2401.12345"

    def test_pdf_url(self):
        assert extract_arxiv_id_from_url("https://arxiv.org/pdf/2401.12345") == "2401.12345"

    def test_non_arxiv_url(self):
        assert extract_arxiv_id_from_url("https://example.com/paper") is None

    def test_huggingface_papers_url(self):
        assert extract_arxiv_id_from_url("https://huggingface.co/papers/2401.12345") == "2401.12345"


class TestNormalizeTitle:
    def test_lowercase(self):
        assert normalize_title("Attention Is All You Need") == "attention is all you need"

    def test_strip_punctuation(self):
        assert normalize_title("Hello, World!") == "hello world"

    def test_collapse_whitespace(self):
        assert normalize_title("  too   many   spaces  ") == "too many spaces"

    def test_combined(self):
        assert normalize_title("  GPT-4: A Large  Model! ") == "gpt-4 a large model"
