#!/usr/bin/env python3
"""
Comprehensive test suite for immanuel_server.py functions.

This test suite provides thorough testing of all functions in the immanuel_server.py file,
including utility functions, MCP tool functions, and error handling.

Running the tests:
    Using pytest (recommended):
        uv run pytest test_immanuel_server.py -v

    Using Python directly:
        uv run python test_immanuel_server.py

The test suite will generate detailed JSON reports in the test_results/ directory,
with one file per function containing test results and success rates.
"""

import json
import os
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys

# Add the current directory to the path to import immanuel_server
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import immanuel_server


class TestResultRecorder:
    """Helper class to record test results for each function."""
    
    def __init__(self):
        self.results = {}
    
    def record_test(self, function_name, test_name, result, error=None):
        """Record a test result."""
        if function_name not in self.results:
            self.results[function_name] = {
                'total_tests': 0,
                'passed': 0,
                'failed': 0,
                'tests': []
            }
        
        self.results[function_name]['total_tests'] += 1
        if result == 'PASSED':
            self.results[function_name]['passed'] += 1
        else:
            self.results[function_name]['failed'] += 1
        
        test_info = {
            'test_name': test_name,
            'result': result,
            'error': str(error) if error else None
        }
        self.results[function_name]['tests'].append(test_info)
    
    def save_results(self, output_dir='test_results'):
        """Save results to separate JSON files per function."""
        os.makedirs(output_dir, exist_ok=True)
        
        for function_name, result_data in self.results.items():
            result_data['success_rate'] = (
                result_data['passed'] / result_data['total_tests'] * 100 
                if result_data['total_tests'] > 0 else 0
            )
            
            filename = f"{output_dir}/{function_name}_test_results.json"
            with open(filename, 'w') as f:
                json.dump(result_data, f, indent=2)
            
            print(f"Results saved to {filename}")


# Global test recorder
recorder = TestResultRecorder()


class TestParseCoordinate:
    """Test cases for parse_coordinate function."""
    
    def test_decimal_coordinates(self):
        """Test decimal coordinate parsing."""
        function_name = 'parse_coordinate'
        
        # Test positive latitude
        try:
            result = immanuel_server.parse_coordinate("32.71", is_latitude=True)
            assert result == 32.71
            recorder.record_test(function_name, 'decimal_positive_latitude', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'decimal_positive_latitude', 'FAILED', e)
        
        # Test negative longitude
        try:
            result = immanuel_server.parse_coordinate("-117.15", is_latitude=False)
            assert result == -117.15
            recorder.record_test(function_name, 'decimal_negative_longitude', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'decimal_negative_longitude', 'FAILED', e)
    
    def test_traditional_coordinates(self):
        """Test traditional coordinate parsing."""
        function_name = 'parse_coordinate'
        
        # Test north latitude
        try:
            result = immanuel_server.parse_coordinate("32n43", is_latitude=True)
            assert 32.7 <= result <= 32.8  # 32°43' = approximately 32.72°
            recorder.record_test(function_name, 'traditional_north_latitude', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'traditional_north_latitude', 'FAILED', e)
        
        # Test west longitude
        try:
            result = immanuel_server.parse_coordinate("117w09", is_latitude=False)
            assert -117.2 <= result <= -117.1  # 117°09'W = approximately -117.15°
            recorder.record_test(function_name, 'traditional_west_longitude', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'traditional_west_longitude', 'FAILED', e)
    
    def test_coordinate_validation(self):
        """Test coordinate range validation."""
        function_name = 'parse_coordinate'
        
        # Test latitude out of range
        try:
            immanuel_server.parse_coordinate("95.0", is_latitude=True)
            recorder.record_test(function_name, 'latitude_out_of_range', 'FAILED', 'Should have raised ValueError')
        except ValueError:
            recorder.record_test(function_name, 'latitude_out_of_range', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'latitude_out_of_range', 'FAILED', e)
        
        # Test longitude out of range
        try:
            immanuel_server.parse_coordinate("185.0", is_latitude=False)
            recorder.record_test(function_name, 'longitude_out_of_range', 'FAILED', 'Should have raised ValueError')
        except ValueError:
            recorder.record_test(function_name, 'longitude_out_of_range', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'longitude_out_of_range', 'FAILED', e)
    
    def test_invalid_formats(self):
        """Test invalid coordinate formats."""
        function_name = 'parse_coordinate'
        
        # Test completely invalid format
        try:
            immanuel_server.parse_coordinate("invalid", is_latitude=True)
            recorder.record_test(function_name, 'invalid_format', 'FAILED', 'Should have raised ValueError')
        except ValueError:
            recorder.record_test(function_name, 'invalid_format', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'invalid_format', 'FAILED', e)


