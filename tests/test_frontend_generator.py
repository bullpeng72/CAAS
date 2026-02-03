"""
Tests for Frontend Code Generator

Tests React + TypeScript frontend generation functionality.
"""

import json

import pytest

from caas_framework.codegen.frontend_generator import (
    FrontendConfig,
    FrontendFramework,
    FrontendGenerator,
    ReactTemplateGenerator,
    StreamlitTemplateGenerator,
)


class TestFrontendConfig:
    """Test FrontendConfig model"""

    def test_config_creation(self):
        """Test creating FrontendConfig"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestProject", port=3000
        )

        assert config.framework == FrontendFramework.REACT
        assert config.project_name == "TestProject"
        assert config.port == 3000
        assert config.backend_url == "http://localhost:8000"
        assert config.enable_auth is False
        assert config.enable_metrics is False

    def test_config_with_custom_backend(self):
        """Test config with custom backend URL"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT,
            project_name="TestProject",
            port=8501,
            backend_url="http://api.example.com:8080",
        )

        assert config.backend_url == "http://api.example.com:8080"

    def test_config_with_features(self):
        """Test config with auth and metrics enabled"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT,
            project_name="TestProject",
            port=3000,
            enable_auth=True,
            enable_metrics=True,
        )

        assert config.enable_auth is True
        assert config.enable_metrics is True


class TestFrontendGenerator:
    """Test FrontendGenerator class"""

    def test_generator_creation(self):
        """Test creating FrontendGenerator"""
        generator = FrontendGenerator()
        assert generator is not None
        assert generator.port_manager is not None

    def test_generate_streamlit(self):
        """Test generating Streamlit frontend"""
        generator = FrontendGenerator()
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT, project_name="TestApp", port=8501
        )

        files = generator.generate(config)

        # Check key files exist
        assert "app.py" in files
        assert "requirements.txt" in files
        assert "README.md" in files
        assert "utils/api_client.py" in files
        assert ".streamlit/config.toml" in files

    def test_generate_react(self):
        """Test generating React frontend"""
        generator = FrontendGenerator()
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )

        files = generator.generate(config)

        # Check key files exist
        assert "package.json" in files
        assert "tsconfig.json" in files
        assert "vite.config.ts" in files
        assert "index.html" in files
        assert "src/main.tsx" in files
        assert "src/App.tsx" in files
        assert "src/api/client.ts" in files
        assert "src/types/api.ts" in files
        assert "README.md" in files

    def test_unsupported_framework(self):
        """Test error with unsupported framework"""
        generator = FrontendGenerator()

        # Create invalid config by manually setting framework
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        # Trick to test unsupported framework
        config.framework = "invalid"

        with pytest.raises(ValueError, match="Unsupported frontend framework"):
            generator.generate(config)


class TestStreamlitTemplateGenerator:
    """Test Streamlit template generation"""

    def test_streamlit_generator_creation(self):
        """Test creating Streamlit generator"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT, project_name="TestApp", port=8501
        )
        generator = StreamlitTemplateGenerator(config)

        assert generator.config == config
        assert generator.backend_spec == {}

    def test_generate_app_py(self):
        """Test generating app.py"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT,
            project_name="TestApp",
            port=8501,
            backend_url="http://localhost:8000",
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        app_py = files["app.py"]

        # Check content
        assert "import streamlit as st" in app_py
        assert "TestApp" in app_py
        assert "http://localhost:8000" in app_py

    def test_generate_agent_runner_page(self):
        """Test generating agent runner page"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT, project_name="TestApp", port=8501
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        agent_runner = files["pages/1_Agent_Runner.py"]

        # Check content
        assert "Agent Runner" in agent_runner
        assert "st.form" in agent_runner
        assert "task_description" in agent_runner

    def test_generate_api_client(self):
        """Test generating API client"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT,
            project_name="TestApp",
            port=8501,
            backend_url="http://api.example.com",
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        api_client = files["utils/api_client.py"]

        # Check content
        assert "class APIClient" in api_client
        assert "http://api.example.com" in api_client
        assert "def get(" in api_client
        assert "def post(" in api_client
        assert "httpx" in api_client

    def test_generate_config_toml(self):
        """Test generating Streamlit config"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT, project_name="TestApp", port=8501
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        config_toml = files[".streamlit/config.toml"]

        # Check content
        assert "port = 8501" in config_toml
        assert "[server]" in config_toml
        assert "[theme]" in config_toml

    def test_generate_requirements(self):
        """Test generating requirements.txt"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT, project_name="TestApp", port=8501
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        requirements = files["requirements.txt"]

        # Check base requirements
        assert "streamlit" in requirements
        assert "httpx" in requirements

    def test_generate_requirements_with_features(self):
        """Test requirements with optional features"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT,
            project_name="TestApp",
            port=8501,
            enable_auth=True,
            enable_metrics=True,
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        requirements = files["requirements.txt"]

        # Check optional requirements
        assert "streamlit-authenticator" in requirements
        assert "plotly" in requirements

    def test_generate_readme(self):
        """Test generating README"""
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT, project_name="TestApp", port=8501
        )
        generator = StreamlitTemplateGenerator(config)

        files = generator.generate()
        readme = files["README.md"]

        # Check content
        assert "TestApp" in readme
        assert "streamlit run app.py" in readme
        assert "http://localhost:8501" in readme
        assert "CAAS" in readme


