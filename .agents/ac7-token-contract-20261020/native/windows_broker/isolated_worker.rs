//! Fixed AC1 CPU/security probe. No shell, SQL, imports, credentials or networking protocol.
//! Controller-selected paths are disposable qualification resources, never owner data.
use std::ffi::c_void;
use std::fs::{File, OpenOptions};
use std::io::{Read, Write};
use std::net::{SocketAddr, TcpListener, TcpStream, UdpSocket};
use std::time::{Duration, Instant};

type Handle = *mut c_void;
#[repr(C)]
struct StartupInfo {
    cb: u32, reserved: *mut u16, desktop: *mut u16, title: *mut u16,
    x: u32, y: u32, width: u32, height: u32, xchars: u32, ychars: u32,
    fill: u32, flags: u32, show: u16, reserved_size: u16,
    reserved_bytes: *mut u8, stdin: Handle, stdout: Handle, stderr: Handle,
}
#[repr(C)]
struct ProcessInfo { process: Handle, thread: Handle, pid: u32, tid: u32 }
#[repr(C)]
struct SidAndAttributes { sid: *mut c_void, attributes: u32 }

#[link(name = "kernel32")]
unsafe extern "system" {
    fn GetCurrentProcess() -> Handle;
    fn GetCurrentProcessId() -> u32;
    fn GetLastError() -> u32;
    fn SetLastError(error: u32);
    fn CloseHandle(handle: Handle) -> i32;
    fn LocalFree(pointer: *mut c_void) -> *mut c_void;
    fn OpenProcess(access: u32, inherit: i32, pid: u32) -> Handle;
    fn IsProcessInJob(process: Handle, job: Handle, result: *mut i32) -> i32;
    fn GetHandleInformation(handle: Handle, flags: *mut u32) -> i32;
    fn SetEvent(event: Handle) -> i32;
    fn GetModuleFileNameW(module: Handle, path: *mut u16, size: u32) -> u32;
    fn CreateProcessW(app: *const u16, command: *mut u16, process_security: *mut c_void,
        thread_security: *mut c_void, inherit: i32, flags: u32, environment: *mut c_void,
        directory: *const u16, startup: *mut StartupInfo, result: *mut ProcessInfo) -> i32;
    fn TerminateProcess(process: Handle, code: u32) -> i32;
    fn WaitForSingleObject(handle: Handle, milliseconds: u32) -> u32;
}
#[link(name = "advapi32")]
unsafe extern "system" {
    fn OpenProcessToken(process: Handle, access: u32, token: *mut Handle) -> i32;
    fn GetTokenInformation(token: Handle, class: u32, buffer: *mut c_void,
        size: u32, returned: *mut u32) -> i32;
    fn ConvertSidToStringSidW(sid: *mut c_void, text: *mut *mut u16) -> i32;
    fn IsTokenRestricted(token: Handle) -> i32;
}

fn code(error: std::io::Error) -> i32 { error.raw_os_error().unwrap_or(-1) }
struct TokenData { storage: Vec<u64>, bytes: usize }
impl TokenData {
    fn as_ptr(&self) -> *const u64 { self.storage.as_ptr() }
    fn require_bytes(&self, minimum: usize) -> Result<(), u32> {
        if self.bytes >= minimum { Ok(()) } else { Err(13) }
    }
}

fn query(token: Handle, class: u32) -> Result<TokenData, u32> {
    let mut bytes = 0u32;
    unsafe { SetLastError(0); }
    let initial = unsafe { GetTokenInformation(token, class, std::ptr::null_mut(), 0, &mut bytes) };
    let initial_error = unsafe { GetLastError() };
    if initial != 0 || initial_error != 122 || !(1..=65536).contains(&bytes) {
        return Err(if initial_error == 0 { 13 } else { initial_error });
    }
    // u64 storage keeps pointer/SID-containing Windows structures aligned.
    let mut data = vec![0u64; (bytes as usize + 7) / 8];
    let mut returned = bytes;
    let ok = unsafe { GetTokenInformation(token, class, data.as_mut_ptr().cast(), bytes, &mut returned) };
    if ok == 0 { return Err(unsafe { GetLastError() }); }
    if returned != bytes { return Err(13); }
    Ok(TokenData { storage: data, bytes: bytes as usize })
}

fn restricted_sid_count(data: &TokenData) -> Result<u32, u32> {
    if data.bytes > 65536 { return Err(13); }
    data.require_bytes(std::mem::size_of::<u32>())?;
    let count = unsafe { *(data.as_ptr().cast::<u32>()) };
    if count > 4096 { return Err(13); }
    if count != 0 {
        // TOKEN_GROUPS aligns its first SID_AND_ATTRIBUTES after GroupCount.
        let alignment = std::mem::align_of::<SidAndAttributes>();
        let offset = (std::mem::size_of::<u32>() + alignment - 1) & !(alignment - 1);
        data.require_bytes(offset + count as usize * std::mem::size_of::<SidAndAttributes>())?;
    }
    Ok(count)
}

