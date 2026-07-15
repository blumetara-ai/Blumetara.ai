import 'dart:convert';
import 'package:flutter/material.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:http/http.dart' as http;

import '../core/constants.dart';
import '../core/network_client.dart';
import '../data/models.dart';

class AppState extends ChangeNotifier {
  bool _isAuthenticated = false;
  String? _authToken;
  Profile? _profile;
  List<Goal> _goals = [];
  List<Reminder> _reminders = [];
  List<HealthReport> _reports = [];
  List<ChatMessage> _messages = [];
  String? _activeConversationId;
  WorkoutPlan? _workoutPlan;
  bool _isLoading = false;

  // Getters
  bool get isAuthenticated => _isAuthenticated;
  String? get authToken => _authToken;
  Profile? get profile => _profile;
  List<Goal> get goals => _goals;
  List<Reminder> get reminders => _reminders;
  List<HealthReport> get reports => _reports;
  List<ChatMessage> get messages => _messages;
  String? get activeConversationId => _activeConversationId;
  WorkoutPlan? get workoutPlan => _workoutPlan;
  bool get isLoading => _isLoading;

  AppState() {
    _loadAuthSession();
  }

  Future<void> _loadAuthSession() async {
    final prefs = await SharedPreferences.getInstance();
    final token = prefs.getString("auth_token");
    if (token != null) {
      _authToken = token;
      _isAuthenticated = true;
      networkClient.updateToken(token);
      await refreshAllData();
    }
    notifyListeners();
  }

  // Authentication Flow
  Future<bool> login(String email, String password) async {
    _isLoading = true;
    notifyListeners();
    
    // Simulate / Perform Firebase Auth mapping.
    // For development, we generate a mock token: mock_[email]
    await Future.delayed(const Duration(milliseconds: 800));
    
    final mockToken = "mock_${email.replaceAll(RegExp(r'[^a-zA-Z0-9]'), '')}";
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString("auth_token", mockToken);
    
    _authToken = mockToken;
    _isAuthenticated = true;
    networkClient.updateToken(mockToken);
    
    await refreshAllData();
    
    _isLoading = false;
    notifyListeners();
    return true;
  }

