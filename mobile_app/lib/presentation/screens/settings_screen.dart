import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../logic/app_state.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _nameController = TextEditingController();
  String _ageRange = '25-34';
  String _gender = 'Male';

  @override
  void initState() {
    super.initState();
    final state = Provider.of<AppState>(context, listen: false);
    _nameController.text = state.profile?.name ?? '';
    _ageRange = state.profile?.ageRange ?? '25-34';
    _gender = state.profile?.gender ?? 'Male';
  }

  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }

  void _save(AppState state) async {
    await state.updateProfile(
      _nameController.text.trim(),
      _ageRange,
      _gender,
    );
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("Profile details updated successfully!"),
          backgroundColor: AppConstants.accentMint,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppState>(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppConstants.defaultPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            "Account Settings",
            style: TextStyle(
              fontSize: 24, 
              fontWeight: FontWeight.bold,
              color: AppConstants.accentMint
            ),
          ),
          const SizedBox(height: 20),

          // Profile Update Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppConstants.defaultPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    "Personal Demographics",
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 12),
                  TextField(
                    controller: _nameController,
                    decoration: const InputDecoration(labelText: "Display Name"),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _ageRange,
                    decoration: const InputDecoration(labelText: "Age range"),
                    items: const [
                      DropdownMenuItem(value: 'Under 18', child: Text('Under 18')),
                      DropdownMenuItem(value: '18-24', child: Text('18-24')),
                      DropdownMenuItem(value: '25-34', child: Text('25-34')),
                      DropdownMenuItem(value: '35-44', child: Text('35-44')),
                      DropdownMenuItem(value: '45+', child: Text('45+')),
                    ],
                    onChanged: (val) => setState(() => _ageRange = val!),
                  ),
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    value: _gender,
                    decoration: const InputDecoration(labelText: "Gender"),
                    items: const [
                      DropdownMenuItem(value: 'Male', child: Text('Male')),
                      DropdownMenuItem(value: 'Female', child: Text('Female')),
                      DropdownMenuItem(value: 'Other', child: Text('Other')),
                    ],
                    onChanged: (val) => setState(() => _gender = val!),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton(
                    onPressed: () => _save(state),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppConstants.accentMint,
                      foregroundColor: AppConstants.primaryDark,
                    ),
                    child: const Text("Save Changes"),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Locked Food Tracking Feature (Coming Soon!)
          Card(
            color: Colors.grey.withOpacity(0.05),
            child: Padding(
              padding: const EdgeInsets.all(AppConstants.defaultPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        "🥗 Food Ingestion & Tracker",
                        style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 4),
                        decoration: BoxDecoration(
                          color: AppConstants.accentMint.withOpacity(0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          "COMING SOON",
                          style: TextStyle(
                            color: AppConstants.accentMint,
                            fontSize: 10,
                            fontWeight: FontWeight.bold
                          ),
                        ),
                      )
                    ],
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Our upcoming update will feature barcode scanner logs, calorie metrics, "
                    "protein calculators, and custom AI meal suggestions grounded in your active health reports.",
                    style: TextStyle(fontSize: 13, color: AppConstants.textGray),
                  ),
                  const SizedBox(height: 12),
                  ElevatedButton.icon(
                    onPressed: null, // Disabled
                    icon: const Icon(Icons.lock_outline),
                    label: const Text("Log Meals (Locked)"),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Subscriptions Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppConstants.defaultPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    "Premium Subscriptions",
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Gain access to 20 chats/day, multiple reminders, custom schedules, and priority support.",
                    style: TextStyle(fontSize: 13, color: AppConstants.textGray),
                  ),
                  const SizedBox(height: 16),
                  OutlinedButton(
                    onPressed: () {
                      _showSubscriptionSuccessDialog(context);
                    },
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppConstants.accentMint,
                      side: BorderSide(color: AppConstants.accentMint),
                    ),
                    child: const Text("Unlock Premium Plan — \$4.99/mo"),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 32),

          // Log Out
          ElevatedButton(
            onPressed: () => state.logout(),
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.errorRed,
              foregroundColor: AppConstants.textWhite,
            ),
            child: const Text("Sign Out of Session"),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  void _showSubscriptionSuccessDialog(BuildContext context) {
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: const Text('Unlock Premium Plan'),
          content: const Text(
            'This action triggers our secure Stripe/Razorpay payment gateway APIs (Subscription-Ready Architecture enabled).\n\n'
            'Confirm payment simulation of \$4.99/month?'
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            ElevatedButton(
              onPressed: () {
                Navigator.pop(context);
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text("Subscription successfully simulated! Access limits upgraded to Premium."),
                    backgroundColor: AppConstants.accentMint,
                  ),
                );
              },
              child: const Text('Simulate Checkout'),
            )
          ],
        );
      },
    );
  }
}
