//! Fixed query-only observer. No process/job opening, Set, terminate or command API.
use std::ffi::c_void;
use std::fs::OpenOptions;
use std::io::{Read, Write};
use std::os::windows::ffi::OsStringExt;
use std::os::windows::fs::OpenOptionsExt;
use std::os::windows::io::AsRawHandle;
type Handle = *mut c_void;
#[repr(C)] #[derive(Default, PartialEq, Eq)] struct FileTime { low: u32, high: u32 }
#[repr(C)] #[derive(Default, PartialEq, Eq)] struct FileInfo {
    attributes: u32, created: FileTime, accessed: FileTime, written: FileTime,
    volume: u32, size_high: u32, size_low: u32, links: u32, index_high: u32, index_low: u32,
}
#[repr(C)] #[derive(Default)] struct Cpu { flags: u32, value: u32 }
#[link(name="kernel32")] unsafe extern "system" {
    fn GetCurrentProcess() -> Handle;
    fn GetCurrentProcessId() -> u32;
    fn GetProcessId(process: Handle) -> u32;
    fn GetProcessTimes(process: Handle, created: *mut FileTime, exited: *mut FileTime,
                       kernel: *mut FileTime, user: *mut FileTime) -> i32;
    fn QueryFullProcessImageNameW(process: Handle, flags: u32, name: *mut u16, count: *mut u32) -> i32;
    fn GetFileInformationByHandle(file: Handle, info: *mut FileInfo) -> i32;
    fn IsProcessInJob(process: Handle, job: Handle, member: *mut i32) -> i32;
    fn WaitForSingleObject(object: Handle, milliseconds: u32) -> u32;
    fn GetExitCodeProcess(process: Handle, code: *mut u32) -> i32;
    fn QueryInformationJobObject(job: Handle, class: i32, data: *mut c_void, bytes: u32, length: *mut u32) -> i32;
    fn QueryPerformanceCounter(value: *mut i64) -> i32;
    fn QueryPerformanceFrequency(value: *mut i64) -> i32;
}
#[link(name="bcrypt")] unsafe extern "system" {
    fn BCryptOpenAlgorithmProvider(algorithm: *mut Handle, name: *const u16, provider: *const u16, flags: u32) -> i32;
    fn BCryptHash(algorithm: Handle, secret: *mut u8, secret_bytes: u32, input: *mut u8,
                  input_bytes: u32, output: *mut u8, output_bytes: u32) -> i32;
    fn BCryptCloseAlgorithmProvider(algorithm: Handle, flags: u32) -> i32;
}
const INPUT: usize = 240;
const OUTPUT: usize = 288;
const MAX_IMAGE: u64 = 128 * 1024 * 1024;
fn u32_at(data: &[u8], at: usize) -> u32 { u32::from_le_bytes(data[at..at+4].try_into().unwrap()) }
fn u64_at(data: &[u8], at: usize) -> u64 { u64::from_le_bytes(data[at..at+8].try_into().unwrap()) }
fn put32(out: &mut Vec<u8>, value: u32) { out.extend_from_slice(&value.to_le_bytes()); }
fn put64(out: &mut Vec<u8>, value: u64) { out.extend_from_slice(&value.to_le_bytes()); }
fn clock() -> Result<u64, &'static str> {
    let mut value = 0;
    if unsafe { QueryPerformanceCounter(&mut value) } == 0 || value < 0 { return Err("QPC_UNAVAILABLE"); }
    Ok(value as u64)
}
fn creation(process: Handle) -> Result<u64, &'static str> {
    let (mut a,mut b,mut c,mut d)=(FileTime::default(),FileTime::default(),FileTime::default(),FileTime::default());
    if unsafe { GetProcessTimes(process,&mut a,&mut b,&mut c,&mut d) } == 0 { return Err("PROCESS_TIMES_UNAVAILABLE"); }
    Ok((a.high as u64)<<32 | a.low as u64)
}
struct Algorithm(Handle);
impl Drop for Algorithm { fn drop(&mut self) { unsafe { BCryptCloseAlgorithmProvider(self.0,0); } } }
fn image(process: Handle) -> Result<[u8;32], &'static str> {
    let mut name=vec![0u16;32768]; let mut length=name.len() as u32;
    if unsafe { QueryFullProcessImageNameW(process,0,name.as_mut_ptr(),&mut length) } == 0
        || length == 0 || length >= 32768 { return Err("IMAGE_NAME_UNAVAILABLE"); }
    let path=std::ffi::OsString::from_wide(&name[..length as usize]);
    let mut file=OpenOptions::new().read(true).share_mode(1).open(path).map_err(|_|"IMAGE_OPEN_UNAVAILABLE")?;
    let mut before=FileInfo::default();
    if unsafe { GetFileInformationByHandle(file.as_raw_handle(),&mut before) } == 0
        || before.attributes & (0x10|0x400) != 0 { return Err("IMAGE_IDENTITY_UNAVAILABLE"); }
    let expected=(before.size_high as u64)<<32|before.size_low as u64;
    if expected == 0 || expected > MAX_IMAGE { return Err("IMAGE_SIZE_UNAVAILABLE"); }
    let mut bytes=Vec::new();
    Read::by_ref(&mut file).take(MAX_IMAGE+1).read_to_end(&mut bytes).map_err(|_|"IMAGE_READ_UNAVAILABLE")?;
    if bytes.len() as u64 != expected { return Err("IMAGE_SIZE_CHANGED"); }
    let mut after=FileInfo::default();
    if unsafe { GetFileInformationByHandle(file.as_raw_handle(),&mut after) }==0
        || before.attributes!=after.attributes || before.volume!=after.volume
        || before.index_high!=after.index_high || before.index_low!=after.index_low
        || before.size_high!=after.size_high || before.size_low!=after.size_low
        || before.written!=after.written { return Err("IMAGE_IDENTITY_CHANGED"); }
    // The original no-write/no-delete file handle stays retained through hashing.
    let mut algorithm=std::ptr::null_mut(); let name=[83u16,72,65,50,53,54,0];
    if unsafe { BCryptOpenAlgorithmProvider(&mut algorithm,name.as_ptr(),std::ptr::null(),0) } < 0 || algorithm.is_null() {
        return Err("HASH_PROVIDER_UNAVAILABLE");
    }
    let algorithm=Algorithm(algorithm); let mut digest=[0u8;32];
    if unsafe { BCryptHash(algorithm.0,std::ptr::null_mut(),0,bytes.as_mut_ptr(),bytes.len() as u32,digest.as_mut_ptr(),32) } < 0 {
        return Err("IMAGE_HASH_UNAVAILABLE");
    }
    Ok(digest)
}
fn live(process: Handle) -> Result<(bool,u32), &'static str> {
    let state=unsafe { WaitForSingleObject(process,0) }; let mut code=0;
    if (state != 0 && state != 258) || unsafe { GetExitCodeProcess(process,&mut code) } == 0 { return Err("LIFETIME_UNAVAILABLE"); }
    Ok((state == 258,code))
}
fn observe(request: &[u8]) -> Result<Vec<u8>, &'static str> {
    if request.len()!=INPUT || &request[..8]!=b"CETAOB1\0" || u32_at(request,8)!=1 { return Err("INPUT_PROFILE_INVALID"); }
    let sequence=u64_at(request,12); let process_value=u64_at(request,20); let job_value=u64_at(request,28);
    if sequence==0 || sequence > i64::MAX as u64 || process_value==0 || job_value==0
        || process_value==u64::MAX || job_value==u64::MAX || process_value==job_value { return Err("INPUT_HANDLES_INVALID"); }
    let process=process_value as usize as Handle; let job=job_value as usize as Handle;
    let own=unsafe { GetCurrentProcess() }; let own_pid=unsafe { GetCurrentProcessId() };
    let own_created=creation(own)?; let own_image=image(own)?;
    if own_image!=request[208..240] { return Err("OBSERVER_IMAGE_MISMATCH"); }
    let start=clock()?; let mut frequency=0;
    if unsafe { QueryPerformanceFrequency(&mut frequency) }==0 || frequency<=0 { return Err("QPF_UNAVAILABLE"); }
    let target_pid=unsafe { GetProcessId(process) }; let mut target_created=0;
    let mut target_image=[0u8;32]; let (mut state,mut reason,mut member,mut exit_available,mut exit_code)=(0,1,0,0,0);
    let mut policy=Cpu::default();
    if let Ok(created)=creation(process) {
        target_created=created;
        if let Ok(digest)=image(process) {
            target_image=digest;
            if target_pid!=u32_at(request,164) || target_created!=u64_at(request,168)
                || target_image!=request[176..208] { reason=7; }
            else if let Ok((alive,code))=live(process) {
                exit_available=1; exit_code=code;
                if !alive { reason=3; }
                else if unsafe { IsProcessInJob(process,job,&mut member) }==0 { reason=4; }
                else if member!=1 { reason=4; }
                else {
                    let mut length=0;
                    if unsafe { QueryInformationJobObject(job,15,&mut policy as *mut _ as *mut c_void,8,&mut length) }==0 { reason=5; }
                    else if length!=8 { reason=6; }
                    else {
                        let mut final_member=0;
                        if unsafe { GetProcessId(process) }!=target_pid || creation(process).ok()!=Some(target_created)
                            || unsafe { IsProcessInJob(process,job,&mut final_member) }==0 || final_member!=1
                            || live(process).map(|v|v.0)!=Ok(true) { reason=7; }
                        else { state=1; reason=0; }
                    }
                }
            }
        } else { reason=2; }
    }
    let end=clock()?; if end<start { return Err("QPC_ROLLBACK"); }
    let mut out=Vec::with_capacity(OUTPUT);
    out.extend_from_slice(b"CETAOR1\0"); put32(&mut out,1); put64(&mut out,sequence);
    out.extend_from_slice(&request[36..164]);
    put32(&mut out,own_pid); put64(&mut out,own_created); out.extend_from_slice(&own_image);
    put32(&mut out,target_pid); put64(&mut out,target_created); out.extend_from_slice(&target_image);
    put32(&mut out,state);put32(&mut out,reason);put32(&mut out,member as u32);
    put32(&mut out,exit_available);put32(&mut out,exit_code);
    put64(&mut out,start);put64(&mut out,end);put64(&mut out,frequency as u64);
    put32(&mut out,if state==1 {policy.flags} else {0});put32(&mut out,if state==1 {policy.value} else {0});
    if out.len()!=OUTPUT { return Err("OUTPUT_LAYOUT_INVALID"); }
    Ok(out)
}
fn main() {
    if std::env::args_os().len()!=2 || std::env::args_os().nth(1).unwrap()!="observe-v1" { std::process::exit(2); }
    let mut input=Vec::new();
    if std::io::stdin().take(INPUT as u64+1).read_to_end(&mut input).is_err() { std::process::exit(2); }
    match observe(&input) {
        Ok(output)=>if std::io::stdout().write_all(&output).is_err() { std::process::exit(3); },
        Err(reason)=>{let _=writeln!(std::io::stderr(),"{}",reason);std::process::exit(2);}
    }
}
