import pytest
from unittest.mock import patch

from thinkmark.utils.url import (
    normalize_url,
    is_url_allowed,
    url_to_filename,
    get_site_directory
)


class TestNormalizeUrl:
    """Test cases for URL normalization."""
    
    def test_normalize_url_removes_fragment(self):
        """Test that URL fragments are removed."""
        url = "https://example.com/page#section1"
        result = normalize_url(url)
        assert result == "https://example.com/page"
    
    def test_normalize_url_removes_trailing_slash(self):
        """Test that trailing slashes are removed from paths."""
        url = "https://example.com/path/"
        result = normalize_url(url)
        assert result == "https://example.com/path"
    
    def test_normalize_url_preserves_domain_root_slash(self):
        """Test that domain root slash is preserved."""
        url = "https://example.com/"
        result = normalize_url(url)
        assert result == "https://example.com/"
    
    def test_normalize_url_handles_no_path(self):
        """Test normalization of URLs with no path."""
        url = "https://example.com"
        result = normalize_url(url)
        assert result == "https://example.com"
    
    def test_normalize_url_handles_query_params(self):
        """Test that query parameters are preserved."""
        url = "https://example.com/page?param=value&other=test"
        result = normalize_url(url)
        assert result == "https://example.com/page?param=value&other=test"
    
    def test_normalize_url_removes_fragment_with_query(self):
        """Test fragment removal with query parameters."""
        url = "https://example.com/page?param=value#fragment"
        result = normalize_url(url)
        assert result == "https://example.com/page?param=value"
    
    def test_normalize_url_complex_path(self):
        """Test normalization of complex paths."""
        url = "https://docs.example.com/api/v1/endpoints/#overview"
        result = normalize_url(url)
        assert result == "https://docs.example.com/api/v1/endpoints"
    
    def test_normalize_url_multiple_slashes(self):
        """Test normalization with multiple trailing slashes."""
        url = "https://example.com/path///"
        result = normalize_url(url)
        assert result == "https://example.com/path"


class TestIsUrlAllowed:
    """Test cases for URL filtering."""
    
    def test_is_url_allowed_no_restrictions(self):
        """Test that URLs are allowed when no restrictions are set."""
        url = "https://example.com/page"
        result = is_url_allowed(url)
        assert result is True
    
    def test_is_url_allowed_domain_allowed(self):
        """Test domain allowlist functionality."""
        url = "https://example.com/page"
        allowed_domains = ["example.com"]
        result = is_url_allowed(url, allowed_domains=allowed_domains)
        assert result is True
    
    def test_is_url_allowed_domain_blocked(self):
        """Test domain blocking functionality."""
        url = "https://blocked.com/page"
        allowed_domains = ["example.com"]
        result = is_url_allowed(url, allowed_domains=allowed_domains)
        assert result is False
    
    def test_is_url_allowed_include_paths(self):
        """Test path inclusion filtering."""
        url = "https://example.com/docs/api"
        include_paths = ["/docs"]
        result = is_url_allowed(url, include_paths=include_paths)
        assert result is True
    
    def test_is_url_allowed_include_paths_blocked(self):
        """Test that URLs not matching include paths are blocked."""
        url = "https://example.com/blog/post"
        include_paths = ["/docs"]
        result = is_url_allowed(url, include_paths=include_paths)
        assert result is False
    
    def test_is_url_allowed_exclude_paths(self):
        """Test path exclusion filtering."""
        url = "https://example.com/private/secret"
        exclude_paths = ["/private"]
        result = is_url_allowed(url, exclude_paths=exclude_paths)
        assert result is False
    
    def test_is_url_allowed_exclude_paths_allowed(self):
        """Test that URLs not matching exclude paths are allowed."""
        url = "https://example.com/public/page"
        exclude_paths = ["/private"]
        result = is_url_allowed(url, exclude_paths=exclude_paths)
        assert result is True
    
    def test_is_url_allowed_multiple_include_paths(self):
        """Test multiple include paths."""
        url1 = "https://example.com/docs/guide"
        url2 = "https://example.com/api/reference"
        url3 = "https://example.com/blog/post"
        include_paths = ["/docs", "/api"]
        
        assert is_url_allowed(url1, include_paths=include_paths) is True
        assert is_url_allowed(url2, include_paths=include_paths) is True
        assert is_url_allowed(url3, include_paths=include_paths) is False
    
    def test_is_url_allowed_multiple_exclude_paths(self):
        """Test multiple exclude paths."""
        url1 = "https://example.com/private/secret"
        url2 = "https://example.com/admin/panel"
        url3 = "https://example.com/public/page"
        exclude_paths = ["/private", "/admin"]
        
        assert is_url_allowed(url1, exclude_paths=exclude_paths) is False
        assert is_url_allowed(url2, exclude_paths=exclude_paths) is False
        assert is_url_allowed(url3, exclude_paths=exclude_paths) is True
    
    def test_is_url_allowed_combined_filters(self):
        """Test combination of domain, include, and exclude filters."""
        url = "https://example.com/docs/public"
        allowed_domains = ["example.com"]
        include_paths = ["/docs"]
        exclude_paths = ["/docs/private"]
        
        result = is_url_allowed(
            url,
            allowed_domains=allowed_domains,
            include_paths=include_paths,
            exclude_paths=exclude_paths
        )
        assert result is True
    
    def test_is_url_allowed_combined_filters_blocked(self):
        """Test that exclude paths take precedence."""
        url = "https://example.com/docs/private/secret"
        allowed_domains = ["example.com"]
        include_paths = ["/docs"]
        exclude_paths = ["/docs/private"]
        
        result = is_url_allowed(
            url,
            allowed_domains=allowed_domains,
            include_paths=include_paths,
            exclude_paths=exclude_paths
        )
        assert result is False
    
    def test_is_url_allowed_empty_lists(self):
        """Test behavior with empty filter lists."""
        url = "https://example.com/page"
        result = is_url_allowed(
            url,
            allowed_domains=[],
            include_paths=[],
            exclude_paths=[]
        )
        assert result is True


