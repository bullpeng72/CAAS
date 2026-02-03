"""Frontend code generation for generated projects.

This module provides frontend generation capabilities for projects,
supporting multiple frontend frameworks (Streamlit, React).
"""

from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel, Field

from caas_framework.codegen.port_manager import PortManager
from caas_framework.codegen.react_templates import ReactTemplates


class FrontendFramework(str, Enum):
    """Supported frontend frameworks."""

    STREAMLIT = "streamlit"
    REACT = "react"


class FrontendConfig(BaseModel):
    """Configuration for frontend generation."""

    framework: FrontendFramework
    project_name: str
    port: int
    backend_url: str = Field(default="http://localhost:8000")
    enable_auth: bool = Field(default=False)
    enable_metrics: bool = Field(default=False)


class FrontendGenerator:
    """Generates frontend code for projects."""

    def __init__(self, port_manager: Optional[PortManager] = None):
        """Initialize the frontend generator.

        Args:
            port_manager: Port manager for allocating ports. If None, creates a new one.
        """
        self.port_manager = port_manager or PortManager()

        # Set up Jinja2 environment
        template_dir = Path(__file__).parent / "templates" / "frontend"
        if template_dir.exists():
            self.jinja_env = Environment(
                loader=FileSystemLoader(str(template_dir)),
                trim_blocks=True,
                lstrip_blocks=True,
            )
        else:
            self.jinja_env = None

    def generate(
        self, config: FrontendConfig, backend_spec: Optional[Dict[str, Any]] = None
    ) -> Dict[str, str]:
        """Generate frontend code based on configuration.

        Args:
            config: Frontend configuration
            backend_spec: Optional backend specification for API integration

        Returns:
            Dictionary mapping file paths to file contents
        """
        if config.framework == FrontendFramework.STREAMLIT:
            generator = StreamlitTemplateGenerator(config, backend_spec, self.jinja_env)
        elif config.framework == FrontendFramework.REACT:
            generator = ReactTemplateGenerator(config, backend_spec, self.jinja_env)
        else:
            raise ValueError(f"Unsupported frontend framework: {config.framework}")

        return generator.generate()


class StreamlitTemplateGenerator:
    """Generates Streamlit frontend code."""

    def __init__(
        self,
        config: FrontendConfig,
        backend_spec: Optional[Dict[str, Any]] = None,
        jinja_env: Optional[Environment] = None,
    ):
        """Initialize the Streamlit generator.

        Args:
            config: Frontend configuration
            backend_spec: Optional backend specification
            jinja_env: Optional Jinja2 environment for template rendering
        """
        self.config = config
        self.backend_spec = backend_spec or {}
        self.jinja_env = jinja_env

    def generate(self) -> Dict[str, str]:
        """Generate Streamlit frontend files.

        Returns:
            Dictionary mapping file paths to file contents
        """
        files = {}

        # Generate main app.py
        files["app.py"] = self._generate_app_py()

        # Generate pages
        files["pages/1_Agent_Runner.py"] = self._generate_agent_runner_page()

        # Generate utilities
        files["utils/api_client.py"] = self._generate_api_client()
        files["utils/session.py"] = self._generate_session_utils()

        # Generate configuration
        files[".streamlit/config.toml"] = self._generate_config_toml()

        # Generate requirements.txt
        files["requirements.txt"] = self._generate_requirements()

        # Generate README
        files["README.md"] = self._generate_readme()

        return files

    def _render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a Jinja2 template or return fallback content.

        Args:
            template_name: Name of the template file
            context: Template context variables

        Returns:
            Rendered template content
        """
        if self.jinja_env:
            try:
                template = self.jinja_env.get_template(f"streamlit/{template_name}")
                return template.render(**context)
            except Exception:
                # Fall through to fallback
                pass

        # Fallback to hardcoded templates
        return self._get_fallback_template(template_name, context)

    def _get_fallback_template(
        self, template_name: str, context: Dict[str, Any]
    ) -> str:
        """Get fallback template content when Jinja2 templates are not available.

        Args:
            template_name: Name of the template
            context: Template context variables

        Returns:
            Template content
        """
        # This will be populated with inline templates as fallback
        # For now, delegate to the specific generator methods
        return ""

    def _generate_app_py(self) -> str:
        """Generate the main app.py file."""
        context = {
            "project_name": self.config.project_name,
            "backend_url": self.config.backend_url,
            "port": self.config.port,
        }

        template_content = self._render_template("app.py.j2", context)
        if template_content:
            return template_content

        # Fallback template
        return f'''"""Main Streamlit application for {self.config.project_name}."""

import streamlit as st
from utils.api_client import APIClient

# Page configuration
st.set_page_config(
    page_title="{self.config.project_name}",
    page_icon="🤖",
    layout="wide"
)

# Initialize API client
if "api_client" not in st.session_state:
    st.session_state.api_client = APIClient(base_url="{self.config.backend_url}")

# Main page
st.title("🤖 {self.config.project_name}")
st.markdown("---")

# Backend health check
with st.sidebar:
    st.header("System Status")

    if st.button("Check Backend Health"):
        try:
            health = st.session_state.api_client.get("/health")
            if health.get("status") == "healthy":
                st.success("✅ Backend is healthy")
            else:
                st.warning("⚠️ Backend status unknown")
        except Exception as e:
            st.error(f"❌ Backend connection failed: {{e}}")

# Welcome message
st.markdown("""
## Welcome to {self.config.project_name}

