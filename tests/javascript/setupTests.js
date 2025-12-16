require('@testing-library/jest-dom');

const modalInstances = new WeakMap();

class BootstrapModalMock {
  constructor(element) {
    this.element = element;
    this.visible = false;
    modalInstances.set(element, this);
  }

  show() {
    this.visible = true;
  }

  hide() {
    this.visible = false;
  }

  static getInstance(element) {
    return modalInstances.get(element);
  }
}

Object.defineProperty(global, 'bootstrap', {
  configurable: true,
  writable: true,
  value: { Modal: BootstrapModalMock }
});

// jsdom doesn't implement scrollTo; some dashboard code uses it.
try {
  Object.defineProperty(globalThis, 'scrollTo', { configurable: true, writable: true, value: jest.fn() });
} catch {
  // ignore
}

// jsdom navigation is limited; prevent hard failures when code calls location APIs.
try {
  Object.defineProperty(globalThis.location, 'assign', { configurable: true, value: jest.fn() });
  Object.defineProperty(globalThis.location, 'replace', { configurable: true, value: jest.fn() });
  Object.defineProperty(globalThis.location, 'reload', { configurable: true, value: jest.fn() });
} catch {
  // Ignore if jsdom marks these as non-configurable in this environment.
}

if (!HTMLElement.prototype.scrollIntoView) {
  HTMLElement.prototype.scrollIntoView = jest.fn();
}

Object.defineProperty(globalThis, 'matchMedia', {
  writable: true,
  value: jest.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: jest.fn(),
    removeListener: jest.fn(),
    addEventListener: jest.fn(),
    removeEventListener: jest.fn(),
    dispatchEvent: jest.fn()
  }))
});

beforeEach(() => {
  jest.clearAllMocks();
  document.body.innerHTML = '';
  document.head.innerHTML = '';
  global.fetch = jest.fn();
  global.confirm = jest.fn(() => true);
  global.alert = jest.fn();
});

afterEach(() => {
  jest.useRealTimers();
});