fn restriction_consistent(raw: i32, last_error: u32, count: u32) -> bool {
    (raw != 0) == (count > 0) && (raw != 0 || last_error == 0)
}

fn sid_text(sid: *mut c_void) -> Result<String, u32> {
    let mut text = std::ptr::null_mut();
    if unsafe { ConvertSidToStringSidW(sid, &mut text) } == 0 { return Err(unsafe { GetLastError() }); }
    let mut len = 0usize;
    unsafe { while len < 256 && *text.add(len) != 0 { len += 1; } }
    let value = if len < 256 { Ok(String::from_utf16_lossy(unsafe { std::slice::from_raw_parts(text, len) })) }
                else { Err(13) };
    unsafe { LocalFree(text.cast()); }
    value
}

fn token_json() -> Result<String, u32> {
    let mut token = std::ptr::null_mut();
    if unsafe { OpenProcessToken(GetCurrentProcess(), 8, &mut token) } == 0 { return Err(unsafe { GetLastError() }); }
    let result = (|| {
        let app = query(token, 29)?;
        let capabilities = query(token, 30)?;
        let container = query(token, 31)?;
        let integrity = query(token, 25)?;
        app.require_bytes(std::mem::size_of::<u32>())?;
        capabilities.require_bytes(std::mem::size_of::<u32>())?;
        container.require_bytes(std::mem::size_of::<*mut c_void>())?;
        integrity.require_bytes(std::mem::size_of::<SidAndAttributes>())?;
        let app_value = unsafe { *(app.as_ptr().cast::<u32>()) };
        let count = unsafe { *(capabilities.as_ptr().cast::<u32>()) };
        let app_sid = unsafe { *(container.as_ptr().cast::<*mut c_void>()) };
        let integrity_sid = unsafe { (*(integrity.as_ptr().cast::<SidAndAttributes>())).sid };
        unsafe { SetLastError(0); }
        let restriction_raw = unsafe { IsTokenRestricted(token) };
        let restriction_error = unsafe { GetLastError() };
        if restriction_raw == 0 && restriction_error != 0 { return Err(restriction_error); }
        let restricting_sids = query(token, 11)?;
        let restricted_count = restricted_sid_count(&restricting_sids)?;
        if !restriction_consistent(restriction_raw, restriction_error, restricted_count) { return Err(13); }
        Ok(format!("{{\"schema\":\"ceta-isolation-token-v2\",\"is_appcontainer\":{},\"capability_count\":{},\"appcontainer_sid\":\"{}\",\"integrity\":\"{}\",\"restricted\":{},\"restriction_raw_result\":{},\"restriction_last_error\":{},\"restricted_sid_count\":{}}}",
            app_value, count, sid_text(app_sid)?, sid_text(integrity_sid)?, restriction_raw != 0,
            restriction_raw, restriction_error, restricted_count))
    })();
    unsafe { CloseHandle(token); }
    result
}

fn process_access(pid: u32, access: u32) -> String {
    let handle = unsafe { OpenProcess(access, 0, pid) };
    if handle.is_null() { format!("{{\"granted\":false,\"error\":{}}}", unsafe { GetLastError() }) }
    else { unsafe { CloseHandle(handle); } "{\"granted\":true,\"error\":0}".into() }
}

fn read_access(path: &str) -> String {
    match File::open(path) {
        Err(error) => format!("{{\"granted\":false,\"error\":{}}}", code(error)),
        Ok(mut file) => {
            let mut bytes = Vec::new();
            match Read::by_ref(&mut file).take(1024).read_to_end(&mut bytes) {
                Ok(count) => format!("{{\"granted\":true,\"error\":0,\"bytes\":{}}}", count),
                Err(error) => format!("{{\"granted\":true,\"read_error\":{}}}", code(error)),
            }
        }
    }
}

fn write_access(path: &str) -> String {
    match OpenOptions::new().write(true).open(path) {
        Err(error) => format!("{{\"granted\":false,\"error\":{}}}", code(error)),
        Ok(mut file) => {
            match file.write_all(b"AC1_UNEXPECTED_WRITE") {
                Ok(()) => "{\"granted\":true,\"written\":true,\"error\":0}".into(),
                Err(error) => format!("{{\"granted\":true,\"written\":false,\"error\":{}}}", code(error)),
            }
        }
    }
}

