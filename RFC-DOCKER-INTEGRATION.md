# RFC: Docker Integration for MCPM

## Summary

This RFC proposes adding native Docker integration to MCPM (Model Context Protocol Manager), enabling seamless orchestration between MCP server profiles and Docker Compose services with bidirectional synchronization.

## Motivation

Currently, MCPM excels at managing MCP servers across various clients through profiles and a router system. However, for production deployments, many users need Docker containerization for:

1. **Isolation**: Containerized MCP servers provide better security and resource isolation
2. **Scalability**: Docker Compose enables easy scaling and load balancing
3. **Production Readiness**: Container orchestration with health checks, restart policies, and monitoring
4. **Environment Consistency**: Consistent deployment across development, staging, and production
5. **Dependency Management**: Self-contained environments with all dependencies

This proposal bridges the gap between MCPM's excellent client management and Docker's production deployment capabilities.

## Detailed Design

### 1. New Command Structure

Add a new top-level `docker` command group with subcommands:

```bash
mcpm docker sync PROFILE_NAME     # Sync profile to Docker Compose
mcpm docker status                # Show Docker integration status  
mcpm docker deploy [SERVICES...]  # Deploy Docker services
mcpm docker generate PROFILE_NAME # Generate Docker Compose from profile
```

### 2. Architecture Components

#### A. DockerIntegration Class (`mcpm/commands/docker.py`)
- Main orchestrator for Docker operations
- Manages server-to-Docker mappings
- Handles Docker Compose generation and deployment
- Provides status monitoring

#### B. DockerSyncOperations Class (`mcpm/commands/target_operations/docker_sync.py`)
- Bidirectional sync operations
- Conflict resolution strategies
- Change detection and smart sync
- Integration with existing target operations

#### C. Enhanced Profile Schema
Future enhancement to add Docker metadata to profiles:
```python
class Profile(BaseModel):
    name: str
    api_key: Optional[str]
    servers: list[ServerConfig]
    docker_metadata: Optional[DockerMetadata] = None  # New field

class DockerMetadata(BaseModel):
    compose_file: Optional[str] = "docker-compose.yml"
    auto_deploy: bool = False
    conflict_resolution: str = "profile_wins"
    last_sync_hash: Optional[str] = None
```

### 3. Server Mapping System

#### A. MCP Server → Docker Service Mapping
```python
server_mappings = {
    'postgresql': {
        'image': 'postgres:16-alpine',
        'environment': ['POSTGRES_USER=${POSTGRES_USER:-mcpuser}', ...],
        'ports': ['5432:5432'],
        'volumes': ['postgres-data:/var/lib/postgresql/data'],
        'networks': ['mcp-network'],
        'healthcheck': {...}
    },
    'context7': {...},
    'github': {...},
    'obsidian': {...}
}
```

#### B. Detection Logic
- **Name-based**: Direct matching (postgresql → postgresql service)
- **Package-based**: NPM package detection (@modelcontextprotocol/server-postgres → postgresql)
- **Command-based**: Command line analysis for custom servers

### 4. Bidirectional Sync

#### A. Sync Directions
1. **Profile → Docker**: Generate Docker Compose from MCPM profile
2. **Docker → Profile**: Create/update MCPM profile from Docker services
3. **Bidirectional**: Intelligent sync with conflict resolution

#### B. Conflict Resolution Strategies
- `profile_wins`: MCPM profile takes precedence
- `docker_wins`: Docker Compose takes precedence  
- `manual`: Require manual intervention
- `merge`: Intelligent merging (future enhancement)

#### C. Change Detection
- File hash comparison for Docker Compose files
- Profile modification timestamps
- Service configuration checksums

### 5. Integration Points

#### A. Command Registration
Add to `mcpm/cli.py`:
```python
from mcpm.commands import docker
main.add_command(docker.docker, name="docker")
```

#### B. Target Operations Extension
Extend existing target operations (`add`, `remove`, `transfer`) to optionally sync with Docker:
```bash
mcpm add postgresql --target %production --sync-docker
mcpm rm postgresql --target %production --sync-docker
```

#### C. Router Integration
Future enhancement to add Docker service discovery to the router:
- Health monitoring of containerized servers
- Automatic port mapping
- Load balancing across container replicas

