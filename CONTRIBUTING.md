# Contributing to PlexShelf Series Manager

Thank you for your interest in contributing! This document provides guidelines for contributing to the project.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Create a new branch for your feature or bugfix
4. Make your changes
5. Test your changes
6. Submit a pull request

## Development Setup

### Prerequisites

- Python 3.11 or higher
- Docker (for containerized development)
- Git

### Local Development

```bash
# Clone your fork
git clone https://github.com/yourusername/plexshelf-series.git
cd plexshelf-series

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
cd src
python main.py
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to all functions and classes
- Keep functions focused and concise
- Add comments for complex logic

## Testing

Before submitting a pull request:

1. Test all functionality manually
2. Ensure the application starts without errors
3. Test Plex connection and library scanning
4. Test series matching algorithms
5. Verify GUI responsiveness
6. Test Docker build: `docker build -t plexshelf-series .`

## Pull Request Process

1. **Update Documentation**: Update README.md if you add features
2. **Describe Changes**: Provide a clear description of what your PR does
3. **Link Issues**: Reference any related issues
4. **Keep it Focused**: One feature/fix per PR
5. **Test**: Ensure everything works before submitting

## Feature Requests

Have an idea for a new feature? Great! Please:

1. Check if it's already been requested
2. Open an issue with the "enhancement" label
3. Describe the feature and its use case
4. Be open to discussion and feedback

## Bug Reports

Found a bug? Please:

1. Check if it's already been reported
2. Open an issue with the "bug" label
3. Describe the bug, including:
   - Steps to reproduce
   - Expected behavior
   - Actual behavior
   - Environment (OS, Docker version, etc.)
   - Relevant logs

## Areas for Contribution

We'd love help with:

- **UI/UX Improvements**: Making the GUI more intuitive
- **Matching Algorithms**: Improving series detection accuracy
- **Testing**: Adding unit tests and integration tests
- **Documentation**: Improving guides and examples
- **Performance**: Optimizing database queries and matching
- **Features**: See open issues for feature requests

## Code of Conduct

- Be respectful and inclusive
- Welcome newcomers
- Focus on constructive feedback
- Keep discussions professional

## Questions?

Feel free to open an issue for questions or join discussions on existing issues.

Thank you for contributing! 🎉