  Future<void> logout() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove("auth_token");
    _authToken = null;
    _isAuthenticated = false;
    networkClient.updateToken(null);
    _profile = null;
    _goals = [];
    _reminders = [];
    _reports = [];
    _messages = [];
    _activeConversationId = null;
    _workoutPlan = null;
    notifyListeners();
  }

  // Refresh helper
  Future<void> refreshAllData() async {
    if (!_isAuthenticated) return;
    await fetchProfile();
    await fetchGoals();
    await fetchReminders();
    await fetchReports();
    await fetchConversations();
    await fetchWorkoutPlan();
  }

  // Profile management
  Future<void> fetchProfile() async {
    try {
      final response = await networkClient.get("/users/profile");
      if (response.statusCode == 200) {
        _profile = Profile.fromJson(jsonDecode(response.body));
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Fetch profile error: $e");
    }
  }

  Future<void> updateProfile(String name, String ageRange, String gender) async {
    try {
      final response = await networkClient.put("/users/profile", {
        "name": name,
        "ageRange": ageRange,
        "gender": gender,
      });
      if (response.statusCode == 200) {
        _profile = Profile.fromJson(jsonDecode(response.body));
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Update profile error: $e");
    }
  }

  // Goal Tracking
  Future<void> fetchGoals() async {
    try {
      final response = await networkClient.get("/goals");
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _goals = data.map((g) => Goal.fromJson(g)).toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Fetch goals error: $e");
    }
  }

  Future<void> addGoal(String type, double target, String unit) async {
    try {
      final response = await networkClient.post("/goals", {
        "goalType": type,
        "targetValue": target,
        "currentValue": 0.0,
        "unit": unit,
      });
      if (response.statusCode == 200) {
        final newGoal = Goal.fromJson(jsonDecode(response.body));
        _goals.add(newGoal);
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Add goal error: $e");
    }
  }

  Future<void> logGoalProgress(String goalId, double progressVal) async {
    try {
      final response = await networkClient.post("/goals/$goalId/progress", {
        "value": progressVal,
        "notes": "Logged via App Tracker",
      });
      if (response.statusCode == 200) {
        await fetchGoals();
      }
    } catch (e) {
      debugPrint("Log progress error: $e");
    }
  }

  // Reminders
  Future<void> fetchReminders() async {
    try {
      final response = await networkClient.get("/reminders");
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _reminders = data.map((r) => Reminder.fromJson(r)).toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Fetch reminders error: $e");
    }
  }

  Future<void> addReminder(String type, String time, {String? medName, String? dosage}) async {
    try {
      final body = {
        "type": type,
        "time": time,
        "timezone": "UTC",
      };
      if (type == "medicine") {
        body["medicineName"] = medName ?? "Vitamin";
        body["dosage"] = dosage ?? "1 pill";
      }
      final response = await networkClient.post("/reminders", body);
      if (response.statusCode == 200) {
        await fetchReminders();
      }
    } catch (e) {
      debugPrint("Add reminder error: $e");
    }
  }

  Future<void> logReminderAdherence(String reminderId, String status) async {
    try {
      final response = await networkClient.post("/reminders/$reminderId/log?status=$status", {});
      if (response.statusCode == 200) {
        await fetchReminders();
      }
    } catch (e) {
      debugPrint("Log reminder error: $e");
    }
  }

  // Health Reports Ingestion
  Future<void> fetchReports() async {
    try {
      final response = await networkClient.get("/reports");
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _reports = data.map((r) => HealthReport.fromJson(r)).toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Fetch reports error: $e");
    }
  }

  Future<void> uploadReport(List<int> bytes, String fileName) async {
    _isLoading = true;
    notifyListeners();
    try {
      final response = await networkClient.uploadFile("/reports/upload", bytes, fileName);
      if (response.statusCode == 200) {
        final Map<String, dynamic> body = jsonDecode(response.body);
        final reportId = body["report"]["_id"];
        
        // Trigger AWS Textract pipeline immediately
        await networkClient.post("/reports/$reportId/analyze", {});
        await fetchReports();
      }
    } catch (e) {
      debugPrint("Upload report error: $e");
    } finally {
      _isLoading = false;
      notifyListeners();
    }
  }

  // TARA AI Chat Thread
  Future<void> fetchConversations() async {
    try {
      final response = await networkClient.get("/conversations");
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        if (data.isNotEmpty) {
          _activeConversationId = data.first["_id"];
          await fetchMessages();
        }
      }
    } catch (e) {
      debugPrint("Fetch conversations error: $e");
    }
  }

  Future<void> fetchMessages() async {
    if (_activeConversationId == null) return;
    try {
      final response = await networkClient.get("/conversations/$_activeConversationId/messages");
      if (response.statusCode == 200) {
        final List<dynamic> data = jsonDecode(response.body);
        _messages = data.map((m) => ChatMessage.fromJson(m)).toList();
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Fetch messages error: $e");
    }
  }

  Future<void> sendMessage(String text) async {
    // Add local optimistic message
    final userMsg = ChatMessage(role: "user", content: text, createdAt: DateTime.now());
    _messages.add(userMsg);
    notifyListeners();

    try {
      final body = {"query": text};
      if (_activeConversationId != null) {
        body["conversationId"] = _activeConversationId!;
      }
      final response = await networkClient.post("/ai/chat", body);
      if (response.statusCode == 200) {
        final data = jsonDecode(response.body);
        _activeConversationId = data["conversationId"];
        
        // Add assistant reply
        final replyMsg = ChatMessage(
          role: "assistant", 
          content: data["reply"], 
          createdAt: DateTime.now()
        );
        _messages.add(replyMsg);
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Send message error: $e");
    }
  }

  // Workouts
  Future<void> fetchWorkoutPlan() async {
    try {
      final response = await networkClient.get("/workout-plans");
      if (response.statusCode == 200) {
        _workoutPlan = WorkoutPlan.fromJson(jsonDecode(response.body));
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Fetch workout plan error: $e");
    }
  }

  Future<void> generateWorkoutPlan(String goal, String difficulty) async {
    try {
      final response = await networkClient.post("/workout-plans", {
        "fitnessGoal": goal,
        "difficulty": difficulty,
        "schedule": ["Monday", "Wednesday", "Friday"]
      });
      if (response.statusCode == 200) {
        _workoutPlan = WorkoutPlan.fromJson(jsonDecode(response.body));
        notifyListeners();
      }
    } catch (e) {
      debugPrint("Generate workout error: $e");
    }
  }
}
