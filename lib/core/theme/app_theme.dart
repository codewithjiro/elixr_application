import 'package:flutter/material.dart';

class AppColors {
  static const background = Color(0xFF0D0D0F);
  static const card = Color(0xFF1A1A1F);
  static const primary = Color(0xFFFF4D8D);
  static const secondary = Color(0xFFFF7EB3);
  static const textPrimary = Color(0xFFF5F5F5);
  static const textSecondary = Color(0xFFA0A0A8);
  static const success = Color(0xFF6EE7B7);
  static const warning = Color(0xFFFBBF24);
  static const error = Color(0xFFFF6B6B);
}

class AppTheme {
  static ThemeData get dark {
    const colorScheme = ColorScheme.dark(
      surface: AppColors.background,
      primary: AppColors.primary,
      secondary: AppColors.secondary,
      error: AppColors.error,
      onSurface: AppColors.textPrimary,
      onPrimary: Colors.white,
    );

    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      scaffoldBackgroundColor: AppColors.background,
      colorScheme: colorScheme,
      cardColor: AppColors.card,
      cardTheme: const CardThemeData(
        color: AppColors.card,
        elevation: 0,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
        ),
      ),
      appBarTheme: const AppBarTheme(
        backgroundColor: AppColors.background,
        foregroundColor: AppColors.textPrimary,
        elevation: 0,
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.card,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(8),
          borderSide: BorderSide.none,
        ),
        labelStyle: const TextStyle(color: AppColors.textSecondary),
        hintStyle: const TextStyle(color: AppColors.textSecondary),
      ),
      textTheme: const TextTheme(
        bodyLarge: TextStyle(color: AppColors.textPrimary),
        bodyMedium: TextStyle(color: AppColors.textPrimary),
        bodySmall: TextStyle(color: AppColors.textSecondary),
        titleLarge: TextStyle(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w600,
        ),
        titleMedium: TextStyle(
          color: AppColors.textPrimary,
          fontWeight: FontWeight.w600,
        ),
      ),
      dividerColor: AppColors.textSecondary.withValues(alpha: 0.2),
    );
  }
}
