class Profile {
  final String name;
  final String ageRange;
  final String gender;

  Profile({required this.name, required this.ageRange, required this.gender});

  factory Profile.fromJson(Map<String, dynamic> json) {
    return Profile(
      name: json['name'] ?? 'User',
      ageRange: json['ageRange'] ?? 'Unspecified',
      gender: json['gender'] ?? 'Unspecified',
    );
  }
}

class Goal {
  final String id;
  final String goalType;
  final double targetValue;
  final double currentValue;
  final String unit;
  final bool active;

  Goal({
    required this.id,
    required this.goalType,
    required this.targetValue,
    required this.currentValue,
    required this.unit,
    required this.active,
  });

  factory Goal.fromJson(Map<String, dynamic> json) {
    return Goal(
      id: json['_id'] ?? '',
      goalType: json['goalType'] ?? 'steps',
      targetValue: (json['targetValue'] ?? 0.0).toDouble(),
      currentValue: (json['currentValue'] ?? 0.0).toDouble(),
      unit: json['unit'] ?? '',
      active: json['active'] ?? true,
    );
  }
}

class MedicineDetails {
  final String name;
  final String dosage;
  final int stockCount;

  MedicineDetails({required this.name, required this.dosage, required this.stockCount});

  factory MedicineDetails.fromJson(Map<String, dynamic> json) {
    return MedicineDetails(
      name: json['name'] ?? '',
      dosage: json['dosage'] ?? '',
      stockCount: json['stockCount'] ?? 0,
    );
  }
}

class Reminder {
  final String id;
  final String type;
  final String time;
  final bool active;
  final MedicineDetails? medicineDetails;

  Reminder({
    required this.id,
    required this.type,
    required this.time,
    required this.active,
    this.medicineDetails,
  });

  factory Reminder.fromJson(Map<String, dynamic> json) {
    return Reminder(
      id: json['_id'] ?? '',
      type: json['type'] ?? 'water',
      time: json['time'] ?? '08:00',
      active: json['active'] ?? true,
      medicineDetails: json['medicineDetails'] != null 
          ? MedicineDetails.fromJson(json['medicineDetails'])
          : null,
    );
  }
}

class ChatMessage {
  final String role;
  final String content;
  final DateTime createdAt;

  ChatMessage({required this.role, required this.content, required this.createdAt});

  factory ChatMessage.fromJson(Map<String, dynamic> json) {
    return ChatMessage(
      role: json['role'] ?? 'user',
      content: json['content'] ?? '',
      createdAt: json['createdAt'] != null 
          ? DateTime.parse(json['createdAt'])
          : DateTime.now(),
    );
  }
}

class HealthReport {
  final String id;
  final String fileName;
  final String fileType;
  final String ocrStatus;
  final String summary;
  final String viewUrl;

  HealthReport({
    required this.id,
    required this.fileName,
    required this.fileType,
    required this.ocrStatus,
    required this.summary,
    required this.viewUrl,
  });

  factory HealthReport.fromJson(Map<String, dynamic> json) {
    return HealthReport(
      id: json['_id'] ?? '',
      fileName: json['fileName'] ?? '',
      fileType: json['fileType'] ?? '',
      ocrStatus: json['ocrStatus'] ?? 'pending',
      summary: json['summary'] ?? '',
      viewUrl: json['viewUrl'] ?? '',
    );
  }
}

class WorkoutPlan {
  final String fitnessGoal;
  final String difficulty;
  final List<dynamic> exercises;
  final List<dynamic> schedule;

  WorkoutPlan({
    required this.fitnessGoal,
    required this.difficulty,
    required this.exercises,
    required this.schedule,
  });

  factory WorkoutPlan.fromJson(Map<String, dynamic> json) {
    return WorkoutPlan(
      fitnessGoal: json['fitnessGoal'] ?? 'general_fitness',
      difficulty: json['difficulty'] ?? 'beginner',
      exercises: json['exercises'] ?? [],
      schedule: json['schedule'] ?? [],
    );
  }
}
