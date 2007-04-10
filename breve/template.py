#! /usr/bin/python
'''
breve - A simple s-expression style template engine inspired by Nevow's Stan.

        Stan was too heavily tied to Nevow and Twisted (which in turn added too
        many heavy dependencies) to allow Stan to be used as a standalone template
        engine in other frameworks. Plus there were some concepts (inheritance) that
        required too much hacking in Stan.
'''

import os, sys
from urllib2 import urlopen, URLError
from breve.util import Namespace, Curval
from breve.tags import Proto, Tag, xml, invisible, cdata, conditionals
from breve.tags.entities import entities
from breve.flatten import flatten, register_flattener, registry
from breve.loaders import FileLoader
from breve.cache import Cache
from breve.globals import _globals
import breve.render

try:
    import tidy as tidylib
except ImportError:
    tidylib = None

_cache = Cache ( )
_loader = FileLoader ( )

class Template ( object ):

    tidy = False
    debug = False
    namespace = ''
    mashup_entities = False  # set to True for old 1.0 behaviour
    loaders = [ _loader ]
    
    def __init__ ( T, tags, root = '.', xmlns = None, doctype = '', **kw ):
        '''
        Uses "T" rather than "self" to avoid confusion with
        subclasses that refer to this class via scoping (see
        the "inherits" class for one example).
        '''        
        class inherits ( Tag ):
            def __str__ ( self ):
                return T.render_partial ( template = self.name, fragments = self.children )

        class slot ( object ):
            def __init__ ( self, name ):
                self.name = name

            def __str__ ( self ):
                return xml ( flatten (
                    T.fragments.get ( self.name, 'slot named "%s" not filled' % self.name )
                ) )

        def preamble ( **kw ):
            T.__dict__.update ( kw )
            return ''

        T.root = root
        T.xmlns = xmlns
        T.xml_encoding = '''<?xml version="1.0" encoding="UTF-8"?>'''
        T.extension = 'b' # default template extension
        T.doctype = doctype
        T.fragments = { }
        T.vars = Namespace ( { 'xmlns': xmlns, } )
        T.tags = { 'cdata': cdata,
                   'xml': xml,
                   'invisible': invisible,
                   'include': T.include,
                   'xinclude': T.xinclude,
                   'inherits': inherits,
                   'override': T.override,
                   'slot': slot,
                   'curval': Curval,
                   'preamble': preamble }
        if T.mashup_entities:
            T.tags.update ( entities )
        T.tags.update ( E = entities ) # fallback in case of name clashes
        T.tags.update ( conditionals )
        T.tags.update ( tags )

    class override ( Tag ): 
        def __str__ ( self ):
            if self.children:
                return ( u''.join ( [ flatten ( c ) for c in self.children ] ) )
            return u''

    def include ( T, filename, vars = None, loader = None ):
        return xml ( T.render_partial ( template = filename, loader = loader ) )

    def xinclude ( T, url, timeout = 300 ):
        def fetch ( url ):
            try:
                return urlopen ( url ).read ( )
            except URLError, e:
                return "Error loading %s: %s" % ( url, e )
        return xml ( _cache.memoize ( url, timeout, fetch, url ) )

    def render_partial ( T, template, fragments = None, vars = None, loader = None, **kw ):
        if loader:
            T.loaders.append ( loader )
            
        if fragments:
            for f in fragments:
                if f.name not in T.fragments:
                    T.fragments [ f.name ] = f

        T.vars.update ( {
            'sequence': breve.render.sequence,
            'mapping': breve.render.mapping
        } )

        if vars:
            ns = kw.get ( 'namespace', T.namespace )
            if ns:
                T.vars [ ns ] = Namespace ( )
                T.vars [ ns ].update ( _globals )
                T.vars [ ns ].update ( vars )
            else:
                T.vars.update ( _globals )
                T.vars.update ( vars )
        else:
            T.vars.update ( _globals )

        filename = "%s.%s" % ( template, T.extension )
        output = u''
        
        try:
            bytecode = _cache.compile ( filename, T.root, T.loaders [ -1 ] )
            output = flatten ( eval ( bytecode, T.tags, T.vars ) )
        except:
            if T.debug:
                return T.debug_out ( sys.exc_info ( )[ :-1 ], filename )
            else:
                print "Error in template ( %s )" % template
                raise
        else:
            if loader:
                T.loaders.pop ( ) # restore the previous loader
            
        if T.tidy and tidylib:
            options = dict ( input_xml = True,
                             output_xhtml = True,
                             add_xml_decl = False,
                             doctype = 'omit',
                             indent = 'auto',
                             tidy_mark = False,
                             input_encoding = 'utf8' )
            return unicode ( tidylib.parseString ( output.encode ( 'utf-8' ), **options ) )
        else:
            return output

    def render ( T, template, vars = None, loader = None, **kw ):
        if loader:
            T.loaders.append ( loader )
        T.vars.update ( vars )
        output = T.render_partial ( template, vars = vars )
        return u'\n'.join ( [ T.xml_encoding, T.doctype, output ] )

    def debug_out ( T, exc_info, filename ):
        import sys, types, pydoc                
        ( etype, evalue )= exc_info

        exception = [
            '<span class="template_exception">',
            'Error in template: %s %s: %s' %
            ( filename,
              pydoc.html.escape ( str ( etype ) ),
              pydoc.html.escape ( str ( evalue ) ) )
        ]
        if type ( evalue ) is types.InstanceType:
            for name in dir ( evalue ):
                if name [ :1 ] == '_' or name == 'args': continue
                value = pydoc.html.repr ( getattr ( evalue, name ) )
                exception.append ( '\n<br />%s&nbsp;=\n%s' % ( name, value ) )
        exception.append ( '</span>' )
        return xml ( ''.join ( exception ) )
            
