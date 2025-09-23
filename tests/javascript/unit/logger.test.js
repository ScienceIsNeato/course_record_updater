const Logger = require('../../../static/logger');

describe('Logger', () => {
  let consoleErrorSpy;
  let consoleWarnSpy;
  let consoleLogSpy;

  beforeEach(() => {
    Logger.setLevel(Logger.LEVELS.INFO);
    consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
    consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation(() => {});
    consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
  });

  afterEach(() => {
    consoleErrorSpy.mockRestore();
    consoleWarnSpy.mockRestore();
    consoleLogSpy.mockRestore();
  });

  it('logs info at default level', () => {
    Logger.info('Information');
    expect(consoleLogSpy).toHaveBeenCalledWith('ℹ️ Information');
  });

  it('does not log debug at info level', () => {
    Logger.debug('Debug message');
    expect(consoleLogSpy).not.toHaveBeenCalled();
  });

  it('logs debug when level set to DEBUG', () => {
    Logger.setLevel(Logger.LEVELS.DEBUG);
    Logger.debug('Debug message', { foo: 'bar' });
    expect(consoleLogSpy).toHaveBeenCalledWith('🐛 Debug message', { foo: 'bar' });
  });

  it('logs warnings and errors with metadata', () => {
    const payload = { id: 1 };
    Logger.warn('Careful', payload);
    Logger.error('Boom', payload);

    expect(consoleWarnSpy).toHaveBeenCalledWith('⚠️ Careful', payload);
    expect(consoleErrorSpy).toHaveBeenCalledWith('❌ Boom', payload);
  });
});
