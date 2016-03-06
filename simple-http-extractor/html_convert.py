#!/usr/bin/python3
# -*- encoding: utf-8 -*-

"""
Simple tool that extracts files from raw HTTP-responses.
Currently it can't handle multiple responses (e.g. continous dump)

Created: 2015-04-10
Initial commit: the-admax

See license terms in ../LICENSE.md
"""

# TODO: Work with continuous dumps (and pcap files)

import re, os, sys, glob, mimetypes, email
import glob, os.path, logging, humanize, magic

from collections import namedtuple
from functools import partial
from mimetypes import guess_extension
from argparse import ArgumentParser
from email.parser import BytesHeaderParser

# requirements: coloredlogs>=0.8, humanize>=0.5.1, python-magic>=0.4.6

try:
  import coloredlogs
  coloredlogs.install(level=logging.DEBUG)
except ImportError: pass


#### _Implementation

HTTP_HEAD = re.compile(br'^HTTP/(\d+\.\d+)\s+(\d+)\s+(.+)\s*')
SPACE = re.compile(br'\s+')
HTTPStatus = namedtuple('HTTPStatus', ('version', 'code', 'message'))

mimetypes.init()
logger = logging.getLogger(__package__ or 'html_convert')

def try_read_until(fp, pattern, chunk_size=16384):
  """
  Perform buffered read of `fp` until pattern, and return all data accumulated and ends with pattern.
  If read failed (no pattern found), file position is backtracked.
  Else: file cursor will be at position right after pattern.

  :returns: None, if EOF reached, otherwise -- the data block (bytes) with data+pattern.
  """
  assert len(pattern) > 0 and isinstance(pattern, bytes)

  chunk_size = max(chunk_size, len(pattern))

  buff = []
  tail = b''
  data = b''

  old_pos = fp.tell()

  while True:
    chunk = fp.read(chunk_size)
    if not chunk:
      break

    split_pos = (tail + chunk).find(pattern)

    if split_pos >= 0:
      split_pos += len(pattern) # Include pattern into result
      buff.append( chunk[:split_pos-len(tail)] )
      data = b''.join(buff)
      break
    else:
      tail = chunk[-len(pattern):] # Memorize last len(pattern) positions to match at next iteration
      buff.append( chunk )

  fp.seek(old_pos + len(data))
  return data or None


def file_read_magic(fp):
  # Strip off HTTP headers if any

  raw_headline = try_read_until(fp, b'\n')
  if raw_headline is None:
    return False

  if raw_headline:
    m = HTTP_HEAD.fullmatch(raw_headline)
    if m:
      http_proto, status_code, status_message = m.groups()
      return HTTPStatus( http_proto
                       , int(status_code)
                       , str(status_message, 'ascii') )
  else:
    return False


### === Header parser
headers_parser = BytesHeaderParser()
def file_read_headers(fp):
  # XXX What if server returned LFLF, and not CRLFCRLF?
  return headers_parser.parsebytes( try_read_until(fp, b'\r\n\r\n') )



### === Mime-guesser component
#_mime_guess_buff = magic.Magic(mime=True, uncompress=True).from_buffer
_mime_guess_buff = magic.Magic(mime=True).from_buffer
def guess_mimetype(fp):
  mimetype = 'application/octet-stream'
  try:
    old_pos = fp.tell()
    mimetype = _mime_guess_buff( fp.read(2048) )
  finally:
    fp.seek(old_pos)
  return mimetype


def extract_filename(msg_headers, guess_mimetype, default_filename):
  # meta = None
  # => guess from content

  # meta != None, multipart
  # => ignore (recurse?)
  #

  filename = None
  msg_mimetype = None
  if msg_headers is not None:
    if msg_headers.get_content_maintype() != 'multipart':
      # Try to take filename directly from headers
      filename = msg_headers.get_filename()
      if filename is not None:
        logger.debug("  Got filename from headers: %r", filename)
        return filename
      else:
        # Guess mimetype from headers or content
        msg_mimetype = msg_headers.get_content_type()
        if msg_mimetype == msg_headers.get_default_type():
          logger.debug("  Specified MIME-type is too generic (equals %r), planned content-assisted detection",
                       msg_headers.get_default_type())
          msg_mimetype = None
        else:  
          logger.debug("  MIME-type (from headers) = %s", msg_mimetype)
    else:
      logger.warning("We can't handle multipart data yet. Skipping file")
      raise ValueError("Can't handle multipart data")

  # Still don't have info on format? 
  if msg_mimetype is None:
    # Guess by data
    msg_mimetype = guess_mimetype()
    logger.debug("  MIME-type (from content) = %s", msg_mimetype)

  # Build a filename from pieces: basename, ext
  ext = guess_extension(msg_mimetype)
  filename = default_filename
  return filename + (ext if not filename.endswith(ext) else '')



def extract_files(input_list, output_dir):
  n_files = 0
  for infilename in input_list:
    if infilename.endswith('/'):
      # TODO Process files recursively?
      continue
    try:
      infilesize = os.path.getsize(infilename)
      logger.info("Processing '{}'...".format(infilename) )

      with open(infilename, 'rb') as infile:
        n_magics = 0
        ## HTTP-Header-Strip Service
        http_magic = file_read_magic(infile)
        if http_magic:
          n_magics += 1
          logger.debug("  Found %d-th magic header in file", n_magics)

          msg_headers = file_read_headers(infile)

          if msg_headers is not None:
            if msg_headers.get_content_maintype() == 'multipart':
              # TODO Add multipart support
              logger.warn("  Won't parse multipart/*-typed messages for now. Skipped")
              continue

            outfilename = extract_filename( msg_headers
                                          , lambda: guess_mimetype(infile)
                                          , infilename)
            outfilename = os.path.join(output_dir, os.path.basename(outfilename))

            with open(outfilename, 'wb') as outfile:
              logger.debug("  Writing '{outfilename}'...".format_map(locals()) )
              # Copy file
              outfile.write( infile.read() )
            outfilesize = humanize.naturalsize( os.path.getsize(outfilename) )
            logger.info("  Written {outfilesize} to {outfilename}".format_map(locals()))
        logger.debug("  Found {} magics in file".format(n_magics))
      n_files += 1
    except Exception as e:
      logger.error("  Caught exception: %s. Skipping." % repr(e))
      if __debug__:
        import traceback
        traceback.print_exc()

  logger.info("Done converting {n} files!".format(n=n_files))

if __name__ == '__main__':
  parser = ArgumentParser(description="Extract files from email messages and raw HTTP-responses")
  parser.add_argument('-v', '--verbose', action='count', default=0, help="Increase verbosity of output")
  parser.add_argument('-o', '--output-dir', default="out", help="Write files to directory, and create if not exist.")
  parser.add_argument('pattern', help="Pattern to match files using `glob.iglob`. Example: 'forum/index.php*'")
  args = parser.parse_args()

  logger_levels = ['WARNING', 'INFO', 'DEBUG']
  log_level = logger_levels[min(args.verbose, len(logger_levels)-1)]
  logger.setLevel( getattr(logging, log_level) )
  logger.info("Logger level set to %s", log_level)
  os.makedirs(args.output_dir, exist_ok=True)

  extract_files( glob.iglob(args.pattern), args.output_dir )
