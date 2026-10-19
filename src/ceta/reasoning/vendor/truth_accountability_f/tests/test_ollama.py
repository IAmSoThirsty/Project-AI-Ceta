import json
import unittest
from truth_accountability import LocalOllamaProposalClient


class FakeResponse:
    def __init__(self, raw): self.raw=raw
    def read(self, maxbytes): return self.raw[:maxbytes]
    def __enter__(self): return self
    def __exit__(self,typ,value,tb): return False


class FakeOpener:
    def __init__(self,raw): self.raw=raw; self.req=None
    def open(self,req,timeout): self.req=req; return FakeResponse(self.raw)


class OllamaTransportTest(unittest.TestCase):
    def test_local_only_transport_refuses_remote(self):
        for url in ("https://example.com:11434","http://192.168.1.1:11434",
                    "http://localhost:11434@evil.org:80","http://localhost:11434/api/generate",
                    "http://localhost", "http://localhost:11434/?x=1"):
            with self.subTest(url=url), self.assertRaises(ValueError):
                LocalOllamaProposalClient(model="local-model",endpoint=url)

    def test_untrusted_local_response_remains_proposal(self):
        body=json.dumps({"response":"{\"kind\":\"fact\",\"text\":\"2 + 2 = 5\"}"}).encode()
        fake=FakeOpener(body)
        client=LocalOllamaProposalClient(model="some-installed-model",opener=fake)
        proposal=client.generate_proposal("record-id","What is 2+2?")
        self.assertIn("2 + 2 = 5",proposal)
        self.assertTrue(fake.req.full_url.endswith("/api/generate"))
        self.assertEqual(json.loads(fake.req.data)["format"],"json")

    def test_malformed_response_fails_closed(self):
        fake=FakeOpener(b'{"not_response":true}')
        client=LocalOllamaProposalClient(model="m",opener=fake)
        with self.assertRaises(ValueError):
            client.generate_proposal("id","a")

    def test_oversize_response_fails_closed(self):
        fake=FakeOpener(b"x"*65537)
        client=LocalOllamaProposalClient(model="m",opener=fake)
        with self.assertRaises(ValueError):
            client.generate_proposal("id","a")


if __name__=="__main__": unittest.main()
