# -*- coding: utf-8 -*-
"""
    werkzeug.testsuite.formparser
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Tests the form parsing facilities.

    :copyright: (c) 2011 by Armin Ronacher.
    :license: BSD, see LICENSE for more details.
"""



import unittest
from io import BytesIO
from os.path import join, dirname

from werkzeug.testsuite import WerkzeugTestCase

from werkzeug import formparser
from werkzeug.test import create_environ, Client
from werkzeug.wrappers import Request, Response
from werkzeug.exceptions import RequestEntityTooLarge


@Request.application
def form_data_consumer(request):
    result_object = request.args['object']
    if result_object == 'text':
        return Response(repr(request.form['text']))
    f = request.files[result_object]
    return Response(b'\n'.join((
        repr(f.filename).encode('ascii'),
        repr(f.name).encode('ascii'),
        repr(f.content_type).encode('ascii'),
        f.stream.read()
    )))


def get_contents(filename):
    f = open(filename, 'rb')
    try:
        return f.read()
    finally:
        f.close()


class FormParserTestCase(WerkzeugTestCase):

    def test_limiting(self):
        data = b'foo=Hello+World&bar=baz'
        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='application/x-www-form-urlencoded',
                                  method='POST')
        req.max_content_length = 400
        self.assert_equal(req.form['foo'], 'Hello World')

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='application/x-www-form-urlencoded',
                                  method='POST')
        req.max_form_memory_size = 7
        self.assert_raises(RequestEntityTooLarge, lambda: req.form['foo'])

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='application/x-www-form-urlencoded',
                                  method='POST')
        req.max_form_memory_size = 400
        self.assert_equal(req.form['foo'], 'Hello World')

        data = ('--foo\r\nContent-Disposition: form-field; name=foo\r\n\r\n'
                'Hello World\r\n'
                '--foo\r\nContent-Disposition: form-field; name=bar\r\n\r\n'
                'bar=baz\r\n--foo--').encode('ascii')
        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_content_length = 4
        self.assert_raises(RequestEntityTooLarge, lambda: req.form['foo'])

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_content_length = 400
        self.assert_equal(req.form['foo'], 'Hello World')

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_form_memory_size = 7
        self.assert_raises(RequestEntityTooLarge, lambda: req.form['foo'])

        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        req.max_form_memory_size = 400
        self.assert_equal(req.form['foo'], 'Hello World')

    def test_parse_form_data_put_without_content(self):
        # A PUT without a Content-Type header returns empty data

        # Both rfc1945 and rfc2616 (1.0 and 1.1) say "Any HTTP/[1.0/1.1] message
        # containing an entity-body SHOULD include a Content-Type header field
        # defining the media type of that body."  In the case where either
        # headers are omitted, parse_form_data should still work.
        env = create_environ('/foo', 'http://example.org/', method='PUT')
        del env['CONTENT_TYPE']
        del env['CONTENT_LENGTH']

        stream, form, files = formparser.parse_form_data(env)
        self.assert_equal(stream.read(), b'')
        self.assert_equal(len(form), 0)
        self.assert_equal(len(files), 0)

    def test_parse_form_data_get_without_content(self):
        env = create_environ('/foo', 'http://example.org/', method='GET')
        del env['CONTENT_TYPE']
        del env['CONTENT_LENGTH']

        stream, form, files = formparser.parse_form_data(env)
        self.assert_equal(stream.read(), b'')
        self.assert_equal(len(form), 0)
        self.assert_equal(len(files), 0)

    def test_large_file(self):
        data = b'x' * (1024 * 600)
        req = Request.from_values(data={'foo': (BytesIO(data), 'test.txt')},
                                  method='POST')
        # make sure we have a real file here, because we expect to be
        # on the disk.  > 1024 * 500
        # XXX: can't test it in Python 3
#        self.assertTrue(isinstance(req.files['foo'].stream, file))