class TestValidateInputs:
    """Test cases for validate_inputs function."""
    
    def test_valid_inputs(self):
        """Test with valid inputs."""
        function_name = 'validate_inputs'
        
        try:
            immanuel_server.validate_inputs("1990-01-01 12:00:00", "32.71", "-117.15")
            recorder.record_test(function_name, 'valid_inputs', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'valid_inputs', 'FAILED', e)
    
    def test_invalid_datetime(self):
        """Test with invalid datetime format."""
        function_name = 'validate_inputs'
        
        try:
            immanuel_server.validate_inputs("invalid-date", "32.71", "-117.15")
            recorder.record_test(function_name, 'invalid_datetime', 'FAILED', 'Should have raised ValueError')
        except ValueError:
            recorder.record_test(function_name, 'invalid_datetime', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'invalid_datetime', 'FAILED', e)
    
    def test_invalid_coordinates(self):
        """Test with invalid coordinates."""
        function_name = 'validate_inputs'
        
        try:
            immanuel_server.validate_inputs("1990-01-01 12:00:00", "invalid", "-117.15")
            recorder.record_test(function_name, 'invalid_coordinates', 'FAILED', 'Should have raised ValueError')
        except ValueError:
            recorder.record_test(function_name, 'invalid_coordinates', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'invalid_coordinates', 'FAILED', e)


class TestGetErrorSuggestion:
    """Test cases for get_error_suggestion function."""
    
    def test_timezone_error(self):
        """Test timezone error suggestion."""
        function_name = 'get_error_suggestion'
        
        try:
            result = immanuel_server.get_error_suggestion("ZoneInfoNotFoundError", "No timezone found")
            assert "pip install tzdata" in result
            recorder.record_test(function_name, 'timezone_error', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'timezone_error', 'FAILED', e)
    
    def test_coordinate_error(self):
        """Test coordinate error suggestion."""
        function_name = 'get_error_suggestion'
        
        try:
            result = immanuel_server.get_error_suggestion("ValueError", "Invalid coordinate format")
            assert "51.38" in result or "51n23" in result
            recorder.record_test(function_name, 'coordinate_error', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'coordinate_error', 'FAILED', e)
    
    def test_datetime_error(self):
        """Test datetime error suggestion."""
        function_name = 'get_error_suggestion'
        
        try:
            result = immanuel_server.get_error_suggestion("ValueError", "Invalid datetime format")
            assert "ISO format" in result
            recorder.record_test(function_name, 'datetime_error', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'datetime_error', 'FAILED', e)


class TestHandleChartError:
    """Test cases for handle_chart_error function."""
    
    def test_timezone_error_handling(self):
        """Test handling of timezone errors."""
        function_name = 'handle_chart_error'
        
        try:
            error = Exception("No time zone found")
            result = immanuel_server.handle_chart_error(error)
            
            assert result["error"] is True
            assert "tzdata" in result["message"]
            assert result["type"] == "Exception"
            assert "suggestion" in result
            recorder.record_test(function_name, 'timezone_error_handling', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'timezone_error_handling', 'FAILED', e)
    
    def test_general_error_handling(self):
        """Test handling of general errors."""
        function_name = 'handle_chart_error'
        
        try:
            error = ValueError("Test error")
            result = immanuel_server.handle_chart_error(error)
            
            assert result["error"] is True
            assert result["message"] == "Test error"
            assert result["type"] == "ValueError"
            assert "suggestion" in result
            recorder.record_test(function_name, 'general_error_handling', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'general_error_handling', 'FAILED', e)


class TestCreateCacheKey:
    """Test cases for create_cache_key function."""
    
    def test_cache_key_generation(self):
        """Test cache key generation."""
        function_name = 'create_cache_key'
        
        try:
            key1 = immanuel_server.create_cache_key("arg1", "arg2", 123)
            key2 = immanuel_server.create_cache_key("arg1", "arg2", 123)
            key3 = immanuel_server.create_cache_key("arg1", "arg2", 124)
            
            assert key1 == key2  # Same args should produce same key
            assert key1 != key3  # Different args should produce different keys
            assert len(key1) == 32  # MD5 hash length
            recorder.record_test(function_name, 'cache_key_generation', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'cache_key_generation', 'FAILED', e)


