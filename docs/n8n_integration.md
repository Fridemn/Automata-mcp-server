# n8n Integration Guide

This guide explains how to integrate Automata MCP Server with n8n.

## Authentication

n8n's MCP client typically uses an Access Token (Bearer Token) for authentication.
Automata MCP Server supports this via the `Authorization` header.

### Configuration

1.  **Set the Access Token**:
    You can configure the access token using the `AUTOMATA_ACCESS_TOKEN` environment variable.

    ```bash
    export AUTOMATA_ACCESS_TOKEN="your-secure-token"
    ```

    Or in your `.env` file:

    ```env
    AUTOMATA_ACCESS_TOKEN=your-secure-token
    ```

2.  **Configure n8n**:
    When adding an MCP Server in n8n:
    -   **Server URL**: `http://<your-server-host>:<port>/sse` (e.g., `http://localhost:8000/sse`)
    -   **Access Token**: Enter the same token you set in `AUTOMATA_ACCESS_TOKEN`.

## Compatibility Changes

The server has been updated to:
-   Accept `Authorization: Bearer <token>` header.
-   Support `AUTOMATA_ACCESS_TOKEN` environment variable.
-   **Swagger UI Support**: You can now use the "Authorize" button in the API documentation (`/docs`) to authenticate with your Access Token.
-   **Note**: `X-API-Key` header and `AUTOMATA_API_KEY` environment variable are no longer supported.

## Troubleshooting

If n8n fails to connect:
-   Ensure the server is running and accessible from n8n.
-   Check the logs for authentication errors.
-   Verify that the token matches exactly.
