import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../core/constants.dart';
import '../../logic/app_state.dart';

class OnboardingScreen extends StatefulWidget {
  final bool startAtProfileStep;
  const OnboardingScreen({super.key, this.startAtProfileStep = false});

  @override
  State<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends State<OnboardingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _profileFormKey = GlobalKey<FormState>();
  
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _nameController = TextEditingController();
  
  bool _isSignUp = false;
  late bool _showProfileStep;
  
  String _selectedGender = 'Female';
  String _selectedAgeRange = '25-34';

  @override
  void initState() {
    super.initState();
    _showProfileStep = widget.startAtProfileStep;
  }

  @override
  void dispose() {
    _emailController.dispose();
    _passwordController.dispose();
    _nameController.dispose();
    super.dispose();
  }

  void _submitAuth() async {
    if (_formKey.currentState!.validate()) {
      final state = Provider.of<AppState>(context, listen: false);
      final success = await state.login(
        _emailController.text.trim(),
        _passwordController.text,
        isSignUp: _isSignUp,
      );
      if (!mounted) return;
      if (success) {
        if (_isSignUp) {
          setState(() {
            _showProfileStep = true;
          });
        }
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(content: Text("Authentication failed. Please try again.")),
        );
      }
    }
  }

  void _submitProfile() async {
    if (_profileFormKey.currentState!.validate()) {
      final state = Provider.of<AppState>(context, listen: false);
      await state.updateProfile(
        _nameController.text.trim(),
        _selectedAgeRange,
        _selectedGender,
      );
      // Once updateProfile completes, AppState fetches profile, and main.dart automatically redirects to dashboard.
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = Provider.of<AppState>(context).isLoading;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: AppConstants.appBackgroundGradient,
        ),
        child: Center(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(AppConstants.defaultPadding * 1.5),
            child: _showProfileStep ? _buildProfileStep(isLoading) : _buildAuthStep(isLoading),
          ),
        ),
      ),
    );
  }

  Widget _buildAuthStep(bool isLoading) {
    return Form(
      key: _formKey,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(
            Icons.energy_savings_leaf_outlined,
            size: 80,
            color: AppConstants.accentMint,
          ),
          const SizedBox(height: 16),
          Text(
            'Blumetara.ai',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 32,
              fontWeight: FontWeight.bold,
              color: AppConstants.textWhite,
              letterSpacing: 1.2,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            _isSignUp ? 'Create your health co-pilot account' : 'Your Premium AI Health Co-Pilot',
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 16,
              color: AppConstants.textGray,
            ),
          ),
          const SizedBox(height: 40),
          
          Container(
            padding: const EdgeInsets.all(AppConstants.defaultPadding),
            decoration: BoxDecoration(
              color: AppConstants.primaryGreenDark.withOpacity(0.15),
              borderRadius: BorderRadius.circular(AppConstants.defaultRadius),
              border: Border.all(
                color: AppConstants.accentMint.withOpacity(0.1),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _emailController,
                  keyboardType: TextInputType.emailAddress,
                  style: const TextStyle(color: AppConstants.textWhite),
                  decoration: InputDecoration(
                    labelText: 'Email Address',
                    labelStyle: const TextStyle(color: AppConstants.textGray),
                    prefixIcon: Icon(Icons.email_outlined, color: AppConstants.accentMint),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.textGray.withOpacity(0.5)),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.isEmpty || !value.contains('@')) {
                      return 'Please enter a valid email';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 16),
                TextFormField(
                  controller: _passwordController,
                  obscureText: true,
                  style: const TextStyle(color: AppConstants.textWhite),
                  decoration: InputDecoration(
                    labelText: 'Password',
                    labelStyle: const TextStyle(color: AppConstants.textGray),
                    prefixIcon: Icon(Icons.lock_outline, color: AppConstants.accentMint),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.textGray.withOpacity(0.5)),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.length < 6) {
                      return 'Password must be at least 6 characters';
                    }
                    return null;
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),
          
          ElevatedButton(
            onPressed: isLoading ? null : _submitAuth,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.accentMint,
              foregroundColor: AppConstants.primaryDark,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: isLoading 
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppConstants.primaryDark),
                  )
                : Text(
                    _isSignUp ? 'Sign Up & Continue' : 'Sign In to Blumetara',
                    style: const TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
          ),
          const SizedBox(height: 16),
          
          TextButton(
            onPressed: () {
              setState(() {
                _isSignUp = !_isSignUp;
              });
            },
            child: Text(
              _isSignUp 
                  ? 'Already have an account? Sign In' 
                  : "Don't have an account? Sign Up",
              style: const TextStyle(color: AppConstants.accentMint),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildProfileStep(bool isLoading) {
    return Form(
      key: _profileFormKey,
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(
            Icons.account_circle_outlined,
            size: 80,
            color: AppConstants.accentMint,
          ),
          const SizedBox(height: 16),
          Text(
            'Personalize TARA',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 28,
              fontWeight: FontWeight.bold,
              color: AppConstants.textWhite,
            ),
          ),
          const SizedBox(height: 8),
          Text(
            'Tell TARA about yourself for personalized health analytics',
            textAlign: TextAlign.center,
            style: const TextStyle(
              fontSize: 15,
              color: AppConstants.textGray,
            ),
          ),
          const SizedBox(height: 32),
          
          Container(
            padding: const EdgeInsets.all(AppConstants.defaultPadding),
            decoration: BoxDecoration(
              color: AppConstants.primaryGreenDark.withOpacity(0.15),
              borderRadius: BorderRadius.circular(AppConstants.defaultRadius),
              border: Border.all(
                color: AppConstants.accentMint.withOpacity(0.1),
              ),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                TextFormField(
                  controller: _nameController,
                  style: const TextStyle(color: AppConstants.textWhite),
                  decoration: InputDecoration(
                    labelText: 'Your Full Name',
                    labelStyle: const TextStyle(color: AppConstants.textGray),
                    prefixIcon: Icon(Icons.person_outline, color: AppConstants.accentMint),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.textGray.withOpacity(0.5)),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                  validator: (value) {
                    if (value == null || value.trim().isEmpty) {
                      return 'Please enter your name';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 24),
                
                DropdownButtonFormField<String>(
                  value: _selectedGender,
                  dropdownColor: AppConstants.primaryDark,
                  style: const TextStyle(color: AppConstants.textWhite, fontSize: 16),
                  decoration: InputDecoration(
                    labelText: 'Gender',
                    labelStyle: const TextStyle(color: AppConstants.textGray),
                    prefixIcon: Icon(Icons.wc_outlined, color: AppConstants.accentMint),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.textGray.withOpacity(0.5)),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                  items: ['Male', 'Female', 'Other'].map((String val) {
                    return DropdownMenuItem<String>(
                      value: val,
                      child: Text(val),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setState(() {
                        _selectedGender = val;
                      });
                    }
                  },
                ),
                const SizedBox(height: 24),
                
                DropdownButtonFormField<String>(
                  value: _selectedAgeRange,
                  dropdownColor: AppConstants.primaryDark,
                  style: const TextStyle(color: AppConstants.textWhite, fontSize: 16),
                  decoration: InputDecoration(
                    labelText: 'Age Range',
                    labelStyle: const TextStyle(color: AppConstants.textGray),
                    prefixIcon: Icon(Icons.calendar_today_outlined, color: AppConstants.accentMint),
                    enabledBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.textGray.withOpacity(0.5)),
                    ),
                    focusedBorder: UnderlineInputBorder(
                      borderSide: BorderSide(color: AppConstants.accentMint),
                    ),
                  ),
                  items: ['Under 18', '18-24', '25-34', '35-44', '45-54', '55+'].map((String val) {
                    return DropdownMenuItem<String>(
                      value: val,
                      child: Text(val),
                    );
                  }).toList(),
                  onChanged: (val) {
                    if (val != null) {
                      setState(() {
                        _selectedAgeRange = val;
                      });
                    }
                  },
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          
          ElevatedButton(
            onPressed: isLoading ? null : _submitProfile,
            style: ElevatedButton.styleFrom(
              backgroundColor: AppConstants.accentMint,
              foregroundColor: AppConstants.primaryDark,
              padding: const EdgeInsets.symmetric(vertical: 16),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(8),
              ),
            ),
            child: isLoading 
                ? const SizedBox(
                    height: 20,
                    width: 20,
                    child: CircularProgressIndicator(strokeWidth: 2, color: AppConstants.primaryDark),
                  )
                : const Text(
                    'Personalize TARA Co-Pilot',
                    style: TextStyle(fontSize: 16, fontWeight: FontWeight.bold),
                  ),
          ),
        ],
      ),
    );
  }
}
