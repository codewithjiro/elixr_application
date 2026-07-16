import 'package:flutter_test/flutter_test.dart';

import 'package:elixr_application/core/constants/app_constants.dart';

void main() {
  test('app constants are defined', () {
    expect(AppConstants.appName, 'ELIXR');
  });
}
