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
});

afterEach(() => {
  jest.useRealTimers();
});
