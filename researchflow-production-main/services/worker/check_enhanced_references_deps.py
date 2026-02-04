#!/usr/bin/env python3
"""
Enhanced References Dependencies Checker
Audits and validates all required packages for AI-enhanced reference processing
"""

import sys
import importlib
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

@dataclass
class DependencyInfo:
    name: str
    required_version: Optional[str]
    installed_version: Optional[str]
    status: str  # "ok", "missing", "version_mismatch", "error"
    import_path: str
    description: str
    install_command: str

class DependencyChecker:
    """Comprehensive dependency checker for Enhanced References system."""
    
    def __init__(self):
        self.results: List[DependencyInfo] = []
        
        # Define all dependencies for enhanced references
        self.dependencies = {
            # Core FastAPI and async
            "fastapi": {
                "required_version": ">=0.100.0",
                "import_path": "fastapi",
                "description": "FastAPI web framework",
                "install_command": "pip install fastapi"
            },
            "uvicorn": {
                "required_version": ">=0.23.0", 
                "import_path": "uvicorn",
                "description": "ASGI server for FastAPI",
                "install_command": "pip install uvicorn"
            },
            "pydantic": {
                "required_version": ">=2.0.0",
                "import_path": "pydantic",
                "description": "Data validation using Python type hints",
                "install_command": "pip install pydantic"
            },
            "aiohttp": {
                "required_version": ">=3.8.0",
                "import_path": "aiohttp", 
                "description": "Async HTTP client/server",
                "install_command": "pip install aiohttp"
            },
            
            # AI and NLP packages
            "openai": {
                "required_version": ">=1.0.0",
                "import_path": "openai",
                "description": "OpenAI API client",
                "install_command": "pip install openai"
            },
            "langchain": {
                "required_version": ">=0.1.0",
                "import_path": "langchain",
                "description": "LangChain framework for LLMs", 
                "install_command": "pip install langchain"
            },
            "langchain_community": {
                "required_version": ">=0.0.10",
                "import_path": "langchain_community",
                "description": "LangChain community components",
                "install_command": "pip install langchain-community"
            },
            "sentence_transformers": {
                "required_version": ">=2.2.0",
                "import_path": "sentence_transformers",
                "description": "Sentence embedding models",
                "install_command": "pip install sentence-transformers"
            },
            "transformers": {
                "required_version": ">=4.30.0",
                "import_path": "transformers", 
                "description": "Hugging Face transformers",
                "install_command": "pip install transformers"
            },
            "torch": {
                "required_version": ">=2.0.0",
                "import_path": "torch",
                "description": "PyTorch deep learning framework",
                "install_command": "pip install torch"
            },
            "numpy": {
                "required_version": ">=1.24.0",
                "import_path": "numpy",
                "description": "Numerical computing",
                "install_command": "pip install numpy"
            },
            "scipy": {
                "required_version": ">=1.10.0",
                "import_path": "scipy",
                "description": "Scientific computing",
                "install_command": "pip install scipy"
            },
            
            # Data processing
            "pandas": {
                "required_version": ">=2.0.0",
                "import_path": "pandas",
                "description": "Data manipulation and analysis",
                "install_command": "pip install pandas"
            },
            "requests": {
                "required_version": ">=2.28.0",
                "import_path": "requests",
                "description": "HTTP library",
                "install_command": "pip install requests"
            },
            "beautifulsoup4": {
                "required_version": ">=4.11.0",
                "import_path": "bs4",
                "description": "HTML/XML parsing",
                "install_command": "pip install beautifulsoup4"
            },
            "lxml": {
                "required_version": ">=4.9.0",
                "import_path": "lxml",
                "description": "XML processing library",
                "install_command": "pip install lxml"
            },
            
            # Database and caching
            "redis": {
                "required_version": ">=4.5.0",
                "import_path": "redis",
                "description": "Redis client for caching",
                "install_command": "pip install redis"
            },
            "sqlalchemy": {
                "required_version": ">=2.0.0", 
                "import_path": "sqlalchemy",
                "description": "SQL toolkit and ORM",
                "install_command": "pip install sqlalchemy"
            },
            
            # Utilities
            "python_dotenv": {
                "required_version": ">=1.0.0",
                "import_path": "dotenv",
                "description": "Environment variable management",
                "install_command": "pip install python-dotenv"
            },
            "tenacity": {
                "required_version": ">=8.2.0",
                "import_path": "tenacity",
                "description": "Retry library",
                "install_command": "pip install tenacity"
            },
            "cachetools": {
                "required_version": ">=5.3.0",
                "import_path": "cachetools",
                "description": "Extensible memoizing collections",
                "install_command": "pip install cachetools"
            },
            
            # Testing (optional but recommended)
            "pytest": {
                "required_version": ">=7.0.0",
                "import_path": "pytest",
                "description": "Testing framework",
                "install_command": "pip install pytest"
            },
            "pytest_asyncio": {
                "required_version": ">=0.21.0",
                "import_path": "pytest_asyncio", 
                "description": "Async testing support for pytest",
                "install_command": "pip install pytest-asyncio"
            }
        }
    
    def get_package_version(self, package_name: str) -> Optional[str]:
        """Get installed version of a package."""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                check=False
            )
            if result.returncode == 0:
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
            return None
        except Exception:
            return None
    
    def check_import(self, import_path: str) -> Tuple[bool, Optional[str]]:
        """Check if a module can be imported and get its version."""
        try:
            module = importlib.import_module(import_path)
            version = getattr(module, '__version__', None)
            return True, version
        except ImportError:
            return False, None
        except Exception as e:
            return False, str(e)
    
    def parse_version_requirement(self, req: str) -> Tuple[str, str]:
        """Parse version requirement string like '>=1.0.0'."""
        if req.startswith(">="):
            return ">=", req[2:]
        elif req.startswith("<="):
            return "<=", req[2:]
        elif req.startswith("=="):
            return "==", req[2:]
        elif req.startswith(">"):
            return ">", req[1:]
        elif req.startswith("<"):
            return "<", req[1:]
        else:
            return "==", req
    
    def check_version_compatibility(self, installed: str, required: str) -> bool:
        """Check if installed version meets requirement."""
        if not required or not installed:
            return True
            
        try:
            from packaging import version
            op, req_ver = self.parse_version_requirement(required)
            installed_ver = version.parse(installed)
            required_ver = version.parse(req_ver)
            
            if op == ">=":
                return installed_ver >= required_ver
            elif op == "<=":
                return installed_ver <= required_ver
            elif op == "==":
                return installed_ver == required_ver
            elif op == ">":
                return installed_ver > required_ver
            elif op == "<":
                return installed_ver < required_ver
            else:
                return True
        except ImportError:
            # packaging not available, do string comparison (less reliable)
            return installed >= required.replace(">=", "").replace("<=", "").replace("==", "")
        except Exception:
            return True
    
    def check_dependency(self, name: str, info: Dict) -> DependencyInfo:
        """Check a single dependency."""
        import_path = info["import_path"]
        required_version = info.get("required_version")
        description = info["description"]
        install_command = info["install_command"]
        
        # Try importing
        can_import, import_version = self.check_import(import_path)
        
        # Get pip version
        pip_version = self.get_package_version(name)
        
        # Determine installed version (prefer import version)
        installed_version = import_version or pip_version
        
        # Determine status
        if not can_import:
            status = "missing"
        elif required_version and installed_version:
            if self.check_version_compatibility(installed_version, required_version):
                status = "ok"
            else:
                status = "version_mismatch"
        elif can_import:
            status = "ok"
        else:
            status = "error"
        
        return DependencyInfo(
            name=name,
            required_version=required_version,
            installed_version=installed_version,
            status=status,
            import_path=import_path,
            description=description,
            install_command=install_command
        )
    
    def check_all_dependencies(self) -> List[DependencyInfo]:
        """Check all dependencies."""
        print("🔍 Checking Enhanced References dependencies...")
        print("=" * 70)
        
        self.results = []
        for name, info in self.dependencies.items():
            dep_info = self.check_dependency(name, info)
            self.results.append(dep_info)
            
            # Print status
            status_emoji = {
                "ok": "✅",
                "missing": "❌",
                "version_mismatch": "⚠️",
                "error": "🔥"
            }
            
            emoji = status_emoji.get(dep_info.status, "❓")
            version_info = f"({dep_info.installed_version})" if dep_info.installed_version else "(not found)"
            required_info = f"requires {dep_info.required_version}" if dep_info.required_version else ""
            
            print(f"{emoji} {dep_info.name:<20} {version_info:<15} {required_info}")
        
        return self.results
    
    def generate_summary(self) -> Dict:
        """Generate summary of dependency check."""
        if not self.results:
            self.check_all_dependencies()
        
        summary = {
            "total": len(self.results),
            "ok": 0,
            "missing": 0,
            "version_mismatch": 0,
            "error": 0
        }
        
        for result in self.results:
            summary[result.status] += 1
        
        return summary
    
    def generate_install_commands(self) -> List[str]:
        """Generate install commands for missing/problematic packages."""
        if not self.results:
            self.check_all_dependencies()
        
        commands = []
        for result in self.results:
            if result.status in ["missing", "version_mismatch"]:
                commands.append(result.install_command)
        
        return commands
    
    def print_detailed_report(self):
        """Print detailed dependency report."""
        if not self.results:
            self.check_all_dependencies()
        
        summary = self.generate_summary()
        
        print("\n" + "=" * 70)
        print("📊 DEPENDENCY SUMMARY")
        print("=" * 70)
        print(f"✅ OK: {summary['ok']}")
        print(f"❌ Missing: {summary['missing']}")
        print(f"⚠️  Version mismatch: {summary['version_mismatch']}")
        print(f"🔥 Error: {summary['error']}")
        print(f"📦 Total: {summary['total']}")
        
        # Show problematic packages
        problematic = [r for r in self.results if r.status != "ok"]
        if problematic:
            print(f"\n⚠️  ISSUES FOUND ({len(problematic)} packages)")
            print("-" * 70)
            for pkg in problematic:
                print(f"Package: {pkg.name}")
                print(f"Status: {pkg.status}")
                print(f"Required: {pkg.required_version or 'any'}")
                print(f"Installed: {pkg.installed_version or 'none'}")
                print(f"Install: {pkg.install_command}")
                print()
        
        # Generate install commands
        install_commands = self.generate_install_commands()
        if install_commands:
            print("💡 QUICK FIX")
            print("-" * 70)
            print("Run these commands to install missing packages:")
            print()
            for cmd in install_commands:
                print(f"  {cmd}")
            print()
            print("Or install all at once:")
            packages = [cmd.split()[-1] for cmd in install_commands]
            print(f"  pip install {' '.join(packages)}")
        
        # Final assessment
        if summary['missing'] == 0 and summary['version_mismatch'] == 0 and summary['error'] == 0:
            print("🎉 ALL DEPENDENCIES OK! Enhanced References should work correctly.")
        elif summary['missing'] + summary['version_mismatch'] <= 3:
            print("⚠️  Minor issues found. Enhanced References may work with reduced functionality.")
        else:
            print("❌ Major issues found. Enhanced References may not work properly.")

