import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../logic/app_state.dart';

class ChatScreen extends StatefulWidget {
  const ChatScreen({super.key});

  @override
  State<ChatScreen> createState() => _ChatScreenState();
}

class _ChatScreenState extends State<ChatScreen> {
  final _controller = TextEditingController();
  final _scrollController = ScrollController();

  void _send() {
    final text = _controller.text.trim();
    if (text.isNotEmpty) {
      Provider.of<AppState>(context, listen: false).sendMessage(text);
      _controller.clear();
      // Scroll to bottom
      Future.delayed(const Duration(milliseconds: 100), () {
        if (_scrollController.hasClients) {
          _scrollController.animateTo(
            _scrollController.position.maxScrollExtent,
            duration: const Duration(milliseconds: 300),
            curve: Curves.easeOut,
          );
        }
      });
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    _scrollController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final state = Provider.of<AppState>(context);
    final hasReportContext = state.reports.isNotEmpty;

    return Column(
      children: [
        // AI Status Bar
        Container(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
          color: AppConstants.primaryGreenDark.withOpacity(0.3),
          child: Row(
            children: [
              CircleAvatar(
                backgroundColor: AppConstants.accentMint.withOpacity(0.2),
                child: Icon(Icons.psychology, color: AppConstants.accentMint),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    const Text(
                      'TARA AI Health Coach',
                      style: TextStyle(fontWeight: FontWeight.bold),
                    ),
                    Text(
                      hasReportContext 
                          ? '✅ Lab report context loaded' 
                          : '⚡ General wellness memory mode',
                      style: TextStyle(
                        fontSize: 12, 
                        color: hasReportContext ? AppConstants.accentMint : AppConstants.textGray
                      ),
                    ),
                  ],
                ),
              ),
            ],
          ),
        ),

        // Message Thread
        Expanded(
          child: ListView.builder(
            controller: _scrollController,
            padding: const EdgeInsets.all(AppConstants.defaultPadding),
            itemCount: state.messages.isEmpty ? 1 : state.messages.length,
            itemBuilder: (context, index) {
              if (state.messages.isEmpty) {
                return _buildWelcomeMessage();
              }
              final msg = state.messages[index];
              final isUser = msg.role == 'user';
              return Align(
                alignment: isUser ? Alignment.centerRight : Alignment.centerLeft,
                child: Container(
                  maxCrossAxisExtent: MediaQuery.of(context).size.width * 0.8,
                  margin: const EdgeInsets.only(bottom: 12),
                  padding: const EdgeInsets.all(12),
                  decoration: BoxDecoration(
                    color: isUser 
                        ? AppConstants.accentMint 
                        : AppConstants.primaryGreenDark.withOpacity(0.4),
                    borderRadius: BorderRadius.only(
                      topLeft: const Radius.circular(12),
                      topRight: const Radius.circular(12),
                      bottomLeft: isUser ? const Radius.circular(12) : Radius.zero,
                      bottomRight: isUser ? Radius.zero : const Radius.circular(12),
                    ),
                    border: isUser 
                        ? null 
                        : Border.all(color: AppConstants.accentMint.withOpacity(0.1)),
                  ),
                  child: Text(
                    msg.content,
                    style: TextStyle(
                      color: isUser ? AppConstants.primaryDark : AppConstants.textWhite,
                      fontSize: 15,
                    ),
                  ),
                ),
              );
            },
          ),
        ),

        // Prompt Suggestion Chips (if chat is empty or starting)
        if (state.messages.isEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 8.0),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Row(
                children: [
                  _buildPromptChip("What does my Vitamin D level mean?"),
                  const SizedBox(width: 8),
                  _buildPromptChip("Generate my weekly workout routine"),
                  const SizedBox(width: 8),
                  _buildPromptChip("How much water should I drink?"),
                ],
              ),
            ),
          ),

        // Input Field Bar
        Padding(
          padding: const EdgeInsets.all(8.0),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _controller,
                  onSubmitted: (_) => _send(),
                  decoration: InputDecoration(
                    hintText: 'Ask TARA about your health & reports...',
                    contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: AppConstants.accentMint.withOpacity(0.3)),
                    ),
                    focusedBorder: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(24),
                      borderSide: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                ),
              ),
              const SizedBox(width: 8),
              CircleAvatar(
                backgroundColor: AppConstants.accentMint,
                child: IconButton(
                  icon: const Icon(Icons.send, color: AppConstants.primaryDark),
                  onPressed: _send,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildWelcomeMessage() {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 40.0),
      child: Column(
        children: [
          Icon(Icons.spa_outlined, size: 50, color: AppConstants.accentMint),
          const SizedBox(height: 16),
          const Text(
            'Meet TARA Health Co-Pilot',
            style: TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 8),
          Text(
            'Your personalized assistant. Ask general health questions, '
            'get workout schedules, or upload lab reports to receive answers '
            'grounded in your medical parameters.',
            textAlign: TextAlign.center,
            style: TextStyle(color: AppConstants.textGray, fontSize: 14),
          ),
        ],
      ),
    );
  }

  Widget _buildPromptChip(String queryText) {
    return ActionChip(
      backgroundColor: AppConstants.primaryGreenDark.withOpacity(0.3),
      side: BorderSide(color: AppConstants.accentMint.withOpacity(0.2)),
      label: Text(
        queryText,
        style: TextStyle(color: AppConstants.accentMint, fontSize: 12),
      ),
      onPressed: () {
        _controller.text = queryText;
        _send();
      },
    );
  }
}