class TestUrlToFilename:
    """Test cases for URL to filename conversion."""
    
    @patch('thinkmark.utils.url.slugify')
    def test_url_to_filename_basic(self, mock_slugify):
        """Test basic URL to filename conversion."""
        mock_slugify.side_effect = lambda x: x.lower().replace('.', '-')
        
        url = "https://example.com/page"
        result = url_to_filename(url)
        
        assert result == "example-com-page.html"
        assert mock_slugify.call_count == 2
    
    @patch('thinkmark.utils.url.slugify')
    def test_url_to_filename_directory(self, mock_slugify):
        """Test URL to directory name conversion."""
        mock_slugify.side_effect = lambda x: x.lower().replace('.', '-')
        
        url = "https://docs.example.com"
        result = url_to_filename(url, is_dir=True)
        
        assert result == "docs-example-com"
        assert mock_slugify.call_count == 1
    
    @patch('thinkmark.utils.url.slugify')
    def test_url_to_filename_no_path(self, mock_slugify):
        """Test URL with no path component."""
        mock_slugify.side_effect = lambda x: x.lower().replace('.', '-')
        
        url = "https://example.com"
        result = url_to_filename(url)
        
        assert result == "example-com.html"
    
    @patch('thinkmark.utils.url.slugify')
    def test_url_to_filename_complex_path(self, mock_slugify):
        """Test URL with complex path."""
        mock_slugify.side_effect = lambda x: x.lower().replace('.', '-').replace('/', '-')
        
        url = "https://docs.example.com/api/v1/endpoints"
        result = url_to_filename(url)
        
        assert result == "docs-example-com-api-v1-endpoints.html"
    
    @patch('thinkmark.utils.url.slugify')
    def test_url_to_filename_no_netloc(self, mock_slugify):
        """Test URL with no netloc (fallback to 'site')."""
        mock_slugify.side_effect = lambda x: x.lower()
        
        url = "/relative/path"
        result = url_to_filename(url)
        
        assert result == "site-relative-path.html"
    
    @patch('thinkmark.utils.url.slugify')
    def test_url_to_filename_trailing_slash(self, mock_slugify):
        """Test URL with trailing slash in path."""
        mock_slugify.side_effect = lambda x: x.lower().replace('.', '-')
        
        url = "https://example.com/path/"
        result = url_to_filename(url)
        
        assert result == "example-com-path.html"


class TestGetSiteDirectory:
    """Test cases for site directory path generation."""
    
    @patch('thinkmark.utils.url.url_to_filename')
    def test_get_site_directory_no_base(self, mock_url_to_filename):
        """Test site directory generation without base directory."""
        mock_url_to_filename.return_value = "example-com"
        
        url = "https://example.com"
        result = get_site_directory(url)
        
        assert result == "example-com"
        mock_url_to_filename.assert_called_once_with(url, is_dir=True)
    
    @patch('thinkmark.utils.url.url_to_filename')
    def test_get_site_directory_with_base(self, mock_url_to_filename):
        """Test site directory generation with base directory."""
        mock_url_to_filename.return_value = "example-com"
        
        url = "https://example.com"
        base_dir = "/tmp/output"
        result = get_site_directory(url, base_dir)
        
        # Result should be absolute path
        assert result.endswith("/tmp/output/example-com")
        mock_url_to_filename.assert_called_once_with(url, is_dir=True)
    
    @patch('thinkmark.utils.url.url_to_filename')
    def test_get_site_directory_relative_base(self, mock_url_to_filename):
        """Test site directory generation with relative base directory."""
        mock_url_to_filename.return_value = "docs-example-com"
        
        url = "https://docs.example.com"
        base_dir = "output"
        result = get_site_directory(url, base_dir)
        
        # Result should be absolute path
        assert result.endswith("/output/docs-example-com")
        assert result.startswith("/")
        mock_url_to_filename.assert_called_once_with(url, is_dir=True)


class TestUrlUtilsIntegration:
    """Integration tests for URL utilities."""
    
    def test_normalize_and_filter_workflow(self):
        """Test typical workflow of normalizing then filtering URLs."""
        # URLs that might come from web scraping
        urls = [
            "https://docs.example.com/guide/#introduction",
            "https://docs.example.com/api/",
            "https://blog.example.com/post",
            "https://docs.example.com/private/internal#notes"
        ]
        
        # Normalize URLs
        normalized = [normalize_url(url) for url in urls]
        expected_normalized = [
            "https://docs.example.com/guide",
            "https://docs.example.com/api",
            "https://blog.example.com/post",
            "https://docs.example.com/private/internal"
        ]
        assert normalized == expected_normalized
        
        # Filter URLs
        allowed_domains = ["docs.example.com"]
        include_paths = ["/guide", "/api"]
        exclude_paths = ["/private"]
        
        filtered = [
            url for url in normalized
            if is_url_allowed(
                url,
                allowed_domains=allowed_domains,
                include_paths=include_paths,
                exclude_paths=exclude_paths
            )
        ]
        
        expected_filtered = [
            "https://docs.example.com/guide",
            "https://docs.example.com/api"
        ]
        assert filtered == expected_filtered