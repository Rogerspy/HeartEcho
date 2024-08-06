import 'package:app/models/chat.dart';
import 'package:http/http.dart' as http;
import 'dart:convert';

class ApiClient {
  final String baseUrl;

  ApiClient({this.baseUrl = 'http://localhost:1127'});

  Future<String> chat(List<Map<String, dynamic>> history) async {
    final response = await http.post(
      Uri.parse('$baseUrl/chat'),
      headers: {'Content-Type': 'application/json', 'charset': 'utf-8'},
      body: jsonEncode({'history': history}),
    );
    if (response.statusCode == 200) {
      return json.decode(utf8.decode(response.bodyBytes))['response'];
    } else {
      throw Exception('Failed to load chat');
    }
  }

  Future<String> learn(
      List<ChatSession> chatSessions, List<String> knowledges) async {
    final response = await http.post(
      Uri.parse('$baseUrl/learn'),
      headers: {'Content-Type': 'application/json', 'charset': 'utf-8'},
      body: jsonEncode({
        'chat': chatSessions.map((e) => e.toHistory()).toList(),
        'knowledge': knowledges,
      }),
    );
    if (response.statusCode == 200) {
      return json.decode(utf8.decode(response.bodyBytes))['response'];
    } else {
      throw Exception('Failed to learn');
    }
  }

  Future<bool> saveModel() async {
    final response = await http.post(
      Uri.parse('$baseUrl/save_model'),
      headers: {'Content-Type': 'application/json'},
    );
    if (response.statusCode == 200) {
      return json.decode(response.body)['saved'];
    } else {
      throw Exception('Failed to save model');
    }
  }

  Future<List<dynamic>> fetchCorpora() async {
    final response = await http.get(Uri.parse('http://localhost:1127/corpus'));
    if (response.statusCode == 200) {
      final List<dynamic> data =
          json.decode(json.decode(response.body)['corpora']);
      return data;
    }
    return [];
  }

  Future<List<dynamic>> fetchCorpusEntries({
    required String corpusId,
    int skip = 0,
    int limit = 100,
  }) async {
    final queryParameters = {
      'corpus_id': corpusId,
      'skip': skip.toString(),
      'limit': limit.toString(),
    };

    final uri = Uri.parse('$baseUrl/corpus_entries')
        .replace(queryParameters: queryParameters);

    final response = await http.get(uri);
    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      return json.decode(data['entries']);
    } else {
      throw Exception('Failed to fetch corpus entries: ${response.statusCode}');
    }
  }

  Future<Map<String, dynamic>> createCorpusEntry(
      Map<String, dynamic> data) async {
    final response = await http.post(
      Uri.parse('$baseUrl/corpus_entry'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(data),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to create corpus entry: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> updateCorpusEntry(
      String entryId, Map<String, dynamic> data) async {
    final response = await http.put(
      Uri.parse('$baseUrl/corpus_entry/$entryId'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode(data),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to update corpus entry: ${response.body}');
    }
  }

  Future<Map<String, dynamic>> createCorpus({
    required String name,
    required String description,
  }) async {
    final response = await http.post(
      Uri.parse('$baseUrl/corpus'),
      headers: {'Content-Type': 'application/json'},
      body: json.encode({'name': name, 'description': description}),
    );

    if (response.statusCode == 200) {
      return json.decode(response.body);
    } else {
      throw Exception('Failed to create corpus: ${response.body}');
    }
  }
}

// ignore: non_constant_identifier_names
final API = ApiClient();
