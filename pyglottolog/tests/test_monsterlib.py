# coding: utf8
from __future__ import unicode_literals, print_function, division

from nose.tools import assert_almost_equal, assert_equal
from clldutils.testing import WithTempDir, capture
from clldutils.path import copytree, Path


class Tests(WithTempDir):
    def setUp(self):
        WithTempDir.setUp(self)
        copytree(Path(__file__).parent.joinpath('data'), self.tmp_path('repos'))
        self.references = self.tmp_path('repos', 'references')

    def test_Collection(self):
        from pyglottolog.monsterlib._bibfiles import Collection
        from pyglottolog.monsterlib._bibfiles_db import Database

        c = Collection(self.references.joinpath('bibtex'))
        with capture(c.check_all) as out:
            self.assertNotIn('invalid', out)
        with capture(c.roundtrip_all) as out:
            self.assertIn('a.bib', out)
        with capture(c['b.bib'].show_characters) as out:
            self.assertIn('CJK UNIFIED IDEOGRAPH', out)
        abib = c[0]
        self.assertEqual(len(list(abib.iterentries())), 2)
        assert abib.size
        assert abib.mtime

        db = self.tmp_path('test.sqlite').as_posix()
        with capture(c.to_sqlite, db) as out:
            self.assertIn('entries total', out)
        with capture(c.to_sqlite, db) as out:
            pass
        with capture(c.to_sqlite, db, rebuild=True) as out:
            pass

        db = Database(db)
        with capture(db.recompute, reload_priorities=c) as out:
            pass
        db.to_bibfile(self.tmp_path('out.bib'))
        db.to_csvfile(self.tmp_path('out.csv'))
        db.to_replacements(self.tmp_path('out.json'))
        self.assertEqual(db.to_hhmapping(), {})
        db.trickle(c)
        key, (entrytype, fields) = db[('b.bib', 'arakawa97')]
        self.assertEqual(entrytype, 'article')
        self.assertEqual(fields['volume'], '16')
        with capture(db.stats) as out:
            pass

        for attr in ['splits', 'merges', 'identified', 'combined']:
            with capture(getattr(db, 'show_' + attr)) as out:
                pass

    def test_load_trigger(self):
        from pyglottolog.monsterlib._libmonster import load_triggers

        load_triggers(self.references.joinpath('hhtype.ini'))

    def test_markconcservative(self):
        from pyglottolog.monsterlib._libmonster import markconservative

        markconservative(
            {1: ('article', {'title': 'Grammar'})},
            {('hhtype', 'grammar'): [[(True, 'grammar')]]},
            {1: ('article', {'title': 'Grammar'})},
            outfn=self.tmp_path('marks.txt'),
            verbose=False)


def test_ulatex_decode():
    from pyglottolog.monsterlib._bibtex_escaping import ulatex_decode

    for i, o in [
        ("", ""),
        ("a\\^o\=\,b", "aôb̦̄"),
        ("Luise\\~no", "Luiseño"),
        ("\\textdoublevertline", "‖"),
        ("\\url{abcdefg}", "abcdefg"),
        ("\\textdoublegrave{o}", "\u020d"),
        ("\\textsubu{\\'{v}}a", "v\u032e\u0301a"),
    ]:
        assert_equal(ulatex_decode(i), o)


def test_distance():
    from pyglottolog.monsterlib._bibfiles_db import distance

    assert_almost_equal(distance({}, {}), 0)
    d1 = dict(author='An Author', year='1998', title='The Title', ENTRYTYPE='article')
    for d2, dist in [
        ({}, 1.0),
        (d1, 0),
        (dict(author='An Author'), 0),
        (dict(author='Another Author'), 0.2173),
        (dict(author='An Author', title='Another Title'), 0.13636),
    ]:
        assert_almost_equal(distance(d1, d2), dist, places=3)


def test_markall():
    from pyglottolog.monsterlib._libmonster import markall

    with capture(markall, {}, {}) as out:
        assert 'updates 0' in out

    res = markall(
        {1: ('article', {'title': 'Grammar'})},
        {('hhtype', 'grammar'): [[(True, 'grammar')]]},
        verbose=False)
    assert res[1][1]['hhtype'] == 'grammar (computerized assignment from "grammar")'


def test_add_inlg_e():
    from pyglottolog.monsterlib._libmonster import add_inlg_e, INLG

    res = add_inlg_e(
        {1: ('article', {'title': 'Grammar of Abc'})},
        {(INLG, 'Abc [abc]'): [[(True, 'abc')]]},
        verbose=False)
    assert_equal(res[1][1][INLG], 'Abc [abc]')


def test_roman():
    from pyglottolog.monsterlib._libmonster import romanint, introman

    assert_equal(introman(5), 'v')
    assert_equal(introman(8), 'viii')
    for i in range(2000):
        assert_equal(romanint(introman(i)), i)


def test_keyid():
    from pyglottolog.monsterlib._libmonster import keyid

    for fields, res in [
        ({}, '__missingcontrib__'),
        (dict(author='An Author'), 'author_no-titlend'),
        (dict(editor='An Author'), 'author_no-titlend'),
        (dict(author='An Author', title='A rather long title'), 'author_rather-longnd'),
        (dict(author='An Author', title='Title', year='2014'), 'author_title2014'),
        (dict(author='An Author', volume='IV'), 'author_no-titleivnd'),
        (dict(author='An Author', extra_hash='a'), 'author_no-titlenda'),
    ]:
        assert_equal(keyid(fields, {}), res)

    with capture(keyid, dict(author='An Author and '), {}) as out:
        assert 'Unparsed' in out


def test_pagecount():
    from pyglottolog.monsterlib._libmonster import pagecount

    for pages, res in [
        ('', ''),
        ('1', '1'),
        ('10-20', '11'),
        ('10-20,v-viii', '4+11'),
    ]:
        assert_equal(pagecount(pages), res)


def test_lgcode():
    from pyglottolog.monsterlib._libmonster import lgcode

    for lgcode_, codes in [
        ('', []),
        ('[abc]', ['abc']),
        ('abc,NOCODE_Abc', ['abc', 'NOCODE_Abc']),
    ]:
        assert_equal(lgcode((None, dict(lgcode=lgcode_))), codes)