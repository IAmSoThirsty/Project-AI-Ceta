//! A second canonical implementation for contract qualification, not a broker.
//! Reads bounded length-prefixed test wires; writes canonical bytes or length 0
//! on rejection. It neither issues authority nor performs filesystem effects.
use serde::de::{self, DeserializeSeed, MapAccess, SeqAccess, Visitor};
use serde_json::{Map, Value};
use std::fmt;
use std::io::{self, Read, Write};
use unicode_normalization::{UnicodeNormalization, UNICODE_VERSION};

const MAX_BYTES: usize = 1024 * 1024;
const MAX_DEPTH: usize = 32;

fn canonical_string<E: de::Error>(value: &str) -> Result<(), E> {
    if !value.nfc().eq(value.chars()) {
        return Err(E::custom("non-canonical Unicode"));
    }
    Ok(())
}

struct Node(usize);

impl<'de> DeserializeSeed<'de> for Node {
    type Value = Value;
    fn deserialize<D: de::Deserializer<'de>>(self, deserializer: D) -> Result<Value, D::Error> {
        if self.0 > MAX_DEPTH {
            return Err(de::Error::custom("depth limit"));
        }
        deserializer.deserialize_any(self)
    }
}

impl<'de> Visitor<'de> for Node {
    type Value = Value;
    fn expecting(&self, formatter: &mut fmt::Formatter) -> fmt::Result {
        formatter.write_str("a bounded integer-only canonical JSON value")
    }
    fn visit_unit<E: de::Error>(self) -> Result<Value, E> { Ok(Value::Null) }
    fn visit_bool<E: de::Error>(self, value: bool) -> Result<Value, E> { Ok(Value::Bool(value)) }
    fn visit_i64<E: de::Error>(self, value: i64) -> Result<Value, E> { Ok(value.into()) }
    fn visit_u64<E: de::Error>(self, value: u64) -> Result<Value, E> {
        let integer = i64::try_from(value).map_err(|_| E::custom("integer range"))?;
        Ok(integer.into())
    }
    fn visit_f64<E: de::Error>(self, value: f64) -> Result<Value, E> {
        // serde_json represents the integer lexeme -0 as a float. The lexical
        // pass below has already rejected every fractional/exponent lexeme.
        if value == 0.0 && value.is_sign_negative() { return Ok(0i64.into()); }
        Err(E::custom("non-integer number"))
    }
    fn visit_str<E: de::Error>(self, value: &str) -> Result<Value, E> {
        canonical_string::<E>(value)?;
        Ok(Value::String(value.into()))
    }
    fn visit_string<E: de::Error>(self, value: String) -> Result<Value, E> {
        canonical_string::<E>(&value)?;
        Ok(Value::String(value))
    }
    fn visit_seq<A: SeqAccess<'de>>(self, mut sequence: A) -> Result<Value, A::Error> {
        let mut values = Vec::new();
        while let Some(value) = sequence.next_element_seed(Node(self.0 + 1))? {
            values.push(value);
        }
        Ok(Value::Array(values))
    }
    fn visit_map<A: MapAccess<'de>>(self, mut map: A) -> Result<Value, A::Error> {
        let mut values = Map::new();
        while let Some(key) = map.next_key::<String>()? {
            if self.0 + 1 > MAX_DEPTH { return Err(de::Error::custom("depth limit")); }
            canonical_string::<A::Error>(&key)?;
            if values.contains_key(&key) { return Err(de::Error::custom("duplicate key")); }
            values.insert(key, map.next_value_seed(Node(self.0 + 1))?);
        }
        Ok(Value::Object(values))
    }
}

fn parse(wire: &[u8]) -> Result<Vec<u8>, ()> {
    if wire.len() > MAX_BYTES || std::str::from_utf8(wire).is_err() { return Err(()); }
    // Enforce the same container-depth bound before tree materialization.
    let (mut depth, mut quoted, mut escaped) = (0usize, false, false);
    for (index, byte) in wire.iter().enumerate() {
        if quoted {
            if escaped { escaped = false; }
            else if *byte == b'\\' { escaped = true; }
            else if *byte == b'"' { quoted = false; }
        } else if *byte == b'"' { quoted = true; }
        else if (byte.is_ascii_digit() || *byte == b'-') &&
            (index == 0 || matches!(wire[index - 1], b'[' | b'{' | b':' | b',' | b' ' | b'\n' | b'\r' | b'\t')) {
            let tail = &wire[index..];
            let length = tail.iter().position(|b| matches!(b, b',' | b']' | b'}' | b' ' | b'\n' | b'\r' | b'\t'))
                .unwrap_or(tail.len());
            if tail[..length].iter().any(|b| matches!(b, b'.' | b'e' | b'E')) { return Err(()); }
        }
        else if *byte == b'[' || *byte == b'{' {
            depth += 1;
            if depth > MAX_DEPTH { return Err(()); }
        } else if *byte == b']' || *byte == b'}' {
            depth = depth.saturating_sub(1);
        }
    }
    let mut parser = serde_json::Deserializer::from_slice(wire);
    let value = Node(0).deserialize(&mut parser).map_err(|_| ())?;
    parser.end().map_err(|_| ())?;
    let canonical = serde_json::to_vec(&value).map_err(|_| ())?;
    if canonical.len() > MAX_BYTES { return Err(()); }
    Ok(canonical)
}

fn main() -> io::Result<()> {
    if std::env::args().nth(1).as_deref() == Some("--identity") {
        println!("{{\"profile\":\"ceta-json-integer-nfc-v1\",\"unicode\":\"{}.{}.{}\",\"authority\":\"NONE\"}}",
                 UNICODE_VERSION.0, UNICODE_VERSION.1, UNICODE_VERSION.2);
        return Ok(());
    }
    let mut input = io::stdin().lock();
    let mut output = io::stdout().lock();
    loop {
        let mut header = [0u8; 4];
        match input.read(&mut header[..1])? {
            0 => return Ok(()),
            _ => input.read_exact(&mut header[1..])?,
        }
        let length = u32::from_be_bytes(header) as usize;
        if length > MAX_BYTES { return Err(io::Error::other("frame size limit")); }
        let mut wire = vec![0u8; length];
        input.read_exact(&mut wire)?;
        let canonical = parse(&wire).unwrap_or_default();
        output.write_all(&(canonical.len() as u32).to_be_bytes())?;
        output.write_all(&canonical)?;
        output.flush()?;
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn known_bytes() {
        assert_eq!(parse(br#"{"z":1,"a":[true,null,-2]}"#).unwrap(), br#"{"a":[true,null,-2],"z":1}"#);
    }
    #[test]
    fn rejects_duplicates_floats_range_and_trailing_data() {
        for wire in [br#"{"a":1,"a":2}"#.as_slice(), b"1.0", b"1e0", b"9223372036854775808", b"{}{}", br#""\ud800""#] {
            assert!(parse(wire).is_err());
        }
    }
    #[test]
    fn unicode_version_is_frozen() { assert_eq!(UNICODE_VERSION, (15, 0, 0)); }
    #[test]
    fn integer_negative_zero_is_preserved_as_canonical_zero() {
        assert_eq!(parse(b"-0").unwrap(), b"0");
        assert_eq!(parse(b"[-0,-1,0]").unwrap(), b"[0,-1,0]");
        assert!(parse(b"-0.0").is_err());
        assert!(parse(b"-0e0").is_err());
    }
}