This is an AI-powered application built with:
- **Backend**: FastAPI (running on {self.config.backend_url})
- **Frontend**: Streamlit (running on port {self.config.port})
- **AI Framework**: CrewAI

### Getting Started

1. Use the sidebar to navigate between pages
2. Check the backend health status in the sidebar
3. Start using the Agent Runner to execute AI tasks

### Features

- 🤖 AI Agent execution
- 📊 Real-time metrics and monitoring
- 🔄 Asynchronous task processing
- 📝 Complete audit logging
""")

# Footer
st.markdown("---")
st.caption("Generated by CAAS - CrewAI as a Service")
'''

    def _generate_agent_runner_page(self) -> str:
        """Generate the Agent Runner page."""
        return '''"""Agent Runner page - Execute AI agents."""

import streamlit as st
from utils.api_client import APIClient

st.set_page_config(page_title="Agent Runner", page_icon="🚀", layout="wide")

# Get API client
api_client = st.session_state.get("api_client")
if not api_client:
    st.error("API client not initialized. Please return to the home page.")
    st.stop()

st.title("🚀 Agent Runner")
st.markdown("Execute AI agents and view results in real-time.")

# Input section
with st.form("agent_form"):
    st.subheader("Agent Configuration")

    task_description = st.text_area(
        "Task Description",
        placeholder="Describe the task you want the agent to perform...",
        height=150
    )

    col1, col2 = st.columns(2)
    with col1:
        temperature = st.slider("Temperature", 0.0, 1.0, 0.7, 0.1)
    with col2:
        max_iterations = st.number_input("Max Iterations", 1, 20, 5)

    submitted = st.form_submit_button("🚀 Run Agent", width='stretch')

if submitted and task_description:
    with st.spinner("Running agent..."):
        try:
            # Call agent endpoint
            response = api_client.post("/api/v1/agents/run", {
                "task": task_description,
                "temperature": temperature,
                "max_iterations": max_iterations
            })

            # Display results
            st.success("✅ Agent execution completed!")

            st.subheader("Results")
            st.json(response)

            # Display metrics if available
            if "metrics" in response:
                st.subheader("Metrics")
                metrics = response["metrics"]
                cols = st.columns(len(metrics))
                for i, (key, value) in enumerate(metrics.items()):
                    cols[i].metric(key, value)

        except Exception as e:
            st.error(f"❌ Error running agent: {e}")

# Recent executions
st.markdown("---")
st.subheader("Recent Executions")

try:
    executions = api_client.get("/api/v1/agents/executions")
    if executions:
        for execution in executions[:5]:
            with st.expander(f"Execution {execution.get('id', 'N/A')}"):
                st.json(execution)
    else:
        st.info("No recent executions found.")
except Exception as e:
    st.warning(f"Could not load recent executions: {e}")
'''

    def _generate_api_client(self) -> str:
        """Generate the API client utility."""
        return f'''"""API client for backend communication."""

import httpx
from typing import Any, Dict, Optional


class APIClient:
    """Client for communicating with the backend API."""

    def __init__(self, base_url: str = "{self.config.backend_url}", timeout: float = 30.0):
        """Initialize the API client.

        Args:
            base_url: Base URL of the backend API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def get(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Make a GET request.

        Args:
            endpoint: API endpoint (e.g., "/health")
            params: Optional query parameters

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{{self.base_url}}{{endpoint}}"
        response = self.client.get(url, params=params)
        response.raise_for_status()
        return response.json()

    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a POST request.

        Args:
            endpoint: API endpoint
            data: Optional form data
            json: Optional JSON data

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{{self.base_url}}{{endpoint}}"
        response = self.client.post(url, data=data, json=json)
        response.raise_for_status()
        return response.json()

    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Make a PUT request.

        Args:
            endpoint: API endpoint
            data: Optional form data
            json: Optional JSON data

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{{self.base_url}}{{endpoint}}"
        response = self.client.put(url, data=data, json=json)
        response.raise_for_status()
        return response.json()

    def delete(self, endpoint: str) -> Dict[str, Any]:
        """Make a DELETE request.

        Args:
            endpoint: API endpoint

        Returns:
            Response JSON

        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{{self.base_url}}{{endpoint}}"
        response = self.client.delete(url)
        response.raise_for_status()
        return response.json()

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
'''

    def _generate_session_utils(self) -> str:
        """Generate session state utilities."""
        return '''"""Session state utilities for Streamlit."""

import streamlit as st
from typing import Any


def get_session_value(key: str, default: Any = None) -> Any:
    """Get a value from session state.

    Args:
        key: Session state key
        default: Default value if key doesn't exist

    Returns:
        Session state value or default
    """
    return st.session_state.get(key, default)


def set_session_value(key: str, value: Any):
    """Set a value in session state.

    Args:
        key: Session state key
        value: Value to set
    """
    st.session_state[key] = value


def clear_session():
    """Clear all session state."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]


def initialize_session_defaults(defaults: dict):
    """Initialize session state with default values.

    Args:
        defaults: Dictionary of default values
    """
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
'''

    def _generate_config_toml(self) -> str:
        """Generate Streamlit configuration file."""
        return f"""[server]
port = {self.config.port}
headless = true
enableCORS = false

[browser]
gatherUsageStats = false

[theme]
primaryColor = "#FF6B6B"
backgroundColor = "#FFFFFF"
secondaryBackgroundColor = "#F0F2F6"
textColor = "#262730"
font = "sans serif"
"""

    def _generate_requirements(self) -> str:
        """Generate requirements.txt."""
        requirements = [
            "streamlit>=1.28.0",
            "httpx>=0.25.0",
        ]

        if self.config.enable_auth:
            requirements.append("streamlit-authenticator>=0.2.0")

        if self.config.enable_metrics:
            requirements.append("plotly>=5.17.0")

        return "\n".join(requirements) + "\n"

    def _generate_readme(self) -> str:
        """Generate README.md."""
        return f"""# {self.config.project_name} - Frontend

Streamlit frontend for {self.config.project_name}.

## Installation

```bash
pip install -r requirements.txt
```

## Running

```bash
streamlit run app.py
```

The application will be available at http://localhost:{self.config.port}

## Backend Configuration

The frontend connects to the backend at: {self.config.backend_url}

To change the backend URL, update the `backend_url` in `app.py`.

## Features

- 🤖 Agent execution interface
- 📊 Real-time monitoring
- 🔄 Asynchronous task tracking
- 📝 Execution history

## Generated by

CAAS - CrewAI as a Service
"""


class ReactTemplateGenerator:
    """Generates React + TypeScript frontend code."""

    def __init__(
        self,
        config: FrontendConfig,
        backend_spec: Optional[Dict[str, Any]] = None,
        jinja_env: Optional[Environment] = None,
    ):
        """Initialize the React generator.

        Args:
            config: Frontend configuration
            backend_spec: Optional backend specification
            jinja_env: Optional Jinja2 environment for template rendering
        """
        self.config = config
        self.backend_spec = backend_spec or {}
        self.jinja_env = jinja_env
        self.templates = ReactTemplates()

    def generate(self) -> Dict[str, str]:
        """Generate React + TypeScript frontend files.

        Returns:
            Dictionary mapping file paths to file contents
        """
        files = {}

        # Generate configuration files
        files["package.json"] = self.templates.package_json_template(
            name=self.config.project_name.lower().replace(" ", "-"),
            description=f"React + TypeScript frontend for {self.config.project_name}",
        )
        files["tsconfig.json"] = self.templates.tsconfig_json_template()
        files["vite.config.ts"] = self._generate_vite_config()
        files["index.html"] = self.templates.index_html_template(
            self.config.project_name
        )

        # Generate entry files
        files["src/main.tsx"] = self.templates.main_tsx_template()
        files["src/App.tsx"] = self.templates.app_tsx_template(self.config.project_name)
        files["src/App.css"] = self.templates.css_template()
        files["src/index.css"] = self.templates.css_template()

        # Generate API types and client
        files.update(self._generate_api_files())

        # Generate components based on backend spec
        files.update(self._generate_components())

        # Generate README
        files["README.md"] = self._generate_readme()

        return files

    def _generate_vite_config(self) -> str:
        """Generate vite.config.ts with backend proxy."""
        # Use template but override server config for backend integration
        base_config = self.templates.vite_config_template()

        # Replace the server config to use configured backend URL
        backend_host = self.config.backend_url.split("://")[-1].split(":")[0]
        backend_port = self.config.backend_url.split(":")[-1].rstrip("/")

        return f"""import {{ defineConfig }} from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({{
  plugins: [react()],
  server: {{
    port: {self.config.port},
    proxy: {{
      '/api': {{
        target: '{self.config.backend_url}',
        changeOrigin: true,
      }},
    }},
  }},
}})
"""

    def _generate_api_files(self) -> Dict[str, str]:
        """Generate API-related TypeScript files."""
        files = {}

        # Extract endpoint information from backend spec
        endpoints = []
        if self.backend_spec and "endpoints" in self.backend_spec:
            for endpoint in self.backend_spec["endpoints"]:
                endpoints.append(
                    {
                        "name": endpoint.get("name", "getData"),
                        "path": endpoint.get("path", "/data"),
                        "method": endpoint.get("method", "GET"),
                        "return_type": endpoint.get("return_type", "any"),
                        "param_type": endpoint.get("param_type", "any"),
                    }
                )

        # If no endpoints provided, create default ones
        if not endpoints:
            endpoints = [
                {
                    "name": "getHealth",
                    "path": "/health",
                    "method": "GET",
                    "return_type": "HealthStatus",
                },
                {
                    "name": "runAgent",
                    "path": "/api/v1/agents/run",
                    "method": "POST",
                    "return_type": "AgentResult",
                    "param_type": "AgentRequest",
                },
            ]

        # Generate API client
        files["src/api/client.ts"] = self.templates.api_client_template(
            base_url="/api", endpoints=endpoints
        )

        # Generate type definitions
        files["src/types/api.ts"] = self._generate_api_types()

        return files

    def _generate_api_types(self) -> str:
        """Generate TypeScript type definitions for API."""
        # Base types that are always needed
        base_types = [
            self.templates.typescript_interface(
                name="HealthStatus",
                fields=[
                    {"name": "status", "type": "string"},
                    {"name": "timestamp", "type": "string"},
                ],
                export=True,
            ),
            self.templates.typescript_interface(
                name="AgentRequest",
                fields=[
                    {"name": "task", "type": "string"},
                    {"name": "temperature", "type": "number"},
                    {"name": "max_iterations", "type": "number"},
                ],
                export=True,
            ),
            self.templates.typescript_interface(
                name="AgentResult",
                fields=[
                    {"name": "result", "type": "string"},
                    {"name": "status", "type": "'success' | 'error'"},
                    {"name": "execution_time", "type": "number"},
                    {"name": "metrics", "type": "Record<string, any>"},
                ],
                export=True,
            ),
        ]

        # Add custom types from backend spec if available
        custom_types = []
        if self.backend_spec and "types" in self.backend_spec:
            for type_def in self.backend_spec["types"]:
                custom_types.append(
                    self.templates.typescript_interface(
                        name=type_def["name"],
                        fields=type_def.get("fields", []),
                        export=True,
                    )
                )

        return "\n".join(base_types + custom_types)

    def _generate_components(self) -> Dict[str, str]:
        """Generate React components."""
        files = {}

        # Generate AgentRunner component
        files[
            "src/components/AgentRunner.tsx"
        ] = self._generate_agent_runner_component()

        # Generate HealthCheck component
        files[
            "src/components/HealthCheck.tsx"
        ] = self._generate_health_check_component()

        # Generate additional components based on backend spec
        if self.backend_spec and "entities" in self.backend_spec:
            for entity in self.backend_spec["entities"]:
                entity_name = entity.get("name", "Item")
                files[
                    f"src/components/{entity_name}List.tsx"
                ] = self.templates.list_component_template(
                    name=f"{entity_name}List", item_type=entity_name, item_render="item"
                )

        return files

    def _generate_agent_runner_component(self) -> str:
        """Generate AgentRunner component using templates."""
        form_fields = [
            {"name": "task", "type": "string"},
            {"name": "temperature", "type": "number"},
            {"name": "max_iterations", "type": "number"},
        ]

        # Use form template as base and customize
        return """import React, { useState } from 'react';
import { apiClient } from '../api/client';
import { AgentRequest, AgentResult } from '../types/api';

export const AgentRunner: React.FC = () => {
  const [task, setTask] = useState<string>('');
  const [temperature, setTemperature] = useState<number>(0.7);
  const [maxIterations, setMaxIterations] = useState<number>(5);
  const [result, setResult] = useState<AgentResult | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const request: AgentRequest = {
        task,
        temperature,
        max_iterations: maxIterations
      };

      const response = await apiClient.runAgent(request);
      setResult(response);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="agent-runner">
      <h2>🚀 Agent Runner</h2>

      <form onSubmit={handleSubmit}>
        <div className="form-field">
          <label htmlFor="task">Task Description</label>
          <textarea
            id="task"
            value={task}
            onChange={(e) => setTask(e.target.value)}
            placeholder="Describe the task you want the agent to perform..."
            rows={6}
            required
          />
        </div>

        <div className="form-field">
          <label htmlFor="temperature">Temperature: {temperature}</label>
          <input
            id="temperature"
            type="range"
            min="0"
            max="1"
            step="0.1"
            value={temperature}
            onChange={(e) => setTemperature(parseFloat(e.target.value))}
          />
        </div>

        <div className="form-field">
          <label htmlFor="maxIterations">Max Iterations</label>
          <input
            id="maxIterations"
            type="number"
            min="1"
            max="20"
            value={maxIterations}
            onChange={(e) => setMaxIterations(parseInt(e.target.value))}
          />
        </div>

        <button type="submit" disabled={loading || !task}>
          {loading ? 'Running...' : '🚀 Run Agent'}
        </button>
      </form>

      {error && (
        <div className="error">
          ❌ Error: {error}
        </div>
      )}

      {result && (
        <div className="result">
          <h3>✅ Results</h3>
          <div className="result-content">
            <p><strong>Status:</strong> {result.status}</p>
            <p><strong>Execution Time:</strong> {result.execution_time}s</p>
            <pre>{result.result}</pre>

            {result.metrics && Object.keys(result.metrics).length > 0 && (
              <div className="metrics">
                <h4>Metrics</h4>
                <pre>{JSON.stringify(result.metrics, null, 2)}</pre>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
"""

    def _generate_health_check_component(self) -> str:
        """Generate HealthCheck component."""
        return """import React, { useState, useEffect } from 'react';
import { apiClient } from '../api/client';
import { HealthStatus } from '../types/api';

export const HealthCheck: React.FC = () => {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    checkHealth();
    const interval = setInterval(checkHealth, 30000); // Check every 30s
    return () => clearInterval(interval);
  }, []);

  const checkHealth = async () => {
    try {
      const response = await apiClient.getHealth();
      setHealth(response);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error');
      setHealth(null);
    } finally {
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="health-check">Checking backend...</div>;
  }

  return (
    <div className="health-check">
      <span className={health ? 'healthy' : 'unhealthy'}>
        {health ? '✅ Backend Healthy' : '❌ Backend Unavailable'}
      </span>
      {error && <span className="error-detail"> ({error})</span>}
    </div>
  );
};
"""

    def _generate_readme(self) -> str:
        """Generate comprehensive README.md."""
        return f"""# {self.config.project_name} - Frontend

React + TypeScript frontend for {self.config.project_name}, powered by Vite.

## Features

- ⚛️ React 18 with TypeScript
- ⚡ Vite for fast development and building
- 🎨 Modern UI components
- 🔌 Type-safe API client
- 🚀 Agent execution interface
- 💚 Backend health monitoring

## Installation

```bash
npm install
```

## Development

Start the development server:

```bash
npm run dev
```

The application will be available at http://localhost:{self.config.port}

## Building

Build for production:

```bash
npm run build
```

Preview production build:

```bash
npm run preview
```

## Type Checking

Run TypeScript type checking:

```bash
npm run type-check
```

## Linting

Run ESLint:

```bash
npm run lint
```

## Backend Configuration

The frontend connects to the backend at: {self.config.backend_url}

To change the backend URL, update the proxy configuration in `vite.config.ts`.

## Project Structure

```
src/
├── api/            # API client and configuration
│   └── client.ts
├── components/     # React components
│   ├── AgentRunner.tsx
│   └── HealthCheck.tsx
├── types/          # TypeScript type definitions
│   └── api.ts
├── App.tsx         # Main application component
├── main.tsx        # Application entry point
└── index.css       # Global styles
```

## Generated by

CAAS - CrewAI as a Service
"""