fn create_scratch(path: &str) -> String {
    match OpenOptions::new().write(true).create_new(true).open(path) {
        Err(error) => format!("{{\"granted\":false,\"error\":{}}}", code(error)),
        Ok(mut file) => match file.write_all(b"CETA_AC1_SCRATCH_V1\n").and_then(|_| file.sync_all()) {
            Ok(()) => "{\"granted\":true,\"error\":0}".into(),
            Err(error) => format!("{{\"granted\":true,\"write_error\":{}}}", code(error)),
        }
    }
}

fn child_attempt(breakaway: bool) -> String {
    let mut path = vec![0u16; 32768];
    let count = unsafe { GetModuleFileNameW(std::ptr::null_mut(), path.as_mut_ptr(), path.len() as u32) };
    if count == 0 || count >= path.len() as u32 { return "{\"available\":false}".into(); }
    let executable = String::from_utf16_lossy(&path[..count as usize]);
    let mut command: Vec<u16> = format!("\"{}\" hold 100", executable).encode_utf16().chain(Some(0)).collect();
    let mut startup: StartupInfo = unsafe { std::mem::zeroed() };
    startup.cb = std::mem::size_of::<StartupInfo>() as u32;
    let mut process: ProcessInfo = unsafe { std::mem::zeroed() };
    let flags = 4 | 0x08000000 | if breakaway { 0x01000000 } else { 0 };
    let ok = unsafe { CreateProcessW(path.as_ptr(), command.as_mut_ptr(), std::ptr::null_mut(), std::ptr::null_mut(),
        0, flags, std::ptr::null_mut(), std::ptr::null(), &mut startup, &mut process) };
    if ok == 0 { format!("{{\"created\":false,\"error\":{}}}", unsafe { GetLastError() }) }
    else {
        // Never leave a failed qualification's suspended escaped child alive.
        let terminated = unsafe { TerminateProcess(process.process, 125) } != 0;
        let waited = unsafe { WaitForSingleObject(process.process, 5000) };
        unsafe { CloseHandle(process.thread); CloseHandle(process.process); }
        format!("{{\"created\":true,\"pid\":{},\"termination_requested\":{},\"wait_result\":{}}}",
                process.pid, terminated, waited)
    }
}

fn net_result<T>(result: std::io::Result<T>) -> String {
    match result {
        Ok(_) => "{\"granted\":true,\"error\":0}".into(),
        Err(error) => format!("{{\"granted\":false,\"error\":{}}}", code(error)),
    }
}

fn probe(args: &[String]) -> Result<(), String> {
    // allowed asset, scratch new file, five denied files, target PID,
    // owned local listener port, excluded inheritable event handle.
    if args.len() != 10 { return Err("PROBE_ARGUMENT_COUNT".into()); }
    if args.iter().any(|value| value.len() > 4096 || value.contains('\0')) { return Err("PROBE_ARGUMENT_BOUNDS".into()); }
    let pid: u32 = args[7].parse().map_err(|_| "PROBE_PID")?;
    let port: u16 = args[8].parse().map_err(|_| "PROBE_PORT")?;
    let excluded: usize = args[9].parse().map_err(|_| "PROBE_HANDLE")?;
    if pid == 0 || port == 0 || excluded == 0 { return Err("PROBE_IDENTITY_REQUIRED".into()); }
    let token = token_json().map_err(|code| format!("PROBE_TOKEN_{}", code))?;
    let mut job_member = 0i32;
    let job_query = unsafe { IsProcessInJob(GetCurrentProcess(), std::ptr::null_mut(), &mut job_member) };
    let mut flags = 0u32;
    let hidden_query = unsafe { GetHandleInformation(excluded as Handle, &mut flags) };
    let hidden_signal = unsafe { SetEvent(excluded as Handle) };
    let hidden_error = if hidden_signal == 0 { unsafe { GetLastError() } } else { 0 };
    let mut results = Vec::new();
    results.push(format!("\"profile\":\"ceta-ac1-native-probe-v1\",\"pid\":{},\"token\":{}", unsafe { GetCurrentProcessId() }, token));
    results.push(format!("\"job_query\":{},\"job_member\":{},\"environment_keys\":{}", job_query, job_member,
        format!("[{}]", std::env::vars_os().map(|(key, _)| format!("\"{}\"", key.to_string_lossy())).collect::<Vec<_>>().join(","))));
    results.push(format!("\"allowed_read\":{},\"scratch_write\":{}", read_access(&args[0]), create_scratch(&args[1])));
    for (index, path) in args[2..7].iter().enumerate() {
        results.push(format!("\"denied_file_{}\":{{\"read\":{},\"write\":{}}}", index, read_access(path), write_access(path)));
    }
    results.push(format!("\"process_rights\":{{\"vm_write\":{},\"create_thread\":{},\"duplicate_handle\":{},\"terminate\":{},\"write_dac\":{}}}",
        process_access(pid, 0x20), process_access(pid, 2), process_access(pid, 0x40), process_access(pid, 1), process_access(pid, 0x40000)));
    results.push(format!("\"hidden_event\":{{\"handle_query\":{},\"signal\":{},\"error\":{}}}", hidden_query, hidden_signal, hidden_error));
    results.push(format!("\"child\":{},\"breakaway\":{}", child_attempt(false), child_attempt(true)));
    let endpoint: SocketAddr = format!("127.0.0.1:{}", port).parse().unwrap();
    results.push(format!("\"tcp_connect\":{}", net_result(TcpStream::connect_timeout(&endpoint, Duration::from_millis(500)))));
    results.push(format!("\"tcp_loopback_listen\":{}", net_result(TcpListener::bind("127.0.0.1:0"))));
    results.push(format!("\"tcp_wildcard_listen\":{}", net_result(TcpListener::bind("0.0.0.0:0"))));
    let udp = UdpSocket::bind("0.0.0.0:0").and_then(|socket| socket.send_to(b"AC1", endpoint));
    results.push(format!("\"udp_loopback\":{}", net_result(udp)));
    println!("{{{}}}", results.join(","));
    Ok(())
}

