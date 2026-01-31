"""
React + TypeScript Templates

Provides templates for React components, TypeScript types, and modern tooling.
"""

from typing import Dict, List, Optional


class ReactTemplates:
    """React + TypeScript code templates"""

    @staticmethod
    def component_template(
        name: str,
        props_interface: Optional[str] = None,
        has_state: bool = False,
        state_type: Optional[str] = None,
        has_effect: bool = False
    ) -> str:
        """Generate React functional component"""

        imports = ["import React"]
        if has_state:
            imports.append("{ useState }")
        if has_effect:
            imports.append("{ useEffect }")

        import_line = imports[0]
        if len(imports) > 1:
            import_line = f"import React, {{ {', '.join(imports[1:])} }} from 'react';"
        else:
            import_line = "import React from 'react';"

        # Props interface
        props_def = ""
        if props_interface:
            props_def = f"\ninterface {name}Props {{\n{props_interface}\n}}\n"
            component_signature = f"export const {name}: React.FC<{name}Props> = (props) => {{"
        else:
            component_signature = f"export const {name}: React.FC = () => {{"

        # State hooks
        state_hooks = ""
        if has_state and state_type:
            state_hooks = f"\n  const [state, setState] = useState<{state_type}>(/* initial state */);\n"

        # Effect hook
        effect_hook = ""
        if has_effect:
            effect_hook = """
  useEffect(() => {
    // Effect logic here
    return () => {
      // Cleanup logic here
    };
  }, []);
"""

        return f"""{import_line}

{props_def}{component_signature}{state_hooks}{effect_hook}
  return (
    <div className="{name.lower()}">
      <h2>{name}</h2>
      {{/* Component content */}}
    </div>
  );
}};
"""

    @staticmethod
    def list_component_template(
        name: str,
        item_type: str,
        item_render: str = "item"
    ) -> str:
        """Generate list component with map"""

        return f"""import React, {{ useState, useEffect }} from 'react';
import {{ {item_type} }} from '../types/api';
import {{ apiClient }} from '../api/client';

interface {name}Props {{
  onItemSelect?: (item: {item_type}) => void;
}}

export const {name}: React.FC<{name}Props> = ({{ onItemSelect }}) => {{
  const [items, setItems] = useState<{item_type}[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {{
    const fetchItems = async () => {{
      try {{
        const data = await apiClient.get{item_type}s();
        setItems(data);
      }} catch (err) {{
        setError(err instanceof Error ? err.message : 'Unknown error');
      }} finally {{
        setLoading(false);
      }}
    }};

    fetchItems();
  }}, []);

  if (loading) return <div>Loading...</div>;
  if (error) return <div>Error: {{error}}</div>;

  return (
    <div className="{name.lower()}">
      {{items.map({item_render} => (
        <div
          key={{{item_render}.id}}
          onClick={{() => onItemSelect?.({item_render})}}
          className="item"
        >
          {{{item_render}.name}}
        </div>
      ))}}
    </div>
  );
}};
"""

    @staticmethod
    def form_component_template(
        name: str,
        fields: List[Dict[str, str]]
    ) -> str:
        """Generate form component"""

        # Build state type
        state_fields = [f"  {field['name']}: {field['type']};" for field in fields]
        state_type = "{\n" + "\n".join(state_fields) + "\n}"

        # Build initial state
        initial_values = []
        for field in fields:
            if field['type'] == 'string':
                initial_values.append(f"    {field['name']}: '',")
            elif field['type'] == 'number':
                initial_values.append(f"    {field['name']}: 0,")
            elif field['type'] == 'boolean':
                initial_values.append(f"    {field['name']}: false,")
            else:
                initial_values.append(f"    {field['name']}: null,")

        initial_state = "{\n" + "\n".join(initial_values) + "\n  }"

        # Build form inputs
        form_inputs = []
        for field in fields:
            input_type = "text"
            if field['type'] == 'number':
                input_type = "number"
            elif field['type'] == 'boolean':
                input_type = "checkbox"

            form_inputs.append(f"""        <div className="form-field">
          <label htmlFor="{field['name']}">{field['name'].title()}</label>
          <input
            id="{field['name']}"
            type="{input_type}"
            value={{formData.{field['name']}}}
            onChange={{(e) => setFormData({{ ...formData, {field['name']}: e.target.value }})}}
          />
        </div>""")

        form_fields = "\n".join(form_inputs)

        return f"""import React, {{ useState }} from 'react';

type FormData = {state_type};

interface {name}Props {{
  onSubmit: (data: FormData) => void;
  onCancel?: () => void;
}}

export const {name}: React.FC<{name}Props> = ({{ onSubmit, onCancel }}) => {{
  const [formData, setFormData] = useState<FormData>({initial_state});

  const handleSubmit = (e: React.FormEvent) => {{
    e.preventDefault();
    onSubmit(formData);
  }};

  return (
    <form onSubmit={{handleSubmit}} className="{name.lower()}">
{form_fields}

      <div className="form-actions">
        <button type="submit">Submit</button>
        {{onCancel && <button type="button" onClick={{onCancel}}>Cancel</button>}}
      </div>
    </form>
  );
}};
"""

    @staticmethod
    def typescript_interface(
        name: str,
        fields: List[Dict[str, str]],
        export: bool = True
    ) -> str:
        """Generate TypeScript interface"""

        export_keyword = "export " if export else ""
        field_lines = [f"  {field['name']}: {field['type']};" for field in fields]
        fields_str = "\n".join(field_lines)

        return f"""{export_keyword}interface {name} {{
{fields_str}
}}
"""

    @staticmethod
    def api_client_template(
        base_url: str = "/api",
        endpoints: List[Dict[str, str]] = None
    ) -> str:
        """Generate API client with Axios"""

        methods = []
        if endpoints:
            for endpoint in endpoints:
                method_name = endpoint.get('name', 'getData')
                return_type = endpoint.get('return_type', 'any')
                path = endpoint.get('path', '/data')
                http_method = endpoint.get('method', 'GET').lower()

                if http_method == 'get':
                    methods.append(f"""
  async {method_name}(): Promise<{return_type}> {{
    const response = await this.client.get<APIResponse<{return_type}>>('{path}');
    return response.data.data;
  }}""")
                elif http_method == 'post':
                    param_type = endpoint.get('param_type', 'any')
                    methods.append(f"""
  async {method_name}(data: {param_type}): Promise<{return_type}> {{
    const response = await this.client.post<APIResponse<{return_type}>>('{path}', data);
    return response.data.data;
  }}""")

        methods_str = "".join(methods) if methods else """
  async getData(): Promise<any> {
    const response = await this.client.get('/data');
    return response.data;
  }"""

        return f"""import axios, {{ AxiosInstance }} from 'axios';

interface APIResponse<T> {{
  data: T;
  status: 'success' | 'error';
  message?: string;
}}

class APIClient {{
  private client: AxiosInstance;

  constructor(baseURL: string = '{base_url}') {{
    this.client = axios.create({{
      baseURL,
      headers: {{
        'Content-Type': 'application/json',
      }},
    }});
  }}{methods_str}
}}

export const apiClient = new APIClient();
"""

    @staticmethod
    def package_json_template(
        name: str,
        description: str = "Generated by CAAS"
    ) -> str:
        """Generate package.json"""

        return f"""{{
  "name": "{name}",
  "version": "0.1.0",
  "description": "{description}",
  "type": "module",
  "scripts": {{
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "type-check": "tsc --noEmit"
  }},
  "dependencies": {{
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "axios": "^1.6.0"
  }},
  "devDependencies": {{
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0",
    "@typescript-eslint/eslint-plugin": "^6.0.0",
    "@typescript-eslint/parser": "^6.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "eslint": "^8.55.0",
    "eslint-plugin-react-hooks": "^4.6.0",
    "eslint-plugin-react-refresh": "^0.4.5",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }}
}}
"""

    @staticmethod
    def tsconfig_json_template() -> str:
        """Generate tsconfig.json"""

        return """{
  "compilerOptions": {
    "target": "ES2020",
    "useDefineForClassFields": true,
    "lib": ["ES2020", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "skipLibCheck": true,

    /* Bundler mode */
    "moduleResolution": "bundler",
    "allowImportingTsExtensions": true,
    "resolveJsonModule": true,
    "isolatedModules": true,
    "noEmit": true,
    "jsx": "react-jsx",

    /* Linting */
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  },
  "include": ["src"],
  "references": [{ "path": "./tsconfig.node.json" }]
}
"""

    @staticmethod
    def vite_config_template() -> str:
        """Generate vite.config.ts"""

        return """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
"""

    @staticmethod
    def index_html_template(title: str = "React App") -> str:
        """Generate index.html"""

        return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <link rel="icon" type="image/svg+xml" href="/vite.svg" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>{title}</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
"""

    @staticmethod
    def main_tsx_template() -> str:
        """Generate main.tsx entry point"""

        return """import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
"""

    @staticmethod
    def app_tsx_template(app_name: str = "App") -> str:
        """Generate App.tsx"""

        return f"""import React from 'react'
import './App.css'

function App() {{
  return (
    <div className="App">
      <header className="App-header">
        <h1>{app_name}</h1>
        <p>Generated by CAAS - CrewAI Automatic Coder System</p>
      </header>
      <main>
        {{/* Your components here */}}
      </main>
    </div>
  )
}}

export default App
"""

    @staticmethod
    def css_template() -> str:
        """Generate basic CSS"""

        return """:root {
  font-family: Inter, system-ui, Avenir, Helvetica, Arial, sans-serif;
  line-height: 1.5;
  font-weight: 400;

  color-scheme: light dark;
  color: rgba(255, 255, 255, 0.87);
  background-color: #242424;

  font-synthesis: none;
  text-rendering: optimizeLegibility;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

body {
  margin: 0;
  display: flex;
  place-items: center;
  min-width: 320px;
  min-height: 100vh;
}

#root {
  max-width: 1280px;
  margin: 0 auto;
  padding: 2rem;
  text-align: center;
}
"""
