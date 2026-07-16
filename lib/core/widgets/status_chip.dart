import 'package:flutter/material.dart';

import '../constants/app_constants.dart';
import '../theme/app_theme.dart';

class StatusChip extends StatelessWidget {
  const StatusChip({super.key, required this.status, this.animate = true});

  final String status;
  final bool animate;

  Color get _color {
    switch (status) {
      case AppConstants.resultPassed:
        return AppColors.success;
      case AppConstants.resultFailed:
        return AppColors.error;
      case AppConstants.resultPartial:
        return AppColors.warning;
      case AppConstants.resultNotAssessed:
        return AppColors.textSecondary;
      case AppConstants.resultInProgress:
        return AppColors.secondary;
      default:
        return AppColors.textSecondary;
    }
  }

  String get _label {
    switch (status) {
      case AppConstants.resultPassed:
        return 'Passed';
      case AppConstants.resultFailed:
        return 'Failed';
      case AppConstants.resultPartial:
        return 'Partial';
      case AppConstants.resultNotAssessed:
        return 'Not assessed';
      case AppConstants.resultInProgress:
        return 'In progress';
      default:
        return status;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AnimatedSwitcher(
      duration: animate ? const Duration(milliseconds: 200) : Duration.zero,
      child: Container(
        key: ValueKey(status),
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
        decoration: BoxDecoration(
          color: _color.withValues(alpha: 0.15),
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: _color.withValues(alpha: 0.5)),
        ),
        child: Text(
          _label,
          style: TextStyle(
            color: _color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
