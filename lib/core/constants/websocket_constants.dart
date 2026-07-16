class WebSocketConstants {
  static const defaultHost = '127.0.0.1';
  static const defaultPort = 8000;
  static const defaultPath = '/ws';
  static const healthPath = '/health';

  static String get defaultUrl =>
      'ws://$defaultHost:$defaultPort$defaultPath';

  static String get healthUrl =>
      'http://$defaultHost:$defaultPort$healthPath';
}
