"""Pinned data-only W045 decoder/compiler worker. Source/cache code is never run."""
import base64
import hashlib
import importlib.util
import io
import json
import marshal
import os
import re
import struct
import sys
import types

SCHEMA='ceta.w045.data-only.v1'
MAX_REQUEST=65536
MAX_RESPONSE=8192
CACHE_BYTES=10572
SOURCE_BYTES=6316
CACHE_SHA256='84d238316c9e49f83111c9f782080ca03b6e74c5f656c79587e129ba6b7ef29f'
SOURCE_SHA256='b7b4a33a9614167f04675f96511d7e73ff7dea3155e949bf4a08a33aeae80f17'
VERSION='3.11.9 (tags/v3.11.9:de54cf5, Apr  2 2024, 10:12:12) [MSC v.1938 64 bit (AMD64)]'
PRIVATE_MARKER=re.compile(br'-----BEGIN (?:[A-Z0-9 ]* )?PRIVATE KEY-----')
FIELDS=('co_argcount','co_posonlyargcount','co_kwonlyargcount','co_nlocals','co_stacksize','co_flags','co_code','co_names','co_varnames','co_freevars','co_cellvars','co_name','co_qualname','co_firstlineno','co_linetable','co_lnotab','co_exceptiontable')

class Rejected(Exception):
    def __init__(self,code):self.code=code

def require(condition,code):
    if not condition:raise Rejected(code)

def unique_pairs(pairs):
    result={}
    for name,value in pairs:
        require(name not in result,'REQUEST_DUPLICATE_FIELD');result[name]=value
    return result

def credential_like(value):
    cursor=0
    while True:
        start=value.find(b'://',cursor)
        if start<0:return False
        for index in range(start+3,len(value)):
            char=value[index:index+1]
            if char==b'@':return True
            if char in b'/?# \t\r\n':cursor=index+1;break
        else:return False

def literal_context(code):
    stack=[(code,0)];visited=markers=0
    while stack:
        value,depth=stack.pop();visited+=1
        require(depth<100 and visited<=100000,'LITERAL_LIMIT_EXCEEDED')
        if isinstance(value,types.CodeType):
            filename=value.co_filename.encode('utf-8')
            require(not PRIVATE_MARKER.search(filename) and not credential_like(filename),'CACHE_FILENAME_PROTECTED')
            stack.extend((item,depth+1) for item in value.co_consts)
        elif isinstance(value,(tuple,frozenset)):
            stack.extend((item,depth+1) for item in value)
        elif isinstance(value,(str,bytes)):
            literal=value.encode('utf-8') if isinstance(value,str) else value
            if PRIVATE_MARKER.search(literal):
                require(PRIVATE_MARKER.fullmatch(literal) is not None,'CACHE_MARKER_EXTENDED_CONTENT');markers+=1
    return markers

def compare(first,second):
    pairs={'code_pairs':0,'constant_pairs':0};visited=0
    def constants(a,b,depth):
        nonlocal visited
        visited+=1;pairs['constant_pairs']+=1
        require(depth<100 and visited<=100000,'STRUCTURE_LIMIT_EXCEEDED')
        if type(a) is not type(b):return False
        if isinstance(a,types.CodeType):return code(a,b,depth+1)
        if isinstance(a,tuple):return len(a)==len(b) and all(constants(x,y,depth+1) for x,y in zip(a,b))
        if isinstance(a,frozenset):
            # Compiled W045 has no code-bearing set constants. Reject unsupported
            # structural set values; never match through marshal encoding bytes.
            require(all(not isinstance(x,(types.CodeType,tuple,frozenset)) for x in a|b),'SET_CONSTANT_UNSUPPORTED')
            return {(type(value),value) for value in a}=={(type(value),value) for value in b}
        return a==b
    def code(a,b,depth):
        pairs['code_pairs']+=1
        require(depth<100 and pairs['code_pairs']<=10000,'CODE_LIMIT_EXCEEDED')
        return all(getattr(a,name)==getattr(b,name) for name in FIELDS) and len(a.co_consts)==len(b.co_consts) and all(constants(x,y,depth+1) for x,y in zip(a.co_consts,b.co_consts))
    return code(first,second,0),pairs