def check_enhanced_references_module():
    """Check if the enhanced references module can be loaded."""
    print("\n🔧 ENHANCED REFERENCES MODULE TEST")
    print("=" * 70)
    
    try:
        # Try to import the enhanced references API
        sys.path.insert(0, str(Path(__file__).parent / "src"))
        from api.enhanced_references import router
        print("✅ Enhanced references API router loaded successfully")
        
        # Check if dependencies are available within the module
        try:
            from agents.writing.integration_hub import get_integration_hub
            print("✅ Integration hub available")
        except ImportError as e:
            print(f"⚠️  Integration hub not available: {e}")
        
        try:
            from agents.writing.reference_management_service import get_reference_service
            print("✅ Reference management service available")
        except ImportError as e:
            print(f"⚠️  Reference management service not available: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Failed to load enhanced references module: {e}")
        return False
    except Exception as e:
        print(f"🔥 Error testing enhanced references module: {e}")
        return False

def main():
    """Main function to run dependency check."""
    print("🎯 Enhanced References Dependencies Audit")
    print("ResearchFlow - AI-Enhanced Reference Management")
    print()
    
    # Check system info
    print(f"🐍 Python: {sys.version.split()[0]}")
    print(f"📂 Working directory: {Path.cwd()}")
    print()
    
    # Check dependencies
    checker = DependencyChecker()
    checker.print_detailed_report()
    
    # Check enhanced references module
    module_ok = check_enhanced_references_module()
    
    # Final recommendation
    print("\n" + "=" * 70)
    print("🎯 FINAL ASSESSMENT")
    print("=" * 70)
    
    summary = checker.generate_summary()
    
    if summary['missing'] == 0 and summary['error'] == 0 and module_ok:
        print("🟢 READY: Enhanced References API is ready to use!")
        print("   ├─ All dependencies are satisfied")
        print("   ├─ Enhanced references module loads correctly")
        print("   └─ You can start the API server with: python3 api_server.py")
        
    elif summary['missing'] <= 2 and summary['error'] == 0:
        print("🟡 PARTIAL: Enhanced References API will work with limited functionality")
        print("   ├─ Core dependencies are available")
        print("   ├─ Some AI features may be disabled")
        print("   └─ Install missing packages for full functionality")
        
    else:
        print("🔴 NOT READY: Enhanced References API will not work properly")
        print("   ├─ Critical dependencies are missing")
        print("   ├─ Install required packages before proceeding") 
        print("   └─ See install commands above")
    
    print()
    return 0 if (summary['missing'] + summary['error']) == 0 else 1

if __name__ == "__main__":
    sys.exit(main())