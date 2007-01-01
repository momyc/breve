from breve.flatten import flatten, register_flattener
import _conditionals as C

conditionals = dict ( [
    ( k, v ) for k, v in C.__dict__.items ( )
    if not k.startswith ( '_' )
] )

class Proto ( str ):
    __slots__ = [ ]
    def __call__ ( self, **kwargs ):
        return Tag ( self )( **kwargs )
    
    def __getitem__ ( self, children ):
        return Tag ( self )[ children ]

def flatten_proto ( p ):
    return '<%s />' % p

register_flattener ( Proto, flatten_proto )


class Tag ( object ):
    def __init__ ( self, name, *args, **kwargs ):
        self.name = name
        self.children = [ ]
        self.attrs = { }
        self.render = None
        self.data = None

    def __call__ ( self, render = None, data = None, *args, **kwargs ):
        self.render = render
        self.data = data
        for k, v in kwargs.items ( ):
            if k [ -1 ] == '_':
                self.attrs [ k [ :-1 ] ] = v
            else:
                self.attrs [ k ] = v
        self.args = args
        return self

    def __getitem__ ( self, k ):
        if type ( k ) in ( tuple, list ):
            self.children.extend ( list ( k ) )
        else:
            self.children.append ( k )
        return self
    
    def __str__ ( self ):
        if self.render:
            self.children = [ ]
            return str ( self.render ( self, self.data ) )

        attrs = ''.join (
            [ ' %s="%s"' % ( k, v )
              for ( k, v ) in self.attrs.items ( ) ]
        )
        if self.children:
            return ( '<%s%s>' % ( self.name, attrs ) +
                     ''.join ( [ flatten ( c ) for c in self.children ] ) +  
                     '</%s>' % self.name )
        return '<%s%s />' % ( self.name, attrs )