def inspect(request):
    require(os.name=='nt' and struct.calcsize('P')==8 and sys.version==VERSION,'WORKER_RUNTIME_IDENTITY')
    require(type(request) is dict and set(request)=={'schema','cache_base64','source_base64'} and request['schema']==SCHEMA,'REQUEST_SCHEMA')
    require(type(request['cache_base64']) is str and type(request['source_base64']) is str,'REQUEST_FIELD_TYPE')
    require(len(request['cache_base64'])==((CACHE_BYTES+2)//3)*4 and len(request['source_base64'])==((SOURCE_BYTES+2)//3)*4,'REQUEST_BOUND')
    cache=base64.b64decode(request['cache_base64'],validate=True);source=base64.b64decode(request['source_base64'],validate=True)
    require(len(cache)==CACHE_BYTES and hashlib.sha256(cache).hexdigest()==CACHE_SHA256,'CACHE_IDENTITY')
    require(len(source)==SOURCE_BYTES and hashlib.sha256(source).hexdigest()==SOURCE_SHA256,'SOURCE_IDENTITY')
    require(cache[:4]==importlib.util.MAGIC_NUMBER==bytes.fromhex('a70d0d0a'),'CACHE_MAGIC')
    require(struct.unpack_from('<I',cache,4)[0]==0 and struct.unpack_from('<I',cache,12)[0]==SOURCE_BYTES,'CACHE_HEADER')
    stream=io.BytesIO(cache[16:]);code=marshal.load(stream)
    require(stream.tell()==len(cache)-16 and isinstance(code,types.CodeType),'CACHE_BODY')
    markers=literal_context(code);require(markers==2,'CACHE_MARKER_COUNT')
    levels=[];measurements=[]
    for level in (0,1,2):
        compiled=compile(source,'<bound-historical-source>','exec',dont_inherit=True,optimize=level)
        equal,pairs=compare(code,compiled)
        require(equal,'CACHE_STRUCTURE_MISMATCH');levels.append(level);measurements.append({'optimization':level,**pairs})
    return {'schema':SCHEMA,'ok':True,'error_code':None,'cache_sha256':CACHE_SHA256,'source_sha256':SOURCE_SHA256,
            'cache_bytes':CACHE_BYTES,'source_bytes':SOURCE_BYTES,'magic_hex':'a70d0d0a','header_flags':0,'marshal_all_body_consumed':True,
            'matching_compile_levels':levels,'comparisons':measurements,'private_marker_constants_validated':markers,
            'filename_excluded_from_equivalence':True,'marshal_reference_encoding_excluded':True,'source_or_cache_execution':False}

def main():
    try:
        raw=sys.stdin.buffer.read(MAX_REQUEST+1);require(len(raw)<=MAX_REQUEST,'REQUEST_BOUND')
        request=json.loads(raw.decode('utf-8'),object_pairs_hook=unique_pairs,parse_constant=lambda _:(_ for _ in ()).throw(Rejected('REQUEST_NUMBER')))
        result=inspect(request)
    except Rejected as error:result={'schema':SCHEMA,'ok':False,'error_code':error.code}
    except (ValueError,TypeError,EOFError,SyntaxError,RecursionError,UnicodeError,MemoryError,OverflowError):result={'schema':SCHEMA,'ok':False,'error_code':'DATA_FORMAT_REJECTED'}
    except BaseException:result={'schema':SCHEMA,'ok':False,'error_code':'WORKER_INTERNAL_ERROR'}
    output=json.dumps(result,separators=(',',':'),allow_nan=False).encode('utf-8')
    if len(output)>MAX_RESPONSE:output=b'{"schema":"ceta.w045.data-only.v1","ok":false,"error_code":"RESPONSE_BOUND"}'
    sys.stdout.buffer.write(output);sys.stdout.buffer.flush()
    return 0 if result.get('ok') is True else 2

if __name__=='__main__':raise SystemExit(main())
