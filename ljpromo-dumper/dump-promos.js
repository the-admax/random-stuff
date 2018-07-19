

/* Usage:
 * 1) Start server at localhost
 * 2) Go to http://www.livejournal.com/ratings/posts/?custom=0
 * 3) Run this script from browser console in context of opened page at step 2.
 * 4) Run fetch_promo_items(offset, [config])
 * 5) ???
 * 6) PROFIT!!!
 */


function fetch_promo_items(initial_offset, given_config) {
  var config = $.extend({
    type: 'entry',   // Type of posts: 'entry' or 'journal'
    max_iters: -1,   // Max. overall fetches made. Default: -1 (infinte)
    step: 5,         // Number of entries fetched per call
    region: 'cyr',   // Region of journals to consider
    max_errors: 5,   // Max number of errors to get prior quitting
    lower_date: Date.parse('2010-12-01'), // Lower bound of timespan of interest
    server_url: 'localhost:8080', // Server hostname and port used to upload data to
  }, given_config);

  initial_offset = initial_offset || 1;

  /// Additional components and functions

  function PostsUploader(url, frame_id) {
    frame_id = frame_id || (Math.random() * 1000000000 | 0);
    
    var iframe = document.createElement("iframe");
    document.body.appendChild(iframe);
    iframe.style.display = "none";
    iframe.contentWindow.name = frame_id;

    var form = this.__form = document.createElement("form");
    form.target = frame_id;
    form.action = url;
    form.method = "POST";
    document.body.appendChild(form);

    var input = this.__input = document.createElement("input");
    input.type = "hidden";
    input.name = "items";
    form.appendChild(input);
  }

  PostsUploader.prototype.postData = function(data) {
    this.__input.value = JSON.stringify(data)
    this.__form.submit();
  };
  
  // Prepare output
  jQuery('#content-wrapper .statistics')
    .one()
    .empty()
    .append('<pre id="-my-promo-posts"></pre>');
    //.append('<table id="-my-promo-posts"></table>');

  var uploader = new PostsUploader("http://" + config['server_url'] + "/save-items?type=" + type);
  
  var $posts_stats = jQuery('#-my-promo-posts');
  //$posts.append( posts_make_line('PUB_DATE POST_URL REPLY_COUNT JOURNAL_ID'.split(' '), 'th') );

  function posts_make_line(items, type) {
    return items.join('\t') + '\n';
  }
  
/*  function posts_make_line(items, type) {
    type = type || 'td';
    tags = ['<'+type+'>', '</'+type+'>']
    function item_process(item) {
      return tags[0] + item + tags[1];
    }
    
    return '<tr>' + items.map(item_process).join(' ') + '</tr>';
  }*/

  function prepare_object(obj, type) {
    var fields, result = {};
    obj.url = obj.object_url;
    if (type == 'entry') {
      fields = 'id pub_date journal_id url reply_count subject body'.split(' ');
      obj.id = obj.post_id;
    } else if (type == 'journal') {
      fields = ['id', 'promo_id', 'url', 'title', 'username'];
      obj.id = obj.journal_id;
    }
    
    fields.forEach(function(name) { result[name] = obj[name]; });
    return result;
  }

  /// Function body itself

  var max_pub_date = Date.now();
  var error_count = 0;
  var item_count = 0;
  var iters = 0;

  // We use function instead of loop because each iteration is started from previous with delay in case of error.
  function _iter_fn(offset) {
    if (iters == config['max_iters'])
      return;
    else if (iters < config['max_iters'])
      ++iters;
    
    LJ.Api.call('selfpromo.get_list',
                 { limit: -config['step'],
                   offset: -offset,
                   region: config['region'],
                   type: config['type']
                 })
      .done(function(data)
    {
      try {
        if (data.error) {
          error_count += 1;
          console.warn('Remote-Error: ' + data.error.message, 'Misses-Left: ' + (config.max_errors - error_count));
        } else {
          slots = data.result.slots;
          if (slots.length == 0) {
            error_count += 1;
            console.warn('Local-Warn: No items got', 'Misses-Left: ' + (config.max_errors - error_count));
          } else {
            error_count = 0;
            var items = [];
            var max_group_pub_date = 0;
            for(var i = 0; i < slots.length; ++i) {
              var item = slots[i].object[0];
              if (item.pub_date !== null) {
                pub_date = Date.parse(item.pub_date);
                max_group_pub_date = Math.max(max_group_pub_date, pub_date);
              }
              item.promo_id = slots[i].promo_id

              item_count += 1;

              items.add( prepare_object(item, type) );
            }

            // Upload items
            uploader.postData(items);

            if (max_group_pub_date > 0)
              max_pub_date = Math.min(max_pub_date, max_group_pub_date);

            // Update statistics
            $posts_stats.html(item_count + ' items uploaded, max-date: ' + (new Date(max_pub_date)));
          }
          if ((config['max_errors'] > error_count) && (max_pub_date >= config['lower_date'])) {
            setTimeout(_iter_fn.bind(null, offset + config['step']),
                      500*(error_count + 1));
          } else if (config['max_errors'] > error_count) {
            console.log('SUCCESS! Got ' + item_count + ' items');
          }
        }
      } catch(e) {
        console.error('ERROR: Fetching aborted because of error:', e, e.stack);
      }
    });
  }
  _iter_fn(initial_offset);
}

//fetch_promo_items(1, 'journal')