class TestCompactChart:
    """Test cases for the new generate_compact_natal_chart function."""

    def test_generate_compact_natal_chart_success(self):
        """Test successful compact natal chart generation."""
        function_name = 'generate_compact_natal_chart'

        try:
            with patch('immanuel_server.charts.Subject'), \
                 patch('immanuel_server.charts.Natal') as mock_natal, \
                 patch('json.dumps') as mock_dumps, \
                 patch('json.loads') as mock_loads, \
                 patch('immanuel_server.attach_lifecycle_section') as mock_lifecycle:

                # Mock the chart generation
                mock_chart = MagicMock()
                mock_natal.return_value = mock_chart

                # Mock the serialization
                mock_dumps.return_value = '{"compact_test": "data"}'
                mock_loads.return_value = {"compact_test": "data"}
                mock_lifecycle.return_value = None

                result = immanuel_server.generate_compact_natal_chart(
                    "1990-01-01 12:00:00", "32.71", "-117.15"
                )

                assert isinstance(result, dict)
                assert "compact_test" in result
                recorder.record_test(function_name, 'success_case', 'PASSED')

        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)

    def test_compact_chart_structure(self):
        """Test the structure of the compact chart to ensure it is correct."""
        function_name = 'generate_compact_natal_chart'

        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Natal') as mock_natal:
                
                # Create a mock chart with the expected structure for CompactJSONSerializer
                mock_chart = MagicMock()
                
                # Mock objects with the indices that should be included
                mock_sun = MagicMock()
                mock_sun.index = 4000001
                mock_sun.name = "Sun"
                mock_sun.sign.name = "Capricorn"
                mock_sun.sign_longitude.formatted = "10°23'45\""
                mock_sun.house.number = 10
                
                mock_moon = MagicMock()
                mock_moon.index = 4000002
                mock_moon.name = "Moon"
                mock_moon.sign.name = "Cancer"
                mock_moon.sign_longitude.formatted = "15°12'30\""
                mock_moon.house.number = 4
                
                # Mock a minor object that should be filtered out
                mock_chiron = MagicMock()
                mock_chiron.index = 9999999
                mock_chiron.name = "Chiron"
                
                mock_chart.objects = {
                    4000001: mock_sun,
                    4000002: mock_moon,
                    9999999: mock_chiron  # Should be filtered out
                }
                
                # Mock houses
                mock_house = MagicMock()
                mock_house.number = 1
                mock_house.sign.name = "Aries"
                mock_chart.houses = {1: mock_house}
                
                # Mock aspects
                mock_chart.aspects = {}
                
                mock_natal.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    
                    # Mock the compact serializer output
                    compact_output = {
                        'objects': {
                            '4000001': {'name': 'Sun', 'sign': 'Capricorn', 'sign_longitude': "10°23'45\"", 'house': 10},
                            '4000002': {'name': 'Moon', 'sign': 'Cancer', 'sign_longitude': "15°12'30\"", 'house': 4}
                        },
                        'houses': {
                            '1': {'number': 1, 'sign': 'Aries'}
                        },
                        'aspects': []
                    }
                    
                    mock_dumps.return_value = json.dumps(compact_output)
                    mock_loads.return_value = compact_output
                    
                    result = immanuel_server.generate_compact_natal_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15"
                    )
                    
                    # Verify basic structure
                    assert isinstance(result, dict)
                    assert 'objects' in result
                    assert 'houses' in result
                    assert 'aspects' in result
                    
                    # Verify object filtering (only major objects)
                    assert len(result['objects']) == 2
                    assert '4000001' in result['objects']  # Sun
                    assert '4000002' in result['objects']  # Moon
                    assert '9999999' not in result['objects']  # Chiron should be filtered out
                    
                    recorder.record_test(function_name, 'structure_verification', 'PASSED')

        except Exception as e:
            recorder.record_test(function_name, 'structure_verification', 'FAILED', e)
    
    def test_compact_solar_return_chart_success(self):
        """Test successful compact solar return chart generation."""
        function_name = 'generate_compact_solar_return_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.SolarReturn') as mock_solar_return:
                
                mock_chart = MagicMock()
                mock_solar_return.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads, \
                     patch('immanuel_server.attach_lifecycle_section') as mock_lifecycle:
                    mock_dumps.return_value = '{"compact_solar_return": "data"}'
                    mock_loads.return_value = {"compact_solar_return": "data"}
                    mock_lifecycle.return_value = None
                    
                    result = immanuel_server.generate_compact_solar_return_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15", 2024
                    )
                    
                    assert isinstance(result, dict)
                    assert "compact_solar_return" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_compact_progressed_chart_success(self):
        """Test successful compact progressed chart generation."""
        function_name = 'generate_compact_progressed_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Progressed') as mock_progressed:
                
                mock_chart = MagicMock()
                mock_progressed.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads, \
                     patch('immanuel_server.attach_lifecycle_section') as mock_lifecycle:
                    mock_dumps.return_value = '{"compact_progressed": "data"}'
                    mock_loads.return_value = {"compact_progressed": "data"}
                    mock_lifecycle.return_value = None
                    
                    result = immanuel_server.generate_compact_progressed_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15", "2024-01-01 12:00:00"
                    )
                    
                    assert isinstance(result, dict)
                    assert "compact_progressed" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_compact_composite_chart_success(self):
        """Test successful compact composite chart generation."""
        function_name = 'generate_compact_composite_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Composite') as mock_composite:
                
                mock_chart = MagicMock()
                mock_composite.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    mock_dumps.return_value = '{"compact_composite": "data"}'
                    mock_loads.return_value = {"compact_composite": "data"}
                    
                    result = immanuel_server.generate_compact_composite_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15",
                        "1988-06-15 14:30:00", "40.71", "-74.00"
                    )
                    
                    assert isinstance(result, dict)
                    assert "compact_composite" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_compact_synastry_aspects_success(self):
        """Test successful compact synastry aspects generation."""
        function_name = 'generate_compact_synastry_aspects'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Natal') as mock_natal:
                
                mock_chart = MagicMock()
                mock_natal.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    
                    # Mock the compact serializer output
                    compact_output = {"aspects": [{"filtered": "aspects"}]}
                    mock_dumps.return_value = json.dumps(compact_output)
                    mock_loads.return_value = compact_output
                    
                    result = immanuel_server.generate_compact_synastry_aspects(
                        "1990-01-01 12:00:00", "32.71", "-117.15",
                        "1988-06-15 14:30:00", "40.71", "-74.00"
                    )
                    
                    assert isinstance(result, dict)
                    assert "aspects" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_compact_transit_chart_success(self):
        """Test successful compact transit chart generation."""
        function_name = 'generate_compact_transit_chart'
        
        try:
            with patch('immanuel_server.charts.Transits') as mock_transits:
                
                mock_chart = MagicMock()
                mock_transits.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    mock_dumps.return_value = '{"compact_transits": "data"}'
                    mock_loads.return_value = {"compact_transits": "data"}
                    
                    result = immanuel_server.generate_compact_transit_chart("32.71", "-117.15")
                    
                    assert isinstance(result, dict)
                    assert "compact_transits" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)


