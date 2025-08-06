# AI Agent Friendly CLI Implementation Plan for MCPM

## Executive Summary

This document outlines a comprehensive plan to make every MCPM feature accessible via pure parameterized CLI commands, eliminating the need for interactive TUI interfaces when used by AI agents or automation scripts.

## Current State Analysis

### ✅ Already AI-Agent Friendly (70% of commands)
- **Core operations**: `search`, `info`, `ls`, `run`, `doctor`, `usage`
- **Profile operations**: `profile ls`, `profile create`, `profile run`, `profile rm` (with `--force`)
- **Configuration**: `config ls`, `config unset`, `config clear-cache`
- **Client listing**: `client ls`
- **Installation**: `install` (with env vars), `uninstall` (with `--force`)

### ❌ Needs Parameterized Alternatives (30% of commands)
- **Server creation**: `new`, `edit`
- **Configuration**: `config set`
- **Client management**: `client edit`, `client import`
- **Profile management**: `profile edit`, `profile inspect`
- **Migration**: `migrate` (partial)

## Implementation Phases

### Phase 1: Server Management (High Priority)

#### 1.1 `mcpm new` - Non-interactive server creation
**Current**: Interactive form only
```bash
mcpm new  # Prompts for all server details
```

**Proposed**: Full CLI parameter support
```bash
mcpm new <server_name> \
  --type {stdio|remote} \
  --command "python -m server" \
  --args "arg1 arg2" \
  --env "KEY1=value1,KEY2=value2" \
  --url "http://example.com" \
  --headers "Authorization=Bearer token" \
  --force
```

**Implementation Requirements**:
- Add CLI parameters to `src/mcpm/commands/new.py`
- Create parameter validation logic
- Implement non-interactive server creation flow
- Maintain backward compatibility with interactive mode

#### 1.2 `mcpm edit` - Non-interactive server editing
**Current**: Interactive form or external editor
```bash
mcpm edit <server>        # Interactive form
mcpm edit <server> -e     # External editor
```

**Proposed**: Field-specific updates
```bash
mcpm edit <server> --name "new_name"
mcpm edit <server> --command "new command"
mcpm edit <server> --args "new args"
mcpm edit <server> --env "KEY=value"
mcpm edit <server> --url "http://new-url.com"
mcpm edit <server> --headers "Header=Value"
mcpm edit <server> --force
```

**Implementation Requirements**:
- Add field-specific CLI parameters to `src/mcpm/commands/edit.py`
- Create parameter-to-config mapping logic
- Implement selective field updates
- Support multiple field updates in single command

### Phase 2: Profile Management (High Priority)

#### 2.1 `mcpm profile edit` - Non-interactive profile editing
**Current**: Interactive server selection
```bash
mcpm profile edit <profile>  # Interactive checkbox selection
```

**Proposed**: Server management via CLI
```bash
mcpm profile edit <profile> --add-server "server1,server2"
mcpm profile edit <profile> --remove-server "server3,server4"
mcpm profile edit <profile> --set-servers "server1,server2,server5"
mcpm profile edit <profile> --rename "new_profile_name"
mcpm profile edit <profile> --force
```

**Implementation Requirements**:
- Add server management parameters to `src/mcpm/commands/profile/edit.py`
- Create server list parsing utilities
- Implement server validation logic
- Support multiple operations in single command

#### 2.2 `mcpm profile inspect` - Non-interactive profile inspection
**Current**: Interactive server selection
```bash
mcpm profile inspect <profile>  # Interactive server selection
```

**Proposed**: Direct server specification
```bash
mcpm profile inspect <profile> --server "server_name"
mcpm profile inspect <profile> --all-servers
mcpm profile inspect <profile> --port 3000
```

**Implementation Requirements**:
- Add server selection parameters to `src/mcpm/commands/profile/inspect.py`
- Implement direct server targeting
- Support batch inspection of all servers

### Phase 3: Client Management (Medium Priority)

#### 3.1 `mcpm client edit` - Non-interactive client editing
**Current**: Interactive server selection
```bash
mcpm client edit <client>  # Interactive server/profile selection
```

**Proposed**: Server management via CLI
```bash
mcpm client edit <client> --add-server "server1,server2"
mcpm client edit <client> --remove-server "server3,server4"
mcpm client edit <client> --set-servers "server1,server2,server5"
mcpm client edit <client> --add-profile "profile1,profile2"
mcpm client edit <client> --remove-profile "profile3"
mcpm client edit <client> --config-path "/custom/path"
mcpm client edit <client> --force
```

**Implementation Requirements**:
- Add server/profile management parameters to `src/mcpm/commands/client.py`
- Create client configuration update logic
- Support mixed server and profile operations

#### 3.2 `mcpm client import` - Non-interactive client import
**Current**: Interactive server selection
```bash
mcpm client import <client>  # Interactive server selection
```

**Proposed**: Automatic or specified import
```bash
mcpm client import <client> --all
mcpm client import <client> --servers "server1,server2"
mcpm client import <client> --create-profile "imported_profile"
mcpm client import <client> --merge-existing
mcpm client import <client> --force
```

**Implementation Requirements**:
- Add import control parameters to `src/mcpm/commands/client.py`
- Implement automatic import logic
- Support profile creation during import

### Phase 4: Configuration Management (Medium Priority)

