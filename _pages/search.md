---
layout: single
title: "Search"
permalink: /search/
author_profile: false
classes: wide
---

{% include base_path %}

<div class="search-page">
  <div class="search-field">
    <input type="text" id="search-input" placeholder="Search articles, notes, projects..." autofocus>
    <span class="search-field__icon">🔍</span>
  </div>

  <div id="search-results" class="search-results"></div>

  <div id="search-init-message" class="search-init-message">
    <p>Type something to search across all content on this site.</p>
  </div>
</div>

<script src="{{ base_path }}/assets/js/simple-jekyll-search.min.js"></script>
<script>
(function() {
  var searchInput = document.getElementById('search-input');
  var resultsContainer = document.getElementById('search-results');
  var initMessage = document.getElementById('search-init-message');

  var sjs = SimpleJekyllSearch({
    searchInput: searchInput,
    resultsContainer: resultsContainer,
    json: '{{ base_path }}/assets/search-data.json',
    searchResultTemplate: '<article class="search-result"><h3 class="search-result__title"><a href="{url}">{title}</a></h3><p class="search-result__excerpt">{excerpt}</p><div class="search-result__meta"><time>{date}</time><span class="search-result__tags">{tags}</span></div></article>',
    noResultsText: '<div class="search-no-results"><p>No results found. Try different keywords.</p></div>',
    limit: 20,
    fuzzy: true
  });

  searchInput.addEventListener('input', function() {
    if (this.value.trim().length > 0) {
      initMessage.style.display = 'none';
    } else {
      initMessage.style.display = 'block';
      resultsContainer.innerHTML = '';
    }
  });
})();
</script>
