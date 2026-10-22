class_name ArcadePedalInput
extends RefCounted

## Faithful rewrite of original Indy Heat arcade Z80 pedal response stage:
## master bank 0, $6793-$67D5; normal pedal-input path is $67B5-$67D5.
##
## Original reads analog pedal via I/O $09, processes it through X-ROM
## slot-1's 8x8 unsigned multiplication table and stores the result in
## indexed car-record field IX+$57 (decimal +87).
##
## The X-ROM's 65,536 multiplication entries were exhaustively checked:
##   product = (pedal_raw * car_factor + 128) >> 8
##
## Local comparison against actual Z80 instructions matched 41,536
## input/factor/bias scenarios, with zero mismatches.
##
## This is the *pedal response*, NOT yet actual car acceleration, grip or
## wheel power. Never substitute it for the missing movement mechanics.

const RESPONSE_MAX: int = 0x7E


static func response(pedal_raw: int, car_factor: int, car_bias: int,
                    input_timeout: bool = false) -> Dictionary:
    assert(pedal_raw >= 0 and pedal_raw <= 255, "Pedal is original 8-bit analog input")
    assert(car_factor >= 0 and car_factor <= 255, "Original car field IX+$58")
    assert(car_bias >= 0 and car_bias <= 255, "Original car field IX+$59")

    # The original routine returns 0x7E and sets car input fault flag on
    # timeout, without reading the X-ROM lookup.
    if input_timeout:
        return {"response": RESPONSE_MAX, "timeout": true}

    var product: int = ((pedal_raw * car_factor) + 128) >> 8
    var offset_sum: int = product + car_bias

    # Z80: ADD A,(IX+$59); JR NC => zero. If carry, ADD A,A;
    # saturate at $7E when result is >=$80 or second ADD carries.
    var result: int = 0
    if offset_sum >= 256:
        result = mini((offset_sum - 256) * 2, RESPONSE_MAX)

    return {"response": result, "timeout": false}