#### 4.1 `mcpm config set` - Non-interactive configuration
**Current**: Interactive prompts
```bash
mcpm config set  # Interactive key/value prompts
```

**Proposed**: Direct key-value setting
```bash
mcpm config set <key> <value>
mcpm config set node_executable "/path/to/node"
mcpm config set registry_url "https://custom-registry.com"
mcpm config set analytics_enabled true
mcpm config set --list  # Show available config keys
```

**Implementation Requirements**:
- Add direct key-value parameters to `src/mcpm/commands/config.py`
- Create configuration key validation
- Add configuration key listing functionality

### Phase 5: Migration Enhancement (Low Priority)

#### 5.1 `mcpm migrate` - Enhanced non-interactive migration
**Current**: Interactive choice prompt
```bash
mcpm migrate  # Interactive choice: migrate/start fresh/ignore
```

**Proposed**: Direct migration control
```bash
mcpm migrate --auto-migrate     # Migrate automatically
mcpm migrate --start-fresh      # Start fresh
mcpm migrate --ignore           # Ignore v1 config
mcpm migrate --backup-path "/path/to/backup"
```

**Implementation Requirements**:
- Add migration control parameters to `src/mcpm/commands/migrate.py`
- Implement automatic migration logic
- Add backup functionality

## Technical Implementation Strategy

### 1. Backwards Compatibility
- All existing interactive commands remain unchanged
- New CLI parameters are additive, not replacing
- Interactive mode remains the default when parameters are missing
- Add `--interactive` flag to force interactive mode when needed

### 2. Flag Standards
- `--force` - Skip all confirmations
- `--json` - Machine-readable output where applicable
- `--verbose` - Detailed output for debugging
- `--dry-run` - Preview changes without applying
- `--non-interactive` - Disable all prompts globally

### 3. Parameter Validation
- Comprehensive parameter validation before execution
- Clear error messages for invalid combinations
- Help text updates for all new parameters
- Parameter conflict detection and resolution

### 4. Environment Variable Support
- Extend existing env var pattern to all commands
- `MCPM_FORCE=true` - Global force flag
- `MCPM_NON_INTERACTIVE=true` - Disable all prompts
- `MCPM_JSON_OUTPUT=true` - JSON output by default
- Server-specific env vars for sensitive data

### 5. Output Standardization
- Consistent JSON output format for programmatic use
- Exit codes: 0 (success), 1 (error), 2 (validation error)
- Structured error messages with error codes
- Progress indicators for long-running operations

## Code Structure Changes

### 1. Utility Functions
Create `src/mcpm/utils/non_interactive.py`:
```python
def is_non_interactive() -> bool:
    """Check if running in non-interactive mode."""
    
def parse_key_value_pairs(pairs: str) -> dict:
    """Parse comma-separated key=value pairs."""
    
def parse_server_list(servers: str) -> list:
    """Parse comma-separated server list."""
    
def validate_server_exists(server: str) -> bool:
    """Validate that server exists in global config."""
```

### 2. Command Parameter Enhancement
For each command, add:
- CLI parameter decorators
- Parameter validation functions
- Non-interactive execution paths
- Parameter-to-config mapping logic

### 3. Interactive Detection
Implement detection logic:
- Check for TTY availability
- Check environment variables
- Check for force flags
- Graceful fallback when required parameters are missing

## Testing Strategy

### 1. Unit Tests
- All new CLI parameters
- Parameter validation logic
- Non-interactive execution paths
- Parameter parsing utilities

### 2. Integration Tests
- Full command workflows
- Parameter combination testing
- Error handling scenarios
- Environment variable integration

### 3. AI Agent Tests
- Headless execution scenarios
- Batch operation testing
- Error recovery testing
- Performance benchmarking

### 4. Regression Tests
- Ensure interactive modes still work
- Backward compatibility verification
- Help text accuracy
- Exit code consistency

## Benefits for AI Agents

1. **Predictable Execution**: No interactive prompts to block automation
2. **Scriptable**: All operations can be scripted and automated
3. **Composable**: Commands can be chained and combined
4. **Debuggable**: Verbose output and clear error messages
5. **Stateless**: No dependency on terminal state or user presence
6. **Batch Operations**: Support for multiple operations in single commands
7. **Error Handling**: Structured error responses for programmatic handling

## Success Metrics

- **Coverage**: 100% of MCPM commands have non-interactive alternatives
- **Compatibility**: 100% backward compatibility with existing workflows
- **Performance**: Non-interactive commands execute ≤ 50ms faster than interactive
- **Reliability**: 99.9% success rate for valid parameter combinations
- **Usability**: Clear documentation and help text for all new parameters

## Timeline

- **Phase 1**: Server Management (1-2 weeks)
- **Phase 2**: Profile Management (1-2 weeks)
- **Phase 3**: Client Management (2-3 weeks)
- **Phase 4**: Configuration Management (1 week)
- **Phase 5**: Migration Enhancement (1 week)
- **Testing & Documentation**: 1-2 weeks

**Total Estimated Timeline**: 7-11 weeks

## Implementation Order

1. Create utility functions and infrastructure
2. Implement server management commands (highest impact)
3. Implement profile management commands
4. Implement client management commands
5. Implement configuration management commands
6. Implement migration enhancements
7. Add comprehensive testing
8. Update documentation and help text

This plan transforms MCPM from a user-centric tool with interactive elements into a fully AI-agent-friendly CLI tool while maintaining all existing functionality for human users.