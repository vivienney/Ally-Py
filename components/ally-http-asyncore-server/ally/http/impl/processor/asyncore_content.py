'''
Created on Nov 1, 2012

@package: ally http
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the asyncore handling of content.
'''

from ally.container.ioc import injected
from ally.design.processor.attribute import defines, requires
from ally.design.processor.context import Context
from ally.design.processor.execution import Chain
from ally.design.processor.handler import HandlerProcessor
from ally.support.util_io import IInputStream, IOutputStream
from ally.zip.util_zip import normOSPath
from collections import Callable
from genericpath import isdir
from io import BytesIO
import os
import time

# --------------------------------------------------------------------

class Request(Context):
    '''
    The request context.
    '''
    # ---------------------------------------------------------------- Required
    method = requires(str) 
    
class RequestContent(Context):
    '''
    The request content context.
    '''
    # ---------------------------------------------------------------- Required
    length = requires(int)
    # ---------------------------------------------------------------- Defined
    contentReader = defines(Callable)
    contentRequired = defines(bool)
    source = defines(IInputStream)

class Response(Context):
    '''
    The response context.
    '''
    # ---------------------------------------------------------------- Optional
    isSuccess = requires(bool)
    
# --------------------------------------------------------------------

@injected
class AsyncoreContentHandler(HandlerProcessor):
    '''
    Provides asyncore content handling, basically this handler buffers up the async data received in order to be
    used by the other handlers.
    '''
    dumpRequestsSize = 1024 * 1024
    # The minimum size of the request length to be dumped on the file system.
    dumpRequestsPath = str
    # The path where the requests are dumped when they are to big to keep in memory.
    
    def __init__(self):
        assert isinstance(self.dumpRequestsSize, int), 'Invalid dump size %s' % self.dumpRequestsSize
        assert isinstance(self.dumpRequestsPath, str), 'Invalid dump path %s' % self.dumpRequestsPath
        self.dumpRequestsPath = normOSPath(self.dumpRequestsPath)
        if not os.path.exists(self.dumpRequestsPath): os.makedirs(self.dumpRequestsPath)
        assert isdir(self.dumpRequestsPath) and os.access(self.dumpRequestsPath, os.W_OK), \
        'Unable to access the dump directory %s' % self.dumpRequestsPath
        super().__init__()
        
        self._count = 0

    def process(self, chain, request:Request, requestCnt:RequestContent, response:Response, **keyargs):
        '''
        @see: HandlerProcessor.process
        
        Provide the headers encoders and decoders.
        '''
        assert isinstance(chain, Chain), 'Invalid chain %s' % chain
        assert isinstance(request, Request), 'Invalid request %s' % request
        assert isinstance(requestCnt, RequestContent), 'Invalid request content %s' % requestCnt
        assert isinstance(response, Response), 'Invalid response %s' % response
        
        if response.isSuccess is False: return  # Skip in case the response is in error
        
        if not requestCnt.length:
            requestCnt.contentRequired = False  # No length or content.
        elif requestCnt.length > self.dumpRequestsSize:
            tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec, *_rest = time.localtime()
            path = 'request_%s_%s-%s-%s_%s-%s-%s' % (self._count, tm_year, tm_mon, tm_mday, tm_hour, tm_min, tm_sec)
            self._count += 1
            requestCnt.contentReader = readerInFile(chain, requestCnt, path)
            requestCnt.contentRequired = True
        else:
            requestCnt.contentReader = readerInMemory(requestCnt)
            requestCnt.contentRequired = True

# --------------------------------------------------------------------

def reader(stream, callBack, length):
    '''
    Provides the reader in stream with finalizing call back.
    '''
    assert isinstance(stream, IOutputStream), 'Invalid stream %s' % stream
    assert callable(callBack), 'Invalid call back %s' % callBack
    assert length is None or isinstance(length, int), 'Invalid length %s' % length
    
    size = 0
    def read(data):
        nonlocal size, stream
        assert stream is not None, 'Reader is finalized'
        assert isinstance(stream, IOutputStream)
        
        if data != b'':
            size += len(data)
            if length is not None:
                if size > length:
                    dif = size - length
                    size = length
                    data = memoryview(data)
                    ret = data[dif:]
                    stream.write(data[:dif])
                else:
                    stream.write(data)
                    if size == length: ret = None
                    else: ret = True
            else:
                stream.write(data)
                ret = True
            
        if data == b'' or ret is not True:
            callBack()
            stream = None
        return ret
    
    return read

def readerInMemory(requestCnt):
    '''
    Provides the reader in memory.
    '''
    assert isinstance(requestCnt, RequestContent), 'Invalid request content %s' % requestCnt
    stream = BytesIO()
    def callBack():
        assert isinstance(requestCnt, RequestContent)
        stream.seek(0)
        requestCnt.source = stream
        requestCnt.contentReader = None
    return reader(stream, callBack, requestCnt.length)

def readerInFile(chain, requestCnt, path):
    '''
    Provides the reader in file.
    '''
    assert isinstance(chain, Chain), 'Invalid chain %s' % chain
    assert isinstance(requestCnt, RequestContent), 'Invalid request content %s' % requestCnt
    stream = open(path, mode='wb')
    def processRemove(final, **keyargs):
        '''
        Remove the buffer file on finalization.
        '''
        stream.close()
        os.remove(path)
    chain.onFinalize(processRemove)

    def callBack():
        assert isinstance(requestCnt, RequestContent)
        nonlocal stream
        stream.close()
        stream = requestCnt.source = open(path, mode='rb')
        requestCnt.contentReader = None
    return reader(stream, callBack, requestCnt.length)
