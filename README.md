# 🚀 Automated Drill-and-Blast System with AI-Powered ML Pipeline

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![React](https://img.shields.io/badge/react-18+-61dafb.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/fastapi-0.104+-009688.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A revolutionary, production-grade solution that transforms mining operations by generating complete, safety-validated drill-and-blast plans without requiring historical training data. The system combines established physics-based models with cutting-edge AI/ML capabilities including SAM-based fragmentation analysis, XGBoost residual learning, and real-time performance monitoring.

## 🌟 Key Features

### 🧠 **AI-Powered ML Pipeline**
- **SAM-Based Fragmentation Analysis**: Advanced computer vision for muckpile image analysis
- **XGBoost Residual Learning**: Continuous improvement of physics predictions with 26+ engineered features
- **Real-Time Performance Monitoring**: Drift detection and intelligent retraining recommendations
- **Automated Data Ingestion**: Batch processing of images and sensor data with quality validation

### ⚡ **Physics-Based Foundation**
- **Immediate Results**: No historical data required - start using immediately
- **Kuz-Ram Fragmentation Model**: Industry-standard fragmentation predictions with configurable parameters
- **Empirical PPV Models**: Accurate vibration predictions with multi-charge support
- **Rosin-Rammler Distributions**: Complete size distribution analysis and curve generation

### 🎯 **Multi-Algorithm Optimization**
- **CP-SAT Solver**: Discrete optimization for charges, delays, and regulatory constraints
- **SciPy Integration**: Continuous optimization with differential evolution and SLSQP
- **Genetic Algorithms**: Global optimization for complex multi-objective scenarios
- **Real-Time Progress**: WebSocket-based optimization monitoring with live updates

### 🛡️ **Safety-First Design**
- **Hard-Coded Safety Gates**: Unbypassable safety constraints and validation
- **Engineer Sign-Off**: Mandatory professional certification with digital signatures
- **Comprehensive Validation**: PPV limits, charge restrictions, regulatory compliance
- **Immutable Audit Trails**: Complete traceability of all decisions and modifications

### 📊 **Advanced Analytics & Reporting**
- **Interactive Dashboards**: Real-time visualization of blast parameters and results
- **Multiple Export Formats**: PDF reports, CSV data, JSON/GeoJSON for GIS integration
- **Performance Metrics**: Model accuracy tracking and improvement analytics
- **Synthetic Data Generation**: Create diverse training scenarios without real blasts

### 🌐 **Modern Architecture**
- **Cloud-Native**: Supabase integration for reliable, scalable data persistence
- **Responsive Web Interface**: React + TypeScript with Material-UI components
- **RESTful API**: FastAPI with automatic OpenAPI documentation
- **Microservices Design**: Scalable, maintainable, and testable architecture

## 🚀 Quick Start

### Prerequisites
- Python 3.11+ 
- Node.js 18+
- PostgreSQL (or Supabase account)

### 1. Installation

```bash
# Clone the repository
git clone 
cd automated-drill-blast-system

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd frontend && npm install && cd ..
```

### 2. Supabase Setup

1. Create a new project at [supabase.com](https://supabase.com)
2. Get your project URL and API keys from the project settings
3. Create a storage bucket named `drill-blast-files` for file uploads
4. Set up the required environment variables (see Configuration section)

### 3. Configuration

```bash
# Set up environment variables
cp .env.example .env
# Edit .env with your Supabase credentials and configuration
```

### 4. Launch the System

```bash
# Start the backend server
python run_dev.py

# In another terminal, start the frontend
cd frontend && npm run dev
```

### 5. Access the Application
- **Web Interface**: http://localhost:3000
- **API Documentation**: http://localhost:8000/docs
- **ML Pipeline**: Navigate to "ML Pipeline" in the web interface

### Using Docker

```bash
# Build and run with Docker Compose
docker-compose up -d

# Or build and run manually
docker build -t drill-blast-system .
docker run -p 8000:8000 drill-blast-system
```

## Usage

### Web Interface

1. Start the server: `drill-blast-system serve`
2. Open your browser to `http://localhost:8000`
3. Access API documentation at `http://localhost:8000/docs`

### Command Line Interface

```bash
# Initialize database
drill-blast-system init-db

# Start server
drill-blast-system serve --host 0.0.0.0 --port 8000

# Check configuration
drill-blast-system check-config

# Create default config file
drill-blast-system create-config --output config.yaml

# Database management
drill-blast-system db status
drill-blast-system db backup --backup-file backup.db
```

## Configuration

The system uses a hierarchical configuration system:

1. Default values in code
2. Configuration file (`config.yaml`)
3. Environment variables
4. Command line arguments

### Environment Variables

```bash
# Supabase Database
export DB_SUPABASE_URL="https://your-project.supabase.co"
export DB_SUPABASE_KEY="your-anon-key"
export DB_SUPABASE_SERVICE_KEY="your-service-role-key"

# API
export API_HOST="127.0.0.1"
export API_PORT="8000"

# Security
export SECURITY_REQUIRE_ENGINEER_SIGNOFF="true"
export SECURITY_AUDIT_TRAIL_ENABLED="true"

# Physics defaults
export PHYSICS_DEFAULT_ROCK_FACTOR_A="7.0"
export PHYSICS_DEFAULT_PPV_K="1.4"
```

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend│────│   FastAPI Backend│────│  Supabase Cloud │
│   (TypeScript)  │    │    (Python)      │    │  (PostgreSQL)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                        │                        │
         │              ┌──────────────────┐              │
         └──────────────│   ML Pipeline    │──────────────┘
                        │  • SAM Analysis  │
                        │  • XGBoost ML    │
                        │  • Data Ingestion│
                        └──────────────────┘
```

### Core Components

- **🎨 Frontend**: React 18 + TypeScript + Material-UI
- **⚙️ Backend**: FastAPI + SQLAlchemy + Pydantic
- **🗄️ Database**: PostgreSQL with Supabase cloud integration
- **🤖 ML Pipeline**: SAM + XGBoost + Computer Vision
- **🔧 Optimization**: OR-Tools CP-SAT + SciPy + PyGAD
- **🛡️ Safety**: Comprehensive validation framework

## 🧠 ML Pipeline Features

### Fragmentation Analysis
- **SAM Integration**: State-of-the-art image segmentation for fragment detection
- **Scale Detection**: Automatic calibration from reference objects and markers
- **Quality Assessment**: Confidence scoring and validation with quality flags
- **Batch Processing**: Handle multiple images simultaneously with progress tracking

### Residual Learning
- **Feature Engineering**: 26+ engineered features from blast parameters including:
  - Interaction terms (burden × spacing, powder factor × rock density)
  - Domain-specific features (burden-diameter ratio, stemming ratio)
  - Polynomial features for non-linear relationships
- **XGBoost Models**: Gradient boosting for physics model corrections
- **Performance Monitoring**: Real-time drift detection and model degradation alerts
- **Retraining Automation**: Intelligent recommendations based on data availability and performance

### Data Management
- **Multi-Format Support**: Images (JPEG, PNG, TIFF), sensor data (CSV, JSON, XML)
- **Quality Control**: Automated validation, filtering, and quality scoring
- **Metadata Tracking**: Complete provenance and audit trails for all measurements
- **Cloud Storage**: Secure, scalable data persistence with Supabase integration

### Performance Monitoring
- **Real-Time Analytics**: Track prediction accuracy and model performance
- **Drift Detection**: Statistical monitoring of prediction quality over time
- **Confidence Intervals**: Uncertainty quantification for all predictions
- **Retraining Triggers**: Automated recommendations based on performance degradation

## Safety and Compliance

The system implements multiple safety layers:

- **Hard Safety Constraints**: Cannot be overridden by users
- **Engineer Sign-off**: Required for all plan exports
- **Audit Trail**: Immutable logging of all critical operations
- **Safety Validation**: Comprehensive constraint checking
- **Legal Disclaimers**: Required acknowledgment before export

## 📈 Use Cases

### 🏭 **Mining Operations**
- Generate blast plans for new sites without historical data
- Optimize existing operations with AI-enhanced predictions
- Ensure regulatory compliance with automated safety validation
- Reduce costs through precise powder factor optimization
- Monitor and improve prediction accuracy over time

### 🎓 **Research & Development**
- Validate physics models against real-world measurements
- Develop new optimization algorithms with synthetic data
- Study blast parameter relationships with ML insights
- Benchmark different prediction approaches and methodologies

### 📚 **Education & Training**
- Teach blast design principles with interactive tools
- Demonstrate optimization algorithms in real-time
- Provide safe environment for learning without real explosives
- Generate diverse scenarios for comprehensive training programs

## 🛠️ Development

### Project Structure
```
├── src/drill_blast_system/     # Backend Python code
│   ├── api/                    # FastAPI routes and middleware
│   ├── ml_pipeline/           # ML components and algorithms
│   │   ├── residual_learner.py    # XGBoost residual learning
│   │   ├── fragmentation_analyzer.py # SAM-based analysis
│   │   ├── data_ingestion.py      # Batch data processing
│   │   └── quality_assessment.py  # Quality validation
│   ├── physics_models/        # Kuz-Ram, PPV implementations
│   ├── optimization/          # Multi-algorithm optimization
│   └── safety/               # Safety validation framework
├── frontend/                  # React TypeScript frontend
│   ├── src/components/       # Reusable UI components
│   │   ├── MLPipeline/       # ML Pipeline interfaces
│   │   ├── Optimization/     # Optimization components
│   │   └── Results/          # Results and reporting
│   ├── src/pages/           # Application pages
│   └── src/services/        # API integration services
├── tests/                   # Comprehensive test suite
├── examples/               # Usage examples and demos
└── docs/                  # Documentation
```

### Running Tests
```bash
# Backend tests
python -m pytest tests/ -v

# Frontend tests
cd frontend && npm test

# ML Pipeline tests
python test_ml_components.py

# Integration tests
python test_ml_pipeline_api.py
```

### Code Quality
```bash
# Python formatting and linting
black src/
flake8 src/
mypy src/

# Frontend linting
cd frontend && npm run lint && npm run type-check
```

## 📊 Performance & Scalability

### Benchmarks
- **Optimization Speed**: <30 seconds for typical blast plans
- **ML Inference**: <2 seconds for fragmentation analysis
- **Concurrent Users**: Supports 100+ simultaneous users
- **Data Processing**: 1000+ images per batch job

### Scalability Features
- **Horizontal Scaling**: Microservices architecture
- **Cloud Integration**: Supabase auto-scaling
- **Caching**: Redis integration for performance
- **Load Balancing**: Multiple backend instances

## API Documentation

Once the server is running, visit:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`
- OpenAPI JSON: `http://localhost:8000/openapi.json`

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## Support

For support and questions:

- Create an issue on GitHub
- Check the documentation at `/docs`
- Review the troubleshooting guide



### Development Setup
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

### Code Standards
- **Python**: Black formatting, type hints, comprehensive docstrings
- **TypeScript**: ESLint + Prettier, strict mode enabled
- **Testing**: >90% coverage requirement
- **Documentation**: Comprehensive API and user documentation

## 🙏 Acknowledgments

- **SAM Model**: Meta AI's Segment Anything Model for advanced image segmentation
- **XGBoost**: Gradient boosting framework for machine learning
- **OR-Tools**: Google's optimization tools for constraint programming
- **FastAPI**: Modern Python web framework for high-performance APIs
- **React**: Facebook's UI library for responsive web interfaces
- **Supabase**: Open source Firebase alternative for cloud infrastructure



## ⚠️ Disclaimer

This software is provided for engineering analysis purposes. All blast plans must be reviewed and approved by qualified mining engineers before implementation. Users are responsible for ensuring compliance with local regulations and safety standards.

---

**🎯 Ready to revolutionize your mining operations with AI-powered blast design?**

 [Contact Us](mailto:i.jeridi20013@pi.tn)