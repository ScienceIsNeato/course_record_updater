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

  // COMPLETE BRANCH COVERAGE - Test all code paths
  it('logs error without data', () => {
    Logger.error('Error without data');
    expect(consoleErrorSpy).toHaveBeenCalledWith('❌ Error without data');
  });

  it('logs warn without data', () => {
    Logger.warn('Warning without data');
    expect(consoleWarnSpy).toHaveBeenCalledWith('⚠️ Warning without data');
  });

  it('logs info without data', () => {
    Logger.info('Info without data');
    expect(consoleLogSpy).toHaveBeenCalledWith('ℹ️ Info without data');
  });

  it('logs debug without data when level is DEBUG', () => {
    Logger.setLevel(Logger.LEVELS.DEBUG);
    Logger.debug('Debug without data');
    expect(consoleLogSpy).toHaveBeenCalledWith('🐛 Debug without data');
  });

  it('does not log error when level is below ERROR', () => {
    Logger.setLevel(-1); // Below ERROR level
    Logger.error('Should not appear');
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it('does not log warn when level is below WARN', () => {
    Logger.setLevel(Logger.LEVELS.ERROR);
    Logger.warn('Should not appear');
    expect(consoleWarnSpy).not.toHaveBeenCalled();
  });

  it('does not log info when level is below INFO', () => {
    Logger.setLevel(Logger.LEVELS.WARN);
    Logger.info('Should not appear');
    expect(consoleLogSpy).not.toHaveBeenCalled();
  });

  it('logs all messages at DEBUG level', () => {
    Logger.setLevel(Logger.LEVELS.DEBUG);
    Logger.error('Error');
    Logger.warn('Warn');
    Logger.info('Info');
    Logger.debug('Debug');
    expect(consoleErrorSpy).toHaveBeenCalledTimes(1);
    expect(consoleWarnSpy).toHaveBeenCalledTimes(1);
    expect(consoleLogSpy).toHaveBeenCalledTimes(2); // info + debug
  });
});
