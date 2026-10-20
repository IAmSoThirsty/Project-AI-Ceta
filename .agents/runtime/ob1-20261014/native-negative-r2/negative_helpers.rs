
use std::ffi::c_void;
use std::io::{Read,Write};
type H=*mut c_void;
#[repr(C)]struct Cpu{flags:u32,value:u32}
#[link(name="kernel32")]unsafe extern "system"{
 fn QueryInformationJobObject(job:H,class:i32,data:*mut c_void,size:u32,length:*mut u32)->i32;
 fn SetInformationJobObject(job:H,class:i32,data:*const c_void,size:u32)->i32;
 fn TerminateProcess(process:H,code:u32)->i32;
 fn GetLastError()->u32;
 fn SetLastError(code:u32);
}
fn main(){
 let path=std::env::current_exe().unwrap();let mode=path.file_stem().unwrap().to_str().unwrap();
 if std::env::args_os().len()!=2||std::env::args_os().nth(1).unwrap()!="observe-v1"{std::process::exit(2);}
 if mode=="silent"{std::thread::sleep(std::time::Duration::from_secs(30));return;}
 if mode=="overlong"{std::io::stdout().write_all(&vec![88u8;289]).unwrap();return;}
 if mode!="rights"{std::process::exit(2);}
 let mut input=Vec::new();std::io::stdin().take(241).read_to_end(&mut input).unwrap();
 if input.len()!=240||&input[..8]!=b"CETAOB1\0"{std::process::exit(2);}
 let process=u64::from_le_bytes(input[20..28].try_into().unwrap()) as usize as H;
 let job=u64::from_le_bytes(input[28..36].try_into().unwrap()) as usize as H;
 let mut policy=Cpu{flags:0,value:0};let mut length=0;
 if unsafe{QueryInformationJobObject(job,15,&mut policy as *mut _ as *mut c_void,8,&mut length)}==0||length!=8{std::process::exit(3);}
 unsafe{SetLastError(0);}
 let set=unsafe{SetInformationJobObject(job,15,&policy as *const _ as *const c_void,8)};
 let set_error=unsafe{GetLastError()};unsafe{SetLastError(0);}
 let terminate=unsafe{TerminateProcess(process,17)};let terminate_error=unsafe{GetLastError()};
 let mut output=Vec::new();
 for value in [set as u32,set_error,terminate as u32,terminate_error]{output.extend_from_slice(&value.to_le_bytes());}
 std::io::stdout().write_all(&output).unwrap();
}
