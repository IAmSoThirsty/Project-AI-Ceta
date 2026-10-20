// Bounded allocation fence around the already selected SQLite win32 VFS.
// Public SQLite VFS v3 ABI declarations; no second SQLite engine or writer.
// Interfaces: sqlite.org/c3ref/vfs.html and sqlite.org/c3ref/io_methods.html.
#define WIN32_LEAN_AND_MEAN
#define NOMINMAX
#include <windows.h>
#include <psapi.h>
#include <algorithm>
#include <atomic>
#include <cstdint>
#include <cstring>
#include <memory>
#include <mutex>
#include <new>
#include <string>
#include <unordered_map>

using i64 = long long;
struct sqlite3_file;
struct sqlite3_io_methods {
    int iVersion;
    int (*xClose)(sqlite3_file*);
    int (*xRead)(sqlite3_file*,void*,int,i64);
    int (*xWrite)(sqlite3_file*,const void*,int,i64);
    int (*xTruncate)(sqlite3_file*,i64);
    int (*xSync)(sqlite3_file*,int);
    int (*xFileSize)(sqlite3_file*,i64*);
    int (*xLock)(sqlite3_file*,int);
    int (*xUnlock)(sqlite3_file*,int);
    int (*xCheckReservedLock)(sqlite3_file*,int*);
    int (*xFileControl)(sqlite3_file*,int,void*);
    int (*xSectorSize)(sqlite3_file*);
    int (*xDeviceCharacteristics)(sqlite3_file*);
    int (*xShmMap)(sqlite3_file*,int,int,int,void volatile**);
    int (*xShmLock)(sqlite3_file*,int,int,int);
    void (*xShmBarrier)(sqlite3_file*);
    int (*xShmUnmap)(sqlite3_file*,int);
    int (*xFetch)(sqlite3_file*,i64,int,void**);
    int (*xUnfetch)(sqlite3_file*,i64,void*);
};
struct sqlite3_file { const sqlite3_io_methods* pMethods; };
using sqlite3_syscall_ptr=void(*)(void);
struct sqlite3_vfs {
    int iVersion,szOsFile,mxPathname;
    sqlite3_vfs* pNext;
    const char* zName;
    void* pAppData;
    int (*xOpen)(sqlite3_vfs*,const char*,sqlite3_file*,int,int*);
    int (*xDelete)(sqlite3_vfs*,const char*,int);
    int (*xAccess)(sqlite3_vfs*,const char*,int,int*);
    int (*xFullPathname)(sqlite3_vfs*,const char*,int,char*);
    void* (*xDlOpen)(sqlite3_vfs*,const char*);
    void (*xDlError)(sqlite3_vfs*,int,char*);
    void (*(*xDlSym)(sqlite3_vfs*,void*,const char*))(void);
    void (*xDlClose)(sqlite3_vfs*,void*);
    int (*xRandomness)(sqlite3_vfs*,int,char*);
    int (*xSleep)(sqlite3_vfs*,int);
    int (*xCurrentTime)(sqlite3_vfs*,double*);
    int (*xGetLastError)(sqlite3_vfs*,int,char*);
    int (*xCurrentTimeInt64)(sqlite3_vfs*,i64*);
    int (*xSetSystemCall)(sqlite3_vfs*,const char*,sqlite3_syscall_ptr);
    sqlite3_syscall_ptr (*xGetSystemCall)(sqlite3_vfs*,const char*);
    const char* (*xNextSystemCall)(sqlite3_vfs*,const char*);
};
constexpr int OK=0,BUSY=5,NOMEM=7,IOERR=10,FULL=13,MISUSE=21,NOTFOUND=12;
constexpr int MAIN_DB=0x100,WAL=0x80000;
constexpr uint64_t MAX_TOTAL=64ULL*1024*1024;
enum State:uint32_t { IDLE,ALLOCATING,RETAINED,FAILED,CLOSED };
enum Close:uint32_t { ABSENT,OPEN,UNCERTAIN,RETIRED };
struct FileFacts {
    uint64_t handle,volume,allocation,eof,limit;
    unsigned char identifier[16];
    uint32_t close_state,close_error,post_close_error,attributes;
};
struct Snapshot {
    uint32_t version,state,reason,winerror;
    uint64_t generation,write_calls,sync_calls,db_highwater,wal_highwater,shm_highwater;
    uint32_t open_files,winerror_known;
    FileFacts files[3];
    FileFacts mapped_shm_probe;
};
struct Owner;
struct CapFile { sqlite3_file outer; Owner* owner; sqlite3_file* real; int kind; };
struct Owner {
    sqlite3_vfs vfs{};
    sqlite3_vfs* base=nullptr;
    int (*unregister_vfs)(sqlite3_vfs*)=nullptr;
    std::string name;
    std::recursive_mutex mutex;
    State state=IDLE;
    uint32_t reason=0,winerror=0;
    bool winerror_known=false;
    uint64_t generation=0,writes=0,syncs=0,db_high=0,wal_high=0,shm_high=0;
    unsigned opens=0;
    CapFile* main=nullptr;
    CapFile* wal=nullptr;
    std::wstring database;
    void volatile* shm_first=nullptr;
    FileFacts slots[3]{};
    FileFacts shm_probe{};
    bool registered=false;
};
static_assert(offsetof(Owner,vfs)==0);
std::mutex registry_mutex;
std::unordered_map<uint64_t,std::unique_ptr<Owner>> registry;
uint64_t next_id=1;

