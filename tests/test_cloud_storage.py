import io
import unittest
from unittest.mock import patch

import httpx
from fastapi import HTTPException, UploadFile
from pypdf import PdfWriter
from backend.app.core.config import settings
from backend.app.services.storage import save_pdf, download_stored, remove_stored


class CloudStorageTests(unittest.TestCase):
    def test_private_round_trip_and_invalid_pdf(self):
        writer = PdfWriter()
        writer.add_blank_page(width=72, height=72)
        data = io.BytesIO()
        writer.write(data)
        objects = {}

        def request(method, url, **kwargs):
            name = url.rsplit('/', 1)[-1]
            self.assertIn('Bearer ', kwargs['headers']['Authorization'])
            if method == 'POST':
                objects[name] = kwargs['content']
                return httpx.Response(200)
            if method == 'GET':
                return httpx.Response(200, content=objects[name])
            del objects[name]
            return httpx.Response(200)

        with patch.object(settings, 'storage_backend', 'supabase'), \
             patch.object(settings, 'supabase_url', 'https://example.supabase.co'), \
             patch.object(settings, 'supabase_service_role_key', 'test-secret'), \
             patch('backend.app.services.storage.httpx.request', side_effect=request):
            name, size = save_pdf(UploadFile(file=io.BytesIO(data.getvalue()), filename='x.pdf'))
            self.assertEqual(size, len(data.getvalue()))
            self.assertEqual(download_stored(name), data.getvalue())
            remove_stored(name)
            self.assertFalse(objects)
            with self.assertRaises(HTTPException) as exc:
                save_pdf(UploadFile(file=io.BytesIO(b'not a PDF'), filename='x.pdf'))
            self.assertEqual(exc.exception.status_code, 415)


if __name__ == '__main__':
    unittest.main()
