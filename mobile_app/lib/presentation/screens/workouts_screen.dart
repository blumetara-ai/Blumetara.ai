import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../logic/app_state.dart';

class WorkoutsScreen extends StatefulWidget {
  const WorkoutsScreen({super.key});

  @override
  State<WorkoutsScreen> createState() => _WorkoutsScreenState();
}

class _WorkoutsScreenState extends State<WorkoutsScreen> {
  String _fitnessGoal = 'general_fitness';
  String _difficulty = 'beginner';
  final Set<int> _completedExercises = {};

  void _generate(AppState state) async {
    await state.generateWorkoutPlan(_fitnessGoal, _difficulty);
    if (mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text("AI Personalized Workout Plan Generated successfully!"),
          backgroundColor: AppConstants.accentMint,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppState>(context);
    final activePlan = state.workoutPlan;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(AppConstants.defaultPadding),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Text(
            "Fitness Plan Generator",
            style: TextStyle(
              fontSize: 24, 
              fontWeight: FontWeight.bold,
              color: AppConstants.accentMint
            ),
          ),
          const SizedBox(height: 8),
          Text(
            "AI-powered workout plans mapped directly to your profile metrics.",
            style: TextStyle(color: AppConstants.textGray),
          ),
          const SizedBox(height: 20),

          // Plan generation card
          Card(
            child: Padding(
              padding: const EdgeInsets.all(AppConstants.defaultPadding),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                children: [
                  const Text(
                    "Setup Target Parameters",
                    style: TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                  ),
                  const SizedBox(height: 12),
                  
                  // Goal Dropdown
                  DropdownButtonFormField<String>(
                    value: _fitnessGoal,
                    decoration: const InputDecoration(labelText: "Workout Goal"),
                    items: const [
                      DropdownMenuItem(value: 'fat_loss', child: Text('🔥 Fat Loss')),
                      DropdownMenuItem(value: 'muscle_gain', child: Text('💪 Muscle Gain')),
                      DropdownMenuItem(value: 'general_fitness', child: Text('⚡ General Fitness')),
                    ],
                    onChanged: (val) {
                      setState(() {
                        _fitnessGoal = val!;
                      });
                    },
                  ),
                  const SizedBox(height: 12),

                  // Difficulty Dropdown
                  DropdownButtonFormField<String>(
                    value: _difficulty,
                    decoration: const InputDecoration(labelText: "Difficulty Level"),
                    items: const [
                      DropdownMenuItem(value: 'beginner', child: Text('Beginner')),
                      DropdownMenuItem(value: 'intermediate', child: Text('Intermediate')),
                      DropdownMenuItem(value: 'advanced', child: Text('Advanced')),
                    ],
                    onChanged: (val) {
                      setState(() {
                        _difficulty = val!;
                      });
                    },
                  ),
                  const SizedBox(height: 16),

                  ElevatedButton(
                    onPressed: () => _generate(state),
                    style: ElevatedButton.styleFrom(
                      backgroundColor: AppConstants.accentMint,
                      foregroundColor: AppConstants.primaryDark,
                    ),
                    child: const Text("Generate Custom Workout Routine"),
                  )
                ],
              ),
            ),
          ),
          const SizedBox(height: 20),

          // Active routine list
          if (activePlan != null) ...[
            Text(
              "Your Active Routine",
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
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        Text(
                          activePlan.fitnessGoal.toUpperCase().replaceAll("_", " "),
                          style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 16),
                        ),
                        Chip(
                          label: Text(activePlan.difficulty),
                          backgroundColor: AppConstants.accentMint.withOpacity(0.15),
                          labelStyle: TextStyle(color: AppConstants.accentMint, fontSize: 12),
                        )
                      ],
                    ),
                    const Divider(height: 20),
                    ListView.builder(
                      shrinkWrap: true,
                      physics: const NeverScrollableScrollPhysics(),
                      itemCount: activePlan.exercises.length,
                      itemBuilder: (context, idx) {
                        final ex = activePlan.exercises[idx];
                        final isCompleted = _completedExercises.contains(idx);
                        return ListTile(
                          contentPadding: EdgeInsets.zero,
                          title: Text(
                            ex["name"],
                            style: TextStyle(
                              fontWeight: FontWeight.bold,
                              decoration: isCompleted ? TextDecoration.lineThrough : null,
                              color: isCompleted ? AppConstants.textGray : AppConstants.textWhite,
                            ),
                          ),
                          subtitle: Text(
                            "Sets: ${ex['sets']} • Reps/Target: ${ex['reps']}",
                            style: TextStyle(
                              decoration: isCompleted ? TextDecoration.lineThrough : null,
                            ),
                          ),
                          trailing: IconButton(
                            icon: Icon(
                              isCompleted ? Icons.check_circle : Icons.circle_outlined,
                              color: isCompleted ? AppConstants.accentMint : AppConstants.textGray,
                            ),
                            onPressed: () {
                              setState(() {
                                if (isCompleted) {
                                  _completedExercises.remove(idx);
                                } else {
                                  _completedExercises.add(idx);
                                }
                              });
                            },
                          ),
                        );
                      },
                    ),
                  ],
                ),
              ),
            ),
          ] else
            _buildPromptBanner(),
          const SizedBox(height: 24),
        ],
      ),
    );
  }

  Widget _buildPromptBanner() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 32.0, horizontal: 16.0),
        child: Column(
          children: [
            Icon(Icons.fitness_center, size: 40, color: AppConstants.textGray),
            const SizedBox(height: 12),
            Text(
              "No plan generated yet. Select your parameters and click Generate above to build your custom schedule.",
              textAlign: TextAlign.center,
              style: TextStyle(color: AppConstants.textGray),
            ),
          ],
        ),
      ),
    );
  }
}