static Owner* find(uint64_t id) {
    auto at=registry.find(id);
    return at==registry.end()?nullptr:at->second.get();
}
static int fail(Owner& o,int reason,DWORD error=0,bool known=false) {
    if(o.state!=FAILED) {o.reason=static_cast<uint32_t>(reason);o.winerror=error;o.winerror_known=known;}
    o.state=FAILED;
    return reason;
}
static int facts(HANDLE h,FileFacts& f) {
    FILE_STANDARD_INFO standard{};FILE_ID_INFO identity{};FILE_ATTRIBUTE_TAG_INFO attributes{};
    if(!GetFileInformationByHandleEx(h,FileStandardInfo,&standard,sizeof(standard)) ||
       !GetFileInformationByHandleEx(h,FileIdInfo,&identity,sizeof(identity)) ||
       !GetFileInformationByHandleEx(h,FileAttributeTagInfo,&attributes,sizeof(attributes)))return IOERR;
    if(standard.Directory || standard.DeletePending || standard.NumberOfLinks!=1 ||
       (attributes.FileAttributes&(FILE_ATTRIBUTE_REPARSE_POINT|FILE_ATTRIBUTE_SPARSE_FILE|FILE_ATTRIBUTE_COMPRESSED)) ||
       attributes.ReparseTag || standard.AllocationSize.QuadPart<standard.EndOfFile.QuadPart)return MISUSE;
    f.volume=identity.VolumeSerialNumber;std::memcpy(f.identifier,identity.FileId.Identifier,16);
    f.allocation=static_cast<uint64_t>(standard.AllocationSize.QuadPart);
    f.eof=static_cast<uint64_t>(standard.EndOfFile.QuadPart);f.attributes=attributes.FileAttributes;
    return OK;
}
static bool same(const FileFacts& a,const FileFacts& b) {
    return a.volume==b.volume && std::memcmp(a.identifier,b.identifier,16)==0;
}
static int measure(Owner& o,int index) {
    auto& slot=o.slots[index];FileFacts actual{};
    if(slot.close_state!=OPEN)return fail(o,MISUSE);
    int rc=facts(reinterpret_cast<HANDLE>(slot.handle),actual);
    if(rc!=OK)return fail(o,rc,rc==IOERR?GetLastError():0,rc==IOERR);
    if(!same(slot,actual))return fail(o,IOERR);
    slot.allocation=actual.allocation;slot.eof=actual.eof;
    if(actual.allocation<slot.limit || actual.eof>slot.limit)return fail(o,FULL);
    return OK;
}
static int allocation(Owner& o,int index) {
    auto& slot=o.slots[index];FILE_ALLOCATION_INFO amount{};
    amount.AllocationSize.QuadPart=static_cast<LONGLONG>(slot.limit);
    if(!SetFileInformationByHandle(reinterpret_cast<HANDLE>(slot.handle),FileAllocationInfo,&amount,sizeof(amount)))return fail(o,IOERR,GetLastError(),true);
    if(!FlushFileBuffers(reinterpret_cast<HANDLE>(slot.handle)))return fail(o,IOERR,GetLastError(),true);
    return measure(o,index);
}
static int boundary(CapFile* file,int amount,i64 offset) {
    auto& o=*file->owner;
    if(o.state==IDLE)return OK;
    if(o.state!=RETAINED)return o.state==ALLOCATING?BUSY:IOERR;
    if(file->kind<0 || amount<0 || offset<0)return fail(o,MISUSE);
    auto size=static_cast<uint64_t>(amount),start=static_cast<uint64_t>(offset);
    if(start>o.slots[file->kind].limit || size>o.slots[file->kind].limit-start)return fail(o,FULL);
    return measure(o,file->kind);
}
static int xClose(sqlite3_file* raw) {
    auto* f=reinterpret_cast<CapFile*>(raw);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    // SQLite retires its sqlite3_file storage even after an xClose error. Always
    // retire the delegated owner; refusing here would abandon its live handle.
    bool unexpected=o.state==RETAINED || o.state==ALLOCATING;
    if(unexpected)fail(o,IOERR);
    int rc=f->real->pMethods->xClose(f->real);
    if(rc!=OK)fail(o,rc);
    if(o.main==f)o.main=nullptr;if(o.wal==f)o.wal=nullptr;
    if(o.opens)o.opens--;raw->pMethods=nullptr;
    return unexpected && rc==OK?IOERR:rc;
}
static int xRead(sqlite3_file* r,void* data,int n,i64 at) {
    auto* f=reinterpret_cast<CapFile*>(r);return f->real->pMethods->xRead(f->real,data,n,at);
}
static int xWrite(sqlite3_file* r,const void* data,int n,i64 at) {
    auto* f=reinterpret_cast<CapFile*>(r);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    int rc=boundary(f,n,at);if(rc!=OK)return rc;
    rc=f->real->pMethods->xWrite(f->real,data,n,at);o.writes++;
    if(o.state==RETAINED) {
        if(rc!=OK)return fail(o,rc);
        uint64_t high=static_cast<uint64_t>(at)+static_cast<uint64_t>(n);
        (f->kind==0?o.db_high:o.wal_high)=std::max(f->kind==0?o.db_high:o.wal_high,high);
        return measure(o,f->kind);
    }
    return rc;
}
static int xTruncate(sqlite3_file* r,i64 size) {
    auto* f=reinterpret_cast<CapFile*>(r);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    int rc=boundary(f,0,size);if(rc!=OK)return rc;
    rc=f->real->pMethods->xTruncate(f->real,size);
    if(o.state==RETAINED) {
        if(rc!=OK)return fail(o,rc);
        // NTFS truncation may release allocation. No successful VFS return is
        // published until that same file's bounded allocation is restored.
        return allocation(o,f->kind);
    }
    return rc;
}
static int xSync(sqlite3_file* r,int flags) {
    auto* f=reinterpret_cast<CapFile*>(r);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    if(o.state==FAILED)return IOERR;
    int rc=f->real->pMethods->xSync(f->real,flags);o.syncs++;
    if(o.state==RETAINED && rc!=OK)return fail(o,rc);
    return rc;
}
#define FORWARD1(name,T) static int name(sqlite3_file* r,T a){auto* f=reinterpret_cast<CapFile*>(r);return f->real->pMethods->name(f->real,a);}
FORWARD1(xFileSize,i64*)
FORWARD1(xLock,int)
FORWARD1(xUnlock,int)
FORWARD1(xCheckReservedLock,int*)
static int xControl(sqlite3_file* r,int op,void* arg) {
    auto* f=reinterpret_cast<CapFile*>(r);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    if(op==23 || op==43)return MISUSE; // No replacement handle or NULL_IO bypass.
    if(o.state==RETAINED) {
        if(op==5)return OK; // Advisory SIZE_HINT is superseded by actual allocation.
        if(op==6 || (op==18 && *static_cast<i64*>(arg)>0))return MISUSE;
    }
    return f->real->pMethods->xFileControl(f->real,op,arg);
}
static int xSector(sqlite3_file* r){auto* f=reinterpret_cast<CapFile*>(r);return f->real->pMethods->xSectorSize(f->real);}
static int xDevice(sqlite3_file* r){auto* f=reinterpret_cast<CapFile*>(r);return f->real->pMethods->xDeviceCharacteristics(f->real);}
static int xShmMap(sqlite3_file* r,int page,int size,int extend,void volatile** out) {
    auto* f=reinterpret_cast<CapFile*>(r);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    if(o.state==FAILED)return IOERR;
    if(o.state==RETAINED) {
        if(page<0 || size<=0 || (static_cast<uint64_t>(page)+1)>o.slots[2].limit/static_cast<uint64_t>(size))return fail(o,FULL);
        int rc=measure(o,2);if(rc!=OK)return rc;
        o.shm_high=std::max(o.shm_high,(static_cast<uint64_t>(page)+1)*static_cast<uint64_t>(size));
    }
    int rc=f->real->pMethods->xShmMap(f->real,page,size,extend,out);
    if(rc==OK && page==0 && *out)o.shm_first=*out;
    if(o.state==RETAINED) {
        if(rc!=OK)return fail(o,rc);
        return measure(o,2);
    }
    return rc;
}
static int xShmLock(sqlite3_file* r,int offset,int n,int flags){auto* f=reinterpret_cast<CapFile*>(r);return f->real->pMethods->xShmLock(f->real,offset,n,flags);}
static void xShmBarrier(sqlite3_file* r){auto* f=reinterpret_cast<CapFile*>(r);f->real->pMethods->xShmBarrier(f->real);}
static int xShmUnmap(sqlite3_file* r,int del){
    auto* f=reinterpret_cast<CapFile*>(r);auto& o=*f->owner;std::lock_guard lock(o.mutex);
    bool unexpected=o.state==RETAINED || o.state==ALLOCATING;
    if(unexpected)fail(o,IOERR);
    int rc=f->real->pMethods->xShmUnmap(f->real,del);o.shm_first=nullptr;
    return unexpected && rc==OK?IOERR:rc;
}
static int xFetch(sqlite3_file*,i64,int,void** out){*out=nullptr;return OK;} // Read through xRead, not a bypassing mapping.
static int xUnfetch(sqlite3_file*,i64,void*){return OK;}
static const sqlite3_io_methods methods={3,xClose,xRead,xWrite,xTruncate,xSync,xFileSize,xLock,xUnlock,xCheckReservedLock,
    xControl,xSector,xDevice,xShmMap,xShmLock,xShmBarrier,xShmUnmap,xFetch,xUnfetch};
