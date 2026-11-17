"""noesis_harness/aead.py

ChaCha20-Poly1305 authenticated encryption, implemented in the standard library
so that this project can perform real cryptographic erasure without breaking
its zero-dependency rule.

Patterns borrowed from:

- **RFC 8439**, *ChaCha20 and Poly1305 for IETF Protocols* (Nir & Langley,
  IRTF/CFRG, June 2018). The algorithm, the construction and every test vector
  in this module come from that document. The RFC is the specification; this
  file is a transcription of it, verified byte-for-byte against the published
  vectors in :data:`RFC_TEST_VECTORS`.
- **SAIHM** (IETF draft-saihm-memory-protocol-03, 2026-10-11): the distinction
  between *cryptographic* erasure (destroy the wrapping key) and
  *access-control* erasure (withdraw access). A cipher is what makes the first
  class reachable at all.
- **Deployment-Time Memorization** (arXiv 2606.10062): cryptographic erasure is
  the only mechanism that reaches zero residue regardless of how many derived
  copies exist, because every copy becomes ciphertext.

Why hand-write a cipher
-----------------------

Python's standard library ships key derivation (``hashlib.scrypt``,
``hashlib.pbkdf2_hmac``) but no symmetric cipher and no AEAD. Adding
``cryptography`` would break the project's first rule. That left two honest
options: report access-control erasure only, or implement a cipher that can be
*proved* correct.

ChaCha20-Poly1305 is the right choice for a hand implementation because:

- it is fully specified by an IETF RFC with published test vectors, so
  correctness is a check rather than a hope;
- it uses only 32-bit addition, XOR and rotation -- no lookup tables, no
  data-dependent branches, so the timing profile does not depend on the key;
- its AEAD construction gives tamper detection for free, which matters because
  a corrupted cell must fail closed rather than decrypt to garbage.

**This is not a claim of side-channel hardness beyond that.** Python cannot
promise constant-time execution: the interpreter, the allocator and the
garbage collector all sit between the arithmetic and the hardware. The module
is suitable for at-rest erasure of local agent memory, which is what it is for.
It is not suitable for a network protocol facing an active attacker with
timing measurements.

Governance
----------

A cipher here does not weaken any other rule. Keys live in a separate key
store, every seal and every destruction writes a receipt, and destroying a key
is an explicit, attributable operation -- the same shape as every other
irreversible act in this project. Stdlib only.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import struct
from typing import Any, Dict, List, Optional, Sequence, Tuple


SCHEMA_VERSION = "noesis.aead.v1"

KEY_BYTES = 32
NONCE_BYTES = 12
TAG_BYTES = 16

#: The four constants that begin every ChaCha state: "expand 32-byte k".
_SIGMA = (0x61707865, 0x3320646E, 0x79622D32, 0x6B206574)

_MASK32 = 0xFFFFFFFF

#: Poly1305 modulus: 2^130 - 5.
_P1305 = (1 << 130) - 5

#: Clamping mask from RFC 8439 section 2.5.
_R_CLAMP = 0x0FFFFFFC0FFFFFFC0FFFFFFC0FFFFFFF


class AeadError(ValueError):
    """Raised when a key, nonce or ciphertext is malformed."""


class AuthenticationError(AeadError):
    """Raised when a ciphertext fails its tag check. Never returns plaintext."""


# --------------------------------------------------------------------------
# ChaCha20 (RFC 8439 section 2.3, 2.4)
# --------------------------------------------------------------------------


def _rotl(value: int, count: int) -> int:
    """32-bit left rotation. No data-dependent branching."""
    value &= _MASK32
    return ((value << count) | (value >> (32 - count))) & _MASK32


def quarter_round(state: List[int], a: int, b: int, c: int, d: int) -> None:
    """The ChaCha quarter round, RFC 8439 section 2.1, in place.

    ``a += b; d ^= a; d <<<= 16`` and so on. Written as four repeated
    add/xor/rotate triples so it transcribes the RFC directly, which is what
    makes the test vector meaningful.
    """
    state[a] = (state[a] + state[b]) & _MASK32
    state[d] = _rotl(state[d] ^ state[a], 16)
    state[c] = (state[c] + state[d]) & _MASK32
    state[b] = _rotl(state[b] ^ state[c], 12)
    state[a] = (state[a] + state[b]) & _MASK32
    state[d] = _rotl(state[d] ^ state[a], 8)
    state[c] = (state[c] + state[d]) & _MASK32
    state[b] = _rotl(state[b] ^ state[c], 7)


def _inner_block(state: List[int]) -> None:
    """One double round: four column rounds then four diagonal rounds."""
    quarter_round(state, 0, 4, 8, 12)
    quarter_round(state, 1, 5, 9, 13)
    quarter_round(state, 2, 6, 10, 14)
    quarter_round(state, 3, 7, 11, 15)
    quarter_round(state, 0, 5, 10, 15)
    quarter_round(state, 1, 6, 11, 12)
    quarter_round(state, 2, 7, 8, 13)
    quarter_round(state, 3, 4, 9, 14)


def _initial_state(key: bytes, counter: int, nonce: bytes) -> List[int]:
    if len(key) != KEY_BYTES:
        raise AeadError("key_must_be_32_bytes")
    if len(nonce) != NONCE_BYTES:
        raise AeadError("nonce_must_be_12_bytes")
    if not 0 <= counter <= _MASK32:
        raise AeadError("counter_out_of_range")
    state = list(_SIGMA)
    state.extend(struct.unpack("<8I", key))
    state.append(counter & _MASK32)
    state.extend(struct.unpack("<3I", nonce))
    return state


def chacha20_block(key: bytes, counter: int, nonce: bytes) -> bytes:
    """One 64-byte keystream block, RFC 8439 section 2.3."""
    working = _initial_state(key, counter, nonce)
    initial = list(working)
    for _ in range(10):
        _inner_block(working)
    out = [(working[i] + initial[i]) & _MASK32 for i in range(16)]
    return struct.pack("<16I", *out)


def chacha20_encrypt(key: bytes, counter: int, nonce: bytes, plaintext: bytes) -> bytes:
    """XOR the ChaCha20 keystream with ``plaintext``.

    Encryption and decryption are the same operation, which is why this is the
    only function either path needs.
    """
    if len(key) != KEY_BYTES:
        raise AeadError("key_must_be_32_bytes")
    if len(nonce) != NONCE_BYTES:
        raise AeadError("nonce_must_be_12_bytes")
    out = bytearray(len(plaintext))
    for offset in range(0, len(plaintext), 64):
        block = chacha20_block(key, counter + (offset // 64), nonce)
        chunk = plaintext[offset : offset + 64]
        for index, byte in enumerate(chunk):
            out[offset + index] = byte ^ block[index]
    return bytes(out)


# --------------------------------------------------------------------------
# Poly1305 (RFC 8439 section 2.5)
# --------------------------------------------------------------------------


def _le_bytes_to_num(data: bytes) -> int:
    return int.from_bytes(data, "little")


def _num_to_16_le_bytes(value: int) -> bytes:
    return int(value).to_bytes(16, "little")


def poly1305_mac(message: bytes, one_time_key: bytes) -> bytes:
    """The Poly1305 authenticator, RFC 8439 section 2.5.1.

    ``r`` is clamped exactly as the RFC requires, and each 16-byte block gets
    the implicit high bit that makes the encoding unambiguous. Python's
    arbitrary-precision integers make the 130-bit arithmetic direct, which is
    the one place this implementation is simpler than a C one.
    """
    if len(one_time_key) != 32:
        raise AeadError("poly1305_key_must_be_32_bytes")
    r = _le_bytes_to_num(one_time_key[:16]) & _R_CLAMP
    s = _le_bytes_to_num(one_time_key[16:])
    accumulator = 0
    for offset in range(0, len(message), 16):
        block = message[offset : offset + 16]
        # The 0x01 byte above the block: 2^(8*len(block)).
        accumulator += _le_bytes_to_num(block) + (1 << (8 * len(block)))
        accumulator = (accumulator * r) % _P1305
    return _num_to_16_le_bytes((accumulator + s) & ((1 << 128) - 1))


def poly1305_key_gen(key: bytes, nonce: bytes) -> bytes:
    """Derive the one-time Poly1305 key from block 0, RFC 8439 section 2.6."""
    return chacha20_block(key, 0, nonce)[:32]


# --------------------------------------------------------------------------
# AEAD_CHACHA20_POLY1305 (RFC 8439 section 2.8)
# --------------------------------------------------------------------------


def _pad16(data: bytes) -> bytes:
    remainder = len(data) % 16
    return b"" if remainder == 0 else b"\x00" * (16 - remainder)


def _mac_data(aad: bytes, ciphertext: bytes) -> bytes:
    """AAD || pad || ciphertext || pad || len(AAD) || len(ciphertext)."""
    return b"".join(
        (
            aad,
            _pad16(aad),
            ciphertext,
            _pad16(ciphertext),
            struct.pack("<Q", len(aad)),
            struct.pack("<Q", len(ciphertext)),
        )
    )


def aead_encrypt(key: bytes, nonce: bytes, plaintext: bytes, aad: bytes = b"") -> bytes:
    """Encrypt and authenticate. Returns ``ciphertext || tag``.

    The nonce must never repeat under one key. Callers in this project give
    every cell its own key, so a fresh random nonce per seal is safe; a caller
    that reuses a key across many messages must supply a counter instead.
    """
    if len(key) != KEY_BYTES:
        raise AeadError("key_must_be_32_bytes")
    if len(nonce) != NONCE_BYTES:
        raise AeadError("nonce_must_be_12_bytes")
    one_time_key = poly1305_key_gen(key, nonce)
    ciphertext = chacha20_encrypt(key, 1, nonce, plaintext)
    tag = poly1305_mac(_mac_data(aad, ciphertext), one_time_key)
    return ciphertext + tag


def aead_decrypt(key: bytes, nonce: bytes, sealed: bytes, aad: bytes = b"") -> bytes:
    """Verify then decrypt. Raises :class:`AuthenticationError` on a bad tag.

    The tag is checked before any plaintext is returned, in constant time, so a
    corrupted or truncated cell fails closed. Returning plaintext from a failed
    verification is the classic way a memory system leaks data it believes it
    has erased.
    """
    if len(sealed) < TAG_BYTES:
        raise AeadError("ciphertext_shorter_than_tag")
    ciphertext, tag = sealed[:-TAG_BYTES], sealed[-TAG_BYTES:]
    one_time_key = poly1305_key_gen(key, nonce)
    expected = poly1305_mac(_mac_data(aad, ciphertext), one_time_key)
    if not hmac.compare_digest(expected, tag):
        raise AuthenticationError("tag_mismatch")
    return chacha20_encrypt(key, 1, nonce, ciphertext)


def random_key() -> bytes:
    """A fresh 256-bit key from the OS entropy source."""
    return secrets.token_bytes(KEY_BYTES)


def random_nonce() -> bytes:
    """A fresh 96-bit nonce. Safe because each cell carries its own key."""
    return secrets.token_bytes(NONCE_BYTES)


def derive_key(passphrase: bytes, salt: bytes, *, n: int = 2 ** 14, r: int = 8, p: int = 1) -> bytes:
    """Derive a key from a passphrase with scrypt.

    Only for a caller that has a passphrase rather than a stored key. The
    default cost is the one ``hashlib.scrypt`` documents as interactive; a
    deployment that protects long-lived data should raise it.
    """
    if not isinstance(passphrase, (bytes, bytearray)) or not passphrase:
        raise AeadError("passphrase_required")
    if not isinstance(salt, (bytes, bytearray)) or len(salt) < 8:
        raise AeadError("salt_must_be_at_least_8_bytes")
    return hashlib.scrypt(passphrase, salt=bytes(salt), n=n, r=r, p=p, dklen=KEY_BYTES)


# --------------------------------------------------------------------------
# RFC 8439 test vectors
# --------------------------------------------------------------------------

#: Every published vector this implementation is checked against. A cipher
#: without vectors is a guess; these are what turn the claim into a check.
RFC_TEST_VECTORS: Dict[str, Dict[str, Any]] = {
    "quarter_round": {
        "state": [0x11111111, 0x01020304, 0x9B8D6F43, 0x01234567],
        "expected": [0xEA2A92F4, 0xCB1CF8CE, 0x4581472E, 0x5881C4BB],
    },
    "block": {
        "key": bytes(range(32)),
        "nonce": bytes.fromhex("000000090000004a00000000"),
        "counter": 1,
        "expected": bytes.fromhex(
            "10f1e7e4d13b5915500fdd1fa32071c4"
            "c7d1f4c733c068030422aa9ac3d46c4e"
            "d2826446079faa0914c2d705d98b02a2"
            "b5129cd1de164eb9cbd083e8a2503c4e"
        ),
    },
    "encrypt": {
        "key": bytes(range(32)),
        "nonce": bytes.fromhex("000000000000004a00000000"),
        "counter": 1,
        "plaintext": (
            b"Ladies and Gentlemen of the class of '99: If I could offer you "
            b"only one tip for the future, sunscreen would be it."
        ),
        "expected": bytes.fromhex(
            "6e2e359a2568f98041ba0728dd0d6981"
            "e97e7aec1d4360c20a27afccfd9fae0b"
            "f91b65c5524733ab8f593dabcd62b357"
            "1639d624e65152ab8f530c359f0861d8"
            "07ca0dbf500d6a6156a38e088a22b65e"
            "52bc514d16ccf806818ce91ab7793736"
            "5af90bbf74a35be6b40b8eedf2785e42"
            "874d"
        ),
    },
    "poly1305": {
        "key": bytes.fromhex(
            "85d6be7857556d337f4452fe42d506a8"
            "0103808afb0db2fd4abff6af4149f51b"
        ),
        "message": b"Cryptographic Forum Research Group",
        "expected": bytes.fromhex("a8061dc1305136c6c22b8baf0c0127a9"),
    },
    "poly1305_key_gen": {
        "key": bytes.fromhex(
            "808182838485868788898a8b8c8d8e8f"
            "909192939495969798999a9b9c9d9e9f"
        ),
        "nonce": bytes.fromhex("000000000001020304050607"),
        "expected": bytes.fromhex(
            "8ad5a08b905f81cc815040274ab29471"
            "a833b637e3fd0da508dbb8e2fdd1a646"
        ),
    },
    "aead": {
        "key": bytes.fromhex(
            "808182838485868788898a8b8c8d8e8f"
            "909192939495969798999a9b9c9d9e9f"
        ),
        "nonce": bytes.fromhex("070000004041424344454647"),
        "aad": bytes.fromhex("50515253c0c1c2c3c4c5c6c7"),
        "plaintext": (
            b"Ladies and Gentlemen of the class of '99: If I could offer you "
            b"only one tip for the future, sunscreen would be it."
        ),
        "expected_tag": bytes.fromhex("1ae10b594f09e26a7e902ecbd0600691"),
        "expected_ciphertext": bytes.fromhex(
            "d31a8d34648e60db7b86afbc53ef7ec2"
            "a4aded51296e08fea9e2b5a736ee62d6"
            "3dbea45e8ca9671282fafb69da92728b"
            "1a71de0a9e060b2905d6a5b67ecd3b36"
            "92ddbd7f2d778b8c9803aee328091b58"
            "fab324e4fad675945585808b4831d7bc"
            "3ff4def08e4b7a9de576d26586cec64b"
            "6116"
        ),
    },
}


#: Appendix A vectors. These are the ones that catch the mistakes the main
#: vectors miss: an empty message, an all-zero key, and the 130-bit partial
#: reduction case where a naive implementation returns a value that is
#: congruent modulo p but not the canonical representative.
APPENDIX_A_POLY1305: Dict[str, Dict[str, Any]] = {
    "zero_key_zero_message": {
        # Appendix A.3 test vector #1: an all-zero key over 64 zero bytes.
        # Everything cancels, so the tag is all zeros -- which is a real check
        # that the implementation does not invent structure where there is none.
        "key": bytes(32),
        "message": bytes(64),
        "expected": bytes(16),
    },
    "zero_r": {
        # Appendix A.3 test vector #2: r is zero, so the accumulator never
        # moves and the tag is exactly s. Catches an implementation that adds
        # s before reducing, or that ignores the key split.
        "key": bytes(16) + bytes.fromhex("36e5f6b5c5e06070f0efca96227a863e"),
        "message": (
            b"Any submission to the IETF intended by the Contributor for "
            b"publication as all or part of an IETF Internet-Draft or RFC and "
            b"any statement made within the context of an IETF activity is "
            b"considered an \"IETF Contribution\". Such statements include "
            b"oral statements in IETF sessions, as well as written and "
            b"electronic communications made at any time or place, which are "
            b"addressed to"
        ),
        "expected": bytes.fromhex("36e5f6b5c5e06070f0efca96227a863e"),
    },
    "partial_reduction": {
        "key": bytes.fromhex(
            "1c9240a5eb55d38af333888604f6b5f0"
            "473917c1402b80099dca5cbc207075c0"
        ),
        "message": (
            b"'Twas brillig, and the slithy toves\n"
            b"Did gyre and gimble in the wabe:\n"
            b"All mimsy were the borogoves,\n"
            b"And the mome raths outgrabe."
        ),
        "expected": bytes.fromhex("4541669a7eaaee61e708dc7cbcc5eb62"),
    },
}


def selftest() -> Dict[str, Any]:
    """Run every RFC 8439 vector and report which ones matched.

    Called by the test suite and by :func:`cipher_capability`, so a deployment
    can assert that the cipher on this machine is the cipher the RFC describes
    before it trusts an erasure claim to it.
    """
    results: Dict[str, bool] = {}

    vector = RFC_TEST_VECTORS["quarter_round"]
    state = list(vector["state"])
    quarter_round(state, 0, 1, 2, 3)
    results["quarter_round"] = state == vector["expected"]

    vector = RFC_TEST_VECTORS["block"]
    results["block"] = (
        chacha20_block(vector["key"], vector["counter"], vector["nonce"]) == vector["expected"]
    )

    vector = RFC_TEST_VECTORS["encrypt"]
    results["encrypt"] = (
        chacha20_encrypt(
            vector["key"], vector["counter"], vector["nonce"], vector["plaintext"]
        )
        == vector["expected"]
    )

    vector = RFC_TEST_VECTORS["poly1305"]
    results["poly1305"] = (
        poly1305_mac(vector["message"], vector["key"]) == vector["expected"]
    )

    vector = RFC_TEST_VECTORS["poly1305_key_gen"]
    results["poly1305_key_gen"] = (
        poly1305_key_gen(vector["key"], vector["nonce"]) == vector["expected"]
    )

    vector = RFC_TEST_VECTORS["aead"]
    sealed = aead_encrypt(
        vector["key"], vector["nonce"], vector["plaintext"], vector["aad"]
    )
    results["aead_ciphertext"] = sealed[:-TAG_BYTES] == vector["expected_ciphertext"]
    results["aead_tag"] = sealed[-TAG_BYTES:] == vector["expected_tag"]
    results["aead_roundtrip"] = (
        aead_decrypt(vector["key"], vector["nonce"], sealed, vector["aad"])
        == vector["plaintext"]
    )

    for name, appendix in APPENDIX_A_POLY1305.items():
        results["poly1305_" + name] = (
            poly1305_mac(appendix["message"], appendix["key"]) == appendix["expected"]
        )

    return {
        "schema_version": SCHEMA_VERSION,
        "algorithm": "AEAD_CHACHA20_POLY1305",
        "reference": "RFC 8439",
        "checks": results,
        "all_passed": all(results.values()),
        "n_checks": len(results),
    }


__all__ = [
    "AeadError",
    "AuthenticationError",
    "KEY_BYTES",
    "NONCE_BYTES",
    "RFC_TEST_VECTORS",
    "SCHEMA_VERSION",
    "TAG_BYTES",
    "aead_decrypt",
    "aead_encrypt",
    "chacha20_block",
    "chacha20_encrypt",
    "derive_key",
    "poly1305_key_gen",
    "poly1305_mac",
    "quarter_round",
    "random_key",
    "random_nonce",
    "selftest",
]