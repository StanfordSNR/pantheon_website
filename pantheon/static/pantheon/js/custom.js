function set_peer_server(node) {
  var peer;

  switch (node) {
    case 'any':
      peer = 'Any';
      break;
    case 'stanford':
    case 'mexico':
      peer = 'AWS California';
      break;
    case 'brazil':
    case 'colombia':
      peer = 'AWS Brazil';
      break;
    case 'india':
    case 'nepal':
      peer = 'AWS India';
      break;
    case 'china':
      peer = 'AWS Korea';
      break;
    default:
      peer = 'Not found';
  }

  $('#peer-server').text(peer);
}

function disable_link(node) {
  var links_available_map = {
    'any': [true, true, true],
    'stanford': [true, true, false],
    'mexico': [true, true, false],
    'brazil': [true, true, false],
    'colombia': [true, true, false],
    'china': [true, true, false],
    'india': [true, true, false],
    'nepal': [false, false, true]
  };

  return function() {
    var links_available = links_available_map[node];
    if (links_available !== undefined) {
      var eth = links_available[0];
      var cell = links_available[1];
      var wifi = links_available[2];
      $("#link option[value='ethernet']").prop('disabled', !eth).toggle(eth);
      $("#link option[value='cellular']").prop('disabled', !cell).toggle(cell);
      $("#link option[value='wireless']").prop('disabled', !wifi).toggle(wifi);
    }
  }
}

$('#node').change(function() {
  var node_name = $(this).val();
  set_peer_server(node_name);
  disable_link(node_name)();
});

function set_node_options(params_json) {
  var params = JSON.parse(params_json);

  $('#node').val(params.node).change();
  $('#link').val(params.link);
  $('#direction').val(params.direction);
  $('#flows').val(params.flows);
  $('#year').val(params.year);
  $('#month').val(params.month);
}

function set_cloud_options(params_json) {
  var params = JSON.parse(params_json);

  $('#src').val(params.src);
  $('#dst').val(params.dst);
  $('#flows').val(params.flows);
  $('#year').val(params.year);
  $('#month').val(params.month);
}

function set_emu_options(params_json) {
  var params = JSON.parse(params_json);

  $('#scenario').val(params.scenario);
  $('#flows').val(params.flows);
  $('#year').val(params.year);
  $('#month').val(params.month);
}

function enable_score_hover() {
  $('.color').popover({
    trigger: "hover focus",
    container: 'body'
  });
}

$(document).on('mouseenter', '.expt-desc', function() {
  var $this = $(this);

  if (this.offsetWidth < this.scrollWidth && !$this.attr('title')) {
    $this.attr('title', $this.text());
  }
});

$(document).on('mouseenter', '.expt-date', function() {
  var $this = $(this);

  if (this.offsetWidth < this.scrollWidth && !$this.attr('title')) {
    $this.attr('title', $this.text());
  }
});