### 6. Docker Compose Structure

Generated Docker Compose files include:

#### A. Standard Networks
```yaml
networks:
  mcp-network:
    driver: bridge
    ipam:
      config:
        - subnet: 10.200.0.0/16
  mcp-management:
    driver: bridge
    ipam:
      config:
        - subnet: 10.201.0.0/16
```

#### B. Service Template
```yaml
services:
  postgresql:
    image: postgres:16-alpine
    container_name: mcp-postgresql
    environment:
      - POSTGRES_USER=${POSTGRES_USER:-mcpuser}
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-password}
      - POSTGRES_DB=${POSTGRES_DB:-mcpdb}
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data
    networks:
      - mcp-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-mcpuser}"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 30s
```

## Implementation Plan

### Phase 1: Core Docker Commands (Week 1-2)
- [x] Implement `DockerIntegration` class
- [x] Add `mcpm docker` command group
- [x] Basic profile → Docker sync
- [x] Docker service status monitoring

### Phase 2: Bidirectional Sync (Week 3-4)  
- [x] Implement `DockerSyncOperations` class
- [x] Docker → profile sync
- [x] Conflict resolution strategies
- [ ] Change detection and smart sync

### Phase 3: Enhanced Integration (Month 2)
- [ ] Extend existing target operations with Docker sync
- [ ] Enhanced profile schema with Docker metadata
- [ ] Router integration for container health monitoring
- [ ] Comprehensive testing and documentation

### Phase 4: Advanced Features (Month 3+)
- [ ] Multi-environment support (dev/staging/prod)
- [ ] Container scaling and load balancing
- [ ] Advanced conflict resolution (merge strategies)
- [ ] Performance monitoring and metrics

## Backward Compatibility

This proposal maintains full backward compatibility:

1. **Existing Profiles**: All current profiles continue to work unchanged
2. **Existing Commands**: No changes to existing command behavior
3. **Optional Feature**: Docker integration is entirely opt-in
4. **Schema Evolution**: Docker metadata is optional and backward-compatible

## Testing Strategy

### Unit Tests
- Server detection and mapping logic
- Docker Compose generation
- Bidirectional sync operations
- Conflict resolution strategies

### Integration Tests
- End-to-end profile → Docker → profile workflows
- Docker deployment and health checks
- Multi-service synchronization
- Error handling and recovery

### Compatibility Tests
- Existing MCPM functionality unchanged
- Various Docker environments (local, remote, CI/CD)
- Different MCP server types and configurations

## Alternatives Considered

### 1. External Tool Approach
**Rejected**: Maintain separate tools for MCPM and Docker
- **Pros**: No changes to MCPM core
- **Cons**: Poor user experience, manual coordination required, configuration drift

### 2. Plugin System
**Future Enhancement**: Implement as MCPM plugin
- **Pros**: Modular, extensible
- **Cons**: Added complexity, plugin infrastructure needed

### 3. Docker-First Approach  
**Rejected**: Make Docker the primary deployment method
- **Pros**: Production-ready by default
- **Cons**: Breaking change, removes client flexibility

## Risks and Mitigations

### Risk 1: Docker Dependency
**Mitigation**: Docker integration is optional, graceful fallback when Docker unavailable

### Risk 2: Configuration Complexity
**Mitigation**: Sensible defaults, comprehensive documentation, example configurations

### Risk 3: Performance Impact
**Mitigation**: Lazy loading, efficient change detection, background operations

### Risk 4: Security Concerns
**Mitigation**: Secure defaults, environment variable handling, container isolation

## Success Metrics

1. **Adoption**: >20% of MCPM users enable Docker integration within 6 months
2. **Reliability**: >99% successful sync operations
3. **Performance**: <2s for typical profile → Docker sync
4. **Community**: Positive feedback, contributions, and documentation improvements

## Conclusion

This Docker integration proposal provides significant value to MCPM users by bridging client management and production deployment. The design maintains backward compatibility while enabling powerful new workflows for containerized MCP server deployments.

The phased implementation allows for iterative development and community feedback, ensuring a robust and well-tested feature that enhances MCPM's production readiness without compromising its core strengths.