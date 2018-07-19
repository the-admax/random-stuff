#!/usr/bin/python3.6

from textwrap import wrap, indent, dedent
import math as m
from string import printable

morse = {
        'A': '.-',
        'B': '-...',
        'C': '-.-.',
        'D': '-..',
        'E': '.',
        'F': '..-.',
        'G': '--.',
        'H': '....',
        'I': '..',
        'J': '.---',
        'K': '-.-',
        'L': '.-..',
        'M': '--',
        'N': '-.',
        'O': '---',
        'P': '.--.',
        'Q': '--.-',
        'R': '.-.',
        'S': '...',
        'T': '-',
        'U': '..-',
        'V': '...-',
        'W': '.--',
        'X': '-..-',
        'Y': '-.--',
        'Z': '--..',
# numbers
        '0': '-----',
        '1': '.----',
        '2': '..---',
        '3': '...--',
        '4': '....-',
        '5': '.....',
        '6': '-....',
        '7': '--...',
        '8': '---..',
        '9': '----.',
# punctuation
        '.': '.-.-.-',
        ',': '--..--',
        '?': '..--..',
        '!': '-.-.--',
        '`': '.----.',
        '/': '-..-.',
        '&': '.-...',
        ':': '---...',
        ';': '-.-.-.',
        '=': '-...-',
        '+': '.-.-.',
        '-': '-....-',
        '(': '-.--.',
        ')': '-.--.-',
        '_': '..--.-',
        '"': '.-..-.',
        '$': '...-..-',
        '@': '.--.-.',

#         'error': '........'
    }


for i,c in enumerate(range(ord('!'), ord('a'))):
    print(chr(c) if chr(c) in morse else ' ', end='')
    if (i % 16 == 15):
        print()
    else:
        print(' ', end='')

    

def pack_code(rep):
    """
    Encodes symbolic Morse repr as binary
    >>> pack_code("--.---")
    (0b111011, 6)
    >>> pack_code("-.")
    (0b10, 2)
    """
    
    return (sum((1 if c == '-' else 0) << i for i, c in enumerate(rep)), len(rep))

def unpack_code(enc_code):
    code, n = enc_code
    return ''.join(('-' if code & (1 << (n-1-i)) else '.') for i in range(n))
        

for ch, coding in morse.items():
    enc = pack_code(coding) 
    #print("%c: [%d] %s, %s" % (ch, enc[1], format(enc[0], "0"+str(enc[1])+"b"), unpack_code(enc)))
    
# print for C
itms = sorted([(ord(ch), pack_code(coding)) for ch, coding in morse.items()], key=lambda itm: itm[0])
cchi = 0
result = []
entry = None
for (chi, enc) in itms:
    if (chi - cchi >= 1) or entry is None:
        cchi = chi+1
        entry = [chi, cchi, [enc]]
        result.append(entry)
    else:
        cchi = chi+1
        entry[1] = cchi
        entry[2].append(enc)

branches = []
table_lengths = []
table_codes = []
var_name = 'c';
sym_offs_t = 'uint8_t'
consumerFunc = 'beepMorse'

offset = 0

for entry in result:
    start, end, codes = entry
    
    singular_condition = (start == end-1)
    
    if chr(start) in printable:
        start = "'%c'" % (start)
    if chr(end) in printable:
        end = "'%c'" % (end)

    if singular_condition:
        branches.append(dedent(f"""\
            if ({var_name} == {start}) {{
                sym_offs = {offset};
            }} """))
    else:
        branches.append(dedent(f"""\
        if ({var_name} >= {start} && {var_name} < {end}) {{
            sym_offs = ({var_name} - {start}) + {offset};
        }} """))
    table_codes.extend(code for code, _ in codes)
    table_lengths.extend(n for _, n in codes)
    offset += len(codes)
    
branches.append("""{
    return false;
}""")

def format_list_repr(xs, fmt_str, width=80, indent_sz=4):
    n_digits = m.ceil(m.log10(max(xs)))
    list_str = ', '.join(format(x, fmt_str[:-1] + str(n_digits) + fmt_str[-1]) for x in xs)    
    out = ''
    for line in wrap(list_str, width):
        out += '\n' + ' '*indent_sz + line
    return out + '\n'
    
print(f"// Len(morse) = {len(morse)}")
print(f"static const uint8_t table_codes[{len(table_codes)}] PROGMEM = {{ "
      f"{format_list_repr(table_codes, '#0b')} }};")
print(f"static const uint8_t table_lengths[{len(table_lengths)}] PROGMEM = {{ "
      f"{format_list_repr(table_lengths, 'd')} }};")
print(f"""\
bool beepMorse(char c) {{
    {sym_offs_t} sym_offs;

    {indent(" else ".join(branches), '    ')}

    uint8_t n_bits = table_lengths[sym_offs];
    uint8_t word = table_codes[sym_offs];
    uint16_t symTime = dotDuration;
    while(n_bits-- > 0) {{
        tone(PIN_SOUND_OUTPUT, TX_BEEP_FREQ);
        delay((word & 1)? TX_MORSE_DASH_TIME : TX_MORSE_DOT_TIME);
        noTone(PIN_SOUND_OUTPUT);
        delay(TX_MORSE_DOT_TIME);

        word >>= 1;
    }}
    return true;
}}
""")