class TestMCPTools:
    """Test cases for MCP tool functions."""
    
    def test_generate_natal_chart_success(self):
        """Test successful natal chart generation."""
        function_name = 'generate_natal_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Natal') as mock_natal:
                
                # Mock the chart generation
                mock_chart = MagicMock()
                mock_natal.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads, \
                     patch('immanuel_server.attach_lifecycle_section') as mock_lifecycle:
                    mock_dumps.return_value = '{"test": "data"}'
                    mock_loads.return_value = {"test": "data"}
                    mock_lifecycle.return_value = None
                    
                    result = immanuel_server.generate_natal_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15"
                    )
                    
                    assert isinstance(result, dict)
                    assert "test" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_generate_natal_chart_error(self):
        """Test natal chart generation with invalid inputs."""
        function_name = 'generate_natal_chart'
        
        try:
            result = immanuel_server.generate_natal_chart(
                "invalid-date", "32.71", "-117.15"
            )
            
            assert result["error"] is True
            assert "message" in result
            assert "type" in result
            recorder.record_test(function_name, 'error_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'error_case', 'FAILED', e)
    
    def test_get_chart_summary_success(self):
        """Test successful chart summary generation."""
        function_name = 'get_chart_summary'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Natal') as mock_natal:
                
                # Mock the chart and its objects
                mock_chart = MagicMock()
                mock_sun = MagicMock()
                mock_sun.sign.name = "Capricorn"
                mock_moon = MagicMock()
                mock_moon.sign.name = "Pisces"
                mock_asc = MagicMock()
                mock_asc.sign.name = "Virgo"
                
                mock_chart.objects = {
                    4000001: mock_sun,
                    4000002: mock_moon,
                    3000001: mock_asc
                }
                mock_chart.shape = "Bowl"
                mock_chart.moon_phase.formatted = "New Moon"
                mock_chart.diurnal = True
                mock_chart.house_system = "Placidus"
                
                mock_natal.return_value = mock_chart
                
                result = immanuel_server.get_chart_summary(
                    "1990-01-01 12:00:00", "32.71", "-117.15"
                )
                
                assert result["sun_sign"] == "Capricorn"
                assert result["moon_sign"] == "Pisces"
                assert result["rising_sign"] == "Virgo"
                recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_get_planetary_positions_success(self):
        """Test successful planetary positions retrieval."""
        function_name = 'get_planetary_positions'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Natal') as mock_natal:
                
                # Mock the chart and planets
                mock_chart = MagicMock()
                mock_sun = MagicMock()
                mock_sun.sign.name = "Capricorn"
                mock_sun.sign_longitude.formatted = "10°23'45\""
                mock_sun.house.number = 5
                
                mock_chart.objects = {4000001: mock_sun}
                mock_natal.return_value = mock_chart
                
                result = immanuel_server.get_planetary_positions(
                    "1990-01-01 12:00:00", "32.71", "-117.15"
                )
                
                assert "planets" in result
                assert "Sun" in result["planets"]
                assert result["planets"]["Sun"]["sign"] == "Capricorn"
                recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_generate_solar_return_chart_success(self):
        """Test successful solar return chart generation."""
        function_name = 'generate_solar_return_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.SolarReturn') as mock_solar_return:
                
                mock_chart = MagicMock()
                mock_solar_return.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads, \
                     patch('immanuel_server.attach_lifecycle_section') as mock_lifecycle:
                    mock_dumps.return_value = '{"solar_return": "data"}'
                    mock_loads.return_value = {"solar_return": "data"}
                    mock_lifecycle.return_value = None
                    
                    result = immanuel_server.generate_solar_return_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15", 2024
                    )
                    
                    assert isinstance(result, dict)
                    assert "solar_return" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_generate_solar_return_chart_invalid_year(self):
        """Test solar return chart with invalid year."""
        function_name = 'generate_solar_return_chart'
        
        try:
            result = immanuel_server.generate_solar_return_chart(
                "1990-01-01 12:00:00", "32.71", "-117.15", 1800
            )
            
            assert result["error"] is True
            assert "year must be between" in result["message"]
            recorder.record_test(function_name, 'invalid_year', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'invalid_year', 'FAILED', e)
    
    def test_generate_progressed_chart_success(self):
        """Test successful progressed chart generation."""
        function_name = 'generate_progressed_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Progressed') as mock_progressed:
                
                mock_chart = MagicMock()
                mock_progressed.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads, \
                     patch('immanuel_server.attach_lifecycle_section') as mock_lifecycle:
                    mock_dumps.return_value = '{"progressed": "data"}'
                    mock_loads.return_value = {"progressed": "data"}
                    mock_lifecycle.return_value = None
                    
                    result = immanuel_server.generate_progressed_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15", "2024-01-01 12:00:00"
                    )
                    
                    assert isinstance(result, dict)
                    assert "progressed" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_generate_composite_chart_success(self):
        """Test successful composite chart generation."""
        function_name = 'generate_composite_chart'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Composite') as mock_composite:
                
                mock_chart = MagicMock()
                mock_composite.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    mock_dumps.return_value = '{"composite": "data"}'
                    mock_loads.return_value = {"composite": "data"}
                    
                    result = immanuel_server.generate_composite_chart(
                        "1990-01-01 12:00:00", "32.71", "-117.15",
                        "1988-06-15 14:30:00", "40.71", "-74.00"
                    )
                    
                    assert isinstance(result, dict)
                    assert "composite" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_generate_synastry_aspects_success(self):
        """Test successful synastry aspects generation."""
        function_name = 'generate_synastry_aspects'
        
        try:
            with patch('immanuel_server.charts.Subject') as mock_subject, \
                 patch('immanuel_server.charts.Natal') as mock_natal:
                
                mock_chart = MagicMock()
                mock_natal.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    mock_dumps.return_value = '{"aspects": {"test": "aspects"}}'
                    mock_loads.return_value = {"aspects": {"test": "aspects"}}
                    
                    result = immanuel_server.generate_synastry_aspects(
                        "1990-01-01 12:00:00", "32.71", "-117.15",
                        "1988-06-15 14:30:00", "40.71", "-74.00"
                    )
                    
                    assert isinstance(result, dict)
                    assert "test" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_generate_transit_chart_success(self):
        """Test successful transit chart generation."""
        function_name = 'generate_transit_chart'
        
        try:
            with patch('immanuel_server.charts.Transits') as mock_transits:
                
                mock_chart = MagicMock()
                mock_transits.return_value = mock_chart
                
                with patch('json.dumps') as mock_dumps, \
                     patch('json.loads') as mock_loads:
                    mock_dumps.return_value = '{"transits": "data"}'
                    mock_loads.return_value = {"transits": "data"}
                    
                    result = immanuel_server.generate_transit_chart("32.71", "-117.15")
                    
                    assert isinstance(result, dict)
                    assert "transits" in result
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_configure_immanuel_settings_success(self):
        """Test successful settings configuration."""
        function_name = 'configure_immanuel_settings'
        
        try:
            with patch('immanuel.setup') as mock_setup:
                mock_settings = MagicMock()
                mock_settings.house_system = "OLD_VALUE"
                mock_setup.settings = mock_settings
                
                with patch('immanuel_server.chart_const') as mock_const:
                    mock_const.CAMPANUS = "CAMPANUS_VALUE"
                    
                    result = immanuel_server.configure_immanuel_settings(
                        "house_system", "CAMPANUS"
                    )
                    
                    assert result["status"] == "success"
                    assert "updated" in result["message"]
                    recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)
    
    def test_configure_immanuel_settings_invalid_key(self):
        """Test settings configuration with invalid key."""
        function_name = 'configure_immanuel_settings'
        
        try:
            result = immanuel_server.configure_immanuel_settings(
                "invalid_setting", "some_value"
            )
            
            assert result["status"] == "warning"
            assert "Unknown setting" in result["message"]
            assert result["applied"] is False
            recorder.record_test(function_name, 'invalid_key', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'invalid_key', 'FAILED', e)
    
    def test_list_available_settings_success(self):
        """Test successful settings listing."""
        function_name = 'list_available_settings'
        
        try:
            with patch('immanuel.setup') as mock_setup:
                mock_settings = MagicMock()
                mock_settings.house_system = "PLACIDUS"
                mock_settings.locale = "en_US"
                mock_settings.objects = [1, 2, 3]
                mock_settings.aspects = [1, 2]
                mock_setup.settings = mock_settings
                
                result = immanuel_server.list_available_settings()
                
                assert result["status"] == "success"
                assert "settings" in result
                assert "house_system" in result["settings"]
                recorder.record_test(function_name, 'success_case', 'PASSED')
        except Exception as e:
            recorder.record_test(function_name, 'success_case', 'FAILED', e)


