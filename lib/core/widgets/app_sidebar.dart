import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../services/auth_service.dart';
import '../constants/app_constants.dart';
import '../theme/app_theme.dart';

class AppSidebar extends StatelessWidget {
  const AppSidebar({super.key});

  static const _items = [
    _NavItem('/dashboard', Icons.dashboard_outlined, 'Dashboard'),
    _NavItem('/tutorials', Icons.menu_book_outlined, 'Tutorials'),
    _NavItem('/movements', Icons.play_circle_outline, 'Start Practice'),
    _NavItem('/camera-test', Icons.videocam_outlined, 'Camera Test'),
    _NavItem('/history', Icons.history, 'History'),
    _NavItem('/progress', Icons.trending_up, 'Progress'),
    _NavItem('/safety', Icons.health_and_safety_outlined, 'Safety Guide'),
    _NavItem('/settings', Icons.settings_outlined, 'Settings'),
  ];

  @override
  Widget build(BuildContext context) {
    final location = GoRouterState.of(context).uri.path;
    final auth = context.watch<AuthService>();
    final user = auth.currentUser;

    return Container(
      width: 220,
      color: AppColors.card,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  AppConstants.appName,
                  style: Theme.of(context).textTheme.titleLarge?.copyWith(
                        color: AppColors.primary,
                        fontWeight: FontWeight.bold,
                      ),
                ),
                if (user != null) ...[
                  const SizedBox(height: 4),
                  Text(
                    user.fullName,
                    style: Theme.of(context).textTheme.bodySmall,
                    overflow: TextOverflow.ellipsis,
                  ),
                ],
              ],
            ),
          ),
          const Divider(height: 1),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(vertical: 8),
              children: [
                for (final item in _items)
                  _SidebarTile(
                    item: item,
                    selected: location.startsWith(item.path),
                    onTap: () => context.go(item.path),
                  ),
              ],
            ),
          ),
          const Divider(height: 1),
          ListTile(
            leading: const Icon(Icons.logout, color: AppColors.error),
            title: const Text('Logout', style: TextStyle(color: AppColors.error)),
            onTap: () async {
              await auth.logout();
              if (context.mounted) context.go('/login');
            },
          ),
        ],
      ),
    );
  }
}

class _NavItem {
  const _NavItem(this.path, this.icon, this.label);

  final String path;
  final IconData icon;
  final String label;
}

class _SidebarTile extends StatelessWidget {
  const _SidebarTile({
    required this.item,
    required this.selected,
    required this.onTap,
  });

  final _NavItem item;
  final bool selected;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return ListTile(
      leading: Icon(
        item.icon,
        color: selected ? AppColors.primary : AppColors.textSecondary,
      ),
      title: Text(
        item.label,
        style: TextStyle(
          color: selected ? AppColors.primary : AppColors.textPrimary,
          fontWeight: selected ? FontWeight.w600 : FontWeight.normal,
        ),
      ),
      selected: selected,
      selectedTileColor: AppColors.primary.withValues(alpha: 0.1),
      onTap: onTap,
    );
  }
}
