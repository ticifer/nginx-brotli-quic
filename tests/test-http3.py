import asyncio, ssl
from aioquic.asyncio import connect, QuicConnectionProtocol
from aioquic.quic.configuration import QuicConfiguration
from aioquic.h3.connection import H3Connection, H3_ALPN
from aioquic.h3.events import HeadersReceived, DataReceived
class Client(QuicConnectionProtocol):
    def __init__(self,*a,**kw):
        super().__init__(*a,**kw); self.http=H3Connection(self._quic); self.done=asyncio.get_running_loop().create_future(); self.status=None; self.body=b''
    def quic_event_received(self,event):
        for ev in self.http.handle_event(event):
            if isinstance(ev,HeadersReceived):
                self.status=dict(ev.headers).get(b':status',self.status)
            if isinstance(ev,DataReceived): self.body+=ev.data
            if getattr(ev,'stream_ended',False) and not self.done.done(): self.done.set_result((self.status,self.body))
async def main():
    config=QuicConfiguration(is_client=True,alpn_protocols=H3_ALPN); config.verify_mode=ssl.CERT_NONE
    async with connect('127.0.0.1',18443,configuration=config,create_protocol=Client) as c:
        sid=c._quic.get_next_available_stream_id()
        c.http.send_headers(sid,[(b':method',b'GET'),(b':scheme',b'https'),(b':authority',b'localhost'),(b':path',b'/')],end_stream=True); c.transmit()
        status,body=await asyncio.wait_for(c.done,10)
        assert status==b'200' and body, (status,body)
        print('HTTP/3 QUIC: 200 OK; body bytes=',len(body))
asyncio.run(main())
