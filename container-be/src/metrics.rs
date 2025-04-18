use std::ffi::{c_char, c_void, CString};

use prometheus::{Encoder, Registry};

#[no_mangle]
pub extern "C" fn prometheus_response(ptr: *const c_void) -> *const c_char {
    let state = unsafe { &*(ptr as *const Registry) };

    let encoder = prometheus::TextEncoder::new();
    let mut buffer = Vec::new();

    let metric_families = state.gather();

    encoder.encode(&metric_families, &mut buffer).unwrap();

    let prometheus = String::from_utf8(buffer).unwrap();

    let c_str_prometheus = std::ffi::CString::new(prometheus).unwrap();

    c_str_prometheus.into_raw()
}

#[no_mangle]
pub extern "C" fn prometheus_response_free(ptr: *mut c_char) {
    if ptr.is_null() {
        return;
    }
    unsafe {
        let _ = CString::from_raw(ptr);
    };
}