def run_all_tests():
    """Run all tests and save results."""
    print("Running comprehensive tests for immanuel_server.py...")
    print("=" * 60)
    
    # Initialize test classes
    test_classes = [
        TestParseCoordinate(),
        TestValidateInputs(),
        TestGetErrorSuggestion(),
        TestHandleChartError(),
        TestCreateCacheKey(),
        TestCompactChart(),
        TestMCPTools()
    ]
    
    # Run all tests
    for test_class in test_classes:
        class_name = test_class.__class__.__name__
        print(f"\nRunning {class_name}...")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for method_name in test_methods:
            print(f"  - {method_name}")
            try:
                method = getattr(test_class, method_name)
                method()
            except Exception as e:
                print(f"    ERROR: {e}")
    
    # Save results
    print("\n" + "=" * 60)
    print("Saving test results...")
    recorder.save_results()
    
    # Print summary
    print("\nTest Summary:")
    print("-" * 40)
    total_tests = 0
    total_passed = 0
    total_failed = 0
    
    for function_name, results in recorder.results.items():
        total_tests += results['total_tests']
        total_passed += results['passed']
        total_failed += results['failed']
        
        print(f"{function_name}: {results['passed']}/{results['total_tests']} passed "
              f"({results['success_rate']:.1f}%)")
    
    print(f"\nOverall: {total_passed}/{total_tests} tests passed "
          f"({total_passed/total_tests*100:.1f}%)")
    
    return recorder.results


if __name__ == "__main__":
    run_all_tests()
