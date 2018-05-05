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

enable_score_hover();
