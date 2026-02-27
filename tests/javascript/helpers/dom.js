function setBody(html) {
  document.body.innerHTML = html;
  return document.body;
}

function createElement(html) {
  const template = document.createElement("template");
  template.innerHTML = html.trim();
  return template.content.firstChild;
}

function triggerDomContentLoaded() {
  document.dispatchEvent(new Event("DOMContentLoaded"));
}

function flushPromises() {
  return new Promise((resolve) => {
    Promise.resolve().then(resolve);
  });
}

module.exports = {
  setBody,
  createElement,
  triggerDomContentLoaded,
  flushPromises,
};
