# The cipher: why it is hand-written, and what it can be trusted for

`noesis_harness/aead.py` implements **AEAD_CHACHA20_POLY1305** from
[RFC 8439](https://www.rfc-editor.org/rfc/rfc8439). `noesis_harness/cell_cipher.py`
uses it to give each memory cell its own key and to erase by destroying that key.

## Why not a library

The project's first rule is zero dependencies. Python's standard library ships
key derivation (`hashlib.scrypt`, `hashlib.pbkdf2_hmac`) but **no symmetric
cipher and no AEAD**, so before this module the only honest erasure claim was
*access control*: content withdrawn from every read path, but readable by
anyone holding a pre-erasure copy.

Adding `cryptography` would break the rule. Implementing a cipher does not.

## Why ChaCha20-Poly1305 specifically

Three properties, in order of importance:

1. **The RFC publishes test vectors.** Correctness is a check, not a hope.
   `selftest()` runs them, and `CellCipher` refuses to construct if any fails.
2. **No lookup tables and no data-dependent branches.** The algorithm is
   32-bit addition, XOR and rotation. That removes the cache-timing class of
   bug that table-driven ciphers are prone to.
3. **The AEAD construction authenticates.** A corrupted or truncated cell fails
   closed instead of decrypting to garbage.

## What is verified

`python -c "from noesis_harness.aead import selftest; print(selftest()['all_passed'])"`

| Check | RFC section |
|---|---|
| Quarter round | 2.1.1 |
| Block function | 2.3.2 |
| Encryption | 2.4.2 |
| Poly1305 MAC | 2.5.2 |
| Poly1305 key generation | 2.6.2 |
| AEAD ciphertext | 2.8.2 |
| AEAD tag | 2.8.2 |
| AEAD round trip | 2.8.2 |
| Empty message, all-zero key | A.3 #1 |
| Zero `r` (tag equals `s`) | A.3 #2 |
| 130-bit partial reduction | A.3 #5 |

The appendix vectors are not decoration. A naive Poly1305 can return a value
congruent modulo `p` that is not the canonical representative; only A.3 #5
catches that. The zero-key vector catches an implementation that invents
structure where there is none.

## What it must not be used for

- **Not a network protocol.** CPython cannot promise constant-time execution:
  the interpreter, the allocator and the garbage collector sit between the
  arithmetic and the hardware. Use it for at-rest data, not for a protocol
  facing an active attacker with timing measurements.
- **Not a replacement for full-disk encryption.** Key destruction makes the
  ciphertext unreadable. It does not reach a copy of the key, a plaintext
  exported before sealing, or raw blocks on a device that was never encrypted.
- **Not a second implementation.** If a cipher is ever added again, this one
  should be replaced rather than joined. One verified implementation is
  auditable; two are not.

## How erasure works

```
seal(cell_id, plaintext):
    key   = keystore.create(cell_id)        one fresh 256-bit key
    nonce = random 96 bits                  safe because the key is fresh
    aad   = cell_id                         binds ciphertext to its slot
    sealed = ChaCha20-Poly1305(key, nonce, plaintext, aad)

erase(cell):
    overwrite the key in place, then remove it
    append a receipt: ciphertext digest, key digest, actor, time
```

After `erase`, every copy of the ciphertext decrypts to nothing, because the
key no longer exists anywhere this process can reach. That is SAIHM's
*cryptographic* erasure class.

The receipt deliberately holds no plaintext: a proof of erasure that contains
what was erased is not a proof, it is a copy.

## The limit, in one sentence

Destroying a key does not destroy a copy of that key, so a deployment that
keeps key backups must destroy those too; `forget.py`'s
`declare_backups()`/`scan_backups()` exists so a receipt reports the replicas
it could not reach instead of implying there were none.