class TestReactTemplateGenerator:
    """Test React + TypeScript template generation"""

    def test_react_generator_creation(self):
        """Test creating React generator"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        assert generator.config == config
        assert generator.backend_spec == {}
        assert generator.templates is not None

    def test_generate_package_json(self):
        """Test generating package.json"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="Test App", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        package_json = files["package.json"]

        # Parse JSON
        data = json.loads(package_json)

        # Check structure
        assert data["name"] == "test-app"
        assert "dependencies" in data
        assert "devDependencies" in data
        assert "scripts" in data

        # Check dependencies
        assert "react" in data["dependencies"]
        assert "react-dom" in data["dependencies"]
        assert "axios" in data["dependencies"]

        # Check dev dependencies
        assert "typescript" in data["devDependencies"]
        assert "vite" in data["devDependencies"]
        assert "@vitejs/plugin-react" in data["devDependencies"]

    def test_generate_tsconfig(self):
        """Test generating tsconfig.json"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        tsconfig = files["tsconfig.json"]

        # tsconfig.json supports comments (JSONC), so we check content instead of parsing
        assert '"compilerOptions"' in tsconfig
        assert '"jsx": "react-jsx"' in tsconfig
        assert '"strict": true' in tsconfig
        assert '"target": "ES2020"' in tsconfig
        assert '"moduleResolution": "bundler"' in tsconfig

    def test_generate_vite_config(self):
        """Test generating vite.config.ts"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT,
            project_name="TestApp",
            port=3000,
            backend_url="http://localhost:8000",
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        vite_config = files["vite.config.ts"]

        # Check content
        assert "defineConfig" in vite_config
        assert "port: 3000" in vite_config
        assert "http://localhost:8000" in vite_config
        assert "'/api'" in vite_config

    def test_generate_index_html(self):
        """Test generating index.html"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        index_html = files["index.html"]

        # Check content
        assert "<title>TestApp</title>" in index_html
        assert '<div id="root"></div>' in index_html
        assert "/src/main.tsx" in index_html

    def test_generate_main_tsx(self):
        """Test generating main.tsx"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        main_tsx = files["src/main.tsx"]

        # Check content
        assert "import React from 'react'" in main_tsx
        assert "import ReactDOM from 'react-dom/client'" in main_tsx
        assert "import App from './App.tsx'" in main_tsx
        assert "ReactDOM.createRoot" in main_tsx

    def test_generate_app_tsx(self):
        """Test generating App.tsx"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        app_tsx = files["src/App.tsx"]

        # Check content
        assert "TestApp" in app_tsx
        assert "CAAS" in app_tsx

    def test_generate_api_client(self):
        """Test generating API client"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT,
            project_name="TestApp",
            port=3000,
            backend_url="http://localhost:8000",
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        api_client = files["src/api/client.ts"]

        # Check content
        assert "import axios" in api_client
        assert "APIClient" in api_client
        assert "baseURL" in api_client
        assert "getHealth" in api_client
        assert "runAgent" in api_client

    def test_generate_api_types(self):
        """Test generating API types"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        api_types = files["src/types/api.ts"]

        # Check content
        assert "interface HealthStatus" in api_types
        assert "interface AgentRequest" in api_types
        assert "interface AgentResult" in api_types

    def test_generate_agent_runner_component(self):
        """Test generating AgentRunner component"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        agent_runner = files["src/components/AgentRunner.tsx"]

        # Check content
        assert "export const AgentRunner" in agent_runner
        assert "React.FC" in agent_runner
        assert "useState" in agent_runner
        assert "handleSubmit" in agent_runner
        assert "AgentRequest" in agent_runner
        assert "AgentResult" in agent_runner

    def test_generate_health_check_component(self):
        """Test generating HealthCheck component"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        health_check = files["src/components/HealthCheck.tsx"]

        # Check content
        assert "export const HealthCheck" in health_check
        assert "React.FC" in health_check
        assert "useEffect" in health_check
        assert "checkHealth" in health_check
        assert "HealthStatus" in health_check

    def test_generate_with_backend_spec(self):
        """Test generating with backend specification"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )

        backend_spec = {
            "endpoints": [
                {
                    "name": "getUsers",
                    "path": "/users",
                    "method": "GET",
                    "return_type": "User[]",
                }
            ],
            "types": [
                {
                    "name": "User",
                    "fields": [
                        {"name": "id", "type": "string"},
                        {"name": "name", "type": "string"},
                        {"name": "email", "type": "string"},
                    ],
                }
            ],
            "entities": [{"name": "User"}],
        }

        generator = ReactTemplateGenerator(config, backend_spec)
        files = generator.generate()

        # Check that custom types are generated
        api_types = files["src/types/api.ts"]
        assert "interface User" in api_types

        # Check that custom endpoint is in API client
        api_client = files["src/api/client.ts"]
        assert "getUsers" in api_client

        # Check that entity component is generated
        assert "src/components/UserList.tsx" in files

    def test_generate_readme(self):
        """Test generating README"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT,
            project_name="TestApp",
            port=3000,
            backend_url="http://localhost:8000",
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()
        readme = files["README.md"]

        # Check content
        assert "TestApp" in readme
        assert "npm install" in readme
        assert "npm run dev" in readme
        assert "http://localhost:3000" in readme
        assert "http://localhost:8000" in readme
        assert "TypeScript" in readme
        assert "Vite" in readme

    def test_all_generated_files_are_typescript(self):
        """Test that all React files use TypeScript extensions"""
        config = FrontendConfig(
            framework=FrontendFramework.REACT, project_name="TestApp", port=3000
        )
        generator = ReactTemplateGenerator(config)

        files = generator.generate()

        # Check TypeScript files
        typescript_files = [k for k in files.keys() if k.endswith((".ts", ".tsx"))]
        assert len(typescript_files) > 0

        # Check no JSX files
        jsx_files = [k for k in files.keys() if k.endswith(".jsx")]
        assert len(jsx_files) == 0


class TestIntegration:
    """Integration tests for frontend generation"""

    def test_generate_streamlit_full_project(self):
        """Test generating complete Streamlit project"""
        generator = FrontendGenerator()
        config = FrontendConfig(
            framework=FrontendFramework.STREAMLIT,
            project_name="FullStreamlitApp",
            port=8501,
            backend_url="http://localhost:8000",
            enable_auth=True,
            enable_metrics=True,
        )

        files = generator.generate(config)

        # Should have all expected files
        assert len(files) >= 6

        # Check all files have content
        for filename, content in files.items():
            assert content, f"File {filename} is empty"
            assert isinstance(content, str), f"File {filename} is not a string"

    def test_generate_react_full_project(self):
        """Test generating complete React project"""
        generator = FrontendGenerator()
        config = FrontendConfig(
            framework=FrontendFramework.REACT,
            project_name="FullReactApp",
            port=3000,
            backend_url="http://localhost:8000",
        )

        files = generator.generate(config)

        # Should have all expected files
        expected_files = [
            "package.json",
            "tsconfig.json",
            "vite.config.ts",
            "index.html",
            "src/main.tsx",
            "src/App.tsx",
            "src/api/client.ts",
            "src/types/api.ts",
            "src/components/AgentRunner.tsx",
            "src/components/HealthCheck.tsx",
            "README.md",
        ]

        for expected_file in expected_files:
            assert expected_file in files, f"Missing file: {expected_file}"

        # Check all files have content
        for filename, content in files.items():
            assert content, f"File {filename} is empty"
            assert isinstance(content, str), f"File {filename} is not a string"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