fn main() {
    let args: Vec<String> = std::env::args().collect();
    let result = if args.len() >= 2 {
        match args[1].as_str() {
            "probe" => probe(&args[2..]),
            "hold" | "cpu" if args.len() == 3 => {
                match args[2].parse::<u64>() {
                    Ok(ms) if (1..=30000).contains(&ms) => {
                        if args[1] == "hold" { std::thread::sleep(Duration::from_millis(ms)); }
                        else { let start = Instant::now(); let mut x = 1u64;
                               while start.elapsed() < Duration::from_millis(ms) { x = x.wrapping_mul(6364136223846793005).wrapping_add(1); std::hint::black_box(x); } }
                        println!("{{\"profile\":\"ceta-ac1-fixed-work-v1\",\"completed\":true}}"); Ok(())
                    },
                    _ => Err("WORK_DURATION_INVALID".into()),
                }
            },
            _ => Err("OPERATION_UNAVAILABLE".into()),
        }
    } else { Err("OPERATION_REQUIRED".into()) };
    if let Err(error) = result { eprintln!("{}", error); std::process::exit(2); }
}

#[cfg(test)]
mod token_measurement_tests {
    use super::*;

    fn buffer(count: u32, bytes: usize) -> TokenData {
        let mut data = TokenData { storage: vec![0; (bytes + 7) / 8], bytes };
        if bytes >= 4 { unsafe { *(data.storage.as_mut_ptr().cast::<u32>()) = count; } }
        data
    }

    #[test]
    fn empty_list_requires_a_measured_count_header() {
        assert_eq!(restricted_sid_count(&buffer(0, 4)), Ok(0));
        assert_eq!(restricted_sid_count(&buffer(0, 3)), Err(13));
    }

    #[test]
    fn positive_count_requires_every_group_slot_in_returned_bytes() {
        assert_eq!(restricted_sid_count(&buffer(1, 24)), Ok(1));
        assert_eq!(restricted_sid_count(&buffer(1, 23)), Err(13));
        assert_eq!(restricted_sid_count(&buffer(2, 24)), Err(13));
    }

    #[test]
    fn excessive_count_is_rejected_before_size_arithmetic() {
        assert_eq!(restricted_sid_count(&buffer(4097, 65536)), Err(13));
        assert_eq!(restricted_sid_count(&buffer(u32::MAX, 8)), Err(13));
        assert_eq!(restricted_sid_count(&buffer(0, 65537)), Err(13));
        assert_eq!(restricted_sid_count(&buffer(4096, 65544)), Err(13));
    }

    #[test]
    fn boolean_error_and_measured_presence_must_agree() {
        assert!(restriction_consistent(0, 0, 0));
        assert!(restriction_consistent(1, 0, 1));
        assert!(restriction_consistent(2, 0, 1));
        assert!(!restriction_consistent(0, 5, 0));
        assert!(!restriction_consistent(0, 0, 1));
        assert!(!restriction_consistent(1, 0, 0));
    }

    #[test]
    fn token_structure_sizes_use_returned_byte_count() {
        let data = buffer(0, 4);
        assert_eq!(data.require_bytes(4), Ok(()));
        assert_eq!(data.require_bytes(8), Err(13));
        assert_eq!(std::mem::size_of::<SidAndAttributes>(), 16);
    }
}