class MultiPartTestCase(WerkzeugTestCase):

    def test_basic(self):
        resources = join(dirname(__file__), 'multipart')
        client = Client(form_data_consumer, Response)

        repository = [
            ('firefox3-2png1txt', '---------------------------186454651713519341951581030105', [
                ('anchor.png', 'file1', 'image/png', 'file1.png'),
                ('application_edit.png', 'file2', 'image/png', 'file2.png')
            ], 'example text'),
            ('firefox3-2pnglongtext', '---------------------------14904044739787191031754711748', [
                ('accept.png', 'file1', 'image/png', 'file1.png'),
                ('add.png', 'file2', 'image/png', 'file2.png')
            ], '--long text\r\n--with boundary\r\n--lookalikes--'),
            ('opera8-2png1txt', '----------zEO9jQKmLc2Cq88c23Dx19', [
                ('arrow_branch.png', 'file1', 'image/png', 'file1.png'),
                ('award_star_bronze_1.png', 'file2', 'image/png', 'file2.png')
            ], 'blafasel öäü'),
            ('webkit3-2png1txt', '----WebKitFormBoundaryjdSFhcARk8fyGNy6', [
                ('gtk-apply.png', 'file1', 'image/png', 'file1.png'),
                ('gtk-no.png', 'file2', 'image/png', 'file2.png')
            ], 'this is another text with ümläüts'),
            ('ie6-2png1txt', '---------------------------7d91b03a20128', [
                ('file1.png', 'file1', 'image/x-png', 'file1.png'),
                ('file2.png', 'file2', 'image/x-png', 'file2.png')
            ], 'ie6 sucks :-/')
        ]

        for name, boundary, files, text in repository:
            folder = join(resources, name)
            data = get_contents(join(folder, 'request.txt'))
            for filename, field, content_type, fsname in files:
                response = client.post('/?object=' + field, data=data, content_type=
                                       'multipart/form-data; boundary="%s"' % boundary,
                                       content_length=len(data))
                lines = response.data.split(b'\n', 3)
                self.assert_equal(lines[0], repr(filename).encode('ascii'))
                self.assert_equal(lines[1], repr(field).encode('ascii'))
                self.assert_equal(lines[2], repr(content_type).encode('ascii'))
                self.assert_equal(lines[3], get_contents(join(folder, fsname)))
            response = client.post('/?object=text', data=data, content_type=
                                   'multipart/form-data; boundary="%s"' % boundary,
                                   content_length=len(data))
            self.assert_equal(response.data, repr(text).encode('utf-8'))

    def test_ie7_unc_path(self):
        client = Client(form_data_consumer, Response)
        data_file = join(dirname(__file__), 'multipart', 'ie7_full_path_request.txt')
        data = get_contents(data_file)
        boundary = '---------------------------7da36d1b4a0164'
        response = client.post('/?object=cb_file_upload_multiple', data=data, content_type=
                                   'multipart/form-data; boundary="%s"' % boundary, content_length=len(data))
        lines = response.data.split(b'\n', 3)
        self.assert_equal(lines[0],
                          repr('Sellersburg Town Council Meeting 02-22-2010doc.doc').encode('ascii'))

    def test_end_of_file(self):
        # This test looks innocent but it was actually timeing out in
        # the Werkzeug 0.5 release version (#394)
        data = (
            '--foo\r\n'
            'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n'
            'Content-Type: text/plain\r\n\r\n'
            'file contents and no end'
        ).encode('ascii')
        data = Request.from_values(input_stream=BytesIO(data),
                                   content_length=len(data),
                                   content_type='multipart/form-data; boundary=foo',
                                   method='POST')
        self.assertTrue(not data.files)
        self.assertTrue(not data.form)

    def test_broken(self):
        data = (
            '--foo\r\n'
            'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n'
            'Content-Transfer-Encoding: base64\r\n'
            'Content-Type: text/plain\r\n\r\n'
            'broken base 64'
            '--foo--'
        ).encode('ascii')
        _, form, files = formparser.parse_form_data(create_environ(data=data,
            method='POST', content_type='multipart/form-data; boundary=foo'))
        self.assertTrue(not files)
        self.assertTrue(not form)

        self.assert_raises(ValueError, formparser.parse_form_data,
            create_environ(data=data, method='POST',
                      content_type='multipart/form-data; boundary=foo'),
                      silent=False)

    def test_file_no_content_type(self):
        data = (
            '--foo\r\n'
            'Content-Disposition: form-data; name="test"; filename="test.txt"\r\n\r\n'
            'file contents\r\n--foo--'
        ).encode('ascii')
        data = Request.from_values(input_stream=BytesIO(data),
                                   content_length=len(data),
                                   content_type='multipart/form-data; boundary=foo',
                                   method='POST')
        self.assert_equal(data.files['test'].filename, 'test.txt')
        self.assert_equal(data.files['test'].read(), b'file contents')

    def test_extra_newline(self):
        # this test looks innocent but it was actually timeing out in
        # the Werkzeug 0.5 release version (#394)
        data = (
            '\r\n\r\n--foo\r\n'
            'Content-Disposition: form-data; name="foo"\r\n\r\n'
            'a string\r\n'
            '--foo--'
        ).encode('ascii')
        data = Request.from_values(input_stream=BytesIO(data),
                                   content_length=len(data),
                                   content_type='multipart/form-data; boundary=foo',
                                   method='POST')
        self.assertTrue(not data.files)
        self.assert_equal(data.form['foo'], 'a string')

    def test_headers(self):
        data = ('--foo\r\n'
                'Content-Disposition: form-data; name="foo"; filename="foo.txt"\r\n'
                'X-Custom-Header: blah\r\n'
                'Content-Type: text/plain; charset=utf-8\r\n\r\n'
                'file contents, just the contents\r\n'
                '--foo--').encode('ascii')
        req = Request.from_values(input_stream=BytesIO(data),
                                  content_length=len(data),
                                  content_type='multipart/form-data; boundary=foo',
                                  method='POST')
        foo = req.files['foo']
        self.assert_equal(foo.mimetype, 'text/plain')
        self.assert_equal(foo.mimetype_params, {'charset': 'utf-8'})
        self.assert_equal(foo.headers['content-type'], foo.content_type)
        self.assert_equal(foo.content_type, 'text/plain; charset=utf-8')
        self.assert_equal(foo.headers['x-custom-header'], 'blah')

    def test_nonstandard_line_endings(self):
        for nl in '\n', '\r', '\r\n':
            data = nl.join((
                '--foo',
                'Content-Disposition: form-data; name=foo',
                '',
                'this is just bar',
                '--foo',
                'Content-Disposition: form-data; name=bar',
                '',
                'blafasel',
                '--foo--'
            )).encode('ascii')
            req = Request.from_values(input_stream=BytesIO(data),
                                      content_length=len(data),
                                      content_type='multipart/form-data; '
                                      'boundary=foo', method='POST')
            self.assert_equal(req.form['foo'], 'this is just bar')
            self.assert_equal(req.form['bar'], 'blafasel')

    def test_failures(self):
        def parse_multipart(stream, boundary, content_length):
            parser = formparser.MultiPartParser(content_length)
            return parser.parse(stream, boundary, content_length)
        self.assert_raises(ValueError, parse_multipart, BytesIO(b''), '', 0)
        self.assert_raises(ValueError, parse_multipart, BytesIO(b''), 'broken  ', 0)

        data = b'--foo\r\n\r\nHello World\r\n--foo--'
        self.assert_raises(ValueError, parse_multipart, BytesIO(data), 'foo', len(data))

        data = b'--foo\r\nContent-Disposition: form-field; name=foo\r\n' \
               b'Content-Transfer-Encoding: base64\r\n\r\nHello World\r\n--foo--'
        self.assert_raises(ValueError, parse_multipart, BytesIO(data), 'foo', len(data))

        data = b'--foo\r\nContent-Disposition: form-field; name=foo\r\n\r\nHello World\r\n'
        self.assert_raises(ValueError, parse_multipart, BytesIO(data), 'foo', len(data))

        x = formparser.parse_multipart_headers(['foo: bar\r\n', ' x test\r\n'])
        self.assert_equal(x['foo'], 'bar\n x test')
        self.assert_raises(ValueError, formparser.parse_multipart_headers,
                           ['foo: bar\r\n', ' x test'])

    def test_bad_newline_bad_newline_assumption(self):
        class ISORequest(Request):
            charset = 'latin1'
        contents = b'U2vlbmUgbORu'
        data = b'--foo\r\nContent-Disposition: form-data; name="test"\r\n' \
               b'Content-Transfer-Encoding: base64\r\n\r\n' + \
               contents + b'\r\n--foo--'
        req = ISORequest.from_values(input_stream=BytesIO(data),
                                     content_length=len(data),
                                     content_type='multipart/form-data; boundary=foo',
                                     method='POST')
        self.assert_equal(req.form['test'], 'Sk\xe5ne l\xe4n')


class InternalFunctionsTestCase(WerkzeugTestCase):

    def test_lien_parser(self):
        assert formparser._line_parse('foo') == ('foo', False)
        assert formparser._line_parse('foo\r\n') == ('foo', True)
        assert formparser._line_parse('foo\r') == ('foo', True)
        assert formparser._line_parse('foo\n') == ('foo', True)

    def test_find_terminator(self):
        lineiter = iter('\n\n\nfoo\nbar\nbaz'.splitlines(True))
        find_terminator = formparser.MultiPartParser()._find_terminator
        line = find_terminator(lineiter)
        assert line == 'foo'
        assert list(lineiter) == ['bar\n', 'baz']
        assert find_terminator([]) == ''
        assert find_terminator(['']) == ''


def suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(FormParserTestCase))
    suite.addTest(unittest.makeSuite(MultiPartTestCase))
    suite.addTest(unittest.makeSuite(InternalFunctionsTestCase))
    return suite
