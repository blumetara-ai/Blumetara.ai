import 'dart:convert';
import 'package:http/http.dart' as http;
import 'constants.dart';

class NetworkClient {
  String? _authToken;

  void updateToken(String? token) {
    _authToken = token;
  }

  Map<String, String> _getHeaders() {
    final headers = {
      'Content-Type': 'application/json',
      'Accept': 'application/json',
    };
    if (_authToken != null) {
      headers['Authorization'] = 'Bearer $_authToken';
    }
    return headers;
  }

  Future<http.Response> get(String endpoint) async {
    final url = Uri.parse("${AppConstants.apiBaseUrl}$endpoint");
    return await http.get(url, headers: _getHeaders());
  }

  Future<http.Response> post(String endpoint, Map<String, dynamic> body) async {
    final url = Uri.parse("${AppConstants.apiBaseUrl}$endpoint");
    return await http.post(url, headers: _getHeaders(), body: jsonEncode(body));
  }

  Future<http.Response> put(String endpoint, Map<String, dynamic> body) async {
    final url = Uri.parse("${AppConstants.apiBaseUrl}$endpoint");
    return await http.put(url, headers: _getHeaders(), body: jsonEncode(body));
  }

  // Upload lab report file
  Future<http.Response> uploadFile(String endpoint, List<int> fileBytes, String fileName) async {
    final url = Uri.parse("${AppConstants.apiBaseUrl}$endpoint");
    final request = http.MultipartRequest('POST', url);
    
    if (_authToken != null) {
      request.headers['Authorization'] = 'Bearer $_authToken';
    }

    final multipartFile = http.MultipartFile.fromBytes(
      'file',
      fileBytes,
      filename: fileName,
    );
    request.files.add(multipartFile);

    final streamedResponse = await request.send();
    return await http.Response.fromStream(streamedResponse);
  }
}

final networkClient = NetworkClient();
