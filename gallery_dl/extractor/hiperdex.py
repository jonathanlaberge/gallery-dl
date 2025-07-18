# -*- coding: utf-8 -*-

# Copyright 2020-2025 Mike Fährmann
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as
# published by the Free Software Foundation.

"""Extractors for https://hiperdex.com/"""

from .common import ChapterExtractor, MangaExtractor
from .. import text, util
from ..cache import memcache

BASE_PATTERN = (r"((?:https?://)?(?:www\.)?"
                r"(?:1st)?hiper(?:dex|toon)\d?\.(?:com|net|info|top))")


class HiperdexBase():
    """Base class for hiperdex extractors"""
    category = "hiperdex"
    root = "https://hiperdex.com"

    @memcache(keyarg=1)
    def manga_data(self, manga, page=None):
        if not page:
            url = "{}/manga/{}/".format(self.root, manga)
            page = self.request(url).text
        extr = text.extract_from(page)

        return {
            "url"    : text.unescape(extr(
                'property="og:url" content="', '"')),
            "manga"  : text.unescape(extr(
                ' property="name" title="', '"')),
            "score"  : text.parse_float(extr(
                'id="averagerate">', '<')),
            "author" : text.remove_html(extr(
                'class="author-content">', '</div>')),
            "artist" : text.remove_html(extr(
                'class="artist-content">', '</div>')),
            "genre"  : text.split_html(extr(
                'class="genres-content">', '</div>'))[::2],
            "type"   : extr(
                'class="summary-content">', '<').strip(),
            "release": text.parse_int(text.remove_html(extr(
                'class="summary-content">', '</div>'))),
            "status" : extr(
                'class="summary-content">', '<').strip(),
            "description": text.remove_html(text.unescape(extr(
                '<div class="description-summary">', "</div>"))),
            "language": "English",
            "lang"    : "en",
        }

    def chapter_data(self, chapter):
        if chapter.startswith("chapter-"):
            chapter = chapter[8:]
        chapter, _, minor = chapter.partition("-")
        data = {
            "chapter"      : text.parse_int(chapter),
            "chapter_minor": "." + minor if minor and minor != "end" else "",
        }
        data.update(self.manga_data(self.manga.lower()))
        return data


class HiperdexChapterExtractor(HiperdexBase, ChapterExtractor):
    """Extractor for hiperdex manga chapters"""
    pattern = BASE_PATTERN + r"(/mangas?/([^/?#]+)/([^/?#]+))"
    example = "https://hiperdex.com/manga/MANGA/CHAPTER/"

    def __init__(self, match):
        root, path, self.manga, self.chapter = match.groups()
        self.root = text.ensure_http_scheme(root)
        ChapterExtractor.__init__(self, match, self.root + path + "/")

    def metadata(self, _):
        return self.chapter_data(self.chapter)

    def images(self, page):
        pattern = util.re(r'id="image-\d+"\s+(?:data-)?src="([^"]+)')
        return [
            (url.strip(), None)
            for url in pattern.findall(page)
        ]


class HiperdexMangaExtractor(HiperdexBase, MangaExtractor):
    """Extractor for hiperdex manga"""
    chapterclass = HiperdexChapterExtractor
    pattern = BASE_PATTERN + r"(/mangas?/([^/?#]+))/?$"
    example = "https://hiperdex.com/manga/MANGA/"

    def __init__(self, match):
        root, path, self.manga = match.groups()
        self.root = text.ensure_http_scheme(root)
        MangaExtractor.__init__(self, match, self.root + path + "/")

    def chapters(self, page):
        data = self.manga_data(self.manga, page)
        self.page_url = url = data["url"]

        url = self.page_url + "ajax/chapters/"
        headers = {
            "Accept": "*/*",
            "X-Requested-With": "XMLHttpRequest",
            "Origin": self.root,
            "Referer": "https://" + text.quote(self.page_url[8:]),
        }
        html = self.request(url, method="POST", headers=headers).text

        results = []
        for item in text.extract_iter(
                html, '<li class="wp-manga-chapter', '</li>'):
            url = text.extr(item, 'href="', '"')
            chapter = url.rstrip("/").rpartition("/")[2]
            results.append((url, self.chapter_data(chapter)))
        return results


class HiperdexArtistExtractor(HiperdexBase, MangaExtractor):
    """Extractor for an artists's manga on hiperdex"""
    subcategory = "artist"
    categorytransfer = False
    chapterclass = HiperdexMangaExtractor
    reverse = False
    pattern = BASE_PATTERN + r"(/manga-a(?:rtist|uthor)/(?:[^/?#]+))"
    example = "https://hiperdex.com/manga-artist/NAME/"

    def __init__(self, match):
        self.root = text.ensure_http_scheme(match[1])
        MangaExtractor.__init__(self, match, self.root + match[2] + "/")

    def chapters(self, page):
        results = []
        for info in text.extract_iter(page, 'id="manga-item-', '<img'):
            url = text.extr(info, 'href="', '"')
            results.append((url, {}))
        return results
