# coding: utf-8

"""
Simple script to recover deleted files from raw partition image.

Initial Author: Andrew D. <the-admax@yandex.ru>
License: MIT
Year of creation: 2015
Year of publication: 2016

"""

# TODO: Argument parsing (and options)
# TODO: Dialog interface
# TODO: Extract file signatures (from 'file' utility)
# TODO: Distributed search

file_begin = b"""<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE eagle SYSTEM "eagle.dtd">"""

file_ending = b'</eagle>'

import re, sys, tempfile, logging, io, string, blessings

def size_fmt(num, suffix='B'):
    for unit in ['','Ki','Mi','Gi','Ti','Pi','Ei','Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)
    
def find_first_garbage(data):
  for (i, c) in enumerate(data):
    if isinstance(c, int):
      c = chr(c)
    if c not in string.printable:
      return i
    

offs_start = -74
CHUNK_SIZE = 8192*1024


logging.basicConfig(level=logging.DEBUG)

ui_term = blessings.Terminal()


tmp_dir = 'eagle_recovery'
with open(sys.argv[1], 'rb') as part_f:
  #for offs in offsets:
  found = False
  percentage = 0
  max_offs = part_f.seek(0, io.SEEK_END)
    
  offs = 0
  if len(sys.argv) > 2:
    offs = int(sys.argv[2])
    assert 0 <= offs <= max_offs
  part_f.seek(offs)
   
  logging.info("Total file size %s (%d chunks of size %s). Starting from %d" % (size_fmt(max_offs), max_offs // CHUNK_SIZE, size_fmt(CHUNK_SIZE), offs))
 
  while True:
    current_chunk_offs = part_f.tell()
    input_data = part_f.read(CHUNK_SIZE) + part_f.peek(len(file_begin))

    if (percentage - 100000 * current_chunk_offs // max_offs) < 0:
      percentage = int(current_chunk_offs / max_offs * 100000)
      with ui_term.location(x=0):
        print("Examing %.3f%% of disk..." % (percentage/1000,), end='\r')
    
    if not len(input_data):
      break
    offs = input_data.find( file_begin )
    if offs >= 0:
      output_filename = tmp_dir + ("/eagle_%d.file" % (current_chunk_offs,))
      logging.info("Found EAGLE signature at 0x%0x of '%s'. Dumping to '%s'" % (current_chunk_offs, part_f.name, output_filename) )

      #part_f.seek(offs + offs_start)
      output_buffer = io.BytesIO()
    
      while True:
        if offs < 0:
          input_data = part_f.read(CHUNK_SIZE) + part_f.peek(len(file_ending))
        else:
          input_data = input_data[offs:]
        offs = 0
        end_offs = input_data.find( file_ending )
        if end_offs < 0:
          # Check if input_data contains garbage
          g_offs = find_first_garbage(input_data)
          if g_offs is not None:
            output_filename += '.partial'
            output_buffer.write(input_data[:g_offs])
            break
          else:
            output_buffer.write(input_data)
        else:
          output_buffer.write(input_data[:end_offs+len(file_ending)])
          break

      output_data = output_buffer.getvalue()
      with open(output_filename, 'wb') as output_file:
        output_file.write( output_data )

      logging.info("Written {size} to {filename}".format( size=size_fmt(len(output_data))
                                                      , filename=output_filename ))
  logging.info("Done! Now inspect the '%s' directory and validate results!" % (tmp_dir,))
