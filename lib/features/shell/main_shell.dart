import 'package:flutter/material.dart';

import '../../core/widgets/app_sidebar.dart';

class MainShell extends StatelessWidget {
  const MainShell({super.key, required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Row(
        children: [
          const AppSidebar(),
          Expanded(child: child),
        ],
      ),
    );
  }
}
