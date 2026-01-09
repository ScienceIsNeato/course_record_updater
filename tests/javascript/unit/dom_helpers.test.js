/**
 * Unit Tests for DOM Test Helpers
 *
 * Tests the test helper functions themselves to ensure they work correctly
 * and to improve overall code coverage.
 */

const { setBody, createElement, triggerDomContentLoaded, flushPromises } = require('../helpers/dom');

describe('DOM Test Helpers', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  describe('setBody', () => {
    test('sets document body innerHTML', () => {
      const html = '<div id="test">Hello World</div>';
      setBody(html);

      expect(document.body.innerHTML).toBe(html);
      expect(document.getElementById('test')).toBeTruthy();
      expect(document.getElementById('test').textContent).toBe('Hello World');
    });

    test('returns the document body', () => {
      const result = setBody('<p>Test</p>');
      expect(result).toBe(document.body);
    });

    test('clears previous content', () => {
      setBody('<div>First</div>');
      expect(document.body.textContent).toBe('First');

      setBody('<div>Second</div>');
      expect(document.body.textContent).toBe('Second');
      expect(document.body.textContent).not.toContain('First');
    });

    test('handles empty string', () => {
      setBody('<div>Content</div>');
      setBody('');
      expect(document.body.innerHTML).toBe('');
    });
  });

  describe('createElement', () => {
    test('creates element from HTML string', () => {
      const element = createElement('<div id="test">Content</div>');
      
      expect(element).toBeInstanceOf(HTMLElement);
      expect(element.id).toBe('test');
      expect(element.textContent).toBe('Content');
    });

    test('trims whitespace from HTML', () => {
      const element = createElement('  <span>Trimmed</span>  ');
      
      expect(element).toBeInstanceOf(HTMLElement);
      expect(element.tagName).toBe('SPAN');
    });

    test('creates complex elements', () => {
      const html = '<div class="wrapper"><span class="inner">Nested</span></div>';
      const element = createElement(html);

      expect(element.className).toBe('wrapper');
      expect(element.querySelector('.inner')).toBeTruthy();
      expect(element.querySelector('.inner').textContent).toBe('Nested');
    });

    test('handles elements with attributes', () => {
      const element = createElement('<button type="submit" disabled>Click</button>');
      
      expect(element.tagName).toBe('BUTTON');
      expect(element.type).toBe('submit');
      expect(element.disabled).toBe(true);
      expect(element.textContent).toBe('Click');
    });
  });

  describe('triggerDomContentLoaded', () => {
    test('dispatches DOMContentLoaded event', () => {
      const listener = jest.fn();
      document.addEventListener('DOMContentLoaded', listener);

      triggerDomContentLoaded();

      expect(listener).toHaveBeenCalled();
      expect(listener).toHaveBeenCalledTimes(1);

      document.removeEventListener('DOMContentLoaded', listener);
    });

    test('event can be listened for multiple times', () => {
      const listener1 = jest.fn();
      const listener2 = jest.fn();
      
      document.addEventListener('DOMContentLoaded', listener1);
      document.addEventListener('DOMContentLoaded', listener2);

      triggerDomContentLoaded();

      expect(listener1).toHaveBeenCalled();
      expect(listener2).toHaveBeenCalled();

      document.removeEventListener('DOMContentLoaded', listener1);
      document.removeEventListener('DOMContentLoaded', listener2);
    });
  });

  describe('flushPromises', () => {
    test('returns a Promise', () => {
      const result = flushPromises();
      expect(result).toBeInstanceOf(Promise);
    });

    test('resolves after current promise queue', async () => {
      let resolved = false;
      Promise.resolve().then(() => {
        resolved = true;
      });

      // Before flush, promise hasn't resolved yet
      expect(resolved).toBe(false);

      // After flush, promise should be resolved
      await flushPromises();
      expect(resolved).toBe(true);
    });

    test('allows async operations to complete', async () => {
      const order = [];

      Promise.resolve().then(() => order.push(1));
      Promise.resolve().then(() => order.push(2));

      await flushPromises();

      expect(order).toEqual([1, 2]);
    });

    test('can be awaited multiple times', async () => {
      const counter = { value: 0 };

      Promise.resolve().then(() => { counter.value++; });
      await flushPromises();
      expect(counter.value).toBe(1);

      Promise.resolve().then(() => { counter.value++; });
      await flushPromises();
      expect(counter.value).toBe(2);
    });
  });
});
