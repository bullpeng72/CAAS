"""
UI Component Generator

Streamlit 기반 UI 컴포넌트 자동 생성
"""

from typing import Dict, Any, List, Optional
from app.codegen.artifact_generator import (
    BaseArtifactGenerator,
    GeneratedArtifact,
    ArtifactMetadata,
    ArtifactType,
)
from app.utils.logger import get_logger

logger = get_logger("ui_generator")


class StreamlitUIGenerator(BaseArtifactGenerator):
    """Streamlit UI 컴포넌트 생성기"""

    def generate(
        self,
        requirement: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedArtifact:
        """Streamlit UI를 생성합니다"""
        self.logger.info("Generating Streamlit UI")

        # UI 페이지 정보 추출
        ui_pages = requirement.get("ui_pages", [])
        project_name = requirement.get("project_name", "my_app")
        summary = requirement.get("summary", "Application")

        if not ui_pages:
            # 기본 UI 생성
            ui_pages = [
                {
                    "id": "home",
                    "name": "Home",
                    "components": [
                        {"type": "title", "content": summary},
                        {"type": "input", "label": "Enter your request"},
                        {"type": "button", "label": "Submit"},
                    ]
                }
            ]

        # 코드 생성
        code_lines = [
            '"""',
            f'{project_name.replace("_", " ").title()} - Streamlit UI',
            '"""',
            "",
            "def main():",
            f'    st.set_page_config(page_title="{project_name.title()}", layout="wide")',
            "",
            "    # Sidebar",
            '    with st.sidebar:',
            f'        st.title("{project_name.title()}")',
            f'        st.markdown("{summary}")',
            "",
        ]

        # 각 페이지 생성
        for page in ui_pages:
            page_name = page.get("name", "Page")
            components = page.get("components", [])

            code_lines.append(f'    # {page_name} Section')
            code_lines.append(f'    st.header("{page_name}")')

            for component in components:
                comp_type = component.get("type", "text")

                if comp_type == "title":
                    content = component.get("content", "Title")
                    code_lines.append(f'    st.title("{content}")')

                elif comp_type == "input":
                    label = component.get("label", "Input")
                    var_name = label.lower().replace(" ", "_")
                    code_lines.append(f'    {var_name} = st.text_input("{label}")')

                elif comp_type == "button":
                    label = component.get("label", "Button")
                    code_lines.append(f'    if st.button("{label}"):')
                    code_lines.append(f'        st.success("Action triggered!")')

                elif comp_type == "output":
                    code_lines.append(f'    st.markdown("**Results:**")')
                    code_lines.append(f'    st.write("Output will be displayed here")')

            code_lines.append("")

        # Main 실행
        code_lines.extend([
            "",
            "if __name__ == '__main__':",
            "    main()",
        ])

        code = "\n".join(code_lines)
        imports = self._build_imports(["streamlit"])

        metadata = ArtifactMetadata(
            type=ArtifactType.UI_COMPONENT,
            name=f"{project_name}_ui",
            description="Streamlit UI Interface",
            framework="streamlit",
        )

        quality_score = self._calculate_quality_score(code)

        return GeneratedArtifact(
            metadata=metadata,
            file_path=f"{project_name}/app.py",
            code=code,
            imports=imports,
            quality_score=quality_score,
        )

    def validate(self, artifact: GeneratedArtifact) -> bool:
        """생성된 UI 코드를 검증합니다"""
        code = artifact.code

        # Streamlit 필수 요소 확인
        if "st." not in code:
            self.logger.error("No Streamlit components found")
            return False

        # 문법 검증
        try:
            compile(code, "<string>", "exec")
            return True
        except SyntaxError as e:
            self.logger.error(f"Syntax error: {e}")
            return False


class ReactUIGenerator(BaseArtifactGenerator):
    """React UI 컴포넌트 생성기 (간단한 버전)"""

    def generate(
        self,
        requirement: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> GeneratedArtifact:
        """React UI를 생성합니다"""
        self.logger.info("Generating React UI")

        project_name = requirement.get("project_name", "my_app")
        summary = requirement.get("summary", "Application")

        # React 컴포넌트 코드
        code_lines = [
            "import React, { useState } from 'react';",
            "",
            f"function {project_name.title().replace('_', '')}App() {{",
            "  const [input, setInput] = useState('');",
            "  const [result, setResult] = useState('');",
            "",
            "  const handleSubmit = async () => {",
            "    // API call logic here",
            "    console.log('Submitting:', input);",
            "  };",
            "",
            "  return (",
            "    <div className='app-container'>",
            f"      <h1>{project_name.replace('_', ' ').title()}</h1>",
            f"      <p>{summary}</p>",
            "",
            "      <div className='input-section'>",
            "        <input",
            "          type='text'",
            "          value={input}",
            "          onChange={(e) => setInput(e.target.value)}",
            "          placeholder='Enter your request'",
            "        />",
            "        <button onClick={handleSubmit}>Submit</button>",
            "      </div>",
            "",
            "      <div className='output-section'>",
            "        {result && <div className='result'>{result}</div>}",
            "      </div>",
            "    </div>",
            "  );",
            "}",
            "",
            f"export default {project_name.title().replace('_', '')}App;",
        ]

        code = "\n".join(code_lines)

        metadata = ArtifactMetadata(
            type=ArtifactType.UI_COMPONENT,
            name=f"{project_name}_ui",
            description="React UI Component",
            framework="react",
            language="javascript",
        )

        quality_score = self._calculate_quality_score(code)

        return GeneratedArtifact(
            metadata=metadata,
            file_path=f"{project_name}/App.jsx",
            code=code,
            imports=[],  # imports included in code
            quality_score=quality_score,
        )

    def validate(self, artifact: GeneratedArtifact) -> bool:
        """생성된 React 코드를 검증합니다"""
        code = artifact.code

        # React 필수 요소 확인
        required = ["import React", "return (", "export default"]
        for req in required:
            if req not in code:
                self.logger.error(f"Missing required element: {req}")
                return False

        return True
