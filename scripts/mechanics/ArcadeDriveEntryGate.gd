class_name ArcadeDriveEntryGate
extends RefCounted

## Original 1991 arcade Z80 drive-entry decisions at 71C8..71FE.
## Authenticated original Z80 vs independent model: 100,000 cases,
## zero mismatches. Connected with downstream 71FA..726C for a further
## 120,000 privately verified original-machine input scenarios.
##
## This stage consumes two ORIGINAL earlier lookup output bytes B/C and
## the indexed source IX-0B. It cannot manufacture B/C or update them.
## Original IX points at physical slot+0x80, so IX-0B is slot+0x75
## and IX+57 is physical slot+0xD7. These are not elapsed seconds,
## engine power constants or independently supplied vehicle speed.
##
## The original high-pedal-response & C=0 combination transfers
## directly to 726D, bypassing the WHOLE later motion chain. Never
## simulate 71FA/7225/7245 on that branch.

const SHORT_CIRCUIT_PC: int = 0x726D
const XROM_ENTRY_PC: int = 0x71FF
const CLAMP_ENTRY_PC: int = 0x7225


static func calculate(pedal_response: int,
                      original_b: int,
                      original_c: int,
                      original_ix_minus_0b: int,
                      original_e76c: int) -> Dictionary:
    assert(pedal_response >= 0 and pedal_response <= 255)
    assert(original_b >= 0 and original_b <= 255)
    assert(original_c >= 0 and original_c <= 255)
    assert(original_ix_minus_0b >= 0 and original_ix_minus_0b <= 255)
    assert(original_e76c >= 0 and original_e76c <= 255)

    if pedal_response >= 16:
        if original_c == 0:
            return {
                "exit": "skip_direct_726D",
                "next_pc": SHORT_CIRCUIT_PC,
                "de": null,
                "source": "car_response_ge_16_C_zero"
            }
        return {
            "exit": "zero_contribution_71FF",
            "next_pc": XROM_ENTRY_PC,
            "de": 0,
            "source": "car_response_ge_16_C_nonzero"
        }

    # Original X-ROM slot1 unsigned rounded byte product. Genuine
    # 71D9 instructions then DOUBLE IN 8 BITS before shifting four.
    var product: int = (original_b * original_ix_minus_0b + 128) >> 8
    var amount: int = (((product << 1) & 255) << 4) & 65535

    # Original byte at E76C is tested by sign bit, not by whether
    # motion is nonzero. The stage negates the entire wrapped DE.
    if (original_e76c & 0x80) != 0:
        amount = (-amount) & 65535

    if original_c == 0:
        return {
            "exit": "skip_xrom_7225",
            "next_pc": CLAMP_ENTRY_PC,
            "de": amount,
            "source": "original_71D9_displacement"
        }

    return {
        "exit": "original_xrom_71FF",
        "next_pc": XROM_ENTRY_PC,
        "de": amount,
        "source": "original_71D9_displacement"
    }
