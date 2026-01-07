import pytest
import json
from unittest.mock import Mock, patch
from ai_agent import EmailAnalyzer


class TestEmailAnalyzer:
    """Test suite for EmailAnalyzer"""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing"""
        with patch.dict('os.environ', {'GROQ_API_KEY': 'test_key'}):
            return EmailAnalyzer(api_key='test_key')
    
    def test_no_reply_sender_detection(self, analyzer):
        """Test detection of no-reply senders"""
        assert analyzer._is_no_reply_sender('no-reply@company.com')
        assert analyzer._is_no_reply_sender('noreply@service.com')
        assert analyzer._is_no_reply_sender('donotreply@site.com')
        assert analyzer._is_no_reply_sender('notifications@app.com')
        assert not analyzer._is_no_reply_sender('john@company.com')
        assert not analyzer._is_no_reply_sender('support@service.com')
    
    def test_newsletter_auto_classification(self, analyzer):
        """Test automatic newsletter classification"""
        result = analyzer.analyze_email(
            'no-reply@newsletter.com',
            'Weekly Updates',
            'Check out this week\'s highlights'
        )
        
        assert result['category'] == 'Newsletter'
        assert result['reply'] == 'No reply needed'
        assert not result['needs_reply']
    
    @patch('ai_agent.Groq')
    def test_important_email_analysis(self, mock_groq, analyzer):
        """Test analysis of important emails"""
        # Mock Groq API response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "Important",
            "priority": "High",
            "reply": "Dear John,\n\nThank you for reaching out.\n\nBest regards,\nMariselvam M",
            "reasoning": "Work-related inquiry from colleague",
            "needs_reply": True
        })
        
        mock_groq.return_value.chat.completions.create.return_value = mock_response
        analyzer.client = mock_groq.return_value
        
        result = analyzer.analyze_email(
            'john@company.com',
            'Project Deadline',
            'We need to discuss the Q4 deliverables'
        )
        
        assert result['category'] == 'Important'
        assert result['priority'] == 'High'
        assert result['needs_reply']
        assert 'Best regards' in result['reply']
    
    @patch('ai_agent.Groq')
    def test_personal_email_analysis(self, mock_groq, analyzer):
        """Test analysis of personal emails"""
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = json.dumps({
            "category": "Personal",
            "priority": "Medium",
            "reply": "Hey! Would love to catch up.\n\nBest regards,\nMariselvam M",
            "reasoning": "Friend asking to meet",
            "needs_reply": True
        })
        
        mock_groq.return_value.chat.completions.create.return_value = mock_response
        analyzer.client = mock_groq.return_value
        
        result = analyzer.analyze_email(
            'friend@gmail.com',
            'Coffee next week?',
            'Hey! Want to grab coffee?'
        )
        
        assert result['category'] == 'Personal'
        assert result['needs_reply']
    
    def test_fallback_response(self, analyzer):
        """Test fallback when API fails"""
        with patch.object(analyzer.client.chat.completions, 'create', side_effect=Exception('API Error')):
            result = analyzer.analyze_email(
                'test@example.com',
                'Test Subject',
                'Test body'
            )
            
            assert 'is_fallback' in result
            assert result['is_fallback']
            assert result['category'] in ['Newsletter', 'Personal']
            assert 'reply' in result
    
    def test_parse_json_response(self, analyzer):
        """Test JSON response parsing"""
        json_str = json.dumps({
            "category": "Important",
            "priority": "High",
            "reply": "Test reply",
            "reasoning": "Test",
            "needs_reply": True
        })
        
        result = analyzer._parse_response(
            json_str,
            'test@example.com',
            'Test'
        )
        
        assert result['category'] == 'Important'
        assert result['priority'] == 'High'
        assert result['needs_reply']
    
    def test_parse_text_response(self, analyzer):
        """Test text format response parsing"""
        text_response = """Category: Important
Priority: High
Reply: This is a test reply"""
        
        result = analyzer._parse_response(
            text_response,
            'test@example.com',
            'Test'
        )
        
        assert result['category'] == 'Important'
        assert result['priority'] == 'High'
        assert 'This is a test reply' in result['reply']
    
    def test_newsletter_fallback_classification(self, analyzer):
        """Test newsletter classification in fallback"""
        result = analyzer._generate_fallback_response(
            'sender@example.com',
            'Weekly Newsletter - Unsubscribe here',
            'Newsletter content'
        )
        
        assert result['category'] == 'Newsletter'
        assert result['reply'] == 'No reply needed'
        assert not result['needs_reply']


class TestRateLimiting:
    """Test rate limiting functionality"""
    
    @patch('time.sleep')
    @patch('time.time')
    def test_rate_limit_enforcement(self, mock_time, mock_sleep):
        """Test that rate limiting delays calls appropriately"""
        from ai_agent import rate_limit
        
        # Mock time progression
        call_times = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        mock_time.side_effect = call_times
        
        @rate_limit(calls=5, period=10)
        def test_function():
            return "called"
        
        # Make 10 calls
        for i in range(10):
            result = test_function()
            assert result == "called"
        
        # Should have slept once (after 5th call)
        assert mock_sleep.call_count >= 1


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--cov=ai_agent'])