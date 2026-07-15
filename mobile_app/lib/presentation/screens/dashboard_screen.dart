import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../logic/app_state.dart';

class DashboardScreen extends StatelessWidget {
  const DashboardScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppState>(context);
    final userName = state.profile?.name ?? 'User';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppConstants.defaultPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          // Header / Greeting
          Row(
            mainAxisAlignment: MainAxisAlignment.between,
            children: [
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Good Morning,',
                    style: TextStyle(fontSize: 16, color: AppConstants.textGray),
                  ),
                  Text(
                    userName,
                    style: const TextStyle(fontSize: 28, fontWeight: FontWeight.bold),
                  ),
                ],
              ),
              IconButton(
                icon: Icon(Icons.notifications_outlined, color: AppConstants.accentMint),
                onPressed: () {},
              ),
            ],
          ),
          const SizedBox(height: 24),

          // Daily Dials / Focus Card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppConstants.defaultPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text(
                    "Today's Focus",
                    style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
                  ),
                  const SizedBox(height: 16),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceAround,
                    children: [
                      _buildInteractiveGoalDial(
                        context,
                        state,
                        'water',
                        'Water',
                        Icons.local_drink,
                        Colors.blue,
                        'L',
                        3.0,
                      ),
                      _buildInteractiveGoalDial(
                        context,
                        state,
                        'steps',
                        'Steps',
                        Icons.directions_run,
                        Colors.green,
                        '',
                        10000.0,
                      ),
                      _buildInteractiveGoalDial(
                        context,
                        state,
                        'sleep',
                        'Sleep',
                        Icons.nightlight_round,
                        Colors.purple,
                        'h',
                        8.0,
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Active Reminders List
          Text(
            "Today's Schedule",
            style: TextStyle(
              fontSize: 20, 
              fontWeight: FontWeight.bold,
              color: AppConstants.accentMint
            ),
          ),
          const SizedBox(height: 12),
          state.reminders.isEmpty
              ? _buildEmptyStateCard('No reminders set for today.', Icons.alarm_off)
              : ListView.builder(
                  shrinkWrap: true,
                  physics: const NeverScrollableScrollPhysics(),
                  itemCount: state.reminders.length > 3 ? 3 : state.reminders.length,
                  itemBuilder: (context, index) {
                    final rem = state.reminders[index];
                    final isMed = rem.type == 'medicine';
                    final title = isMed ? rem.medicineDetails?.name ?? 'Medication' : 'Drink Water';
                    final sub = isMed ? rem.medicineDetails?.dosage ?? '1 pill' : 'Hydration Alert';
                    return Card(
                      margin: const EdgeInsets.only(bottom: 8),
                      child: ListTile(
                        leading: Icon(
                          isMed ? Icons.medication : Icons.local_drink,
                          color: AppConstants.accentMint,
                        ),
                        title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                        subtitle: Text(sub),
                        trailing: Text(
                          rem.time,
                          style: TextStyle(
                            color: AppConstants.accentMint,
                            fontWeight: FontWeight.bold
                          ),
                        ),
                      ),
                    );
                  },
                ),
          const SizedBox(height: 20),

          // Health Report Upload Widget
          Text(
            "Upload Laboratory Reports",
            style: TextStyle(
              fontSize: 20, 
              fontWeight: FontWeight.bold,
              color: AppConstants.accentMint
            ),
          ),
          const SizedBox(height: 12),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppConstants.defaultPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    "Ingest Blood Reports & PDFs for RAG Chat Context",
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    "Parsed text will feed TARA AI's medical contextual memory.",
                    style: TextStyle(fontSize: 12, color: AppConstants.textGray),
                  ),
                  const SizedBox(height: 16),
                  ElevatedButton.icon(
                    onPressed: state.isLoading 
                        ? null 
                        : () => _simulateReportUpload(context, state),
                    icon: state.isLoading 
                        ? const SizedBox(
                            width: 16, 
                            height: 16, 
                            child: CircularProgressIndicator(strokeWidth: 2)
                          )
                        : const Icon(Icons.cloud_upload_outlined),
                    label: Text(state.isLoading ? "Analyzing Report..." : "Select & Ingest Lab Report"),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppConstants.accentMint.withOpacity(0.2),
                      foregroundColor: AppConstants.textWhite,
                      side: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                  if (state.reports.isNotEmpty) ...[
                    const Divider(height: 24),
                    const Text(
                      "Latest Ingested Report:",
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      state.reports.first.fileName,
                      style: TextStyle(fontSize: 14, color: AppConstants.accentMint),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      state.reports.first.summary.isNotEmpty
                          ? state.reports.first.summary.split("\n\n").first
                          : "Status: ${state.reports.first.ocrStatus.toUpperCase()}",
                      maxLines: 2,
                      overflow: TextOverflow.ellipsis,
                      style: const TextStyle(fontSize: 12),
                    ),
                  ]
                ],
              ),
            ),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildInteractiveGoalDial(
    BuildContext context,
    AppState state,
    String type,
    String label,
    IconData icon,
    Color color,
    String unit,
    double defaultTarget,
  ) {
    Goal? matchingGoal;
    try {
      matchingGoal = state.goals.firstWhere((g) => g.goalType == type);
    } catch (_) {
      matchingGoal = null;
    }

    final current = matchingGoal?.currentValue ?? 0.0;
    final target = matchingGoal?.targetValue ?? defaultTarget;
    final progress = target > 0 ? (current / target).clamp(0.0, 1.0) : 0.0;

    String displayVal;
    if (type == 'steps') {
      displayVal = "${current.toInt()} / ${target.toInt()}";
    } else {
      displayVal = "${current.toStringAsFixed(1)}$unit / ${target.toStringAsFixed(1)}$unit";
    }

    return GestureDetector(
      onTap: () => _showLogProgressDialog(context, state, type, matchingGoal, target, unit),
      child: Column(
        children: [
          Stack(
            alignment: Alignment.center,
            children: [
              SizedBox(
                height: 70,
                width: 70,
                child: CircularProgressIndicator(
                  value: progress,
                  strokeWidth: 6,
                  backgroundColor: color.withOpacity(0.15),
                  valueColor: AlwaysStoppedAnimation<Color>(color),
                ),
              ),
              Icon(icon, size: 28, color: color),
            ],
          ),
          const SizedBox(height: 8),
          Text(label, style: const TextStyle(fontWeight: FontWeight.bold)),
          Text(displayVal, style: TextStyle(fontSize: 12, color: AppConstants.textGray)),
        ],
      ),
    );
  }

  void _showLogProgressDialog(
    BuildContext context,
    AppState state,
    String type,
    Goal? goal,
    double target,
    String unit,
  ) {
    final valueController = TextEditingController();
    showDialog(
      context: context,
      builder: (context) {
        return AlertDialog(
          title: Text("Log ${type[0].toUpperCase()}${type.substring(1)} Progress"),
          content: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text("Add to your current daily progress (Target: $target$unit)"),
              const SizedBox(height: 16),
              TextField(
                controller: valueController,
                keyboardType: const TextInputType.numberWithOptions(decimal: true),
                style: const TextStyle(color: AppConstants.textWhite),
                decoration: InputDecoration(
                  labelText: "Value to add",
                  labelStyle: const TextStyle(color: AppConstants.textGray),
                  suffixText: unit,
                  suffixStyle: const TextStyle(color: AppConstants.accentMint),
                  enabledBorder: UnderlineInputBorder(
                    borderSide: BorderSide(color: AppConstants.textGray.withOpacity(0.5)),
                  ),
                  focusedBorder: const UnderlineInputBorder(
                    borderSide: BorderSide(color: AppConstants.accentMint),
                  ),
                ),
              ),
            ],
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text("Cancel", style: TextStyle(color: AppConstants.textGray)),
            ),
            ElevatedButton(
              onPressed: () async {
                final double? addVal = double.tryParse(valueController.text.trim());
                if (addVal != null && addVal > 0) {
                  if (goal == null) {
                    await state.addGoal(type, target, unit);
                    await state.refreshAllData();
                    Goal? newGoal;
                    try {
                      newGoal = state.goals.firstWhere((g) => g.goalType == type);
                    } catch (_) {
                      newGoal = null;
                    }
                    if (newGoal != null) {
                      await state.logGoalProgress(newGoal.id, addVal);
                    }
                  } else {
                    await state.logGoalProgress(goal.id, addVal);
                  }
                  if (context.mounted) {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text("Successfully logged progress for $type!"),
                        backgroundColor: AppConstants.accentMint,
                      ),
                    );
                  }
                }
              },
              style: ElevatedButton.styleFrom(
                backgroundColor: AppConstants.accentMint,
                foregroundColor: AppConstants.primaryDark,
              ),
              child: const Text("Log"),
            ),
          ],
        );
      },
    );
  }

  Widget _buildEmptyStateCard(String message, IconData icon) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 24.0, horizontal: 16.0),
        child: Column(
          children: [
            Icon(icon, size: 40, color: AppConstants.textGray),
            const SizedBox(height: 8),
            Text(
              message,
              textAlign: TextAlign.center,
              style: TextStyle(color: AppConstants.textGray),
            ),
          ],
        ),
      ),
    );
  }

  // Simulate file upload with mock medical document contents to keep it self-contained
  void _simulateReportUpload(BuildContext context, AppState state) async {
    final mockPdfBytes = List<int>.generate(100, (i) => i);
    final mockFileName = "BloodReport_June2026.pdf";
    await state.uploadReport(mockPdfBytes, mockFileName);
    
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("AWS Textract extraction and embedding ingestion completed! TARA now holds this report context."),
          backgroundColor: AppConstants.accentMint,
        ),
      );
    }
  }
}
