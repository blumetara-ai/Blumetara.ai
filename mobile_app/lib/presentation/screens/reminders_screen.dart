import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../logic/app_state.dart';

class RemindersScreen extends StatelessWidget {
  const RemindersScreen({super.key});

  void _showAddReminderDialog(BuildContext context, AppState state) {
    final nameController = TextEditingController();
    final dosageController = TextEditingController();
    String type = 'medicine';
    TimeOfDay selectedTime = TimeOfDay.now();

    showDialog(
      context: context,
      builder: (context) {
        return StatefulBuilder(
          builder: (context, setState) {
            return AlertDialog(
              title: const Text('Add New Reminder'),
              content: SingleChildScrollView(
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    DropdownButton<String>(
                      value: type,
                      isExpanded: true,
                      items: const [
                        DropdownMenuItem(value: 'medicine', child: Text('💊 Medicine Alert')),
                        DropdownMenuItem(value: 'water', child: Text('💧 Water Reminder')),
                      ],
                      onChanged: (val) {
                        setState(() {
                          type = val!;
                        });
                      },
                    ),
                    const SizedBox(height: 16),
                    if (type == 'medicine') ...[
                      TextField(
                        controller: nameController,
                        decoration: const InputDecoration(labelText: 'Medicine Name'),
                      ),
                      const SizedBox(height: 12),
                      TextField(
                        controller: dosageController,
                        decoration: const InputDecoration(labelText: 'Dosage (e.g. 1 Tablet)'),
                      ),
                      const SizedBox(height: 16),
                    ],
                    Row(
                      mainAxisAlignment: MainAxisAlignment.between,
                      children: [
                        Text("Selected Time: ${selectedTime.format(context)}"),
                        ElevatedButton(
                          onPressed: () async {
                            final TimeOfDay? picked = await showTimePicker(
                              context: context,
                              initialTime: selectedTime,
                            );
                            if (picked != null) {
                              setState(() {
                                selectedTime = picked;
                              });
                            }
                          },
                          child: const Text("Pick Time"),
                        )
                      ],
                    )
                  ],
                ),
              ),
              actions: [
                TextButton(
                  onPressed: () => Navigator.pop(context),
                  child: const Text('Cancel'),
                ),
                ElevatedButton(
                  onPressed: () {
                    final timeStr = "${selectedTime.hour.toString().padLeft(2, '0')}:${selectedTime.minute.toString().padLeft(2, '0')}";
                    state.addReminder(
                      type, 
                      timeStr, 
                      medName: type == 'medicine' ? nameController.text.trim() : null,
                      dosage: type == 'medicine' ? dosageController.text.trim() : null,
                    );
                    Navigator.pop(context);
                  },
                  child: const Text('Add'),
                )
              ],
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppState>(context);

    return Scaffold(
      floatingActionButton: FloatingActionButton(
        backgroundColor: AppConstants.accentMint,
        onPressed: () => _showAddReminderDialog(context, state),
        child: const Icon(Icons.add, color: AppConstants.primaryDark),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(AppConstants.defaultPadding),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Text(
              "Schedules & Alerts",
              style: TextStyle(
                fontSize: 24, 
                fontWeight: FontWeight.bold,
                color: AppConstants.accentMint
              ),
            ),
            const SizedBox(height: 8),
            Text(
              "Maintain your daily medication consistency and hydration logs.",
              style: TextStyle(color: AppConstants.textGray),
            ),
            const SizedBox(height: 20),

            state.reminders.isEmpty
                ? const Center(
                    child: Padding(
                      padding: EdgeInsets.symmetric(vertical: 60.0),
                      child: Text("No reminders configured yet. Add your first reminder below!"),
                    ),
                  )
                : ListView.builder(
                    shrinkWrap: true,
                    physics: const NeverScrollableScrollPhysics(),
                    itemCount: state.reminders.length,
                    itemBuilder: (context, index) {
                      final rem = state.reminders[index];
                      final isMed = rem.type == 'medicine';
                      final title = isMed ? rem.medicineDetails?.name ?? 'Medicine' : 'Drink Water';
                      final sub = isMed 
                          ? "${rem.medicineDetails?.dosage ?? '1 pill'} • Stock left: ${rem.medicineDetails?.stockCount ?? 30}"
                          : "Water Hydration Log";

                      return Card(
                        margin: const EdgeInsets.only(bottom: 12),
                        child: Padding(
                          padding: const EdgeInsets.all(8.0),
                          child: ListTile(
                            leading: CircleAvatar(
                              backgroundColor: AppConstants.accentMint.withOpacity(0.15),
                              child: Icon(
                                isMed ? Icons.medication : Icons.local_drink,
                                color: AppConstants.accentMint,
                              ),
                            ),
                            title: Text(title, style: const TextStyle(fontWeight: FontWeight.bold)),
                            subtitle: Text(sub),
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              children: [
                                Text(
                                  rem.time,
                                  style: TextStyle(
                                    fontWeight: FontWeight.bold,
                                    color: AppConstants.accentMint,
                                    fontSize: 16
                                  ),
                                ),
                                const SizedBox(width: 8),
                                IconButton(
                                  icon: const Icon(Icons.check_circle_outline, color: AppConstants.accentMint),
                                  onPressed: () {
                                    state.logReminderAdherence(rem.id, "taken");
                                    ScaffoldMessenger.of(context).showSnackBar(
                                      SnackBar(
                                        content: Text("Logged: Completed schedule for $title"),
                                        backgroundColor: AppConstants.accentMint,
                                      ),
                                    );
                                  },
                                )
                              ],
                            ),
                          ),
                        ),
                      );
                    },
                  )
          ],
        ),
      ),
    );
  }
}
