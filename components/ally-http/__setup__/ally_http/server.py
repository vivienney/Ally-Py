'''
Created on Nov 23, 2011

@package: ally http
@copyright: 2012 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Runs the basic web server.
'''

from . import server_type, server_protocol, server_version, server_host, \
    server_port
from .processor import assemblyNotFound, connectionClose, connection
from ally.container import ioc
from ally.design.processor.assembly import Assembly
from ally.design.processor.handler import Handler
from ally.http.impl.processor.router_by_path import RoutingByPathHandler
from ally.http.server import server_basic
from threading import Thread

# --------------------------------------------------------------------

@ioc.entity
def assemblyServer() -> Assembly:
    '''
    The assembly used in processing the server requests.
    '''
    return Assembly('Server')

# --------------------------------------------------------------------

@ioc.entity
def serverBasicRequestHandler():
    return type('RequestHandler', (server_basic.RequestHandler,), {'protocol_version': server_protocol()})

@ioc.entity
def serverBasic():
    b = server_basic.BasicServer()
    b.serverVersion = server_version()
    b.serverHost = server_host()
    b.serverPort = server_port()
    b.requestHandlerFactory = serverBasicRequestHandler()
    b.assembly = assemblyServer()
    return b

# --------------------------------------------------------------------

@ioc.entity
def notFoundRouter() -> Handler:
    b = RoutingByPathHandler()
    b.assembly = assemblyNotFound()
    b.pattern = '(?:.*)'
    return b

# --------------------------------------------------------------------

@ioc.before(assemblyServer)
def updateAssemblyServerForProtocolSupport():
    if server_protocol() >= 'HTTP/1.1':
        if server_type() == 'basic': assemblyServer().add(connectionClose())
        # For the basic version we don't need the ensure length because is closing the connection anyway.
        else: assemblyServer().add(connection())
    
@ioc.after(updateAssemblyServerForProtocolSupport)
def updateAssemblyServer():
    assemblyServer().add(notFoundRouter())

# --------------------------------------------------------------------

@ioc.start
def runServer():
    if server_type() == 'basic':
        Thread(name='HTTP server thread', target=server_basic.run, args=(serverBasic(),)).start()