static int xOpen(sqlite3_vfs* v,const char* name,sqlite3_file* raw,int flags,int* out) {
    try {
    auto& o=*reinterpret_cast<Owner*>(v);auto* f=reinterpret_cast<CapFile*>(raw);
    raw->pMethods=nullptr;f->owner=&o;f->kind=(flags&MAIN_DB)?0:(flags&WAL)?1:-1;
    f->real=reinterpret_cast<sqlite3_file*>(reinterpret_cast<unsigned char*>(raw)+((sizeof(CapFile)+15)&~size_t(15)));
    std::lock_guard lock(o.mutex);
    if(o.state!=IDLE || (f->kind==0 && o.main) || (f->kind==1 && o.wal))return BUSY;
    int rc=o.base->xOpen(o.base,name,f->real,flags,out);
    if(f->real->pMethods) {
        if(f->real->pMethods->iVersion!=3){f->real->pMethods->xClose(f->real);f->real->pMethods=nullptr;return MISUSE;}
        raw->pMethods=&methods;o.opens++;
        if(f->kind==0) {
            o.main=f;
            int count=name?MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,name,-1,nullptr,0):0;
            if(count<=1 || count>32767)return MISUSE;
            o.database.resize(static_cast<size_t>(count));
            MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,name,-1,o.database.data(),count);
            o.database.resize(static_cast<size_t>(count-1));
        }
        if(f->kind==1)o.wal=f;
    }
    return rc;
    }catch(const std::bad_alloc&){return NOMEM;}catch(...){return IOERR;}
}
static int xDelete(sqlite3_vfs* v,const char* name,int sync) {
    auto& o=*reinterpret_cast<Owner*>(v);std::lock_guard lock(o.mutex);
    if(o.state==RETAINED || o.state==ALLOCATING)return fail(o,IOERR);
    return o.base->xDelete(o.base,name,sync);
}
// Use the base object's address for base VFS methods; its implementation may
// legitimately depend on more than the public fields copied into our wrapper.
static int xAccess(sqlite3_vfs* v,const char* n,int f,int* out){auto& o=*reinterpret_cast<Owner*>(v);return o.base->xAccess(o.base,n,f,out);}
static int xFullPath(sqlite3_vfs* v,const char* n,int count,char* out){auto& o=*reinterpret_cast<Owner*>(v);return o.base->xFullPathname(o.base,n,count,out);}
static int noSystemCall(sqlite3_vfs*,const char*,sqlite3_syscall_ptr){return MISUSE;}
static sqlite3_syscall_ptr noGetSystemCall(sqlite3_vfs*,const char*){return nullptr;}
static const char* noNextSystemCall(sqlite3_vfs*,const char*){return nullptr;}
static void snapshot(const Owner& o,Snapshot& out) {
    out={};out.version=1;out.state=o.state;out.reason=o.reason;out.winerror=o.winerror;
    out.generation=o.generation;out.write_calls=o.writes;out.sync_calls=o.syncs;
    out.db_highwater=o.db_high;out.wal_highwater=o.wal_high;out.shm_highwater=o.shm_high;out.open_files=o.opens;
    out.winerror_known=o.winerror_known?1:0;
    std::memcpy(out.files,o.slots,sizeof(out.files));
    out.mapped_shm_probe=o.shm_probe;
}
#define EXPORT extern "C" __declspec(dllexport) int __cdecl
EXPORT ceta_capacity_abi(uint32_t* version,uint32_t* bytes) noexcept {
    if(!version||!bytes)return MISUSE;*version=1;*bytes=sizeof(Snapshot);return OK;
}
EXPORT ceta_capacity_create(const wchar_t* sqlite_path,const char* name,uint64_t* id) noexcept {
    try {
        if(!sqlite_path || !name || !id)return MISUSE;
        size_t length=strnlen_s(name,96);if(length<24 || length>=96)return MISUSE;
        for(size_t n=0;n<length;n++)if(!(name[n]>='a'&&name[n]<='z') && !(name[n]>='0'&&name[n]<='9') && name[n]!='_')return MISUSE;
        HMODULE sqlite=GetModuleHandleW(sqlite_path);if(!sqlite)return MISUSE;
        auto version=reinterpret_cast<int(*)()>(GetProcAddress(sqlite,"sqlite3_libversion_number"));
        auto find_vfs=reinterpret_cast<sqlite3_vfs*(*)(const char*)>(GetProcAddress(sqlite,"sqlite3_vfs_find"));
        auto reg=reinterpret_cast<int(*)(sqlite3_vfs*,int)>(GetProcAddress(sqlite,"sqlite3_vfs_register"));
        auto unreg=reinterpret_cast<int(*)(sqlite3_vfs*)>(GetProcAddress(sqlite,"sqlite3_vfs_unregister"));
        if(!version||!find_vfs||!reg||!unreg||version()!=3053004)return MISUSE;
        auto* base=find_vfs("win32");if(!base||base->iVersion!=3||base->szOsFile<=0||base->szOsFile>65536)return MISUSE;
        auto owner=std::make_unique<Owner>();owner->name=name;owner->base=base;owner->unregister_vfs=unreg;
        owner->vfs=*base;owner->vfs.pNext=nullptr;owner->vfs.zName=owner->name.c_str();
        owner->vfs.szOsFile=static_cast<int>(((sizeof(CapFile)+15)&~size_t(15))+base->szOsFile);owner->vfs.xOpen=xOpen;
        owner->vfs.xDelete=xDelete;owner->vfs.xAccess=xAccess;owner->vfs.xFullPathname=xFullPath;
        owner->vfs.xSetSystemCall=noSystemCall;owner->vfs.xGetSystemCall=noGetSystemCall;
        owner->vfs.xNextSystemCall=noNextSystemCall;
        std::lock_guard lock(registry_mutex);
        if(registry.size()>=256 || find_vfs(name))return BUSY;
        uint64_t token=next_id++;
        auto [it,inserted]=registry.emplace(token,std::move(owner));if(!inserted)return MISUSE;
        int rc=reg(&it->second->vfs,0);if(rc!=OK){registry.erase(it);return rc;}
        it->second->registered=true;*id=token;return OK;
    }catch(const std::bad_alloc&){return NOMEM;}catch(...){return MISUSE;}
}
EXPORT ceta_capacity_state(uint64_t id,Snapshot* out) noexcept {
    if(!out)return MISUSE;std::unique_lock global(registry_mutex,std::try_to_lock);if(!global.owns_lock())return BUSY;
    auto* o=find(id);if(!o)return MISUSE;std::unique_lock local(o->mutex,std::try_to_lock);if(!local.owns_lock())return BUSY;
    snapshot(*o,*out);return OK; // No native query, SQL, allocation, blocking lock or wait.
}
EXPORT ceta_capacity_reserve(uint64_t id,uint64_t db,uint64_t wal,uint64_t shm,Snapshot* out) noexcept {
    try {
        if(!out||!db||!wal||!shm||db>MAX_TOTAL||wal>MAX_TOTAL-db||shm>MAX_TOTAL-db-wal)return MISUSE;
        if((db|wal|shm)&65535)return MISUSE;
        std::unique_lock global(registry_mutex);auto* o=find(id);if(!o)return MISUSE;
        std::unique_lock local(o->mutex);global.unlock();
        if(o->state!=IDLE||!o->main||!o->wal||!o->shm_first||o->opens!=2)return BUSY;
        std::wstring paths[3]={o->database,o->database+L"-wal",o->database+L"-shm"};
        uint64_t limits[3]={db,wal,shm};o->state=ALLOCATING;o->generation++;o->reason=o->winerror=0;o->winerror_known=false;
        for(int i=0;i<3;i++) {
            auto& slot=o->slots[i];slot={};slot.limit=limits[i];
            HANDLE h=CreateFileW(paths[i].c_str(),GENERIC_READ|GENERIC_WRITE,FILE_SHARE_READ|FILE_SHARE_WRITE,nullptr,
                OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_WRITE_THROUGH,nullptr);
            if(h==INVALID_HANDLE_VALUE){fail(*o,IOERR,GetLastError(),true);snapshot(*o,*out);return IOERR;}
            slot.handle=reinterpret_cast<uint64_t>(h);slot.close_state=OPEN;
            if(facts(h,slot)!=OK || slot.eof>slot.limit || slot.allocation>slot.limit){fail(*o,MISUSE);snapshot(*o,*out);return MISUSE;}
            if(i<2) {
                HANDLE real=nullptr;auto* file=i==0?o->main:o->wal;
                FileFacts actual{};
                if(file->real->pMethods->xFileControl(file->real,29,&real)!=OK || facts(real,actual)!=OK || !same(slot,actual)){
                    fail(*o,MISUSE);snapshot(*o,*out);return MISUSE;}
                int chunk=0;
                if(file->real->pMethods->xFileControl(file->real,6,&chunk)!=OK){fail(*o,MISUSE);snapshot(*o,*out);return MISUSE;}
            }
            if(i==2) {
                // Derive the SHM name from SQLite's actual mapped address, then
                // compare that file's identity with the retained allocation.
                wchar_t mapped[32768]{};
                DWORD count=K32GetMappedFileNameW(GetCurrentProcess(),const_cast<void*>(o->shm_first),mapped,32768);
                if(!count || count>=32768 || mapped[0]!=L'\\'){fail(*o,MISUSE);snapshot(*o,*out);return MISUSE;}
                std::wstring selected=L"\\\\?\\GLOBALROOT";selected.append(mapped,count);
                HANDLE observed=CreateFileW(selected.c_str(),FILE_READ_ATTRIBUTES,FILE_SHARE_READ|FILE_SHARE_WRITE,
                    nullptr,OPEN_EXISTING,FILE_FLAG_OPEN_REPARSE_POINT,nullptr);
                if(observed==INVALID_HANDLE_VALUE){fail(*o,IOERR,GetLastError(),true);snapshot(*o,*out);return IOERR;}
                o->shm_probe={};o->shm_probe.handle=reinterpret_cast<uint64_t>(observed);o->shm_probe.close_state=OPEN;
                int measured=facts(observed,o->shm_probe);
                o->shm_probe.close_state=UNCERTAIN;SetLastError(0);
                BOOL retired=CloseHandle(observed);o->shm_probe.close_error=GetLastError();
                if(retired)o->shm_probe.close_state=RETIRED;
                if(!retired || measured!=OK || !same(slot,o->shm_probe)){fail(*o,MISUSE);snapshot(*o,*out);return MISUSE;}
            }
            if(i && slot.volume!=o->slots[0].volume){fail(*o,MISUSE);snapshot(*o,*out);return MISUSE;}
            int rc=allocation(*o,i);if(rc!=OK){snapshot(*o,*out);return rc;}
        }
        o->state=RETAINED;snapshot(*o,*out);return OK;
    }catch(const std::bad_alloc&){return NOMEM;}catch(...){return MISUSE;}
}
EXPORT ceta_capacity_measure(uint64_t id,Snapshot* out) noexcept {
    if(!out)return MISUSE;std::unique_lock global(registry_mutex);auto* o=find(id);if(!o)return MISUSE;
    std::unique_lock local(o->mutex);global.unlock();
    if(o->state!=RETAINED)return MISUSE;
    int result=OK;for(int i=0;i<3;i++){int rc=measure(*o,i);if(rc!=OK)result=rc;}
    snapshot(*o,*out);return result;
}
EXPORT ceta_capacity_release(uint64_t id,Snapshot* out) noexcept {
    if(!out)return MISUSE;std::unique_lock global(registry_mutex);auto* o=find(id);if(!o)return MISUSE;
    std::unique_lock local(o->mutex);global.unlock();
    if(o->state!=RETAINED&&o->state!=FAILED&&o->state!=ALLOCATING)return MISUSE;
    int result=OK;
    for(auto& slot:o->slots)if(slot.close_state==OPEN) {
        slot.close_state=UNCERTAIN;SetLastError(0);
        BOOL done=CloseHandle(reinterpret_cast<HANDLE>(slot.handle));slot.close_error=GetLastError();
        if(done) {
            slot.close_state=RETIRED;DWORD flags=0;SetLastError(0);
            BOOL still=GetHandleInformation(reinterpret_cast<HANDLE>(slot.handle),&flags);
            slot.post_close_error=still?0:GetLastError();
        }else result=IOERR;
    }
    bool pending=o->shm_probe.close_state==OPEN||o->shm_probe.close_state==UNCERTAIN;
    for(const auto& slot:o->slots)pending|=slot.close_state==OPEN||slot.close_state==UNCERTAIN;
    o->state=pending?FAILED:IDLE;if(pending)result=IOERR;
    snapshot(*o,*out);return result;
}
EXPORT ceta_capacity_destroy(uint64_t id) noexcept {
    std::unique_lock global(registry_mutex);auto* o=find(id);if(!o)return MISUSE;
    std::unique_lock local(o->mutex);global.unlock();
    if(o->state!=IDLE || o->opens!=0 || !o->registered)return BUSY;
    int rc=o->unregister_vfs(&o->vfs);if(rc!=OK)return rc;
    o->registered=false;o->state=CLOSED;
    // A bounded tombstone retains VFS address identity against late opens.
    // No file/mapping/SQLite handle or live registered VFS remains.
    return OK;
}
