'''
Created on Mar 18, 2013

@package: ally core
@copyright: 2011 Sourcefabric o.p.s.
@license: http://www.gnu.org/licenses/gpl-3.0.txt
@author: Gabriel Nistor

Provides the model property encoder.
'''

from ally.api.operator.container import Model
from ally.api.operator.type import TypeModel, TypeModelProperty
from ally.container.ioc import injected
from ally.core.spec.resources import Normalizer
from ally.core.spec.transform.encoder import IEncoder, EncoderWithSpecifiers
from ally.core.spec.transform.index import NAME_BLOCK
from ally.core.spec.transform.render import IRender
from ally.design.cache import CacheWeak
from ally.design.processor.assembly import Assembly
from ally.design.processor.attribute import requires, defines, optional
from ally.design.processor.branch import Branch
from ally.design.processor.context import Context
from ally.design.processor.execution import Processing
from ally.design.processor.handler import HandlerBranching
from ally.exception import DevelError

# --------------------------------------------------------------------

class Create(Context):
    '''
    The create encoder context.
    '''
    # ---------------------------------------------------------------- Defined
    encoder = defines(IEncoder, doc='''
    @rtype: IEncoder
    The encoder for the model.
    ''')
    # ---------------------------------------------------------------- Optional
    name = optional(str)
    specifiers = optional(list)
    # ---------------------------------------------------------------- Required
    objType = requires(object)
    
class Support(Context):
    '''
    The encoder support context.
    '''
    # ---------------------------------------------------------------- Optional
    hideProperties = optional(bool)
    # ---------------------------------------------------------------- Required
    normalizer = requires(Normalizer)

class CreateProperty(Context):
    '''
    The create property encoder context.
    '''
    # ---------------------------------------------------------------- Defined
    name = defines(str, doc='''
    @rtype: string
    The name used to render the property with.
    ''')
    objType = defines(object, doc='''
    @rtype: object
    The property type.
    ''')
    # ---------------------------------------------------------------- Required
    encoder = requires(IEncoder)
    
# --------------------------------------------------------------------

@injected
class ModelPropertyEncode(HandlerBranching):
    '''
    Implementation for a handler that provides the model property encoding.
    '''
    
    propertyEncodeAssembly = Assembly
    # The encode processors to be used for encoding properties.
    
    def __init__(self):
        assert isinstance(self.propertyEncodeAssembly, Assembly), \
        'Invalid property encode assembly %s' % self.propertyEncodeAssembly
        super().__init__(Branch(self.propertyEncodeAssembly).included().using(create=CreateProperty), support=Support)
        
        self._cache = CacheWeak()
        
    def process(self, chain, propertyProcessing, create:Create, **keyargs):
        '''
        @see: HandlerBranching.process
        
        Create the model property encoder.
        '''
        assert isinstance(propertyProcessing, Processing), 'Invalid processing %s' % propertyProcessing
        assert isinstance(create, Create), 'Invalid create %s' % create
        
        if create.encoder is not None: return 
        # There is already an encoder, nothing to do.
        if not isinstance(create.objType, TypeModelProperty): return
        # The type is not for a model, nothing to do, just move along
        propType = create.objType
        assert isinstance(propType, TypeModelProperty)
        modelType = propType.parent
        assert isinstance(modelType, TypeModel)
        assert isinstance(modelType.container, Model)
        
        if Create.name in create and create.name: name = create.name
        else: name = modelType.container.name
        if Create.specifiers in create: specifiers = create.specifiers or ()
        else: specifiers = ()
        
        cache = self._cache.key(propertyProcessing, name, propType, *specifiers)
        if not cache.has:
            arg = propertyProcessing.execute(create=propertyProcessing.ctx.create(objType=propType, name=propType.property),
                                             **keyargs)
            assert isinstance(arg.create, CreateProperty), 'Invalid create property %s' % arg.create
            if arg.create.encoder is None: raise DevelError('Cannot encode %s' % propType)
            cache.value = EncoderModelProperty(name, arg.create.encoder, specifiers)
        
        create.encoder = cache.value

# --------------------------------------------------------------------

class EncoderModelProperty(EncoderWithSpecifiers):
    '''
    Implementation for a @see: IEncoder for model property.
    '''
    
    def __init__(self, name, encoder, specifiers=None):
        '''
        Construct the model property encoder.
        '''
        assert isinstance(name, str), 'Invalid model name %s' % name
        assert isinstance(encoder, IEncoder), 'Invalid property encoder %s' % encoder
        super().__init__(specifiers)
        
        self.name = name
        self.encoder = encoder
        
    def render(self, obj, render, support):
        '''
        @see: IEncoder.render
        '''
        assert isinstance(render, IRender), 'Invalid render %s' % render
        assert isinstance(support, Support), 'Invalid support %s' % support
        assert isinstance(support.normalizer, Normalizer), 'Invalid normalizer %s' % support.normalizer
        
        if Support.hideProperties in support: hideProperties = support.hideProperties
        else: hideProperties = False
            
        render.beginObject(support.normalizer.normalize(self.name), **self.populate(obj, support, indexBlock=NAME_BLOCK))
        if not hideProperties: self.encoder.render(obj, render, support)
        render.end()
